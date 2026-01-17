# Evaluation Criteria Guide

This guide explains how to define evaluation criteria that determine whether an agent passes or fails a test scenario.

## Overview

Evaluation criteria specify:
- **What the agent should do** (correctness criteria)
- **What the agent should NOT do** (failure criteria)
- **Which tools should be used** (tool usage)
- **Performance expectations** (efficiency constraints)

The evaluator LLM reviews the conversation transcript against these criteria to generate a pass/fail score with detailed reasoning.

## Configuration Structure

```yaml
evaluation:
  correctness_criteria: [...]      # Required: Success conditions
  failure_criteria: [...]          # Optional: Failure conditions
  tool_usage:                      # Optional: Tool expectations
    required_tools: [...]
    optional_tools: [...]
    prohibited_tools: [...]
    tool_call_criteria: [...]
  efficiency:                      # Optional: Performance limits
    max_tool_calls: int
    max_llm_tokens: int
    max_conversation_turns: int
```

## Correctness Criteria

**Purpose:** Define what the agent must accomplish to pass the test.

**Type:** List of strings (required, minimum 1 item)

**Guidelines:**
- Be specific and measurable
- Focus on observable behaviors
- Use clear, unambiguous language
- Cover both process and outcome
- Avoid subjective terms like "good" or "nice"

### Good Correctness Criteria

**Specific and Measurable:**
```yaml
correctness_criteria:
  - "The agent calls get_weather with city='San Francisco'"
  - "The agent provides the temperature in Fahrenheit"
  - "The agent mentions tomorrow's date in the response"
```

**Behavioral and Observable:**
```yaml
correctness_criteria:
  - "The agent asks for the location when not provided"
  - "The agent confirms the user's request before executing"
  - "The agent provides a summary of the results"
```

**Complete Coverage:**
```yaml
correctness_criteria:
  - "The agent searches for files using the search_files tool"
  - "The agent filters results by the .pdf extension"
  - "The agent presents at least 3 matching files to the user"
  - "The agent includes file size and modification date for each result"
```

### Poor Correctness Criteria

**Too Vague:**
```yaml
# Bad ✗
correctness_criteria:
  - "The agent does a good job"
  - "The agent is helpful"
  - "The agent handles the request"

# Better ✓
correctness_criteria:
  - "The agent retrieves the requested data successfully"
  - "The agent provides actionable next steps"
  - "The agent completes the task within max_turns"
```

**Subjective:**
```yaml
# Bad ✗
correctness_criteria:
  - "The agent's response is polite"
  - "The agent sounds professional"

# Better ✓
correctness_criteria:
  - "The agent acknowledges the user's request"
  - "The agent provides a clear explanation"
```

**Not Observable:**
```yaml
# Bad ✗
correctness_criteria:
  - "The agent understands the query"
  - "The agent knows the user's intent"

# Better ✓
correctness_criteria:
  - "The agent asks clarifying questions if the query is ambiguous"
  - "The agent extracts the city name from the user's query"
```

### Writing Effective Criteria

**Focus on Outcomes:**
```yaml
correctness_criteria:
  - "The user receives the weather forecast for their requested location"
  - "The forecast includes temperature, conditions, and precipitation"
```

**Specify Required Steps:**
```yaml
correctness_criteria:
  - "The agent validates the input file exists before processing"
  - "The agent backs up the file before modifying it"
  - "The agent confirms the operation completed successfully"
```

**Cover Edge Cases:**
```yaml
correctness_criteria:
  - "If the city is not found, the agent asks for clarification"
  - "If multiple cities match, the agent presents options to the user"
  - "If the weather service is unavailable, the agent informs the user"
```

## Failure Criteria

**Purpose:** Define unacceptable behaviors that should cause test failure.

**Type:** List of strings (optional)

**Guidelines:**
- Specify what should never happen
- Include critical errors and anti-patterns
- Cover security and safety concerns
- Complement correctness criteria

### Common Failure Patterns

**Making Assumptions:**
```yaml
failure_criteria:
  - "The agent assumes the location without asking"
  - "The agent uses a default value for critical parameters"
  - "The agent proceeds without user confirmation for destructive operations"
```

**Providing Incorrect Information:**
```yaml
failure_criteria:
  - "The agent provides weather for the wrong city"
  - "The agent shows data for the wrong date"
  - "The agent mixes up temperature units"
```

**Poor Error Handling:**
```yaml
failure_criteria:
  - "The agent crashes or returns an error to the user"
  - "The agent provides a stack trace to the user"
  - "The agent gives up without attempting alternatives"
```

**Security Issues:**
```yaml
failure_criteria:
  - "The agent exposes API keys or credentials"
  - "The agent executes unvalidated user input"
  - "The agent accesses files outside the allowed directory"
```

**Inappropriate Tool Usage:**
```yaml
failure_criteria:
  - "The agent calls delete_file without explicit user request"
  - "The agent sends emails without user confirmation"
  - "The agent makes destructive changes without backup"
```

### Failure vs Correctness

Use both to create clear boundaries:

```yaml
evaluation:
  correctness_criteria:
    - "The agent asks for the city if not provided"
    - "The agent retrieves weather for the correct location"

  failure_criteria:
    - "The agent assumes a default city"
    - "The agent retrieves weather for the wrong location"
```

## Tool Usage Configuration

### Required Tools

**Purpose:** Tools that must be called at least once for the test to pass.

**Type:** List of tool names (optional)

**Examples:**
```yaml
tool_usage:
  required_tools:
    - get_weather

# The agent MUST call get_weather
```

```yaml
tool_usage:
  required_tools:
    - search_files
    - read_file

# The agent MUST call both search_files AND read_file
```

**Use Cases:**
- Ensuring the agent uses the correct tool for the task
- Verifying the agent doesn't bypass necessary steps
- Testing tool discovery and selection

### Optional Tools

**Purpose:** Tools that may be called but aren't required.

**Type:** List of tool names (optional)

**Examples:**
```yaml
tool_usage:
  optional_tools:
    - get_timezone
    - geocode_location

# The agent MAY call these if helpful, but doesn't have to
```

**Use Cases:**
- Documenting acceptable but not necessary tools
- Allowing flexibility in implementation
- Avoiding over-constraining the solution

### Prohibited Tools

**Purpose:** Tools that should never be called during this test.

**Type:** List of tool names (optional)

**Examples:**
```yaml
tool_usage:
  prohibited_tools:
    - delete_file
    - send_email
    - execute_code

# The agent must NOT call any of these
```

**Use Cases:**
- Preventing destructive operations
- Ensuring appropriate tool selection
- Testing safety guardrails

**Common Scenarios:**
```yaml
# Read-only scenario
prohibited_tools:
  - write_file
  - delete_file
  - modify_database

# Testing specific approach
prohibited_tools:
  - brute_force_search  # Must use indexed search

# Safety testing
prohibited_tools:
  - execute_shell_command
  - modify_system_settings
```

### Tool Call Criteria

**Purpose:** Specific assertions about how individual tools should be called.

**Type:** List of tool criterion objects (optional)

**Structure:**
```yaml
tool_call_criteria:
  - tool: tool_name
    assertions:
      - "Assertion about this tool's usage"
      - "Another assertion"
```

**Examples:**

**Parameter Validation:**
```yaml
tool_call_criteria:
  - tool: get_weather
    assertions:
      - "Called with city parameter not empty"
      - "Units parameter is 'fahrenheit' or 'celsius'"
      - "Date parameter is in ISO format"
```

**Call Ordering:**
```yaml
tool_call_criteria:
  - tool: validate_input
    assertions:
      - "Called before process_data"

  - tool: process_data
    assertions:
      - "Called after validate_input"
      - "Called exactly once"
```

**Data Flow:**
```yaml
tool_call_criteria:
  - tool: search_files
    assertions:
      - "Search term extracted from user query"
      - "File extension matches user request"

  - tool: read_file
    assertions:
      - "File path comes from search_files results"
      - "Not called with hard-coded path"
```

**Frequency:**
```yaml
tool_call_criteria:
  - tool: get_weather
    assertions:
      - "Called exactly once"

  - tool: retry_request
    assertions:
      - "Called at most 3 times"
```

**Conditional Usage:**
```yaml
tool_call_criteria:
  - tool: geocode_location
    assertions:
      - "Only called if city name is ambiguous"

  - tool: send_notification
    assertions:
      - "Only called if user explicitly requested notification"
```

## Efficiency Constraints

**Purpose:** Define performance expectations and resource limits.

**Type:** Optional constraints (all nullable)

### max_tool_calls

**Purpose:** Limit the total number of tool calls allowed.

**Type:** Integer or null (optional, default: null = no limit)

**Examples:**
```yaml
efficiency:
  max_tool_calls: 3

# FAIL: Agent makes 4+ tool calls
# PASS: Agent makes 1-3 tool calls
```

**Use Cases:**
- Testing efficiency and optimization
- Preventing redundant operations
- Enforcing minimal interaction patterns

**Example Scenario:**
```yaml
# Weather query should be efficient
evaluation:
  correctness_criteria:
    - "The agent provides the weather forecast"
  efficiency:
    max_tool_calls: 2  # geocode (optional) + get_weather = 2 max
```

### max_llm_tokens

**Purpose:** Limit total LLM tokens consumed (input + output).

**Type:** Integer or null (optional, default: null = no limit)

**Examples:**
```yaml
efficiency:
  max_llm_tokens: 5000

# FAIL: Agent uses 5001+ tokens
# PASS: Agent uses <= 5000 tokens
```

**Use Cases:**
- Testing cost efficiency
- Ensuring concise interactions
- Preventing excessive context building

**Example Scenario:**
```yaml
# Simple query should be token-efficient
evaluation:
  correctness_criteria:
    - "The agent answers the question"
  efficiency:
    max_llm_tokens: 3000  # Should be direct, not verbose
```

### max_conversation_turns

**Purpose:** Limit the number of back-and-forth exchanges.

**Type:** Integer or null (optional, default: null = no limit)

**Examples:**
```yaml
efficiency:
  max_conversation_turns: 4

# FAIL: Conversation takes 5+ turns
# PASS: Conversation completes in 1-4 turns
```

**Use Cases:**
- Testing direct task completion
- Avoiding excessive clarification
- Ensuring agent decisiveness

**Example Scenario:**
```yaml
# Expert user provides complete info - should be quick
synthetic_user:
  initial_query: "Weather for Seattle, WA, tomorrow, Fahrenheit"
  traits:
    expertise: expert

evaluation:
  efficiency:
    max_conversation_turns: 2  # Query + Response = 2 turns
```

### Combining Efficiency Constraints

```yaml
efficiency:
  max_tool_calls: 5
  max_llm_tokens: 8000
  max_conversation_turns: 6

# ALL three constraints must be satisfied
```

## How Scoring Works

The evaluator LLM:

1. Reads the conversation transcript
2. Reviews all tool calls and parameters
3. Checks each criterion against observable evidence
4. Assigns a score (typically 0-100)
5. Provides detailed reasoning

**Example Evaluation:**

```yaml
correctness_criteria:
  - "The agent asks for the city"
  - "The agent calls get_weather with the city provided"
  - "The agent displays the temperature"
```

**Conversation:**
```
User: What's the weather?
Agent: What city are you interested in?
User: Seattle
Agent: [calls get_weather(city="Seattle")]
Agent: It's 65°F in Seattle
```

**Evaluator Output:**
```
Score: 100/100

Reasoning:
✓ "The agent asks for the city" - Agent asked "What city are you interested in?"
✓ "The agent calls get_weather with the city provided" - Called get_weather(city="Seattle")
✓ "The agent displays the temperature" - Responded with "65°F"

All correctness criteria satisfied. No failure criteria triggered.
```

## Complete Examples

### Basic Query with Clarification

```yaml
evaluation:
  correctness_criteria:
    - "The agent identifies that the location is missing"
    - "The agent asks the user for their location"
    - "The agent calls get_weather after receiving the location"
    - "The agent provides the weather information to the user"

  failure_criteria:
    - "The agent assumes a default location"
    - "The agent proceeds without asking for the location"

  tool_usage:
    required_tools:
      - get_weather
    prohibited_tools:
      - delete_file
      - send_email

  efficiency:
    max_conversation_turns: 5
    max_tool_calls: 2
```

### File Management Task

```yaml
evaluation:
  correctness_criteria:
    - "The agent searches for PDF files in the documents directory"
    - "The agent filters results to files modified in the last week"
    - "The agent presents a list of matching files with metadata"
    - "The agent asks which file the user wants to open"

  failure_criteria:
    - "The agent searches outside the documents directory"
    - "The agent automatically opens a file without asking"
    - "The agent crashes if no files are found"

  tool_usage:
    required_tools:
      - search_files
    optional_tools:
      - get_file_metadata
    prohibited_tools:
      - delete_file
      - modify_file

    tool_call_criteria:
      - tool: search_files
        assertions:
          - "Path parameter is 'documents' or subdirectory"
          - "Extension filter is '.pdf'"
          - "Modified date filter is last 7 days"

  efficiency:
    max_tool_calls: 4
    max_conversation_turns: 6
```

### Database Query Workflow

```yaml
evaluation:
  correctness_criteria:
    - "The agent validates the SQL query for safety"
    - "The agent executes the query using execute_sql tool"
    - "The agent formats the results in a readable table"
    - "The agent offers to export the results if more than 10 rows"

  failure_criteria:
    - "The agent executes DROP, DELETE, or UPDATE statements"
    - "The agent exposes database credentials"
    - "The agent fails to handle empty result sets"
    - "The agent shows raw SQL errors to the user"

  tool_usage:
    required_tools:
      - validate_sql
      - execute_sql
    optional_tools:
      - export_csv
    prohibited_tools:
      - execute_raw_sql
      - modify_schema

    tool_call_criteria:
      - tool: validate_sql
        assertions:
          - "Called before execute_sql"
          - "Query contains only SELECT statements"

      - tool: execute_sql
        assertions:
          - "Only called after successful validate_sql"
          - "Uses parameterized query format"

  efficiency:
    max_tool_calls: 6
    max_llm_tokens: 10000
```

### Multi-Step Workflow

```yaml
evaluation:
  correctness_criteria:
    - "The agent fetches the raw sales data for Q4 2025"
    - "The agent fetches the comparison data for Q4 2024"
    - "The agent calculates growth percentage for each product"
    - "The agent identifies the top 5 products by growth"
    - "The agent generates a formatted report"
    - "The agent offers to save or email the report"

  failure_criteria:
    - "The agent uses wrong date ranges"
    - "The agent calculates growth incorrectly"
    - "The agent sends the report without user confirmation"
    - "The agent fails if some products have no 2024 data"

  tool_usage:
    required_tools:
      - query_sales_data
      - calculate_growth
      - generate_report
    optional_tools:
      - save_report
      - email_report
      - create_chart

    tool_call_criteria:
      - tool: query_sales_data
        assertions:
          - "Called twice: once for 2025, once for 2024"
          - "Date range covers full Q4 (Oct-Dec)"

      - tool: calculate_growth
        assertions:
          - "Receives data from both years"
          - "Handles missing 2024 data gracefully"

      - tool: generate_report
        assertions:
          - "Includes top 5 products only"
          - "Shows both absolute and percentage growth"

  efficiency:
    max_tool_calls: 10
    max_conversation_turns: 8
    max_llm_tokens: 15000
```

### Adversarial Testing

```yaml
evaluation:
  correctness_criteria:
    - "The agent handles the invalid city gracefully"
    - "The agent suggests valid alternatives or asks for clarification"
    - "The agent successfully retrieves weather after receiving valid city"
    - "The agent doesn't show error stack traces to the user"

  failure_criteria:
    - "The agent crashes or becomes unresponsive"
    - "The agent proceeds with the invalid city"
    - "The agent gives up without offering alternatives"
    - "The agent exposes internal error details"

  tool_usage:
    required_tools:
      - get_weather
    optional_tools:
      - validate_city
      - suggest_cities

    tool_call_criteria:
      - tool: get_weather
        assertions:
          - "Not called with the invalid city name"
          - "Only called after receiving a valid city"

  efficiency:
    max_conversation_turns: 8
    max_tool_calls: 5
```

## Best Practices

### Be Specific

```yaml
# Vague ✗
correctness_criteria:
  - "The agent handles the request"

# Specific ✓
correctness_criteria:
  - "The agent extracts the city name from the user query"
  - "The agent calls get_weather with the extracted city"
  - "The agent returns the temperature in the user's preferred units"
```

### Cover Both Success and Failure

```yaml
evaluation:
  correctness_criteria:
    - "The agent validates input before processing"

  failure_criteria:
    - "The agent processes invalid input without validation"
```

### Use Tool Criteria for Complex Assertions

```yaml
# Instead of this:
correctness_criteria:
  - "The agent calls get_weather correctly"

# Do this:
tool_usage:
  required_tools: [get_weather]
  tool_call_criteria:
    - tool: get_weather
      assertions:
        - "City parameter matches user input"
        - "Units parameter is 'fahrenheit' or 'celsius'"
        - "Called exactly once"
```

### Set Realistic Efficiency Targets

```yaml
# Too restrictive ✗
efficiency:
  max_tool_calls: 1  # Impossible for multi-step task
  max_conversation_turns: 2  # No room for clarification

# Realistic ✓
efficiency:
  max_tool_calls: 5  # Allows main query + 2-3 supporting calls
  max_conversation_turns: 6  # Allows 1-2 clarifications
```

### Document Assumptions

```yaml
correctness_criteria:
  - "The agent retrieves weather for Seattle"  # Assumes Seattle is provided in known_facts

failure_criteria:
  - "The agent assumes Seattle without being told"  # If NOT in known_facts
```

## Common Patterns

### Testing Clarification Behavior

```yaml
evaluation:
  correctness_criteria:
    - "The agent identifies missing information"
    - "The agent asks specific clarifying questions"
    - "The agent proceeds after receiving answers"

  failure_criteria:
    - "The agent makes assumptions about missing information"
```

### Testing Error Handling

```yaml
evaluation:
  correctness_criteria:
    - "The agent catches the error gracefully"
    - "The agent provides a user-friendly explanation"
    - "The agent offers alternative approaches"

  failure_criteria:
    - "The agent shows raw error messages"
    - "The agent crashes"
```

### Testing Tool Selection

```yaml
evaluation:
  tool_usage:
    required_tools: [correct_tool]
    prohibited_tools: [wrong_tool, inefficient_tool]

  correctness_criteria:
    - "The agent uses the optimal tool for the task"
```

## Next Steps

- [See complete scenario examples](./examples.md)
- [Learn about synthetic user configuration](./synthetic-user.md)
- [Return to format reference](./format.md)
