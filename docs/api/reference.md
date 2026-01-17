# API Reference

This document provides comprehensive reference documentation for MCProbe's programmatic API.

## Table of Contents

- [Core Data Models](#core-data-models)
  - [Test Scenarios](#test-scenarios)
  - [Conversation Models](#conversation-models)
  - [Judgment Models](#judgment-models)
  - [Configuration Models](#configuration-models)
- [Key Classes](#key-classes)
  - [Orchestrator](#orchestrator)
  - [Synthetic User](#synthetic-user)
  - [Judge](#judge)
  - [Agent Base](#agent-base)
  - [LLM Provider](#llm-provider)
- [Persistence Models](#persistence-models)
- [Analysis Models](#analysis-models)
- [Exception Hierarchy](#exception-hierarchy)

## Core Data Models

### Test Scenarios

#### TestScenario

Complete test scenario definition loaded from YAML files.

**Import**: `from mcprobe.models.scenario import TestScenario`

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique scenario name (auto-trimmed, non-empty) |
| `description` | `str` | Scenario description (auto-trimmed, non-empty) |
| `synthetic_user` | `SyntheticUserConfig` | Synthetic user configuration |
| `evaluation` | `EvaluationConfig` | Evaluation criteria configuration |
| `tags` | `list[str]` | Optional tags for categorization |

**Example**:
```python
from mcprobe.models.scenario import TestScenario

scenario = TestScenario(
    name="weather-lookup",
    description="Test weather information retrieval",
    synthetic_user=SyntheticUserConfig(...),
    evaluation=EvaluationConfig(...),
    tags=["weather", "api"]
)
```

#### SyntheticUserConfig

Configuration for the synthetic user persona and behavior.

**Import**: `from mcprobe.models.scenario import SyntheticUserConfig`

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `persona` | `str` | Required | User persona description |
| `initial_query` | `str` | Required | Initial query to start conversation |
| `clarification_behavior` | `ClarificationBehavior` | `ClarificationBehavior()` | Clarification response configuration |
| `max_turns` | `int` | `10` | Maximum conversation turns (1-100) |

#### ClarificationBehavior

Defines how the synthetic user responds to clarification requests.

**Import**: `from mcprobe.models.scenario import ClarificationBehavior`

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `known_facts` | `list[str]` | `[]` | Facts the user knows and can provide |
| `unknown_facts` | `list[str]` | `[]` | Facts the user doesn't know |
| `traits` | `UserTraits` | `UserTraits()` | Personality traits |

#### UserTraits

Personality traits affecting synthetic user behavior.

**Import**: `from mcprobe.models.scenario import UserTraits`

**Fields**:

| Field | Type | Default | Values | Description |
|-------|------|---------|--------|-------------|
| `patience` | `PatienceLevel` | `MEDIUM` | `LOW`, `MEDIUM`, `HIGH` | Patience with clarifying questions |
| `verbosity` | `VerbosityLevel` | `CONCISE` | `CONCISE`, `MEDIUM`, `VERBOSE` | Response verbosity |
| `expertise` | `ExpertiseLevel` | `NOVICE` | `NOVICE`, `INTERMEDIATE`, `EXPERT` | Technical expertise level |

#### EvaluationConfig

Configuration for how conversations are evaluated.

**Import**: `from mcprobe.models.scenario import EvaluationConfig`

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `correctness_criteria` | `list[str]` | Required success criteria (at least 1) |
| `failure_criteria` | `list[str]` | Conditions that cause failure |
| `tool_usage` | `ToolUsageConfig` | Tool usage requirements |
| `efficiency` | `EfficiencyConfig` | Optional efficiency targets |

#### ToolUsageConfig

Expected tool usage patterns for evaluation.

**Import**: `from mcprobe.models.scenario import ToolUsageConfig`

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `required_tools` | `list[str]` | `[]` | Tools that must be called |
| `optional_tools` | `list[str]` | `[]` | Tools that may be called |
| `prohibited_tools` | `list[str]` | `[]` | Tools that must not be called |
| `tool_call_criteria` | `list[ToolCallCriterion]` | `[]` | Specific tool call assertions |

#### ToolCallCriterion

Assertions about how a specific tool should be called.

**Import**: `from mcprobe.models.scenario import ToolCallCriterion`

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `tool` | `str` | Tool name |
| `assertions` | `list[str]` | Natural language assertions about the call |

#### EfficiencyConfig

Optional efficiency targets for evaluation.

**Import**: `from mcprobe.models.scenario import EfficiencyConfig`

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_tool_calls` | `int \| None` | `None` | Maximum allowed tool calls |
| `max_llm_tokens` | `int \| None` | `None` | Maximum LLM tokens |
| `max_conversation_turns` | `int \| None` | `None` | Maximum conversation turns |

### Conversation Models

#### ConversationResult

Complete result of a conversation run.

**Import**: `from mcprobe.models.conversation import ConversationResult`

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `turns` | `list[ConversationTurn]` | All conversation turns |
| `final_answer` | `str` | Final answer provided by agent |
| `total_tool_calls` | `list[ToolCall]` | All tool calls made during conversation |
| `total_tokens` | `int` | Total LLM tokens used |
| `duration_seconds` | `float` | Total conversation duration |
| `termination_reason` | `TerminationReason` | Why the conversation ended |

#### ConversationTurn

Single turn in a conversation.

**Import**: `from mcprobe.models.conversation import ConversationTurn`

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `role` | `str` | "user" or "assistant" |
| `content` | `str` | Message content |
| `tool_calls` | `list[ToolCall]` | Tool calls in this turn |
| `timestamp` | `float` | Unix timestamp |

#### ToolCall

Record of a single tool invocation.

**Import**: `from mcprobe.models.conversation import ToolCall`

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `str` | Name of the tool called |
| `parameters` | `dict[str, Any]` | Parameters passed to tool |
| `result` | `Any` | Result returned by tool |
| `latency_ms` | `float` | Tool execution time in milliseconds |
| `error` | `str \| None` | Error message if tool call failed |

#### AgentResponse

Response from the agent under test.

**Import**: `from mcprobe.models.conversation import AgentResponse`

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `message` | `str` | Required | Agent's message text |
| `tool_calls` | `list[ToolCall]` | `[]` | Tool calls made in this response |
| `is_complete` | `bool` | `False` | Whether agent considers task complete |
| `metadata` | `dict[str, Any]` | `{}` | Additional metadata |

#### UserResponse

Response from the synthetic user.

**Import**: `from mcprobe.models.conversation import UserResponse`

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `message` | `str` | Required | User's message text |
| `is_satisfied` | `bool` | `False` | Whether user is satisfied |
| `tokens_used` | `int` | `0` | Tokens used for this response |

#### TerminationReason

Reason why a conversation ended.

**Import**: `from mcprobe.models.conversation import TerminationReason`

**Values**:
- `USER_SATISFIED`: User satisfied with agent's response
- `MAX_TURNS`: Maximum conversation turns reached
- `ERROR`: Error occurred during conversation
- `LOOP_DETECTED`: Conversation stuck in a loop

### Judgment Models

#### JudgmentResult

Result of evaluating a conversation against test criteria.

**Import**: `from mcprobe.models.judgment import JudgmentResult`

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `passed` | `bool` | Overall pass/fail status |
| `score` | `float` | Overall score (0.0-1.0) |
| `correctness_results` | `dict[str, bool]` | Correctness criterion → passed |
| `failure_results` | `dict[str, bool]` | Failure criterion → triggered |
| `tool_usage_results` | `dict[str, Any]` | Tool usage evaluation details |
| `efficiency_results` | `dict[str, Any]` | Efficiency metrics |
| `reasoning` | `str` | Judge's reasoning |
| `suggestions` | `list[str]` | Improvement suggestions |
| `quality_metrics` | `QualityMetrics` | Quality measurements |
| `structured_suggestions` | `list[MCPSuggestion]` | Structured MCP improvements |

#### QualityMetrics

Conversation quality measurements.

**Import**: `from mcprobe.models.judgment import QualityMetrics`

**Fields**:

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `clarification_count` | `int` | `0` | ≥ 0 | Number of clarifications requested |
| `backtrack_count` | `int` | `0` | ≥ 0 | Number of times agent backtracked |
| `turns_to_first_answer` | `int` | `0` | ≥ 0 | Turns until first answer attempt |
| `final_answer_completeness` | `float` | `0.0` | 0.0-1.0 | Completeness of final answer |

#### MCPSuggestion

Structured suggestion for MCP server improvement.

**Import**: `from mcprobe.models.judgment import MCPSuggestion`

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `category` | `SuggestionCategory` | Required | Type of suggestion |
| `tool_name` | `str \| None` | `None` | Affected tool name |
| `issue` | `str` | Required | Description of the issue |
| `suggestion` | `str` | Required | Improvement suggestion |
| `severity` | `SuggestionSeverity` | `MEDIUM` | Severity level |

#### SuggestionCategory

Category of MCP server improvement suggestion.

**Import**: `from mcprobe.models.judgment import SuggestionCategory`

**Values**:
- `DESCRIPTION`: Tool or parameter description issues
- `PARAMETER`: Parameter definition issues
- `RETURN_VALUE`: Return value issues
- `SCHEMA`: Schema definition issues

#### SuggestionSeverity

Severity level of an improvement suggestion.

**Import**: `from mcprobe.models.judgment import SuggestionSeverity`

**Values**:
- `LOW`: Minor improvement
- `MEDIUM`: Moderate improvement
- `HIGH`: Critical improvement

### Configuration Models

See [Configuration Reference](../configuration/reference.md) for complete details on:
- `LLMConfig`
- `OrchestratorConfig`
- `MCProbeConfig`

## Key Classes

### Orchestrator

Main coordination class for running test scenarios.

**Import**: `from mcprobe.orchestrator.orchestrator import ConversationOrchestrator`

#### Constructor

```python
def __init__(
    self,
    agent: AgentUnderTest,
    synthetic_user: SyntheticUserLLM,
    judge: ConversationJudge,
) -> None
```

**Parameters**:
- `agent`: Agent under test to converse with
- `synthetic_user`: Synthetic user to simulate
- `judge`: Judge for evaluating the conversation

#### Methods

##### run

```python
async def run(
    self,
    scenario: TestScenario
) -> tuple[ConversationResult, JudgmentResult]
```

Run a complete test scenario.

**Parameters**:
- `scenario`: Test scenario to execute

**Returns**: Tuple of (conversation_result, judgment_result)

**Raises**: `OrchestrationError` if the conversation fails

**Example**:
```python
from mcprobe.orchestrator.orchestrator import ConversationOrchestrator

orchestrator = ConversationOrchestrator(agent, synthetic_user, judge)
conversation_result, judgment_result = await orchestrator.run(scenario)

print(f"Passed: {judgment_result.passed}")
print(f"Score: {judgment_result.score}")
```

### Synthetic User

LLM-powered synthetic user for testing.

**Import**: `from mcprobe.synthetic_user.user import SyntheticUserLLM`

#### Constructor

```python
def __init__(
    self,
    provider: LLMProvider,
    config: SyntheticUserConfig,
) -> None
```

**Parameters**:
- `provider`: LLM provider for generating responses
- `config`: Synthetic user configuration from test scenario

#### Methods

##### get_initial_query

```python
async def get_initial_query(self) -> str
```

Get the initial query to start the conversation.

**Returns**: Initial query from scenario configuration

##### respond

```python
async def respond(
    self,
    assistant_message: str,
    *,
    is_final_answer: bool = False,
) -> UserResponse
```

Generate a response to the assistant's message.

**Parameters**:
- `assistant_message`: The assistant's message to respond to
- `is_final_answer`: Whether the assistant considers this a final answer

**Returns**: UserResponse with the synthetic user's reply and satisfaction status

**Raises**: `OrchestrationError` if the LLM call fails

##### reset

```python
def reset(self) -> None
```

Reset the synthetic user for a new conversation.

#### Properties

##### questions_asked

```python
@property
def questions_asked(self) -> int
```

Number of clarifying questions the assistant has asked.

##### config

```python
@property
def config(self) -> SyntheticUserConfig
```

Get the synthetic user configuration.

**Example**:
```python
from mcprobe.synthetic_user.user import SyntheticUserLLM
from mcprobe.providers.factory import create_provider
from mcprobe.models.config import LLMConfig

llm_config = LLMConfig(provider="ollama", model="llama3.2")
provider = create_provider(llm_config)

user = SyntheticUserLLM(provider, scenario.synthetic_user)
initial_query = await user.get_initial_query()
```

### Judge

LLM-powered judge for evaluating conversation results.

**Import**: `from mcprobe.judge.judge import ConversationJudge`

#### Constructor

```python
def __init__(self, provider: LLMProvider) -> None
```

**Parameters**:
- `provider`: LLM provider to use for evaluation

#### Methods

##### evaluate

```python
async def evaluate(
    self,
    scenario: TestScenario,
    result: ConversationResult,
) -> JudgmentResult
```

Evaluate a conversation result against scenario criteria.

**Parameters**:
- `scenario`: Test scenario with evaluation criteria
- `result`: Conversation result to evaluate

**Returns**: JudgmentResult with pass/fail status and detailed evaluation

**Raises**: `JudgmentError` if evaluation fails

**Example**:
```python
from mcprobe.judge.judge import ConversationJudge

judge = ConversationJudge(provider)
judgment = await judge.evaluate(scenario, conversation_result)

for criterion, passed in judgment.correctness_results.items():
    print(f"{criterion}: {'PASS' if passed else 'FAIL'}")
```

### Agent Base

Abstract base class for agents under test.

**Import**: `from mcprobe.agents.base import AgentUnderTest`

#### Methods (Abstract)

##### send_message

```python
@abstractmethod
async def send_message(self, message: str) -> AgentResponse
```

Send a user message and get the agent's response.

**Parameters**:
- `message`: The user's message text

**Returns**: AgentResponse containing the agent's reply and any tool calls

**Raises**: `OrchestrationError` if the agent fails to respond

##### reset

```python
@abstractmethod
async def reset(self) -> None
```

Reset conversation state for a new test. Should clear conversation history and return agent to initial state.

##### get_available_tools

```python
@abstractmethod
def get_available_tools(self) -> list[dict[str, object]]
```

Return the tool schemas available to this agent.

**Returns**: List of tool definitions in OpenAI-compatible format. Empty list if the agent has no tools.

#### Properties

##### name

```python
@property
def name(self) -> str
```

Human-readable name for this agent. Defaults to class name.

**Example Implementation**:
```python
from mcprobe.agents.base import AgentUnderTest
from mcprobe.models.conversation import AgentResponse, ToolCall

class MyAgent(AgentUnderTest):
    async def send_message(self, message: str) -> AgentResponse:
        # Process message and generate response
        response_text = await self._generate_response(message)

        return AgentResponse(
            message=response_text,
            tool_calls=[],
            is_complete=True
        )

    async def reset(self) -> None:
        self._conversation_history = []

    def get_available_tools(self) -> list[dict[str, object]]:
        return []
```

### LLM Provider

Abstract base class for LLM provider implementations.

**Import**: `from mcprobe.providers.base import LLMProvider`

#### Constructor

```python
def __init__(self, config: LLMConfig) -> None
```

**Parameters**:
- `config`: LLM configuration

#### Methods (Abstract)

##### generate

```python
@abstractmethod
async def generate(
    self,
    messages: list[Message],
    *,
    tools: list[dict[str, Any]] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> LLMResponse
```

Generate a completion from messages.

**Parameters**:
- `messages`: List of conversation messages
- `tools`: Optional list of tool definitions for function calling
- `temperature`: Override the configured temperature
- `max_tokens`: Override the configured max tokens

**Returns**: LLMResponse with generated content and metadata

**Raises**: `LLMProviderError` if the API call fails

##### generate_structured

```python
@abstractmethod
async def generate_structured(
    self,
    messages: list[Message],
    response_schema: type[BaseModel],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> BaseModel
```

Generate a structured response matching the schema.

**Parameters**:
- `messages`: List of conversation messages
- `response_schema`: Pydantic model class defining expected response
- `temperature`: Override the configured temperature
- `max_tokens`: Override the configured max tokens

**Returns**: Instance of response_schema populated with generated data

**Raises**: `LLMProviderError` if API call fails or response doesn't match schema

#### Properties (Abstract)

##### supports_tools

```python
@property
@abstractmethod
def supports_tools(self) -> bool
```

Whether this provider supports tool/function calling.

##### supports_structured_output

```python
@property
@abstractmethod
def supports_structured_output(self) -> bool
```

Whether this provider supports structured JSON output.

#### Helper Classes

##### Message

Unified message format for LLM conversations.

**Import**: `from mcprobe.providers.base import Message`

**Fields**:
- `role`: "user", "assistant", or "system"
- `content`: Message text
- `tool_calls`: Optional tool invocations
- `tool_call_id`: Optional tool result reference

##### LLMResponse

Unified response format from LLM providers.

**Import**: `from mcprobe.providers.base import LLMResponse`

**Fields**:
- `content`: Generated text
- `tool_calls`: List of tool calls (if any)
- `finish_reason`: Why generation stopped
- `usage`: Token usage (`prompt_tokens`, `completion_tokens`)
- `raw_response`: Provider-specific response for debugging

## Persistence Models

### TestRunResult

Complete test run result for persistence.

**Import**: `from mcprobe.persistence.models import TestRunResult`

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | UUID v4 identifier |
| `timestamp` | `datetime` | When the test was run |
| `scenario_name` | `str` | Scenario name |
| `scenario_file` | `str` | Path to scenario YAML |
| `scenario_tags` | `list[str]` | Scenario tags |
| `conversation_result` | `ConversationResult` | Conversation details |
| `judgment_result` | `JudgmentResult` | Evaluation details |
| `agent_type` | `str` | Type of agent tested |
| `model_name` | `str` | LLM model used |
| `duration_seconds` | `float` | Total test duration |
| `mcprobe_version` | `str` | MCProbe version |
| `python_version` | `str` | Python version |
| `git_commit` | `str \| None` | Git commit hash |
| `git_branch` | `str \| None` | Git branch |
| `ci_environment` | `dict[str, str]` | CI environment variables |

### IndexEntry

Entry in the results index for fast lookup.

**Import**: `from mcprobe.persistence.models import IndexEntry`

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | UUID v4 identifier |
| `timestamp` | `datetime` | When the test was run |
| `scenario_name` | `str` | Scenario name |
| `scenario_file` | `str` | Path to scenario YAML |
| `passed` | `bool` | Pass/fail status |
| `score` | `float` | Overall score |

### TrendEntry

Type for trend data entries stored in JSON files.

**Import**: `from mcprobe.persistence.models import TrendEntry`

**Fields** (TypedDict):

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | UUID v4 identifier |
| `timestamp` | `str` | ISO format timestamp |
| `passed` | `bool` | Pass/fail status |
| `score` | `float` | Overall score |
| `duration_seconds` | `float` | Test duration |
| `total_tool_calls` | `int` | Number of tool calls |
| `total_tokens` | `int` | Total tokens used |
| `turns` | `int` | Number of conversation turns |

## Analysis Models

### ScenarioTrends

Trend analysis for a single scenario.

**Import**: `from mcprobe.analysis.models import ScenarioTrends`

**Fields**:

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `scenario_name` | `str` | - | Scenario name |
| `run_count` | `int` | ≥ 0 | Number of runs analyzed |
| `pass_rate` | `float` | 0.0-1.0 | Percentage of passing runs |
| `pass_trend` | `TrendDirection` | - | Pass rate trend direction |
| `current_score` | `float` | 0.0-1.0 | Most recent score |
| `avg_score` | `float` | 0.0-1.0 | Average score |
| `min_score` | `float` | 0.0-1.0 | Minimum score |
| `max_score` | `float` | 0.0-1.0 | Maximum score |
| `score_trend` | `TrendDirection` | - | Score trend direction |
| `score_variance` | `float` | ≥ 0 | Score variance |
| `avg_duration` | `float` | ≥ 0 | Average duration in seconds |
| `avg_tool_calls` | `float` | ≥ 0 | Average tool calls per run |
| `avg_tokens` | `float` | ≥ 0 | Average tokens per run |

### TrendDirection

Direction of a metric trend.

**Import**: `from mcprobe.analysis.models import TrendDirection`

**Values**:
- `IMPROVING`: Metric is improving over time
- `STABLE`: Metric is stable/unchanged
- `DEGRADING`: Metric is degrading over time

### Regression

Represents a detected regression.

**Import**: `from mcprobe.analysis.models import Regression`

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `scenario_name` | `str` | Affected scenario |
| `metric` | `str` | Metric name (e.g., "pass_rate", "score") |
| `previous_value` | `float` | Previous metric value |
| `current_value` | `float` | Current metric value |
| `change_percent` | `float` | Percentage change |
| `severity` | `str` | "low", "medium", or "high" |

### FlakyScenario

Represents a flaky scenario detection.

**Import**: `from mcprobe.analysis.models import FlakyScenario`

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `scenario_name` | `str` | Scenario name |
| `pass_rate` | `float` | Pass rate (0.0-1.0) |
| `score_variance` | `float \| None` | Score variance if applicable |
| `coefficient_of_variation` | `float \| None` | Coefficient of variation if applicable |
| `reason` | `str` | Why scenario is considered flaky |
| `severity` | `str` | "low", "medium", or "high" |
| `run_count` | `int` | Number of runs analyzed |

## Exception Hierarchy

All MCProbe exceptions inherit from `MCProbeError` for easy catching.

**Import**: `from mcprobe.exceptions import *`

### Exception Tree

```
MCProbeError (base)
├── ConfigurationError
│   └── Raised for configuration-related errors
│
├── ProviderError
│   ├── ProviderNotFoundError
│   │   └── Requested provider is not registered
│   ├── ProviderConfigError
│   │   └── Provider configuration is invalid
│   └── LLMProviderError
│       └── Error during LLM API call
│
├── ScenarioError
│   ├── ScenarioParseError
│   │   └── Failed to parse scenario YAML
│   └── ScenarioValidationError
│       └── Scenario failed validation
│
├── OrchestrationError
│   └── Conversation orchestration errors
│
└── JudgmentError
    └── Judgment/evaluation errors
```

### Usage Example

```python
from mcprobe.exceptions import (
    MCProbeError,
    OrchestrationError,
    JudgmentError,
)

try:
    conversation_result, judgment_result = await orchestrator.run(scenario)
except OrchestrationError as e:
    logger.error(f"Conversation failed: {e}")
    # Handle orchestration failure
except JudgmentError as e:
    logger.error(f"Evaluation failed: {e}")
    # Handle judgment failure
except MCProbeError as e:
    logger.error(f"MCProbe error: {e}")
    # Handle any other MCProbe error
```

### Fail-Fast Philosophy

MCProbe follows a fail-fast approach:
- Errors propagate immediately without fallbacks
- No silent error suppression
- Clear error messages with context
- All errors inherit from `MCProbeError` for easy top-level catching

## Programmatic Usage Examples

### Running a Single Scenario

```python
from mcprobe.models.config import LLMConfig
from mcprobe.providers.factory import create_provider
from mcprobe.agents.simple import SimpleLLMAgent
from mcprobe.synthetic_user.user import SyntheticUserLLM
from mcprobe.judge.judge import ConversationJudge
from mcprobe.orchestrator.orchestrator import ConversationOrchestrator
from mcprobe.parser.scenario import ScenarioParser

# Parse scenario
parser = ScenarioParser()
scenario = parser.parse_file("scenario.yaml")

# Create LLM provider
llm_config = LLMConfig(
    provider="ollama",
    model="llama3.2",
    base_url="http://localhost:11434"
)
provider = create_provider(llm_config)

# Create components
agent = SimpleLLMAgent(provider)
synthetic_user = SyntheticUserLLM(provider, scenario.synthetic_user)
judge = ConversationJudge(provider)
orchestrator = ConversationOrchestrator(agent, synthetic_user, judge)

# Run test
conversation_result, judgment_result = await orchestrator.run(scenario)

# Process results
print(f"Passed: {judgment_result.passed}")
print(f"Score: {judgment_result.score:.2f}")
print(f"Turns: {len(conversation_result.turns)}")
print(f"Tool calls: {len(conversation_result.total_tool_calls)}")
```

### Custom Agent Implementation

```python
from mcprobe.agents.base import AgentUnderTest
from mcprobe.models.conversation import AgentResponse

class MyCustomAgent(AgentUnderTest):
    def __init__(self, my_config):
        self.config = my_config
        self.history = []

    async def send_message(self, message: str) -> AgentResponse:
        # Your custom agent logic
        response = await self._process_message(message)

        return AgentResponse(
            message=response,
            tool_calls=[],
            is_complete=self._is_task_complete()
        )

    async def reset(self) -> None:
        self.history = []

    def get_available_tools(self) -> list[dict[str, object]]:
        return []  # or your tool definitions

# Use your custom agent
agent = MyCustomAgent(my_config)
orchestrator = ConversationOrchestrator(agent, synthetic_user, judge)
```

### Analyzing Test Results

```python
from mcprobe.persistence import ResultLoader
from mcprobe.analysis import TrendAnalyzer, FlakyDetector

# Load results
loader = ResultLoader("test-results")
results = loader.load_all(limit=100)

# Analyze trends
analyzer = TrendAnalyzer(loader)
trends = analyzer.analyze_all(window=20)

for trend in trends:
    print(f"{trend.scenario_name}: {trend.pass_rate:.0%} pass rate")
    print(f"  Trend: {trend.pass_trend.value}")
    print(f"  Avg score: {trend.avg_score:.2f}")

# Detect flaky tests
detector = FlakyDetector(loader)
flaky = detector.detect_flaky_scenarios(min_runs=5)

for f in flaky:
    print(f"Flaky: {f.scenario_name} ({f.severity})")
    print(f"  Reason: {f.reason}")
```

## Related Documentation

- [Configuration Reference](../configuration/reference.md) - Complete configuration options
- [Architecture Overview](../architecture/overview.md) - System architecture and data flow
- [CLI Reference](../cli/README.md) - Command-line interface
- [Scenario Format](../scenarios/README.md) - Test scenario structure
