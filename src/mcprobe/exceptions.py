"""Custom exception hierarchy for MCProbe.

All exceptions inherit from MCProbeError for easy catching at the top level.
Follows fail-fast principles - errors propagate immediately without fallbacks.
"""


class MCProbeError(Exception):
    """Base exception for all MCProbe errors."""


class ConfigurationError(MCProbeError):
    """Configuration-related errors."""


class ProviderError(MCProbeError):
    """LLM provider errors."""


class ProviderNotFoundError(ProviderError):
    """Requested provider is not registered."""


class ProviderConfigError(ProviderError):
    """Provider configuration is invalid."""


class LLMProviderError(ProviderError):
    """Error during LLM API call."""


class ScenarioError(MCProbeError):
    """Test scenario errors."""


class ScenarioParseError(ScenarioError):
    """Failed to parse scenario YAML."""


class ScenarioValidationError(ScenarioError):
    """Scenario failed validation."""


class OrchestrationError(MCProbeError):
    """Conversation orchestration errors."""


class JudgmentError(MCProbeError):
    """Judgment/evaluation errors."""
