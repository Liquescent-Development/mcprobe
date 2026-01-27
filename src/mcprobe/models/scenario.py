"""Test scenario data models.

Defines the structure for test scenario YAML files including synthetic user
configuration and evaluation criteria.
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class PatienceLevel(str, Enum):
    """How patient the synthetic user is with clarifying questions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class VerbosityLevel(str, Enum):
    """How verbose the synthetic user's responses are."""

    CONCISE = "concise"
    MEDIUM = "medium"
    VERBOSE = "verbose"


class ExpertiseLevel(str, Enum):
    """Technical expertise level of the synthetic user."""

    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class UserTraits(BaseModel):
    """Personality traits affecting synthetic user behavior."""

    patience: PatienceLevel = PatienceLevel.MEDIUM
    verbosity: VerbosityLevel = VerbosityLevel.CONCISE
    expertise: ExpertiseLevel = ExpertiseLevel.NOVICE


class ClarificationBehavior(BaseModel):
    """How the synthetic user responds to clarification requests."""

    known_facts: list[str] = Field(default_factory=list)
    unknown_facts: list[str] = Field(default_factory=list)
    traits: UserTraits = Field(default_factory=UserTraits)


class SyntheticUserConfig(BaseModel):
    """Configuration for the synthetic user in a test scenario."""

    persona: str = Field(..., min_length=1)
    initial_query: str = Field(..., min_length=1)
    clarification_behavior: ClarificationBehavior = Field(default_factory=ClarificationBehavior)
    max_turns: int = Field(default=10, ge=1, le=100)


class ToolCallCriterion(BaseModel):
    """Assertions about how a specific tool should be called."""

    tool: str = Field(..., min_length=1)
    assertions: list[str] = Field(default_factory=list)


class ToolUsageConfig(BaseModel):
    """Configuration for expected tool usage in evaluation."""

    required_tools: list[str] = Field(default_factory=list)
    optional_tools: list[str] = Field(default_factory=list)
    prohibited_tools: list[str] = Field(default_factory=list)
    tool_call_criteria: list[ToolCallCriterion] = Field(default_factory=list)


class EfficiencyConfig(BaseModel):
    """Optional efficiency targets for evaluation."""

    max_tool_calls: int | None = None
    max_llm_tokens: int | None = None
    max_conversation_turns: int | None = None


class EvaluationConfig(BaseModel):
    """Configuration for how the conversation is evaluated."""

    correctness_criteria: list[str] = Field(..., min_length=1)
    failure_criteria: list[str] = Field(default_factory=list)
    tool_usage: ToolUsageConfig = Field(default_factory=ToolUsageConfig)
    efficiency: EfficiencyConfig = Field(default_factory=EfficiencyConfig)


class ScenarioLLMOverride(BaseModel):
    """Per-scenario LLM configuration overrides.

    All fields are optional - only set values will override global config.
    """

    model: str | None = None
    temperature: float | None = None
    extra_instructions: str | None = None


class ScenarioConfig(BaseModel):
    """Optional per-scenario configuration overrides."""

    judge: ScenarioLLMOverride | None = None
    synthetic_user: ScenarioLLMOverride | None = None


class TestScenario(BaseModel):
    """Complete test scenario definition."""

    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    skip: bool | str | None = None  # True or reason string to skip this scenario
    synthetic_user: SyntheticUserConfig
    evaluation: EvaluationConfig
    tags: list[str] = Field(default_factory=list)
    config: ScenarioConfig | None = None  # Optional per-scenario overrides

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Validate that scenario name is not just whitespace."""
        if not v.strip():
            msg = "Scenario name cannot be empty or whitespace"
            raise ValueError(msg)
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        """Validate that description is not just whitespace."""
        if not v.strip():
            msg = "Scenario description cannot be empty or whitespace"
            raise ValueError(msg)
        return v.strip()
