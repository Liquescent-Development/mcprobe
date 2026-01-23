"""Conversation judge implementation.

Evaluates conversation results against test scenario criteria.
"""

from pydantic import BaseModel, Field

from mcprobe.exceptions import JudgmentError
from mcprobe.judge.prompts import build_criteria_check_prompt, build_judge_prompt
from mcprobe.models.conversation import ConversationResult, ConversationTurn
from mcprobe.models.judgment import (
    JudgmentResult,
    MCPSuggestion,
    QualityMetrics,
    SuggestionCategory,
    SuggestionSeverity,
)
from mcprobe.models.scenario import TestScenario
from mcprobe.providers.base import LLMProvider, Message


class JudgeQualityMetrics(BaseModel):
    """Quality metrics from judge evaluation."""

    clarification_count: int = 0
    backtrack_count: int = 0
    turns_to_first_answer: int = 0
    final_answer_completeness: float = 0.0


class JudgeStructuredSuggestion(BaseModel):
    """Structured suggestion from judge evaluation."""

    category: str
    tool_name: str | None = None
    issue: str
    suggestion: str
    severity: str = "medium"


class JudgeEvaluation(BaseModel):
    """Structured output from the judge LLM."""

    passed: bool
    score: float
    correctness_results: dict[str, bool]
    failure_results: dict[str, bool]
    tool_usage_results: dict[str, object]
    efficiency_results: dict[str, object]
    reasoning: str
    suggestions: list[str]
    quality_metrics: JudgeQualityMetrics = Field(default_factory=JudgeQualityMetrics)
    structured_suggestions: list[JudgeStructuredSuggestion] = Field(default_factory=list)


class CriteriaCheckResult(BaseModel):
    """Lightweight result from criteria check - used for mid-conversation evaluation."""

    all_criteria_met: bool
    correctness_results: dict[str, bool]
    brief_reasoning: str


class ConversationJudge:
    """LLM-powered judge for evaluating conversation results.

    Evaluates whether the agent under test successfully helped the user
    according to the test scenario's evaluation criteria.
    """

    def __init__(self, provider: LLMProvider) -> None:
        """Initialize the conversation judge.

        Args:
            provider: LLM provider to use for evaluation.
        """
        self._provider = provider

    async def evaluate(
        self,
        scenario: TestScenario,
        result: ConversationResult,
    ) -> JudgmentResult:
        """Evaluate a conversation result against scenario criteria.

        Args:
            scenario: Test scenario with evaluation criteria.
            result: Conversation result to evaluate.

        Returns:
            JudgmentResult with pass/fail status and detailed evaluation.

        Raises:
            JudgmentError: If evaluation fails.
        """
        prompt = build_judge_prompt(scenario, result)

        try:
            evaluation = await self._provider.generate_structured(
                messages=[Message(role="user", content=prompt)],
                response_schema=JudgeEvaluation,
            )
        except Exception as e:
            msg = f"Judge evaluation failed: {e}"
            raise JudgmentError(msg) from e

        if not isinstance(evaluation, JudgeEvaluation):
            msg = "Judge returned invalid evaluation format"
            raise JudgmentError(msg)

        # Build the judgment result from the evaluation
        return self._build_judgment_result(scenario, result, evaluation)

    def _build_judgment_result(
        self,
        scenario: TestScenario,
        result: ConversationResult,
        evaluation: JudgeEvaluation,
    ) -> JudgmentResult:
        """Build a JudgmentResult from the judge's evaluation.

        Args:
            scenario: Test scenario with evaluation criteria.
            result: Conversation result that was evaluated.
            evaluation: Structured evaluation from the judge LLM.

        Returns:
            Complete judgment result.
        """
        eval_config = scenario.evaluation

        # Extract tool usage details
        tool_usage = evaluation.tool_usage_results
        required_used = tool_usage.get("required_tools_used", [])
        prohibited_used = tool_usage.get("prohibited_tools_used", [])

        # Build tool usage dict for the result
        tool_usage_dict = {
            "required_tools": eval_config.tool_usage.required_tools,
            "required_tools_used": required_used if isinstance(required_used, list) else [],
            "optional_tools": eval_config.tool_usage.optional_tools,
            "prohibited_tools": eval_config.tool_usage.prohibited_tools,
            "prohibited_tools_used": prohibited_used if isinstance(prohibited_used, list) else [],
            "all_required_used": tool_usage.get("all_required_used", False),
            "no_prohibited_used": tool_usage.get("no_prohibited_used", True),
            "criteria_results": tool_usage.get("criteria_results", {}),
        }

        # Build efficiency dict for the result
        efficiency = evaluation.efficiency_results
        efficiency_dict = {
            "total_tool_calls": len(result.total_tool_calls),
            "max_tool_calls": eval_config.efficiency.max_tool_calls,
            "total_turns": len(result.turns),
            "max_turns": eval_config.efficiency.max_conversation_turns,
            "within_limits": efficiency.get("within_limits", True),
            "total_tokens": result.total_tokens,
        }

        # Build quality metrics
        qm = evaluation.quality_metrics
        quality_metrics = QualityMetrics(
            clarification_count=qm.clarification_count,
            backtrack_count=qm.backtrack_count,
            turns_to_first_answer=qm.turns_to_first_answer,
            final_answer_completeness=qm.final_answer_completeness,
        )

        # Build structured suggestions with validated enums
        structured_suggestions = []
        for s in evaluation.structured_suggestions:
            try:
                category = SuggestionCategory(s.category)
            except ValueError:
                category = SuggestionCategory.DESCRIPTION  # Default fallback

            try:
                severity = SuggestionSeverity(s.severity)
            except ValueError:
                severity = SuggestionSeverity.MEDIUM  # Default fallback

            structured_suggestions.append(
                MCPSuggestion(
                    category=category,
                    tool_name=s.tool_name,
                    issue=s.issue,
                    suggestion=s.suggestion,
                    severity=severity,
                )
            )

        return JudgmentResult(
            passed=evaluation.passed,
            score=evaluation.score,
            correctness_results=evaluation.correctness_results,
            failure_results=evaluation.failure_results,
            tool_usage_results=tool_usage_dict,
            efficiency_results=efficiency_dict,
            reasoning=evaluation.reasoning,
            suggestions=evaluation.suggestions,
            quality_metrics=quality_metrics,
            structured_suggestions=structured_suggestions,
        )

    async def check_criteria(
        self,
        scenario: TestScenario,
        turns: list[ConversationTurn],
    ) -> CriteriaCheckResult:
        """Check if correctness criteria are met mid-conversation.

        This is a lightweight evaluation used after each agent turn to determine
        if the conversation can terminate early.

        Args:
            scenario: Test scenario with evaluation criteria.
            turns: Conversation turns so far.

        Returns:
            CriteriaCheckResult with pass/fail status for each criterion.

        Raises:
            JudgmentError: If evaluation fails.
        """
        prompt = build_criteria_check_prompt(scenario, turns)

        try:
            result = await self._provider.generate_structured(
                messages=[Message(role="user", content=prompt)],
                response_schema=CriteriaCheckResult,
            )
        except Exception as e:
            msg = f"Criteria check failed: {e}"
            raise JudgmentError(msg) from e

        if not isinstance(result, CriteriaCheckResult):
            msg = "Judge returned invalid criteria check format"
            raise JudgmentError(msg)

        return result
