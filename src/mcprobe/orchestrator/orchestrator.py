"""Conversation orchestrator implementation.

Coordinates the conversation between the synthetic user and the agent under test.
"""

import time

from mcprobe.agents.base import AgentUnderTest
from mcprobe.exceptions import OrchestrationError
from mcprobe.judge.judge import ConversationJudge
from mcprobe.models.conversation import (
    ConversationResult,
    ConversationTurn,
    TerminationReason,
    ToolCall,
)
from mcprobe.models.judgment import JudgmentResult
from mcprobe.models.scenario import TestScenario
from mcprobe.synthetic_user.user import SyntheticUserLLM


class ConversationOrchestrator:
    """Orchestrates conversations between synthetic users and agents.

    Manages the conversation loop, tracks turns and tool calls,
    and coordinates with the judge for evaluation.
    """

    def __init__(
        self,
        agent: AgentUnderTest,
        synthetic_user: SyntheticUserLLM,
        judge: ConversationJudge,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            agent: Agent under test to converse with.
            synthetic_user: Synthetic user to simulate.
            judge: Judge for evaluating the conversation.
        """
        self._agent = agent
        self._synthetic_user = synthetic_user
        self._judge = judge

    async def run(self, scenario: TestScenario) -> tuple[ConversationResult, JudgmentResult]:
        """Run a complete test scenario.

        Args:
            scenario: Test scenario to execute.

        Returns:
            Tuple of (conversation_result, judgment_result).

        Raises:
            OrchestrationError: If the conversation fails.
        """
        # Reset state
        await self._agent.reset()
        self._synthetic_user.reset()

        # Run conversation
        conversation_result = await self._run_conversation(scenario)

        # Evaluate with judge
        judgment_result = await self._judge.evaluate(scenario, conversation_result)

        return conversation_result, judgment_result

    async def _run_conversation(self, scenario: TestScenario) -> ConversationResult:
        """Run the conversation loop until completion.

        Uses judge-driven termination: after each agent turn, the judge evaluates
        whether the correctness criteria have been met. If so, the conversation
        terminates early. Otherwise, the synthetic user generates a follow-up.

        Args:
            scenario: Test scenario with configuration.

        Returns:
            ConversationResult with all turns and tool calls.

        Raises:
            OrchestrationError: If the conversation fails.
        """
        start_time = time.time()
        turns: list[ConversationTurn] = []
        all_tool_calls: list[ToolCall] = []
        total_tokens = 0
        max_turns = scenario.synthetic_user.max_turns
        termination_reason = TerminationReason.MAX_TURNS
        final_answer = ""

        # Get initial query from synthetic user
        initial_query = await self._synthetic_user.get_initial_query()

        # Add user turn for initial query
        turns.append(
            ConversationTurn(
                role="user",
                content=initial_query,
                tool_calls=[],
                timestamp=time.time(),
            )
        )

        current_user_message = initial_query
        turn_count = 0

        while turn_count < max_turns:
            turn_count += 1

            # Get response from agent
            try:
                agent_response = await self._agent.send_message(current_user_message)
            except Exception as e:
                msg = f"Agent failed to respond: {e}"
                raise OrchestrationError(msg) from e

            # Record agent turn
            turns.append(
                ConversationTurn(
                    role="assistant",
                    content=agent_response.message,
                    tool_calls=agent_response.tool_calls,
                    timestamp=time.time(),
                )
            )

            # Track all tool calls
            all_tool_calls.extend(agent_response.tool_calls)

            # Check criteria with judge after each agent turn
            try:
                criteria_result = await self._judge.check_criteria(scenario, turns)
            except Exception as e:
                msg = f"Judge criteria check failed: {e}"
                raise OrchestrationError(msg) from e

            # If all criteria are met, terminate successfully
            if criteria_result.all_criteria_met:
                final_answer = agent_response.message
                termination_reason = TerminationReason.CRITERIA_MET
                break

            # Criteria not yet met - get follow-up from synthetic user
            try:
                user_response = await self._synthetic_user.respond(agent_response.message)
            except Exception as e:
                msg = f"Synthetic user failed to respond: {e}"
                raise OrchestrationError(msg) from e

            # Aggregate token usage from synthetic user
            total_tokens += user_response.tokens_used

            # Record user turn and continue
            turns.append(
                ConversationTurn(
                    role="user",
                    content=user_response.message,
                    tool_calls=[],
                    timestamp=time.time(),
                )
            )
            current_user_message = user_response.message

            # Check for potential loops (user repeating same message)
            if self._detect_loop(turns):
                termination_reason = TerminationReason.LOOP_DETECTED
                final_answer = agent_response.message
                break

        # If we hit max turns without criteria being met
        if termination_reason == TerminationReason.MAX_TURNS and turns:
            # Find the last assistant message for final_answer
            for turn in reversed(turns):
                if turn.role == "assistant":
                    final_answer = turn.content
                    break

        duration = time.time() - start_time

        return ConversationResult(
            turns=turns,
            final_answer=final_answer,
            total_tool_calls=all_tool_calls,
            total_tokens=total_tokens,
            duration_seconds=duration,
            termination_reason=termination_reason,
        )

    def _detect_loop(self, turns: list[ConversationTurn]) -> bool:
        """Detect if the conversation is stuck in a loop.

        Args:
            turns: List of conversation turns.

        Returns:
            True if a loop is detected.
        """
        min_turns_for_loop = 4
        if len(turns) < min_turns_for_loop:
            return False

        # Get last N user messages
        loop_detection_window = 3
        user_messages = [t.content for t in turns if t.role == "user"]

        if len(user_messages) < loop_detection_window:
            return False

        recent_messages = user_messages[-loop_detection_window:]

        # Check if all recent user messages are identical
        return len(set(recent_messages)) == 1
