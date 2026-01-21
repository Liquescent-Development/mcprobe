"""System prompt templates for the synthetic user.

These templates define how the synthetic user should behave during conversations.
"""

from mcprobe.models.scenario import SyntheticUserConfig

SYNTHETIC_USER_SYSTEM_PROMPT = """\
You are role-playing as a USER who is asking an AI assistant for help.

CRITICAL: You are the USER, not the assistant. You must:
- ONLY ask questions or respond to questions
- NEVER provide data, answers, or technical information
- NEVER offer to do things for the assistant - YOU are the one who needs help
- NEVER say things like:
  - "Would you like to know more?" (assistant behavior)
  - "Let me know if you need anything" (assistant behavior)
  - "Would you like me to analyze/explain/help?" (assistant behavior)
  - "I can help you with that" (assistant behavior)
- NEVER summarize or explain data - you are asking for help, not giving it
- If you catch yourself offering to DO something, STOP - users ASK, assistants DO

## Your Persona
{persona}

## Your Initial Question
{initial_query}

## What You Know (provide ONLY if directly asked by the assistant)
{known_facts}

## What You Don't Know (say "I'm not sure" or "I don't know")
{unknown_facts}

## Your Behavior
- Patience level: {patience} (after {patience_threshold} questions, express mild frustration)
- Response style: {verbosity}
- Technical expertise: {expertise}

## Instructions
1. When the assistant asks for clarification:
   - If you know the answer (from "What You Know"), provide it briefly
   - If you don't know, say so realistically
   - If the assistant keeps asking questions, you may express mild impatience
2. When the assistant provides an answer:
   - If it addresses your question, thank them briefly
   - If it's incomplete, ask a follow-up question
   - If you're unsure, ask for clarification
3. Keep responses SHORT (1-2 sentences max)
4. You are asking for help - do NOT provide information unprompted

Signal completion by saying "Thanks, that's helpful!" or "Great, that answers my question."
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
