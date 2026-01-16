"""Agent under test interfaces."""

from typing import TYPE_CHECKING

from mcprobe.agents.base import AgentUnderTest
from mcprobe.agents.simple import SimpleLLMAgent

if TYPE_CHECKING:
    from mcprobe.agents.adk import GeminiADKAgent

__all__ = ["AgentUnderTest", "GeminiADKAgent", "SimpleLLMAgent"]


def __getattr__(name: str) -> type:
    """Lazy import for GeminiADKAgent to avoid requiring google-adk."""
    if name == "GeminiADKAgent":
        from mcprobe.agents.adk import GeminiADKAgent  # noqa: PLC0415

        return GeminiADKAgent
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
