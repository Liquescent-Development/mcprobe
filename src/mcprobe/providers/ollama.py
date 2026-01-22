"""Ollama LLM provider.

Uses the ollama Python SDK for local model inference.
"""

import json
from typing import Any

import ollama
from pydantic import BaseModel

from mcprobe.exceptions import LLMProviderError
from mcprobe.models.config import LLMConfig
from mcprobe.providers.base import LLMProvider, LLMResponse, Message
from mcprobe.providers.factory import ProviderRegistry

# Default max tokens value from LLMConfig
DEFAULT_MAX_TOKENS = 4096

# Default context size for Ollama (much larger than Ollama's default of 2048)
DEFAULT_CONTEXT_SIZE = 65536

# Valid reasoning levels for Ollama models that support thinking (e.g., gpt-oss)
VALID_REASONING_LEVELS = {"low", "medium", "high"}


@ProviderRegistry.register("ollama")
class OllamaProvider(LLMProvider):
    """Ollama provider for local LLM inference."""

    def __init__(self, config: LLMConfig) -> None:
        """Initialize the Ollama provider.

        Args:
            config: LLM configuration with model and optional base_url.
        """
        super().__init__(config)

        # Initialize async client with optional custom host
        client_kwargs: dict[str, Any] = {}
        if config.base_url:
            client_kwargs["host"] = config.base_url

        self._client = ollama.AsyncClient(**client_kwargs)

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert MCProbe messages to Ollama format.

        Args:
            messages: List of conversation messages.

        Returns:
            List of Ollama message dictionaries.
        """
        ollama_messages: list[dict[str, Any]] = []

        for msg in messages:
            ollama_msg: dict[str, Any] = {
                "role": msg.role,
                "content": msg.content,
            }
            ollama_messages.append(ollama_msg)

        return ollama_messages

    def _convert_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        """Convert tool definitions to Ollama format.

        Args:
            tools: List of tool definitions in OpenAI-like format.

        Returns:
            List of Ollama tool objects or None.
        """
        if not tools:
            return None

        # Ollama uses OpenAI-compatible tool format
        return tools

    def _extract_tool_calls(self, response: ollama.ChatResponse) -> list[dict[str, Any]]:
        """Extract tool calls from Ollama response.

        Args:
            response: Ollama chat response.

        Returns:
            List of tool call dictionaries.
        """
        tool_calls: list[dict[str, Any]] = []

        if not response.message.tool_calls:
            return tool_calls

        for i, tool_call in enumerate(response.message.tool_calls):
            tool_calls.append(
                {
                    "id": f"call_{i}",
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": json.dumps(tool_call.function.arguments),
                    },
                }
            )

        return tool_calls

    async def generate(
        self,
        messages: list[Message],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a completion from messages.

        Args:
            messages: List of conversation messages.
            tools: Optional list of tool definitions.
            temperature: Override the configured temperature.
            max_tokens: Override the configured max tokens.

        Returns:
            LLMResponse with the generated content.

        Raises:
            LLMProviderError: If the API call fails.
        """
        ollama_messages = self._convert_messages(messages)
        ollama_tools = self._convert_tools(tools)

        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        elif self._config.temperature != 0.0:
            options["temperature"] = self._config.temperature

        if max_tokens is not None:
            options["num_predict"] = max_tokens
        elif self._config.max_tokens != DEFAULT_MAX_TOKENS:
            options["num_predict"] = self._config.max_tokens

        # Set context window size (Ollama defaults to only 2048)
        context_size = self._config.context_size or DEFAULT_CONTEXT_SIZE
        options["num_ctx"] = context_size

        # Set reasoning/thinking level if configured (for models like gpt-oss)
        if self._config.reasoning and self._config.reasoning in VALID_REASONING_LEVELS:
            options["think"] = self._config.reasoning

        try:
            response = await self._client.chat(
                model=self._config.model,
                messages=ollama_messages,
                tools=ollama_tools,
                options=options,
            )
        except ollama.ResponseError as e:
            # Parse common Ollama errors for better user feedback
            error_str = str(e)
            if "not found" in error_str.lower():
                msg = (
                    f"Ollama model '{self._config.model}' not found. "
                    f"Check that the model exists on the server "
                    f"(run 'ollama list' or check /api/tags endpoint). "
                    f"Original error: {e}"
                )
            else:
                msg = f"Ollama API error: {e}"
            raise LLMProviderError(msg) from e
        except Exception as e:
            msg = f"Ollama API error: {e}"
            raise LLMProviderError(msg) from e

        # Extract content
        content = response.message.content or ""

        # Extract tool calls
        tool_calls = self._extract_tool_calls(response)

        # Determine finish reason
        finish_reason = "stop"
        if response.done_reason:
            finish_reason = response.done_reason

        # Extract usage metrics
        usage: dict[str, int] = {
            "prompt_tokens": response.prompt_eval_count or 0,
            "completion_tokens": response.eval_count or 0,
        }

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage,
            raw_response=response,
        )

    async def generate_structured(
        self,
        messages: list[Message],
        response_schema: type[BaseModel],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> BaseModel:
        """Generate a structured response matching the schema.

        Args:
            messages: List of conversation messages.
            response_schema: Pydantic model class defining the expected response.
            temperature: Override the configured temperature.
            max_tokens: Override the configured max tokens.

        Returns:
            Instance of response_schema populated with the generated data.

        Raises:
            LLMProviderError: If the API call fails or response doesn't match schema.
        """
        ollama_messages = self._convert_messages(messages)

        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        elif self._config.temperature != 0.0:
            options["temperature"] = self._config.temperature

        if max_tokens is not None:
            options["num_predict"] = max_tokens
        elif self._config.max_tokens != DEFAULT_MAX_TOKENS:
            options["num_predict"] = self._config.max_tokens

        # Set context window size (Ollama defaults to only 2048)
        context_size = self._config.context_size or DEFAULT_CONTEXT_SIZE
        options["num_ctx"] = context_size

        # Set reasoning/thinking level if configured (for models like gpt-oss)
        if self._config.reasoning and self._config.reasoning in VALID_REASONING_LEVELS:
            options["think"] = self._config.reasoning

        try:
            response = await self._client.chat(
                model=self._config.model,
                messages=ollama_messages,
                format=response_schema.model_json_schema(),
                options=options,
            )
        except ollama.ResponseError as e:
            # Parse common Ollama errors for better user feedback
            error_str = str(e)
            if "not found" in error_str.lower():
                msg = (
                    f"Ollama model '{self._config.model}' not found. "
                    f"Check that the model exists on the server "
                    f"(run 'ollama list' or check /api/tags endpoint). "
                    f"Original error: {e}"
                )
            else:
                msg = f"Ollama API error: {e}"
            raise LLMProviderError(msg) from e
        except Exception as e:
            msg = f"Ollama API error: {e}"
            raise LLMProviderError(msg) from e

        content = response.message.content
        if not content:
            msg = "Ollama returned empty response for structured generation"
            raise LLMProviderError(msg)

        try:
            return response_schema.model_validate_json(content)
        except Exception as e:
            msg = f"Failed to parse Ollama response as {response_schema.__name__}: {e}"
            raise LLMProviderError(msg) from e

    @property
    def supports_tools(self) -> bool:
        """Ollama supports tool/function calling for compatible models."""
        return True

    @property
    def supports_structured_output(self) -> bool:
        """Ollama supports structured JSON output via format parameter."""
        return True
