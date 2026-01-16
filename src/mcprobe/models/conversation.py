"""Conversation data models.

Defines the structure for conversation turns, tool calls, and results.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Record of a tool invocation."""

    tool_name: str
    parameters: dict[str, Any]
    result: Any
    latency_ms: float
    error: str | None = None


class AgentResponse(BaseModel):
    """Response from the agent under test."""

    message: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    is_complete: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserResponse(BaseModel):
    """Response from the synthetic user."""

    message: str
    is_satisfied: bool = False
    tokens_used: int = 0


class ConversationTurn(BaseModel):
    """Single turn in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    timestamp: float


class TerminationReason(str, Enum):
    """Reason why a conversation ended."""

    USER_SATISFIED = "user_satisfied"
    MAX_TURNS = "max_turns"
    ERROR = "error"
    LOOP_DETECTED = "loop_detected"


class ConversationResult(BaseModel):
    """Complete result of a conversation run."""

    turns: list[ConversationTurn]
    final_answer: str
    total_tool_calls: list[ToolCall]
    total_tokens: int = 0
    duration_seconds: float
    termination_reason: TerminationReason
