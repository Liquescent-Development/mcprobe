"""Tests for Ollama provider error handling."""

from unittest.mock import AsyncMock

import ollama
import pytest

from mcprobe.exceptions import LLMProviderError
from mcprobe.models.config import LLMConfig
from mcprobe.providers.ollama import OllamaProvider


class TestOllamaProviderErrorHandling:
    """Tests for Ollama provider error messages."""

    @pytest.fixture
    def provider(self) -> OllamaProvider:
        """Create a provider with test config."""
        config = LLMConfig(
            provider="ollama",
            model="test-model:latest",
            base_url="http://localhost:11434",
        )
        return OllamaProvider(config)

    @pytest.mark.asyncio
    async def test_model_not_found_error_message(self, provider: OllamaProvider) -> None:
        """Test that model-not-found errors have helpful messages."""
        from mcprobe.providers.base import Message

        # Mock the client to raise a ResponseError with "not found"
        mock_error = ollama.ResponseError("model 'test-model:latest' not found")
        provider._client = AsyncMock()
        provider._client.chat = AsyncMock(side_effect=mock_error)

        messages = [Message(role="user", content="test")]

        with pytest.raises(LLMProviderError) as exc_info:
            await provider.generate(messages)

        error_msg = str(exc_info.value)
        assert "test-model:latest" in error_msg
        assert "not found" in error_msg.lower()
        assert "ollama list" in error_msg
        assert "/api/tags" in error_msg

    @pytest.mark.asyncio
    async def test_other_response_error_preserved(self, provider: OllamaProvider) -> None:
        """Test that other ResponseErrors are passed through."""
        from mcprobe.providers.base import Message

        mock_error = ollama.ResponseError("connection refused")
        provider._client = AsyncMock()
        provider._client.chat = AsyncMock(side_effect=mock_error)

        messages = [Message(role="user", content="test")]

        with pytest.raises(LLMProviderError) as exc_info:
            await provider.generate(messages)

        error_msg = str(exc_info.value)
        assert "Ollama API error" in error_msg
        assert "connection refused" in error_msg

    @pytest.mark.asyncio
    async def test_structured_generation_model_not_found(
        self, provider: OllamaProvider
    ) -> None:
        """Test that generate_structured also has helpful model-not-found errors."""
        from pydantic import BaseModel

        from mcprobe.providers.base import Message

        class TestSchema(BaseModel):
            value: str

        mock_error = ollama.ResponseError("model 'test-model:latest' not found")
        provider._client = AsyncMock()
        provider._client.chat = AsyncMock(side_effect=mock_error)

        messages = [Message(role="user", content="test")]

        with pytest.raises(LLMProviderError) as exc_info:
            await provider.generate_structured(messages, TestSchema)

        error_msg = str(exc_info.value)
        assert "test-model:latest" in error_msg
        assert "not found" in error_msg.lower()
        assert "ollama list" in error_msg
