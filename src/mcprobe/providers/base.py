"""Abstract base class for LLM providers.

Defines the interface that all LLM provider implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from mcprobe.models.config import LLMConfig


class Message(BaseModel):
    """Unified message format for LLM conversations."""

    role: str  # "user", "assistant", "system"
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class LLMResponse(BaseModel):
    """Unified response format from LLM providers."""

    content: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    finish_reason: str
    usage: dict[str, int]  # prompt_tokens, completion_tokens
    raw_response: Any = None  # Provider-specific response for debugging


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, config: LLMConfig) -> None:
        """Initialize the provider with configuration."""
        self._config = config

    @property
    def config(self) -> LLMConfig:
        """Get the provider configuration."""
        return self._config

    @abstractmethod
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
            tools: Optional list of tool definitions for function calling.
            temperature: Override the configured temperature.
            max_tokens: Override the configured max tokens.

        Returns:
            LLMResponse with the generated content and metadata.

        Raises:
            LLMProviderError: If the API call fails.
        """
        ...

    @abstractmethod
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
        ...

    @property
    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether this provider supports tool/function calling."""
        ...

    @property
    @abstractmethod
    def supports_structured_output(self) -> bool:
        """Whether this provider supports structured JSON output."""
        ...
