"""Prompt templates for the conversation judge.

These templates define how the judge evaluates conversations against test criteria.
"""

from mcprobe.models.conversation import ConversationResult, ConversationTurn
from mcprobe.models.scenario import TestScenario, ToolCallCriterion

CRITERIA_CHECK_PROMPT = """\
You are checking whether an AI agent has satisfied the success criteria for a task.

## User's Goal
{user_persona}

## User's Initial Query
{initial_query}

## Correctness Criteria (ALL must be satisfied)
{correctness_criteria}

## Conversation So Far
{conversation_transcript}

## Your Task
Determine if the conversation should END because the user's question has been answered.

CRITICAL - User satisfaction signals completion:
- If the user says "thanks", "that's what I needed", "perfect", "great", etc. → ALL CRITERIA MET
- User satisfaction is the PRIMARY signal - if the user is happy, mark all_criteria_met: true
- Do NOT continue nitpicking criteria if the user has expressed satisfaction

Secondary check (only if user hasn't expressed satisfaction):
- Evaluate if the agent substantively addressed each criterion
- Be reasonable - minor differences in wording or thresholds are OK

IMPORTANT: For correctness_results, use the EXACT criterion text as the key.
Do NOT paraphrase, shorten, or modify the criterion text in any way.

Respond in JSON format:
{{
    "all_criteria_met": true/false,
    "correctness_results": {{"<exact criterion text>": true/false, ...}},
    "brief_reasoning": "One sentence explaining your assessment"
}}
"""

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

### Tool Call Criteria
Evaluate if the actual tool calls satisfy these assertions:
{tool_call_criteria}

### Efficiency Targets
Max tool calls: {max_tool_calls}
Max conversation turns: {max_turns}

## Conversation Quality Analysis
Analyze the conversation flow and provide metrics:
1. How many clarifying questions did the agent ask?
2. Did the conversation backtrack or repeat topics? Count the backtracks.
3. How many turns until the first substantive answer was given?
4. Was the final answer complete? Score from 0.0 to 1.0.

## MCP Server Improvement Suggestions
If there were issues with tool usage, provide structured suggestions categorized by:
- description: Tool description was unclear
- parameter: Parameter documentation was insufficient
- return_value: Return value format/content was problematic
- schema: Schema definition had issues

## Your Task
Evaluate the conversation and provide your assessment in JSON format.

IMPORTANT: For correctness_results and failure_results, use the EXACT criterion text as the key.
Do NOT paraphrase, shorten, or modify the criterion text in any way.

{{
    "passed": true/false,
    "score": 0.0-1.0,
    "correctness_results": {{"<exact criterion text>": true/false, ...}},
    "failure_results": {{"<exact criterion text>": true/false, ...}},
    "tool_usage_results": {{
        "required_tools_used": ["list"],
        "prohibited_tools_used": ["list"],
        "all_required_used": true/false,
        "no_prohibited_used": true/false,
        "criteria_results": {{"tool_name": {{"assertion": true/false, ...}}, ...}}
    }},
    "efficiency_results": {{
        "tool_calls": number,
        "conversation_turns": number,
        "within_limits": true/false
    }},
    "quality_metrics": {{
        "clarification_count": number,
        "backtrack_count": number,
        "turns_to_first_answer": number,
        "final_answer_completeness": 0.0-1.0
    }},
    "reasoning": "Brief explanation of your judgment",
    "suggestions": ["Improvement suggestions for the MCP server if applicable"],
    "structured_suggestions": [
        {{
            "category": "description|parameter|return_value|schema",
            "tool_name": "name or null if general",
            "issue": "What the problem was",
            "suggestion": "How to fix it",
            "severity": "low|medium|high"
        }}
    ]
}}
"""


def format_conversation_transcript(
    turns: list[ConversationTurn],
    truncate_results: int | None = None,
) -> str:
    """Format conversation turns into a readable transcript.

    Args:
        turns: List of conversation turns.
        truncate_results: If set, truncate tool results to this many characters.
            Use None for full results (needed for final evaluation).
            Use a value like 200 for mid-conversation checks where full results
            aren't needed.

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
                    result_str = str(tc.result)
                    if truncate_results and len(result_str) > truncate_results:
                        result_str = result_str[:truncate_results] + "... [truncated]"
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
            lines.append(f"   Result: {tc.result}")
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


def format_tool_call_criteria(criteria: list[ToolCallCriterion]) -> str:
    """Format tool call criteria for the judge prompt.

    Args:
        criteria: List of tool call criteria.

    Returns:
        Formatted tool call criteria string.
    """
    if not criteria:
        return "None specified"

    lines: list[str] = []
    for criterion in criteria:
        lines.append(f"Tool: {criterion.tool}")
        for assertion in criterion.assertions:
            lines.append(f"  - {assertion}")
    return "\n".join(lines)


# Truncation limit for mid-conversation criteria checks
# Full results aren't needed to determine if criteria are met
CRITERIA_CHECK_RESULT_TRUNCATE_LEN = 500


def build_criteria_check_prompt(
    scenario: TestScenario,
    turns: list[ConversationTurn],
) -> str:
    """Build the prompt for checking criteria mid-conversation.

    Args:
        scenario: Test scenario with evaluation criteria.
        turns: Conversation turns so far.

    Returns:
        Formatted criteria check prompt string.
    """
    evaluation = scenario.evaluation
    user_config = scenario.synthetic_user

    # Use truncated tool results for mid-conversation checks
    # The assistant's response text contains the relevant info for criteria
    return CRITERIA_CHECK_PROMPT.format(
        user_persona=user_config.persona,
        initial_query=user_config.initial_query,
        correctness_criteria=format_criteria_list(evaluation.correctness_criteria),
        conversation_transcript=format_conversation_transcript(
            turns, truncate_results=CRITERIA_CHECK_RESULT_TRUNCATE_LEN
        ),
    )


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
    required_tools = ", ".join(evaluation.tool_usage.required_tools) or "None"
    prohibited_tools = ", ".join(evaluation.tool_usage.prohibited_tools) or "None"

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
        tool_call_criteria=format_tool_call_criteria(evaluation.tool_usage.tool_call_criteria),
        max_tool_calls=max_tool_calls,
        max_turns=max_turns,
    )
