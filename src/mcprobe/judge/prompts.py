"""Prompt templates for the conversation judge.

These templates define how the judge evaluates conversations against test criteria.
"""

from mcprobe.models.conversation import ConversationResult, ConversationTurn
from mcprobe.models.scenario import TestScenario

# Truncation limits for result strings in output
TRANSCRIPT_RESULT_TRUNCATE_LEN = 200
TOOL_CALL_RESULT_TRUNCATE_LEN = 100

JUDGE_EVALUATION_PROMPT = """\
You are evaluating an AI agent's performance on a user assistance task.

## Test Scenario
{scenario_description}

## User's Goal
{user_persona}

## User's Initial Query
{initial_query}

## Conversation Transcript
{conversation_transcript}

## Tool Calls Made
{tool_calls}

## Evaluation Criteria

### Correctness (all must be satisfied for pass)
{correctness_criteria}

### Failure Conditions (any triggered = fail)
{failure_criteria}

### Tool Usage Requirements
Required tools: {required_tools}
Prohibited tools: {prohibited_tools}

### Efficiency Targets
Max tool calls: {max_tool_calls}
Max conversation turns: {max_turns}

## Your Task
Evaluate the conversation and provide your assessment in JSON format:
{{
    "passed": true/false,
    "score": 0.0-1.0,
    "correctness_results": {{"criterion": true/false, ...}},
    "failure_results": {{"criterion": true/false, ...}},
    "tool_usage_results": {{
        "required_tools_used": ["list"],
        "prohibited_tools_used": ["list"],
        "all_required_used": true/false,
        "no_prohibited_used": true/false
    }},
    "efficiency_results": {{
        "tool_calls": number,
        "conversation_turns": number,
        "within_limits": true/false
    }},
    "reasoning": "Brief explanation of your judgment",
    "suggestions": ["Improvement suggestions for the MCP server if applicable"]
}}
"""


def format_conversation_transcript(turns: list[ConversationTurn]) -> str:
    """Format conversation turns into a readable transcript.

    Args:
        turns: List of conversation turns.

    Returns:
        Formatted transcript string.
    """
    lines: list[str] = []
    for turn in turns:
        role = turn.role.upper()
        lines.append(f"[{role}]: {turn.content}")
        if turn.tool_calls:
            for tc in turn.tool_calls:
                lines.append(f"  -> Tool call: {tc.tool_name}({tc.parameters})")
                if tc.error:
                    lines.append(f"     Error: {tc.error}")
                else:
                    result_str = str(tc.result)[:TRANSCRIPT_RESULT_TRUNCATE_LEN]
                    if len(str(tc.result)) > TRANSCRIPT_RESULT_TRUNCATE_LEN:
                        result_str += "..."
                    lines.append(f"     Result: {result_str}")
    return "\n".join(lines)


def format_tool_calls(result: ConversationResult) -> str:
    """Format all tool calls from a conversation.

    Args:
        result: Conversation result containing tool calls.

    Returns:
        Formatted tool calls string.
    """
    if not result.total_tool_calls:
        return "No tool calls were made."

    lines: list[str] = []
    for i, tc in enumerate(result.total_tool_calls, 1):
        lines.append(f"{i}. {tc.tool_name}")
        lines.append(f"   Parameters: {tc.parameters}")
        if tc.error:
            lines.append(f"   Error: {tc.error}")
        else:
            result_str = str(tc.result)[:TOOL_CALL_RESULT_TRUNCATE_LEN]
            if len(str(tc.result)) > TOOL_CALL_RESULT_TRUNCATE_LEN:
                result_str += "..."
            lines.append(f"   Result: {result_str}")
        lines.append(f"   Latency: {tc.latency_ms:.1f}ms")
    return "\n".join(lines)


def format_criteria_list(criteria: list[str]) -> str:
    """Format a list of criteria as bullet points.

    Args:
        criteria: List of criterion strings.

    Returns:
        Formatted bullet list.
    """
    if not criteria:
        return "None specified"
    return "\n".join(f"- {c}" for c in criteria)


def build_judge_prompt(
    scenario: TestScenario,
    result: ConversationResult,
) -> str:
    """Build the evaluation prompt for the judge.

    Args:
        scenario: Test scenario with evaluation criteria.
        result: Conversation result to evaluate.

    Returns:
        Formatted judge prompt string.
    """
    evaluation = scenario.evaluation
    user_config = scenario.synthetic_user

    # Format tool usage info
    required_tools = (
        ", ".join(evaluation.tool_usage.required_tools)
        or "None"
    )
    prohibited_tools = (
        ", ".join(evaluation.tool_usage.prohibited_tools)
        or "None"
    )

    # Format efficiency limits
    max_tool_calls = evaluation.efficiency.max_tool_calls or "No limit"
    max_turns = evaluation.efficiency.max_conversation_turns or "No limit"

    return JUDGE_EVALUATION_PROMPT.format(
        scenario_description=scenario.description,
        user_persona=user_config.persona,
        initial_query=user_config.initial_query,
        conversation_transcript=format_conversation_transcript(result.turns),
        tool_calls=format_tool_calls(result),
        correctness_criteria=format_criteria_list(evaluation.correctness_criteria),
        failure_criteria=format_criteria_list(evaluation.failure_criteria),
        required_tools=required_tools,
        prohibited_tools=prohibited_tools,
        max_tool_calls=max_tool_calls,
        max_turns=max_turns,
    )
