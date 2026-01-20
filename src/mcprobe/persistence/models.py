"""Persistence data models.

Defines the structure for test run results to be stored and retrieved.
"""

from datetime import datetime
from typing import Any, TypedDict

from pydantic import BaseModel, Field

from mcprobe.models.conversation import ConversationResult
from mcprobe.models.judgment import JudgmentResult


class TestRunResult(BaseModel):
    """Complete test run result for persistence."""

    run_id: str  # UUID v4
    timestamp: datetime
    scenario_name: str
    scenario_file: str
    scenario_tags: list[str] = Field(default_factory=list)

    # Core results
    conversation_result: ConversationResult
    judgment_result: JudgmentResult

    # Context
    agent_type: str
    duration_seconds: float

    # LLM models used
    judge_model: str
    synthetic_user_model: str
    agent_model: str | None = None  # None for ADK agents that don't expose model name

    # Environment
    mcprobe_version: str
    python_version: str
    git_commit: str | None = None
    git_branch: str | None = None
    ci_environment: dict[str, str] = Field(default_factory=dict)

    # Agent configuration capture (for tracking changes that affect performance)
    agent_system_prompt: str | None = None
    agent_system_prompt_hash: str | None = None  # SHA256 (first 16 chars)
    mcp_tool_schemas: list[dict[str, Any]] = Field(default_factory=list)
    mcp_tool_schemas_hash: str | None = None  # SHA256 (first 16 chars)


class IndexEntry(BaseModel):
    """Entry in the results index for fast lookup."""

    run_id: str
    timestamp: datetime
    scenario_name: str
    scenario_file: str
    passed: bool
    score: float


class ResultIndex(BaseModel):
    """Index of all test run results."""

    entries: list[IndexEntry] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)


class TrendEntry(TypedDict):
    """Type for trend data entries stored in JSON files."""

    run_id: str
    timestamp: str  # ISO format
    passed: bool
    score: float
    duration_seconds: float
    total_tool_calls: int
    total_tokens: int
    turns: int
