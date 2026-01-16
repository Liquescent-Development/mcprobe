# MCProbe a Conversational MCP Tester

> A testing framework that validates MCP servers provide sufficient information for LLM agents to answer real-world questions correctly, using synthetic users and LLM judges.

## Problem Statement

MCP servers expose tools with schemas and descriptions, but there's no systematic way to verify that:

1. Tool descriptions are clear enough for an LLM to understand when to use them
2. Parameter schemas provide sufficient guidance for correct invocation
3. Return values contain enough information to formulate correct answers
4. The combination of available tools can solve realistic user problems
5. Edge cases (ambiguous queries, missing data) are handled gracefully

Current testing approaches either:
- Test tools in isolation (unit tests) without validating LLM comprehension
- Use canned responses that don't adapt to clarification requests
- Benchmark LLM capabilities rather than MCP server quality

## Solution Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                MCprobe                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐   │
│  │   Test       │    │  Synthetic   │    │   System Under Test      │   │
│  │   Scenario   │───▶│  User LLM    │◀──▶│   (Agent + MCP Server)   │   │
│  │   (YAML)     │    │              │    │                          │   │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘   │
│         │                   │                        │                  │
│         │                   │                        │                  │
│         ▼                   ▼                        ▼                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      Conversation Log                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                    │
│                                    ▼                                    │
│                         ┌──────────────────┐                            │
│                         │    Judge LLM     │                            │
│                         │                  │                            │
│                         │  • Correctness   │                            │
│                         │  • Tool Usage    │                            │
│                         │  • Efficiency    │                            │
│                         └──────────────────┘                            │
│                                    │                                    │
│                                    ▼                                    │
│                         ┌──────────────────┐                            │
│                         │   Test Report    │                            │
│                         └──────────────────┘                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Test Scenario Definition

Test scenarios are defined in YAML and describe what the synthetic user wants to accomplish, how they should behave, and what constitutes success.

```yaml
# test-scenarios/weather-planning.yaml
name: "Trip weather planning"
description: "User planning a trip needs weather forecasts for multiple cities"

synthetic_user:
  persona: |
    You are planning a road trip from Phoenix to San Francisco next week.
    You want to know what weather to expect along the route.
    You're flexible on exact dates but need to travel sometime in the next 7 days.
  
  initial_query: "What's the weather going to be like for a road trip from Phoenix to SF?"
  
  # How the synthetic user should respond to clarification requests
  clarification_behavior:
    # Information the user knows and can provide if asked
    known_facts:
      - "Leaving from Phoenix, Arizona"
      - "Destination is San Francisco"
      - "Flexible on dates within the next 7 days"
      - "Will be driving, takes about 10-12 hours"
      - "Prefer to avoid rain if possible"
    
    # Information the user doesn't know (should say "I don't know")
    unknown_facts:
      - "Exact route preferences"
      - "Specific times of day for travel"
    
    # Personality traits affecting responses
    traits:
      patience: "medium"  # Will answer 2-3 clarifying questions before getting frustrated
      verbosity: "concise"  # Gives brief answers unless asked for details
      expertise: "novice"  # Doesn't know technical weather terminology

  # Maximum conversation turns before timeout
  max_turns: 10

# What makes this test pass or fail
evaluation:
  # Required elements in the final answer
  correctness_criteria:
    - "Provides weather forecast for Phoenix area"
    - "Provides weather forecast for San Francisco area"
    - "Mentions temperature ranges"
    - "Mentions precipitation likelihood"
    - "Covers multiple days (not just today)"
  
  # Things that should NOT happen
  failure_criteria:
    - "Provides weather for wrong cities"
    - "Only provides current weather, not forecast"
    - "Makes up specific numbers without using weather tools"
    - "Asks more than 3 clarifying questions"
    - "Gets stuck in a loop"
  
  # Tool usage expectations
  tool_usage:
    required_tools:
      - "get_weather_forecast"  # Must use this tool
    optional_tools:
      - "get_current_weather"
      - "get_location_coordinates"
    prohibited_tools: []
    
    # Expectations about how tools are called
    tool_call_criteria:
      - tool: "get_weather_forecast"
        assertions:
          - "location parameter includes 'Phoenix' or coordinates near Phoenix"
          - "location parameter includes 'San Francisco' or coordinates near SF"
          - "forecast_days >= 3"
  
  # Efficiency scoring (optional)
  efficiency:
    max_tool_calls: 6
    max_llm_tokens: 4000
    max_conversation_turns: 5
```

### 2. Synthetic User LLM

The synthetic user simulates a real person interacting with the agent. Unlike canned responses, it:
- Responds naturally to unexpected clarification requests
- Maintains persona consistency throughout the conversation
- Knows when to say "I don't know" vs provide information
- Can express frustration if the agent asks too many questions
- Recognizes when to accept an answer as complete

**System Prompt Template:**

```
You are simulating a user interacting with an AI assistant. Your goal is to get 
help with a specific task while behaving like a realistic human user.

## Your Persona
{persona}

## Your Initial Question
{initial_query}

## What You Know (provide if asked)
{known_facts}

## What You Don't Know (say "I'm not sure" or "I don't know")
{unknown_facts}

## Your Behavior
- Patience level: {patience} (after {patience_threshold} clarifying questions, 
  express mild frustration)
- Response style: {verbosity}
- Technical expertise: {expertise}

## Instructions
1. Start by asking your initial question
2. When the assistant asks for clarification:
   - If you know the answer (from "What You Know"), provide it naturally
   - If you don't know, say so realistically
   - If the assistant keeps asking questions, you may express mild impatience
3. When the assistant provides an answer:
   - If it seems to address your question, thank them and indicate you're satisfied
   - If it's incomplete or wrong, ask follow-up questions
   - If you're unsure, ask for clarification
4. Never break character or reveal you're a synthetic user
5. Respond conversationally, not in bullet points

Signal completion by saying something like "Thanks, that's helpful!" or 
"Great, that answers my question."
```

### 3. System Under Test Interface

The framework needs a standard interface to interact with any agent + MCP server combination:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class ToolCall:
    """Record of a tool invocation"""
    tool_name: str
    parameters: dict[str, Any]
    result: Any
    latency_ms: float
    error: Optional[str] = None

@dataclass
class AgentResponse:
    """Response from the agent"""
    message: str
    tool_calls: List[ToolCall]
    is_complete: bool  # Agent believes conversation is done
    metadata: dict[str, Any] = None

class AgentUnderTest(ABC):
    """Interface that test subjects must implement"""
    
    @abstractmethod
    async def send_message(self, message: str) -> AgentResponse:
        """Send a user message and get the agent's response"""
        pass
    
    @abstractmethod
    async def reset(self) -> None:
        """Reset conversation state for a new test"""
        pass
    
    @abstractmethod
    def get_available_tools(self) -> List[dict]:
        """Return MCP tool schemas for analysis"""
        pass

# Example implementation for a generic MCP client
class MCPAgentUnderTest(AgentUnderTest):
    def __init__(
        self,
        mcp_server_command: str,
        llm_provider: str = "google",
        llm_model: str = "gemini-2.5-pro",
        system_prompt: Optional[str] = None
    ):
        self.mcp_server_command = mcp_server_command
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.system_prompt = system_prompt or self._default_system_prompt()
        self._conversation_history = []
        self._mcp_client = None
    
    async def send_message(self, message: str) -> AgentResponse:
        # Implementation connects to MCP server, sends to LLM with tools,
        # executes any tool calls, and returns the response
        ...
```

### 4. Conversation Orchestrator

Manages the back-and-forth between synthetic user and system under test:

```python
@dataclass
class ConversationTurn:
    role: str  # "user" or "assistant"
    content: str
    tool_calls: List[ToolCall]
    timestamp: float

@dataclass 
class ConversationResult:
    turns: List[ConversationTurn]
    final_answer: str
    total_tool_calls: List[ToolCall]
    total_tokens: int
    duration_seconds: float
    termination_reason: str  # "user_satisfied", "max_turns", "error", "loop_detected"

class ConversationOrchestrator:
    def __init__(
        self,
        synthetic_user: SyntheticUserLLM,
        agent_under_test: AgentUnderTest,
        max_turns: int = 10,
        loop_detection_threshold: int = 3
    ):
        self.synthetic_user = synthetic_user
        self.agent = agent_under_test
        self.max_turns = max_turns
        self.loop_threshold = loop_detection_threshold
    
    async def run_conversation(self) -> ConversationResult:
        turns = []
        
        # Get initial query from synthetic user
        user_message = await self.synthetic_user.get_initial_query()
        
        for turn_num in range(self.max_turns):
            # Send to agent
            agent_response = await self.agent.send_message(user_message)
            turns.append(ConversationTurn(
                role="assistant",
                content=agent_response.message,
                tool_calls=agent_response.tool_calls,
                timestamp=time.time()
            ))
            
            # Check if agent thinks we're done
            if agent_response.is_complete:
                # Let synthetic user confirm
                user_response = await self.synthetic_user.respond(
                    agent_response.message,
                    is_final_answer=True
                )
                turns.append(ConversationTurn(
                    role="user",
                    content=user_response.message,
                    tool_calls=[],
                    timestamp=time.time()
                ))
                
                if user_response.is_satisfied:
                    return self._build_result(turns, "user_satisfied")
            
            # Check for conversation loops
            if self._detect_loop(turns):
                return self._build_result(turns, "loop_detected")
            
            # Get synthetic user's response
            user_response = await self.synthetic_user.respond(agent_response.message)
            turns.append(ConversationTurn(
                role="user",
                content=user_response.message,
                tool_calls=[],
                timestamp=time.time()
            ))
            user_message = user_response.message
        
        return self._build_result(turns, "max_turns")
```

### 5. Judge LLM

Evaluates the conversation against the test criteria:

```python
@dataclass
class JudgmentResult:
    passed: bool
    score: float  # 0.0 to 1.0
    correctness_results: dict[str, bool]  # criterion -> passed
    failure_results: dict[str, bool]  # criterion -> triggered
    tool_usage_results: dict[str, Any]
    efficiency_results: dict[str, Any]
    reasoning: str  # Judge's explanation
    suggestions: List[str]  # Improvements for the MCP server

class ConversationJudge:
    def __init__(
        self,
        llm_provider: str = "ollama",
        llm_model: str = "gpt-oss"
    ):
        self.llm = self._init_llm(llm_provider, llm_model)
    
    async def evaluate(
        self,
        scenario: TestScenario,
        conversation: ConversationResult
    ) -> JudgmentResult:
        
        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(scenario, conversation)
        
        # Get structured judgment
        response = await self.llm.generate(
            prompt,
            response_format=JudgmentResponseSchema
        )
        
        return self._parse_judgment(response, scenario, conversation)
    
    def _build_evaluation_prompt(
        self,
        scenario: TestScenario,
        conversation: ConversationResult
    ) -> str:
        return f"""
You are evaluating an AI agent's performance on a user assistance task.

## Test Scenario
{scenario.description}

## User's Goal
{scenario.synthetic_user.persona}
Initial query: "{scenario.synthetic_user.initial_query}"

## Conversation Transcript
{self._format_conversation(conversation)}

## Tool Calls Made
{self._format_tool_calls(conversation.total_tool_calls)}

## Evaluation Criteria

### Correctness (all must be satisfied for pass)
{self._format_criteria(scenario.evaluation.correctness_criteria)}

### Failure Conditions (any triggered = fail)
{self._format_criteria(scenario.evaluation.failure_criteria)}

### Tool Usage Requirements
Required tools: {scenario.evaluation.tool_usage.required_tools}
Prohibited tools: {scenario.evaluation.tool_usage.prohibited_tools}
Tool call assertions:
{self._format_tool_assertions(scenario.evaluation.tool_usage.tool_call_criteria)}

### Efficiency Targets (optional)
Max tool calls: {scenario.evaluation.efficiency.max_tool_calls}
Max conversation turns: {scenario.evaluation.efficiency.max_conversation_turns}

## Your Task
Evaluate the conversation and provide:
1. For each correctness criterion: did the final answer satisfy it? (true/false with brief reason)
2. For each failure condition: was it triggered? (true/false with brief reason)
3. Tool usage assessment: were required tools used correctly? Any prohibited tools used?
4. Overall pass/fail determination
5. Suggestions for improving the MCP server's tool descriptions or schemas if the agent struggled

Respond in the specified JSON format.
"""
```

### 6. Test Runner & Reporter

Integrates with standard test frameworks:

```python
# pytest integration
import pytest
from mcp_tester import MCPTestSuite, TestScenario

class TestWeatherMCPServer:
    @pytest.fixture
    def mcp_agent(self):
        return MCPAgentUnderTest(
            mcp_server_command="npx weather-mcp-server",
            llm_model="claude-sonnet-4-20250514"
        )
    
    @pytest.fixture
    def test_suite(self):
        return MCPTestSuite.from_directory("./test-scenarios/weather/")
    
    @pytest.mark.asyncio
    async def test_weather_scenarios(self, mcp_agent, test_suite):
        results = await test_suite.run(mcp_agent)
        
        for scenario_name, result in results.items():
            assert result.judgment.passed, (
                f"Scenario '{scenario_name}' failed: {result.judgment.reasoning}"
            )
    
    @pytest.mark.asyncio
    async def test_single_scenario(self, mcp_agent):
        scenario = TestScenario.from_file("./test-scenarios/weather/trip-planning.yaml")
        result = await scenario.run(mcp_agent)
        
        assert result.judgment.passed
        assert result.judgment.score >= 0.8
        assert "get_weather_forecast" in [
            tc.tool_name for tc in result.conversation.total_tool_calls
        ]
```

**CLI Interface:**

```bash
# Run all scenarios against an MCP server
mcp-tester run \
  --server "npx @example/weather-mcp" \
  --scenarios ./test-scenarios/ \
  --output ./results/ \
  --format html,json,junit

# Run with specific LLM configuration
mcp-tester run \
  --server "python my_mcp_server.py" \
  --scenarios ./scenarios/ \
  --agent-model claude-sonnet-4-20250514 \
  --user-model gpt-4o-mini \
  --judge-model claude-sonnet-4-20250514

# Generate scenario suggestions from MCP server introspection
mcp-tester generate-scenarios \
  --server "npx @example/weather-mcp" \
  --output ./generated-scenarios/ \
  --complexity medium \
  --count 10

# Analyze MCP server tool quality
mcp-tester analyze \
  --server "npx @example/weather-mcp" \
  --output ./analysis-report.md
```

## Test Scenario Categories

The framework should support different types of tests:

### 1. Happy Path Tests
User has a clear question, provides all needed information upfront.
Tests that tools work correctly when used as intended.

### 2. Clarification Tests  
User's initial query is ambiguous. Tests that:
- Agent recognizes ambiguity
- Asks appropriate clarifying questions
- Correctly uses clarified information

### 3. Edge Case Tests
- Missing data from tools
- Tool errors/timeouts
- Conflicting information from multiple tools
- User provides incorrect information

### 4. Adversarial Tests
- User gives contradictory information
- User changes requirements mid-conversation
- Extremely vague initial queries

### 5. Efficiency Tests
Same scenario run multiple times with scoring on:
- Number of tool calls
- Token usage
- Conversation length
- Time to resolution

## MCP Server Quality Analysis

Beyond pass/fail testing, the framework can analyze MCP server quality:

```yaml
# Output from: mcprobe analyze --server "npx weather-mcp"

mcp_server_analysis:
  server: "weather-mcp"
  tools_analyzed: 5
  
  overall_score: 0.72
  
  tool_scores:
    get_current_weather:
      description_clarity: 0.9
      parameter_documentation: 0.8
      return_value_documentation: 0.6  # Needs improvement
      suggested_improvements:
        - "Document units for temperature (Celsius vs Fahrenheit)"
        - "Clarify what 'conditions' field contains"
    
    get_forecast:
      description_clarity: 0.7
      parameter_documentation: 0.5  # Needs improvement
      return_value_documentation: 0.7
      suggested_improvements:
        - "Parameter 'days' should specify valid range (1-14)"
        - "Description should mention this returns daily summaries, not hourly"
        - "Add examples to parameter descriptions"
  
  common_failure_patterns:
    - pattern: "Agent calls get_current_weather when user asks about future"
      frequency: 3/10 tests
      likely_cause: "Tool descriptions don't clearly differentiate current vs forecast"
      suggestion: "Add 'Use get_forecast for future weather' to get_current_weather description"
    
    - pattern: "Agent passes city name when coordinates expected"
      frequency: 2/10 tests  
      likely_cause: "Parameter description says 'location' without specifying format"
      suggestion: "Change parameter name to 'coordinates' or add format example"
```

## Configuration

Global configuration for the test runner:

```yaml
# mcp-tester.yaml
defaults:
  agent:
    provider: anthropic
    model: claude-sonnet-4-20250514
    temperature: 0
    max_tokens: 4096
    
  synthetic_user:
    provider: anthropic
    model: claude-haiku-3-5-20241022  # Cheaper model for user simulation
    temperature: 0.7  # Some variability in responses
    
  judge:
    provider: anthropic
    model: claude-sonnet-4-20250514
    temperature: 0
    
  orchestrator:
    max_turns: 10
    turn_timeout_seconds: 30
    loop_detection_threshold: 3
    
  reporting:
    formats: [json, html, junit]
    output_dir: ./test-results
    save_conversations: true
    save_tool_calls: true

# Provider configurations
providers:
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    
  openai:
    api_key: ${OPENAI_API_KEY}
    
  # Local models via Ollama
  ollama:
    base_url: http://localhost:11434

# Test filtering
filters:
  tags: [smoke, regression]
  exclude_tags: [slow, flaky]
```

## Example: Complete Test File

```yaml
# test-scenarios/database/query-builder.yaml
name: "SQL Query Builder"
description: "User needs help building a complex SQL query"
tags: [smoke, sql, multi-tool]

synthetic_user:
  persona: |
    You are a product manager who knows basic SQL but struggles with 
    complex joins and aggregations. You're trying to get a report of 
    customer orders for the last quarter.
  
  initial_query: |
    I need to get a list of our top customers from last quarter. 
    Can you help me write a query for that?
  
  clarification_behavior:
    known_facts:
      - "Top customers means by total order value"
      - "Last quarter is Q3 2024 (July-September)"
      - "The database has 'customers', 'orders', and 'order_items' tables"
      - "Want the top 20 customers"
      - "Need customer name, email, and total spent"
    
    unknown_facts:
      - "Exact column names in the tables"
      - "Whether there's a 'total' column or need to sum items"
    
    traits:
      patience: high
      verbosity: medium
      expertise: novice

  max_turns: 8

evaluation:
  correctness_criteria:
    - "Final query joins customers and orders tables"
    - "Query filters to Q3 2024 date range"
    - "Query aggregates order values per customer"
    - "Query orders by total descending"
    - "Query limits to 20 results"
    - "Query selects customer name, email, and total"
  
  failure_criteria:
    - "Query has syntax errors"
    - "Query would return all customers instead of top 20"
    - "Agent makes up table/column names without checking schema"
    - "Agent provides query without explaining it"
  
  tool_usage:
    required_tools:
      - "get_database_schema"
    optional_tools:
      - "validate_sql"
      - "explain_query"
    prohibited_tools:
      - "execute_sql"  # Should only build, not execute
    
    tool_call_criteria:
      - tool: "get_database_schema"
        assertions:
          - "Called before generating final query"
          - "Queried relevant tables (customers, orders)"
  
  efficiency:
    max_tool_calls: 4
    max_conversation_turns: 5
```

## Implementation Phases

### Phase 1: Core Framework (MVP)
- [ ] Test scenario YAML parser
- [ ] Synthetic user LLM with basic persona support
- [ ] Simple agent interface (Anthropic + OpenAI + Gemini + OpenWebUI + Ollama)
- [ ] Conversation orchestrator
- [ ] Basic judge with pass/fail
- [ ] CLI for running single scenarios

### Phase 2: MCP Integration
- [ ] MCP client wrapper
- [ ] Tool schema introspection
- [ ] Tool call recording and assertion
- [ ] Support for stdio and HTTP MCP transports

### Phase 3: Enhanced Evaluation
- [ ] Detailed tool usage scoring
- [ ] Efficiency metrics
- [ ] Conversation quality analysis
- [ ] MCP server improvement suggestions

### Phase 4: Test Generation
- [ ] Auto-generate scenarios from MCP tool schemas
- [ ] Fuzzing for edge cases
- [ ] Scenario templates library

### Phase 5: CI/CD & Reporting
- [ ] pytest plugin
- [ ] GitHub Actions integration
- [ ] HTML report generation
- [ ] Trend analysis over time
- [ ] Flaky test detection

## Open Questions

1. **Model selection**: Should synthetic user and judge use the same model as the agent under test, or different models to avoid blind spots?

2. **Determinism**: How to balance reproducibility (temperature=0) with realistic variability in synthetic user responses?

3. **Ground truth**: For correctness evaluation, should we require expected answers in test scenarios, or rely purely on the judge's assessment?

4. **Tool mocking**: Should the framework support mocking MCP tool responses for deterministic testing?

## References

- [LangWatch Scenario](https://github.com/langwatch/scenario) - Agent testing with synthetic users
- [agent-benchmark](https://github.com/blazemeter/agent-benchmark) - MCP testing (no synthetic user yet)
- [MCP-Bench](https://github.com/Accenture/mcp-bench) - Benchmarking tool-using agents
- [DeepEval MultiTurnMCPUseMetric](https://deepeval.com/docs/metrics-multi-turn-mcp-use)
- [Inspect AI](https://ukgovernmentbeis.github.io/inspect_ai/) - Multi-turn agent evaluation
