"""Tests for OpenAI-compatible LLM provider."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, SecretStr

from mcprobe.exceptions import LLMProviderError, ProviderConfigError
from mcprobe.models.config import LLMConfig
from mcprobe.providers.base import Message
from mcprobe.providers.factory import ProviderRegistry, create_provider
from mcprobe.providers.openai_compat import OpenAICompatibleProvider


class TestProviderRegistration:
    """Tests for provider registration."""

    def test_provider_registered(self) -> None:
        """Verify 'openai' is in the registry."""
        assert ProviderRegistry.is_registered("openai")
        assert "openai" in ProviderRegistry.list_providers()

    def test_create_provider_returns_openai_provider(self) -> None:
        """Verify create_provider returns OpenAICompatibleProvider instance."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key=SecretStr("test-key"),
        )
        provider = create_provider(config)
        assert isinstance(provider, OpenAICompatibleProvider)


class TestConfiguration:
    """Tests for provider configuration."""

    def test_api_key_from_config(self) -> None:
        """API key provided via LLMConfig.api_key is used."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key=SecretStr("config-api-key"),
        )
        provider = OpenAICompatibleProvider(config)
        # Verify provider was created (key was accepted)
        assert provider._client is not None

    def test_api_key_from_environment(self) -> None:
        """API key resolved from OPENAI_API_KEY env var when not in config."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-api-key"}):
            config = LLMConfig(
                provider="openai",
                model="gpt-4",
            )
            provider = OpenAICompatibleProvider(config)
            assert provider._client is not None

    def test_missing_api_key_raises_error(self) -> None:
        """ProviderConfigError raised when no API key available."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure OPENAI_API_KEY is not set
            os.environ.pop("OPENAI_API_KEY", None)
            config = LLMConfig(
                provider="openai",
                model="gpt-4",
            )
            with pytest.raises(ProviderConfigError) as exc_info:
                OpenAICompatibleProvider(config)
            assert "API key not found" in str(exc_info.value)

    def test_custom_base_url(self) -> None:
        """Custom base_url is passed to OpenAI client."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key=SecretStr("test-key"),
            base_url="http://localhost:8000/v1",
        )
        provider = OpenAICompatibleProvider(config)
        # OpenAI client normalizes URLs and may add trailing slash
        assert str(provider._client.base_url).rstrip("/") == "http://localhost:8000/v1"


class TestMessageConversion:
    """Tests for message conversion."""

    @pytest.fixture
    def provider(self) -> OpenAICompatibleProvider:
        """Create a provider instance for testing."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key=SecretStr("test-key"),
        )
        return OpenAICompatibleProvider(config)

    def test_convert_user_message(self, provider: OpenAICompatibleProvider) -> None:
        """User messages converted correctly."""
        messages = [Message(role="user", content="Hello")]
        result = provider._convert_messages(messages)
        assert result == [{"role": "user", "content": "Hello"}]

    def test_convert_assistant_message(self, provider: OpenAICompatibleProvider) -> None:
        """Assistant messages converted correctly."""
        messages = [Message(role="assistant", content="Hi there!")]
        result = provider._convert_messages(messages)
        assert result == [{"role": "assistant", "content": "Hi there!"}]

    def test_convert_system_message(self, provider: OpenAICompatibleProvider) -> None:
        """System messages converted correctly."""
        messages = [Message(role="system", content="You are helpful.")]
        result = provider._convert_messages(messages)
        assert result == [{"role": "system", "content": "You are helpful."}]

    def test_convert_tool_result_message(self, provider: OpenAICompatibleProvider) -> None:
        """Tool result messages include tool_call_id."""
        messages = [
            Message(
                role="tool",
                content='{"result": "success"}',
                tool_call_id="call_123",
            )
        ]
        result = provider._convert_messages(messages)
        assert result == [
            {
                "role": "tool",
                "content": '{"result": "success"}',
                "tool_call_id": "call_123",
            }
        ]

    def test_convert_assistant_with_tool_calls(
        self, provider: OpenAICompatibleProvider
    ) -> None:
        """Assistant messages with tool calls preserve them."""
        tool_calls = [
            {
                "id": "call_abc",
                "type": "function",
                "function": {"name": "get_weather", "arguments": '{"city": "NYC"}'},
            }
        ]
        messages = [
            Message(
                role="assistant",
                content="",
                tool_calls=tool_calls,
            )
        ]
        result = provider._convert_messages(messages)
        assert result == [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": tool_calls,
            }
        ]


class TestToolHandling:
    """Tests for tool handling."""

    @pytest.fixture
    def provider(self) -> OpenAICompatibleProvider:
        """Create a provider instance for testing."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key=SecretStr("test-key"),
        )
        return OpenAICompatibleProvider(config)

    def test_convert_tools(self, provider: OpenAICompatibleProvider) -> None:
        """Tool definitions converted to OpenAI format."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a city",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                    },
                },
            }
        ]
        result = provider._convert_tools(tools)
        assert result == tools  # OpenAI format is pass-through

    def test_convert_tools_none(self, provider: OpenAICompatibleProvider) -> None:
        """None tools returns None."""
        result = provider._convert_tools(None)
        assert result is None

    def test_extract_tool_calls(self, provider: OpenAICompatibleProvider) -> None:
        """Tool calls extracted from response in correct format."""
        # Create mock tool call objects
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_xyz"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "search"
        mock_tool_call.function.arguments = '{"query": "test"}'

        result = provider._extract_tool_calls([mock_tool_call])
        assert result == [
            {
                "id": "call_xyz",
                "type": "function",
                "function": {
                    "name": "search",
                    "arguments": '{"query": "test"}',
                },
            }
        ]

    def test_no_tool_calls_returns_empty_list(
        self, provider: OpenAICompatibleProvider
    ) -> None:
        """Empty list returned when no tool calls."""
        assert provider._extract_tool_calls(None) == []
        assert provider._extract_tool_calls([]) == []


class TestGenerateMethod:
    """Tests for generate method."""

    @pytest.fixture
    def provider(self) -> OpenAICompatibleProvider:
        """Create a provider instance for testing."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key=SecretStr("test-key"),
        )
        return OpenAICompatibleProvider(config)

    @pytest.fixture
    def mock_response(self) -> MagicMock:
        """Create a mock OpenAI response."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "Hello, I'm an AI assistant!"
        response.choices[0].message.tool_calls = None
        response.choices[0].finish_reason = "stop"
        response.usage.prompt_tokens = 10
        response.usage.completion_tokens = 20
        return response

    @pytest.mark.asyncio
    async def test_generate_returns_llm_response(
        self, provider: OpenAICompatibleProvider, mock_response: MagicMock
    ) -> None:
        """Returns valid LLMResponse object."""
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [Message(role="user", content="Hello")]
        result = await provider.generate(messages)

        assert result.content == "Hello, I'm an AI assistant!"
        assert result.finish_reason == "stop"
        assert result.tool_calls == []

    @pytest.mark.asyncio
    async def test_generate_extracts_content(
        self, provider: OpenAICompatibleProvider, mock_response: MagicMock
    ) -> None:
        """Response content is extracted correctly."""
        mock_response.choices[0].message.content = "Specific content here"
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [Message(role="user", content="Hello")]
        result = await provider.generate(messages)

        assert result.content == "Specific content here"

    @pytest.mark.asyncio
    async def test_generate_extracts_usage(
        self, provider: OpenAICompatibleProvider, mock_response: MagicMock
    ) -> None:
        """Token usage metrics are extracted."""
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [Message(role="user", content="Hello")]
        result = await provider.generate(messages)

        assert result.usage == {"prompt_tokens": 100, "completion_tokens": 50}

    @pytest.mark.asyncio
    async def test_generate_with_tools(
        self, provider: OpenAICompatibleProvider, mock_response: MagicMock
    ) -> None:
        """Tools are passed correctly to API."""
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [Message(role="user", content="Hello")]
        tools = [{"type": "function", "function": {"name": "test"}}]
        await provider.generate(messages, tools=tools)

        # Verify tools were passed to the API
        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["tools"] == tools

    @pytest.mark.asyncio
    async def test_generate_handles_api_error(
        self, provider: OpenAICompatibleProvider
    ) -> None:
        """LLMProviderError raised on API error."""
        provider._client.chat.completions.create = AsyncMock(
            side_effect=Exception("API connection failed")
        )

        messages = [Message(role="user", content="Hello")]
        with pytest.raises(LLMProviderError) as exc_info:
            await provider.generate(messages)
        assert "API connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_with_tool_calls_response(
        self, provider: OpenAICompatibleProvider, mock_response: MagicMock
    ) -> None:
        """Tool calls in response are extracted correctly."""
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "get_data"
        mock_tool_call.function.arguments = '{"id": 1}'

        mock_response.choices[0].message.tool_calls = [mock_tool_call]
        mock_response.choices[0].finish_reason = "tool_calls"
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [Message(role="user", content="Get data for id 1")]
        result = await provider.generate(messages)

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["id"] == "call_123"
        assert result.tool_calls[0]["function"]["name"] == "get_data"
        assert result.finish_reason == "tool_calls"


class SampleResponseSchema(BaseModel):
    """Sample schema for structured output testing."""

    name: str
    value: int


class TestGenerateStructuredMethod:
    """Tests for generate_structured method."""

    @pytest.fixture
    def provider(self) -> OpenAICompatibleProvider:
        """Create a provider instance for testing."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key=SecretStr("test-key"),
        )
        return OpenAICompatibleProvider(config)

    @pytest.fixture
    def mock_response(self) -> MagicMock:
        """Create a mock OpenAI response for structured output."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = '{"name": "test", "value": 42}'
        return response

    @pytest.mark.asyncio
    async def test_generate_structured_returns_model(
        self, provider: OpenAICompatibleProvider, mock_response: MagicMock
    ) -> None:
        """Returns validated Pydantic model."""
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [Message(role="user", content="Generate data")]
        result = await provider.generate_structured(messages, SampleResponseSchema)

        assert isinstance(result, SampleResponseSchema)
        assert result.name == "test"
        assert result.value == 42

    @pytest.mark.asyncio
    async def test_generate_structured_validates_schema(
        self, provider: OpenAICompatibleProvider, mock_response: MagicMock
    ) -> None:
        """Invalid JSON raises error."""
        mock_response.choices[0].message.content = '{"invalid": "data"}'
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [Message(role="user", content="Generate data")]
        with pytest.raises(LLMProviderError) as exc_info:
            await provider.generate_structured(messages, SampleResponseSchema)
        assert "Failed to parse" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_structured_passes_schema_to_api(
        self, provider: OpenAICompatibleProvider, mock_response: MagicMock
    ) -> None:
        """Schema is passed in correct format."""
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [Message(role="user", content="Generate data")]
        await provider.generate_structured(messages, SampleResponseSchema)

        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        assert "response_format" in call_kwargs
        assert call_kwargs["response_format"]["type"] == "json_schema"
        assert call_kwargs["response_format"]["json_schema"]["name"] == "SampleResponseSchema"

    @pytest.mark.asyncio
    async def test_generate_structured_empty_response_raises_error(
        self, provider: OpenAICompatibleProvider, mock_response: MagicMock
    ) -> None:
        """Empty response raises LLMProviderError."""
        mock_response.choices[0].message.content = None
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [Message(role="user", content="Generate data")]
        with pytest.raises(LLMProviderError) as exc_info:
            await provider.generate_structured(messages, SampleResponseSchema)
        assert "empty response" in str(exc_info.value)


class TestProperties:
    """Tests for provider properties."""

    @pytest.fixture
    def provider(self) -> OpenAICompatibleProvider:
        """Create a provider instance for testing."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key=SecretStr("test-key"),
        )
        return OpenAICompatibleProvider(config)

    def test_supports_tools_returns_true(
        self, provider: OpenAICompatibleProvider
    ) -> None:
        """supports_tools returns True."""
        assert provider.supports_tools is True

    def test_supports_structured_output_returns_true(
        self, provider: OpenAICompatibleProvider
    ) -> None:
        """supports_structured_output returns True."""
        assert provider.supports_structured_output is True
