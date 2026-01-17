"""OpenAI-compatible LLM provider.

Works with any OpenAI API-compatible endpoint including:
- OpenAI API
- Azure OpenAI
- vLLM
- LiteLLM
- Ollama (OpenAI compatibility mode)
- Any other OpenAI-compatible service
"""

import os
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from mcprobe.exceptions import LLMProviderError, ProviderConfigError
from mcprobe.models.config import LLMConfig
from mcprobe.providers.base import LLMProvider, LLMResponse, Message
from mcprobe.providers.factory import ProviderRegistry

# Default max tokens value from LLMConfig
DEFAULT_MAX_TOKENS = 4096


@ProviderRegistry.register("openai")
class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible provider for LLM inference."""

    def __init__(self, config: LLMConfig) -> None:
        """Initialize the OpenAI-compatible provider.

        Args:
            config: LLM configuration with model, optional base_url, and api_key.

        Raises:
            ProviderConfigError: If no API key is available.
        """
        super().__init__(config)

        # Resolve API key: config takes priority, then environment variable
        api_key: str | None = None
        if config.api_key:
            api_key = config.api_key.get_secret_value()
        else:
            api_key = os.environ.get("OPENAI_API_KEY")

        if not api_key:
            msg = (
                "OpenAI API key not found. Provide via config.api_key "
                "or OPENAI_API_KEY environment variable."
            )
            raise ProviderConfigError(msg)

        # Initialize async client
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url

        self._client = AsyncOpenAI(**client_kwargs)

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert MCProbe messages to OpenAI format.

        Args:
            messages: List of conversation messages.

        Returns:
            List of OpenAI message dictionaries.
        """
        openai_messages: list[dict[str, Any]] = []

        for msg in messages:
            openai_msg: dict[str, Any] = {
                "role": msg.role,
                "content": msg.content,
            }

            # Include tool_call_id for tool result messages
            if msg.tool_call_id:
                openai_msg["tool_call_id"] = msg.tool_call_id

            # Include tool_calls for assistant messages that made tool calls
            if msg.tool_calls:
                openai_msg["tool_calls"] = msg.tool_calls

            openai_messages.append(openai_msg)

        return openai_messages

    def _convert_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        """Convert tool definitions to OpenAI format.

        Args:
            tools: List of tool definitions.

        Returns:
            List of OpenAI tool objects or None.
        """
        if not tools:
            return None

        # OpenAI uses the standard tool format
        return tools

    def _extract_tool_calls(
        self, tool_calls: list[Any] | None
    ) -> list[dict[str, Any]]:
        """Extract tool calls from OpenAI response.

        Args:
            tool_calls: Tool calls from OpenAI response.

        Returns:
            List of tool call dictionaries.
        """
        result: list[dict[str, Any]] = []

        if not tool_calls:
            return result

        for tool_call in tool_calls:
            result.append(
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
            )

        return result

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
        openai_messages = self._convert_messages(messages)
        openai_tools = self._convert_tools(tools)

        # Build request kwargs
        request_kwargs: dict[str, Any] = {
            "model": self._config.model,
            "messages": openai_messages,
        }

        # Set temperature
        if temperature is not None:
            request_kwargs["temperature"] = temperature
        elif self._config.temperature != 0.0:
            request_kwargs["temperature"] = self._config.temperature

        # Set max tokens
        if max_tokens is not None:
            request_kwargs["max_tokens"] = max_tokens
        elif self._config.max_tokens != DEFAULT_MAX_TOKENS:
            request_kwargs["max_tokens"] = self._config.max_tokens

        # Add tools if provided
        if openai_tools:
            request_kwargs["tools"] = openai_tools

        try:
            response = await self._client.chat.completions.create(**request_kwargs)
        except Exception as e:
            msg = f"OpenAI API error: {e}"
            raise LLMProviderError(msg) from e

        # Extract the first choice
        choice = response.choices[0]

        # Extract content
        content = choice.message.content or ""

        # Extract tool calls
        tool_calls = self._extract_tool_calls(choice.message.tool_calls)

        # Determine finish reason
        finish_reason = choice.finish_reason or "stop"

        # Extract usage metrics
        usage: dict[str, int] = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
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
        openai_messages = self._convert_messages(messages)

        # Build request kwargs
        request_kwargs: dict[str, Any] = {
            "model": self._config.model,
            "messages": openai_messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.__name__,
                    "schema": response_schema.model_json_schema(),
                    "strict": True,
                },
            },
        }

        # Set temperature
        if temperature is not None:
            request_kwargs["temperature"] = temperature
        elif self._config.temperature != 0.0:
            request_kwargs["temperature"] = self._config.temperature

        # Set max tokens
        if max_tokens is not None:
            request_kwargs["max_tokens"] = max_tokens
        elif self._config.max_tokens != DEFAULT_MAX_TOKENS:
            request_kwargs["max_tokens"] = self._config.max_tokens

        try:
            response = await self._client.chat.completions.create(**request_kwargs)
        except Exception as e:
            msg = f"OpenAI API error: {e}"
            raise LLMProviderError(msg) from e

        content = response.choices[0].message.content
        if not content:
            msg = "OpenAI returned empty response for structured generation"
            raise LLMProviderError(msg)

        try:
            return response_schema.model_validate_json(content)
        except Exception as e:
            msg = f"Failed to parse OpenAI response as {response_schema.__name__}: {e}"
            raise LLMProviderError(msg) from e

    @property
    def supports_tools(self) -> bool:
        """OpenAI supports tool/function calling."""
        return True

    @property
    def supports_structured_output(self) -> bool:
        """OpenAI supports structured JSON output via response_format."""
        return True
