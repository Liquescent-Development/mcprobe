# Architecture Overview

This document provides a high-level overview of MCProbe's architecture, including its core components, data flow, and extension points.

## System Architecture

MCProbe uses a conversational testing architecture with four main components:

```
┌─────────────────────────────────────────────────────────────────┐
│                       Orchestrator                              │
│                   (Conversation Control)                        │
└───────┬─────────────────────────────────────────────┬───────────┘
        │                                             │
        │ manages                                     │ coordinates
        │                                             │
        v                                             v
┌──────────────────┐                          ┌──────────────────┐
│ Synthetic User   │  ←──── converses ─────→  │  Agent Under    │
│     (LLM)        │                          │      Test       │
└──────────────────┘                          └──────────────────┘
        │                                             │
        │ scenario config                             │ responses
        │                                             │
        v                                             v
┌──────────────────────────────────────────────────────────────────┐
│                         Test Scenario                            │
│                    (Persona + Criteria)                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              │ provides criteria
                              v
                     ┌──────────────────┐
                     │      Judge       │
                     │      (LLM)       │
                     └──────────────────┘
                              │
                              v
                     ┌──────────────────┐
                     │ Judgment Result  │
                     │ (Pass/Fail/Score)│
                     └──────────────────┘
```

## Core Components

### 1. Orchestrator

**Path**: `mcprobe.orchestrator.orchestrator.ConversationOrchestrator`

The orchestrator is the central coordination layer that manages the entire test execution flow.

**Responsibilities**:
- Manages the conversation loop between synthetic user and agent
- Tracks conversation turns and tool calls
- Detects conversation loops and termination conditions
- Coordinates with the judge for evaluation
- Enforces timeout and turn limits

**Key Methods**:
- `run(scenario) -> (ConversationResult, JudgmentResult)`: Execute a complete test scenario
- `_run_conversation(scenario) -> ConversationResult`: Run the conversation loop
- `_detect_loop(turns) -> bool`: Detect if conversation is stuck in a loop

**Termination Conditions**:
- Judge determines all correctness criteria are met
- Maximum turns reached
- Loop detected (3+ identical user messages)
- Error occurred

### 2. Synthetic User

**Path**: `mcprobe.synthetic_user.user.SyntheticUserLLM`

An LLM-powered synthetic user that simulates realistic human interaction with the agent.

**Responsibilities**:
- Maintains persona consistency throughout conversation
- Generates initial queries based on scenario
- Responds to agent messages naturally with follow-up questions
- Tracks clarification behavior and known/unknown facts

**Key Methods**:
- `get_initial_query() -> str`: Return the initial query from scenario
- `respond(message) -> UserResponse`: Generate natural follow-up response to agent
- `reset()`: Clear state for new conversation

**Note**: The synthetic user no longer determines satisfaction. Termination decisions are made by the judge evaluating correctness criteria after each agent turn.

**Persona Traits**:
- Patience level (low/medium/high)
- Verbosity (concise/medium/verbose)
- Expertise (novice/intermediate/expert)

### 3. Judge

**Path**: `mcprobe.judge.judge.ConversationJudge`

An LLM-powered evaluator that assesses conversation quality against defined criteria.

**Responsibilities**:
- Check correctness criteria after each agent turn (mid-conversation evaluation)
- Determine when to terminate conversation (all criteria met)
- Evaluate final conversation quality
- Check failure conditions
- Verify tool usage requirements
- Assess efficiency metrics
- Generate improvement suggestions
- Compute quality metrics

**Key Methods**:
- `check_criteria(scenario, turns) -> CriteriaCheckResult`: Lightweight mid-conversation check
- `evaluate(scenario, result) -> JudgmentResult`: Full evaluation of completed conversation

**Evaluation Dimensions**:
- **Correctness**: Did the agent meet the success criteria?
- **Failure Conditions**: Were any failure conditions triggered?
- **Tool Usage**: Were required tools used? Were prohibited tools avoided?
- **Efficiency**: Was the solution efficient in terms of turns, tool calls, and tokens?
- **Quality Metrics**: Clarifications, backtracks, completeness

**Structured Output**:
The judge uses structured generation to ensure consistent, parseable evaluation results.

### 4. Agent Under Test

**Path**: `mcprobe.agents.base.AgentUnderTest` (abstract base class)

The system or agent being tested. MCProbe provides two built-in implementations:

**SimpleLLMAgent** (`mcprobe.agents.simple`):
- Basic LLM agent using Ollama or similar providers
- No tool calling capabilities
- Suitable for simple conversational testing

**GeminiADKAgent** (`mcprobe.agents.adk`):
- Wraps Gemini ADK agents with MCP tools
- Full tool calling support
- Requires agent factory function

**Interface**:
- `send_message(message) -> AgentResponse`: Send a message and get response
- `reset()`: Reset conversation state
- `get_available_tools() -> list[dict]`: Get available tool definitions

**Custom Agent Implementation**:
```python
from mcprobe.agents.base import AgentUnderTest
from mcprobe.models.conversation import AgentResponse

class MyCustomAgent(AgentUnderTest):
    async def send_message(self, message: str) -> AgentResponse:
        # Your implementation
        pass

    async def reset(self) -> None:
        # Reset state
        pass

    def get_available_tools(self) -> list[dict]:
        # Return tool schemas
        return []
```

## Data Flow

### Test Execution Flow

```
1. Load Test Scenario
   ├─ Parse YAML file
   ├─ Validate scenario structure
   └─ Create SyntheticUserConfig + EvaluationConfig

2. Initialize Components
   ├─ Create LLM providers (Ollama, OpenAI, etc.)
   ├─ Initialize Agent Under Test
   ├─ Create Synthetic User with scenario persona
   ├─ Create Judge evaluator
   └─ Create Orchestrator

3. Run Conversation (Judge-Driven Termination)
   ├─ Synthetic User generates initial query
   ├─ Loop until termination:
   │  ├─ Agent receives message
   │  ├─ Agent makes tool calls (if applicable)
   │  ├─ Agent returns response
   │  ├─ Judge evaluates correctness criteria
   │  ├─ If all criteria met → terminate with CRITERIA_MET
   │  ├─ Else: Synthetic User generates follow-up
   │  └─ Check other termination conditions (max turns, loops)
   └─ Return ConversationResult

4. Evaluate Result
   ├─ Judge analyzes conversation
   ├─ Check correctness criteria
   ├─ Check failure conditions
   ├─ Verify tool usage
   ├─ Assess efficiency
   └─ Return JudgmentResult

5. Store & Report
   ├─ Persist TestRunResult
   ├─ Update result index
   └─ Generate reports (HTML/JSON/JUnit)
```

### Data Model Flow

```
TestScenario (YAML)
    │
    ├─→ SyntheticUserConfig ─→ SyntheticUserLLM
    │       ├─ persona
    │       ├─ initial_query
    │       └─ clarification_behavior
    │
    └─→ EvaluationConfig ─→ ConversationJudge
            ├─ correctness_criteria
            ├─ failure_criteria
            ├─ tool_usage
            └─ efficiency

ConversationResult
    ├─ turns: list[ConversationTurn]
    ├─ total_tool_calls: list[ToolCall]
    ├─ termination_reason
    └─ duration_seconds

JudgmentResult
    ├─ passed: bool
    ├─ score: float
    ├─ correctness_results
    ├─ failure_results
    ├─ tool_usage_results
    ├─ efficiency_results
    ├─ quality_metrics
    └─ structured_suggestions
```

## Key Abstractions

### 1. Provider Abstraction

**Path**: `mcprobe.providers.base.LLMProvider`

Abstraction layer for different LLM providers (Ollama, OpenAI, etc.).

**Key Methods**:
- `generate(messages, tools) -> LLMResponse`: Standard completion
- `generate_structured(messages, schema) -> BaseModel`: Structured output

**Benefits**:
- Uniform interface across providers
- Easy to add new providers
- Supports both tool calling and structured generation

### 2. Message Format

**Path**: `mcprobe.providers.base.Message`

Unified message format for LLM conversations.

**Fields**:
- `role`: "user", "assistant", "system"
- `content`: Message text
- `tool_calls`: Optional tool invocations
- `tool_call_id`: Optional tool result reference

### 3. Conversation Models

**Path**: `mcprobe.models.conversation`

Core data models for tracking conversations:

- **ToolCall**: Record of a single tool invocation with parameters, result, latency, and errors
- **ConversationTurn**: Single message exchange with role, content, tool calls, and timestamp
- **AgentResponse**: Agent's reply including message, tool calls, completion status, and metadata
- **UserResponse**: Synthetic user's reply with token usage
- **ConversationResult**: Complete conversation record with all turns, tool calls, tokens, duration, and termination reason

## Extension Points

### 1. Custom Agents

Implement `AgentUnderTest` to test any agent type:

```python
from mcprobe.agents.base import AgentUnderTest

class MyAgent(AgentUnderTest):
    async def send_message(self, message: str) -> AgentResponse:
        # Custom logic
        pass
```

### 2. Custom Providers

Implement `LLMProvider` to support new LLM APIs:

```python
from mcprobe.providers.base import LLMProvider

class MyProvider(LLMProvider):
    async def generate(self, messages, **kwargs) -> LLMResponse:
        # Custom API integration
        pass
```

Register your provider:

```python
from mcprobe.providers.factory import ProviderRegistry

ProviderRegistry.register("myprovider", MyProvider)
```

### 3. Custom Analyzers

Create custom analysis logic for test results:

```python
from mcprobe.persistence import ResultLoader
from mcprobe.analysis.models import ScenarioTrends

class MyAnalyzer:
    def __init__(self, loader: ResultLoader):
        self.loader = loader

    def analyze(self) -> list[ScenarioTrends]:
        # Custom analysis logic
        pass
```

### 4. Custom Report Generators

Implement custom report formats:

```python
from mcprobe.persistence.models import TestRunResult

class MyReportGenerator:
    def generate(self, results: list[TestRunResult], output_path: Path):
        # Custom report generation
        pass
```

## Error Handling

MCProbe follows a fail-fast approach with a clear exception hierarchy:

```
MCProbeError (base)
├── ConfigurationError
├── ProviderError
│   ├── ProviderNotFoundError
│   ├── ProviderConfigError
│   └── LLMProviderError
├── ScenarioError
│   ├── ScenarioParseError
│   └── ScenarioValidationError
├── OrchestrationError
└── JudgmentError
```

All errors inherit from `MCProbeError` for easy catching:

```python
from mcprobe.exceptions import MCProbeError

try:
    await orchestrator.run(scenario)
except MCProbeError as e:
    # Handle any MCProbe error
    logger.error(f"Test failed: {e}")
```

## Persistence Layer

MCProbe stores test results in a structured file format:

```
test-results/
├── index.json                    # Fast lookup index
├── trends/                       # Trend data by scenario
│   ├── scenario_name_1.json
│   └── scenario_name_2.json
└── runs/                         # Individual run results
    ├── YYYY-MM-DD/
    │   ├── run_id_1.json
    │   └── run_id_2.json
    └── YYYY-MM-DD/
```

**Models**: See `mcprobe.persistence.models` for:
- `TestRunResult`: Complete test run record
- `IndexEntry`: Fast lookup entry
- `TrendEntry`: Historical trend data

## Analysis Capabilities

MCProbe includes built-in analysis features:

### Trend Analysis
- Pass rate trends over time
- Score trends and variance
- Performance metrics (duration, tool calls, tokens)

### Regression Detection
- Automatic detection of performance regressions
- Configurable thresholds and severity levels

### Flaky Test Detection
- Identifies tests with inconsistent results
- Coefficient of variation analysis
- Minimum run requirements

See [Analysis Documentation](../analysis/README.md) for details.

## Related Documentation

- [Configuration Reference](../configuration/reference.md) - Complete configuration options
- [API Reference](../api/reference.md) - Programmatic API documentation
- [Scenario Format](../scenarios/README.md) - Test scenario structure
- [Agent Guide](../agents/README.md) - Creating custom agents
