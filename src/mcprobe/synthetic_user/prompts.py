"""System prompt templates for the synthetic user.

These templates define how the synthetic user should behave during conversations.
"""

from mcprobe.models.scenario import SyntheticUserConfig

SYNTHETIC_USER_SYSTEM_PROMPT = """\
Your task is to simulate a realistic USER who is asking an AI assistant for help.
Generate responses as the user would respond - asking questions, providing clarifications,
and expressing satisfaction or follow-up needs.

CRITICAL: Generate USER responses, not assistant responses. Users:
- ASK questions and REQUEST help
- PROVIDE clarifications when asked
- EXPRESS thanks when satisfied
- NEVER offer to do things - users need help, they don't offer it
- NEVER say things like:
  - "Would you like to know more?" (that's what assistants say)
  - "Let me know if you need anything" (that's what assistants say)
  - "Would you like me to analyze/explain/help?" (that's what assistants say)
  - "I can help you with that" (that's what assistants say)
- NEVER summarize or explain data - users ask for explanations, not give them
- Remember: Users ASK, assistants DO

## The User's Persona
{persona}

## The User's Initial Question
{initial_query}

## What The User Knows (provide ONLY if directly asked by the assistant)
{known_facts}

## What The User Doesn't Know (say "I'm not sure" or "I don't know")
{unknown_facts}

## The User's Behavior
- Patience level: {patience} (after {patience_threshold} questions, express mild frustration)
- Response style: {verbosity}
- Technical expertise: {expertise}

## How To Generate User Responses
1. When the assistant asks for clarification:
   - If the user knows the answer (from "What The User Knows"), provide it briefly
   - If the user doesn't know, say so realistically
   - If the assistant keeps asking questions, the user may express mild impatience
2. When the assistant provides an answer:
   - If it addresses the question, thank them briefly
   - If it's incomplete, ask a follow-up question
   - If unclear, ask for clarification
3. Keep responses SHORT (1-2 sentences max)
4. The user is asking for help - do NOT provide information unprompted

Signal completion by generating "Thanks, that's helpful!" or "Great, that answers my question."
"""

SATISFACTION_CHECK_PROMPT = """\
You are evaluating whether a simulated user would be satisfied with the response.

## User's Goal
{persona}

## User's Original Question
{initial_query}

## Assistant's Response
{assistant_response}

## Task
Determine if this response adequately addresses the user's question. Consider:
- Does it answer the core question?
- Is the information useful and actionable?
- Would a real user feel their question was answered?

Respond with a JSON object:
{{"is_satisfied": true/false, "reason": "brief explanation"}}
"""

# Patience thresholds by level
PATIENCE_THRESHOLDS = {
    "low": 1,
    "medium": 3,
    "high": 5,
}


def build_synthetic_user_prompt(config: SyntheticUserConfig) -> str:
    """Build the system prompt for the synthetic user.

    Args:
        config: Synthetic user configuration from the scenario.

    Returns:
        Formatted system prompt string.
    """
    behavior = config.clarification_behavior
    traits = behavior.traits

    known_facts_str = "\n".join(f"- {fact}" for fact in behavior.known_facts) or "None specified"
    unknown_facts_str = (
        "\n".join(f"- {fact}" for fact in behavior.unknown_facts) or "None specified"
    )

    patience_threshold = PATIENCE_THRESHOLDS.get(traits.patience.value, 3)

    return SYNTHETIC_USER_SYSTEM_PROMPT.format(
        persona=config.persona,
        initial_query=config.initial_query,
        known_facts=known_facts_str,
        unknown_facts=unknown_facts_str,
        patience=traits.patience.value,
        patience_threshold=patience_threshold,
        verbosity=traits.verbosity.value,
        expertise=traits.expertise.value,
    )


def build_satisfaction_check_prompt(
    *,
    persona: str,
    initial_query: str,
    assistant_response: str,
) -> str:
    """Build the prompt for checking user satisfaction.

    Args:
        persona: Description of the user's persona.
        initial_query: The user's initial question.
        assistant_response: The assistant's response to evaluate.

    Returns:
        Formatted satisfaction check prompt.
    """
    return SATISFACTION_CHECK_PROMPT.format(
        persona=persona,
        initial_query=initial_query,
        assistant_response=assistant_response,
    )
