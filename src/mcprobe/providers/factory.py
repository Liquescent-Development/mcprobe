"""Provider factory and registry.

Provides decorator-based registration and factory functions for LLM providers.
"""

from collections.abc import Callable
from typing import ClassVar

from mcprobe.exceptions import ProviderConfigError, ProviderNotFoundError
from mcprobe.models.config import LLMConfig
from mcprobe.providers.base import LLMProvider


class ProviderRegistry:
    """Registry of available LLM providers."""

    _providers: ClassVar[dict[str, type[LLMProvider]]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[type[LLMProvider]], type[LLMProvider]]:
        """Decorator to register a provider.

        Args:
            name: The name to register the provider under (e.g., "gemini", "ollama").

        Returns:
            Decorator function that registers the provider class.

        Example:
            @ProviderRegistry.register("gemini")
            class GeminiProvider(LLMProvider):
                ...
        """

        def decorator(provider_class: type[LLMProvider]) -> type[LLMProvider]:
            cls._providers[name.lower()] = provider_class
            return provider_class

        return decorator

    @classmethod
    def get(cls, name: str) -> type[LLMProvider]:
        """Get a provider class by name.

        Args:
            name: The registered name of the provider.

        Returns:
            The provider class.

        Raises:
            ProviderNotFoundError: If the provider is not registered.
        """
        provider = cls._providers.get(name.lower())
        if provider is None:
            available = ", ".join(sorted(cls._providers.keys()))
            msg = f"Provider '{name}' not found. Available: {available or 'none'}"
            raise ProviderNotFoundError(msg)
        return provider

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names.

        Returns:
            Sorted list of registered provider names.
        """
        return sorted(cls._providers.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a provider is registered.

        Args:
            name: The name to check.

        Returns:
            True if the provider is registered.
        """
        return name.lower() in cls._providers


def create_provider(config: LLMConfig) -> LLMProvider:
    """Factory function to create a provider instance from config.

    Args:
        config: LLM configuration specifying the provider and settings.

    Returns:
        Configured LLMProvider instance.

    Raises:
        ProviderNotFoundError: If the provider is not registered.
        ProviderConfigError: If provider instantiation fails.
    """
    provider_class = ProviderRegistry.get(config.provider)
    try:
        return provider_class(config)
    except Exception as e:
        msg = f"Failed to create provider '{config.provider}': {e}"
        raise ProviderConfigError(msg) from e
