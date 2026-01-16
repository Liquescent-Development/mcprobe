"""Configuration data models.

Defines the structure for MCProbe configuration including LLM provider settings.
"""

from pydantic import BaseModel, Field, SecretStr


class LLMConfig(BaseModel):
    """Configuration for an LLM provider."""

    provider: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)
    api_key: SecretStr | None = None
    base_url: str | None = None


class OrchestratorConfig(BaseModel):
    """Configuration for the conversation orchestrator."""

    max_turns: int = Field(default=10, ge=1)
    turn_timeout_seconds: float = Field(default=30.0, gt=0)
    loop_detection_threshold: int = Field(default=3, ge=2)


class MCProbeConfig(BaseModel):
    """Global configuration for MCProbe."""

    agent: LLMConfig
    synthetic_user: LLMConfig
    judge: LLMConfig
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
