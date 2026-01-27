# Scenario Format Reference

This document provides a complete reference for the MCProbe test scenario YAML format.

## Quick Links

- [Synthetic User Configuration](./synthetic-user.md)
- [Evaluation Criteria](./evaluation.md)
- [Example Scenarios](./examples.md)

## Schema Overview

A test scenario consists of seven top-level sections:

```yaml
name: string                    # Required: Scenario identifier
description: string             # Required: What this scenario tests
skip: bool | string             # Optional: Skip scenario (true or reason string)
synthetic_user: {...}           # Required: User simulation config
evaluation: {...}               # Required: Success/failure criteria
tags: [...]                     # Optional: Classification tags
config: {...}                   # Optional: Per-scenario LLM overrides
```

## Complete Schema Reference

### Top-Level Fields

#### `name`
- **Type:** `string`
- **Required:** Yes
- **Constraints:**
  - Minimum length: 1 character
  - Cannot be only whitespace
  - Automatically trimmed of leading/trailing whitespace
- **Description:** A unique, descriptive name for the test scenario
- **Example:** `"Weather Query with City Clarification"`

#### `description`
- **Type:** `string`
- **Required:** Yes
- **Constraints:**
  - Minimum length: 1 character
  - Cannot be only whitespace
  - Automatically trimmed of leading/trailing whitespace
- **Description:** Detailed explanation of what behavior this scenario tests
- **Example:** `"Tests the agent's ability to handle ambiguous weather queries by asking for clarification about the city"`

#### `skip`
- **Type:** `bool | string`
- **Required:** No
- **Default:** `false`
- **Description:** Skip this scenario during test execution. Set to `true` to skip without a reason, or provide a string explanation for why the scenario is skipped.
- **Examples:**
  - `skip: true` - Skip without reason
  - `skip: "Waiting on analytics API implementation"`
  - `skip: "Feature not ready for testing"`
- **Pytest Integration:** When set, the scenario appears as SKIPPED in pytest output with the reason displayed

#### `synthetic_user`
- **Type:** `SyntheticUserConfig` object
- **Required:** Yes
- **Description:** Configuration for the simulated user in the conversation
- **See:** [Synthetic User Configuration](./synthetic-user.md) for detailed reference

#### `evaluation`
- **Type:** `EvaluationConfig` object
- **Required:** Yes
- **Description:** Criteria used to evaluate the agent's performance
- **See:** [Evaluation Criteria](./evaluation.md) for detailed reference

#### `tags`
- **Type:** `list[string]`
- **Required:** No
- **Default:** `[]`
- **Description:** Tags for organizing and filtering scenarios
- **Example:** `["weather", "clarification", "basic"]`

#### `config`
- **Type:** `ScenarioConfig` object
- **Required:** No
- **Default:** `null`
- **Description:** Per-scenario LLM configuration overrides for judge and synthetic user
- **See:** [Per-Scenario Configuration](#per-scenario-configuration) section below

### Per-Scenario Configuration

The `config` section allows you to override LLM settings for specific scenarios without changing your global `mcprobe.yaml` configuration. This is useful for:

- Using a stricter/more lenient judge for specific test cases
- Customizing synthetic user behavior per scenario
- Testing with different models for specific scenarios

#### ScenarioConfig Fields

##### `config.judge`
- **Type:** `ScenarioLLMOverride` object
- **Required:** No
- **Description:** Overrides for the judge LLM configuration

##### `config.synthetic_user`
- **Type:** `ScenarioLLMOverride` object
- **Required:** No
- **Description:** Overrides for the synthetic user LLM configuration

#### ScenarioLLMOverride Fields

| Field | Type | Description |
|-------|------|-------------|
| `model` | `string \| null` | Override the model for this scenario |
| `temperature` | `float \| null` | Override the temperature for this scenario |
| `extra_instructions` | `string \| null` | Additional instructions appended to system prompts |

**Note:** Only specified fields are overridden. Unspecified fields inherit from global config.

#### Per-Scenario Configuration Examples

**Custom judge instructions for strict validation:**
```yaml
name: Strict Tool Parameter Test
description: Verifies exact parameter matching

config:
  judge:
    extra_instructions: |
      Be extremely strict about tool parameter validation.
      Any parameter that doesn't match exactly should fail the test.
      Do not accept approximate or "close enough" values.

synthetic_user:
  persona: A precise user who expects exact results
  initial_query: Get the weather for latitude 37.7749, longitude -122.4194

evaluation:
  correctness_criteria:
    - The agent calls get_weather with exact coordinates provided
```

**Different model for complex scenario:**
```yaml
name: Complex Multi-Step Reasoning
description: Tests multi-step problem solving

config:
  judge:
    model: gpt-4o  # Use more capable model for complex evaluation
  synthetic_user:
    model: gpt-4o-mini
    temperature: 0.5  # Slightly more varied responses

synthetic_user:
  persona: A user with a complex, multi-part question
  initial_query: I need to plan a trip considering weather, flights, and hotels

evaluation:
  correctness_criteria:
    - The agent addresses all three aspects of the query
```

**Customizing synthetic user behavior:**
```yaml
name: Impatient User Test
description: Tests agent response to impatient users

config:
  synthetic_user:
    extra_instructions: |
      You are in a hurry. Express frustration if the agent asks
      more than one clarifying question. Use short, curt responses.

synthetic_user:
  persona: A busy executive with no time to spare
  initial_query: Weather now!
  clarification_behavior:
    traits:
      patience: low
      verbosity: concise

evaluation:
  correctness_criteria:
    - The agent provides weather information quickly
    - The agent minimizes clarifying questions
```

### SyntheticUserConfig Fields

#### `persona`
- **Type:** `string`
- **Required:** Yes
- **Constraints:** Minimum length: 1 character
- **Description:** Character description that guides the synthetic user's behavior
- **Example:** `"A busy professional who needs quick weather information"`

#### `initial_query`
- **Type:** `string`
- **Required:** Yes
- **Constraints:** Minimum length: 1 character
- **Description:** The first message the synthetic user sends to the agent
- **Example:** `"What's the weather like?"`

#### `max_turns`
- **Type:** `integer`
- **Required:** No
- **Default:** `10`
- **Constraints:**
  - Minimum: 1
  - Maximum: 100
- **Description:** Maximum number of conversation turns before timeout
- **Example:** `8`

#### `clarification_behavior`
- **Type:** `ClarificationBehavior` object
- **Required:** No
- **Default:** `{}`
- **Description:** How the user responds when asked clarifying questions

##### `clarification_behavior.known_facts`
- **Type:** `list[string]`
- **Required:** No
- **Default:** `[]`
- **Description:** Information the user knows and can provide when asked
- **Example:**
  ```yaml
  known_facts:
    - "I'm in San Francisco"
    - "I need the forecast for tomorrow"
  ```

##### `clarification_behavior.unknown_facts`
- **Type:** `list[string]`
- **Required:** No
- **Default:** `[]`
- **Description:** Information the user doesn't know (will say so if asked)
- **Example:**
  ```yaml
  unknown_facts:
    - "The exact postal code"
    - "Temperature in Celsius or Fahrenheit"
  ```

##### `clarification_behavior.traits`
- **Type:** `UserTraits` object
- **Required:** No
- **Default:** `{patience: "medium", verbosity: "concise", expertise: "novice"}`

###### `traits.patience`
- **Type:** `enum[string]`
- **Required:** No
- **Default:** `"medium"`
- **Values:** `"low"`, `"medium"`, `"high"`
- **Description:** How tolerant the user is of clarifying questions
  - `low`: Gets frustrated quickly, may give up
  - `medium`: Reasonably patient, will answer a few questions
  - `high`: Very patient, will engage in extended clarification

###### `traits.verbosity`
- **Type:** `enum[string]`
- **Required:** No
- **Default:** `"concise"`
- **Values:** `"concise"`, `"medium"`, `"verbose"`
- **Description:** How much detail the user provides in responses
  - `concise`: Brief, minimal answers
  - `medium`: Balanced responses
  - `verbose`: Detailed, chatty responses

###### `traits.expertise`
- **Type:** `enum[string]`
- **Required:** No
- **Default:** `"novice"`
- **Values:** `"novice"`, `"intermediate"`, `"expert"`
- **Description:** User's technical knowledge level
  - `novice`: Non-technical, may use imprecise terminology
  - `intermediate`: Some technical knowledge
  - `expert`: Deep technical understanding, uses precise terms

### EvaluationConfig Fields

#### `correctness_criteria`
- **Type:** `list[string]`
- **Required:** Yes
- **Constraints:** Minimum length: 1
- **Description:** Things the agent must do correctly to pass
- **Example:**
  ```yaml
  correctness_criteria:
    - "The agent retrieves weather data for the correct city"
    - "The agent provides temperature in the requested units"
  ```

#### `failure_criteria`
- **Type:** `list[string]`
- **Required:** No
- **Default:** `[]`
- **Description:** Behaviors that indicate test failure
- **Example:**
  ```yaml
  failure_criteria:
    - "The agent assumes the city without asking"
    - "The agent provides data for the wrong location"
  ```

#### `tool_usage`
- **Type:** `ToolUsageConfig` object
- **Required:** No
- **Default:** `{}`

##### `tool_usage.required_tools`
- **Type:** `list[string]`
- **Required:** No
- **Default:** `[]`
- **Description:** Tools that must be called at least once
- **Example:** `["get_weather", "geocode_location"]`

##### `tool_usage.optional_tools`
- **Type:** `list[string]`
- **Required:** No
- **Default:** `[]`
- **Description:** Tools that may be called but aren't required
- **Example:** `["get_timezone"]`

##### `tool_usage.prohibited_tools`
- **Type:** `list[string]`
- **Required:** No
- **Default:** `[]`
- **Description:** Tools that should never be called
- **Example:** `["delete_file", "send_email"]`

##### `tool_usage.tool_call_criteria`
- **Type:** `list[ToolCallCriterion]`
- **Required:** No
- **Default:** `[]`
- **Description:** Specific assertions about how tools should be called

###### ToolCallCriterion Fields

**`tool`**
- **Type:** `string`
- **Required:** Yes
- **Constraints:** Minimum length: 1
- **Description:** Name of the tool this criterion applies to

**`assertions`**
- **Type:** `list[string]`
- **Required:** No
- **Default:** `[]`
- **Description:** Conditions that must be true about this tool's usage
- **Example:**
  ```yaml
  tool_call_criteria:
    - tool: get_weather
      assertions:
        - "Called with the city name extracted from user input"
        - "Units parameter matches user preference"
  ```

#### `efficiency`
- **Type:** `EfficiencyConfig` object
- **Required:** No
- **Default:** `{}`

##### `efficiency.max_tool_calls`
- **Type:** `integer` or `null`
- **Required:** No
- **Default:** `null`
- **Description:** Maximum number of tool calls allowed (null = no limit)
- **Example:** `5`

##### `efficiency.max_llm_tokens`
- **Type:** `integer` or `null`
- **Required:** No
- **Default:** `null`
- **Description:** Maximum LLM tokens consumed (null = no limit)
- **Example:** `10000`

##### `efficiency.max_conversation_turns`
- **Type:** `integer` or `null`
- **Required:** No
- **Default:** `null`
- **Description:** Maximum conversation turns allowed (null = no limit)
- **Example:** `6`

## Complete Example

This example shows all available fields:

```yaml
name: Comprehensive Weather Query Test
description: |
  Tests the agent's ability to handle a weather query with missing information,
  ask appropriate clarifying questions, and provide accurate results with
  proper error handling.

# Optional: Skip this scenario
# skip: true  # or skip: "Reason for skipping"

# Optional: Per-scenario LLM configuration overrides
config:
  judge:
    extra_instructions: |
      Pay special attention to whether the agent correctly interprets
      "tomorrow" as the next calendar day, not "in 24 hours".
  synthetic_user:
    temperature: 0.2  # Slightly varied responses

synthetic_user:
  persona: |
    A busy professional who needs quick weather information but tends to
    provide incomplete details in initial queries. Moderately patient but
    prefers efficient interactions.

  initial_query: "What's the weather like?"

  max_turns: 8

  clarification_behavior:
    known_facts:
      - "I'm asking about San Francisco"
      - "I need the forecast for tomorrow"
      - "I prefer Fahrenheit"

    unknown_facts:
      - "The exact postal code"
      - "Whether to include hourly breakdown"

    traits:
      patience: medium
      verbosity: concise
      expertise: novice

evaluation:
  correctness_criteria:
    - "The agent asks for the location since it wasn't specified"
    - "The agent retrieves weather data for San Francisco"
    - "The agent provides tomorrow's forecast, not today's"
    - "Temperature is displayed in Fahrenheit"

  failure_criteria:
    - "The agent assumes a location without asking"
    - "The agent provides today's weather instead of tomorrow's"
    - "The agent crashes on missing information"

  tool_usage:
    required_tools:
      - get_weather

    optional_tools:
      - geocode_location
      - get_timezone

    prohibited_tools:
      - delete_file
      - send_email

    tool_call_criteria:
      - tool: get_weather
        assertions:
          - "Called with city='San Francisco' or equivalent"
          - "Units parameter is 'fahrenheit' or 'imperial'"
          - "Date parameter is tomorrow's date"

      - tool: geocode_location
        assertions:
          - "If called, uses 'San Francisco' as input"

  efficiency:
    max_tool_calls: 5
    max_llm_tokens: 8000
    max_conversation_turns: 6

tags:
  - weather
  - clarification
  - intermediate
```

## Minimal Example

This example shows only required fields:

```yaml
name: Basic Greeting Test
description: Verifies the agent responds to a simple greeting.

synthetic_user:
  persona: A casual user seeking friendly interaction
  initial_query: "Hello! How are you?"

evaluation:
  correctness_criteria:
    - "The agent responds with a greeting"
    - "The agent offers assistance"
```

## Validation Rules

MCProbe validates scenarios according to these rules:

1. **Required Fields:** `name`, `description`, `synthetic_user.persona`, `synthetic_user.initial_query`, and `evaluation.correctness_criteria` must be present
2. **Non-Empty Strings:** `name` and `description` cannot be empty or only whitespace
3. **Positive Integers:** `max_turns` must be between 1 and 100
4. **Non-Empty Lists:** `correctness_criteria` must contain at least one item
5. **Enum Values:** Patience, verbosity, and expertise must use valid enum values
6. **Tool Names:** Tool names in `tool_call_criteria` must be non-empty strings
7. **Skip Field:** If provided, `skip` must be a boolean or non-empty string

## Common Patterns

### Skipping Scenarios

Skip scenarios that are not ready or temporarily disabled:

```yaml
name: Future Analytics Feature
description: Tests analytics dashboard integration
skip: "Waiting on analytics API implementation"

synthetic_user:
  persona: A data analyst
  initial_query: "Show me the analytics dashboard"

evaluation:
  correctness_criteria:
    - "Dashboard displays correct metrics"
```

Or skip without a reason:

```yaml
name: Experimental Feature
description: Tests experimental functionality
skip: true

synthetic_user:
  persona: A power user
  initial_query: "Enable experimental mode"
```

### Testing Clarification
```yaml
synthetic_user:
  initial_query: "What's the weather?"  # Ambiguous
  clarification_behavior:
    known_facts:
      - "I'm in Seattle"
```

### Testing Error Handling
```yaml
evaluation:
  failure_criteria:
    - "The agent crashes or shows error messages to user"
    - "The agent provides incorrect default values"
```

### Testing Efficiency
```yaml
evaluation:
  efficiency:
    max_tool_calls: 2
    max_conversation_turns: 3
  correctness_criteria:
    - "The agent completes the task efficiently"
```

### Testing Tool Usage
```yaml
evaluation:
  tool_usage:
    required_tools: [get_weather]
    prohibited_tools: [delete_file, send_email]
    tool_call_criteria:
      - tool: get_weather
        assertions:
          - "Called exactly once"
          - "City parameter is not empty"
```

## Next Steps

- [Learn about synthetic user configuration](./synthetic-user.md)
- [Understand evaluation criteria](./evaluation.md)
- [See complete scenario examples](./examples.md)
