# Your First Real Scenario

This tutorial teaches you how to create a comprehensive test scenario for an MCP-powered agent. We'll build a weather assistant scenario step by step.

## What You'll Learn

- Anatomy of a scenario file
- Creating realistic user personas
- Defining clarification behavior
- Setting tool usage expectations
- Writing evaluation criteria
- Iterating and improving scenarios

## Prerequisites

Before starting, make sure you've:
- Completed the [Quickstart Guide](quickstart.md)
- Installed MCProbe and Ollama
- Understand basic scenario structure

## The Scenario: Weather Planning

We'll create a test for a weather assistant that helps users plan trips. The scenario will:
- Test that the agent asks appropriate clarifying questions
- Verify correct tool usage (weather API calls)
- Ensure the final answer is comprehensive
- Handle ambiguous user requests

## Step 1: Define the Basic Structure

Create a file named `weather_trip.yaml`:

```yaml
name: Trip Weather Planning
description: User planning a road trip needs weather forecasts for multiple cities

synthetic_user:
  persona: |
    You are planning a road trip from Phoenix to San Francisco next week.
    You want to know what weather to expect along the route.
    You're flexible on exact dates but need to travel sometime in the next 7 days.

  initial_query: "What's the weather going to be like for a road trip from Phoenix to SF?"

  max_turns: 10

evaluation:
  correctness_criteria:
    - Provides weather forecast for Phoenix area
    - Provides weather forecast for San Francisco area

  failure_criteria:
    - Provides weather for wrong cities
    - Only provides current weather, not forecast
```

This is the skeleton. Let's build it out section by section.

## Step 2: Add Clarification Behavior

Real users don't always provide complete information upfront. Define what your synthetic user knows and doesn't know:

```yaml
synthetic_user:
  persona: |
    You are planning a road trip from Phoenix to San Francisco next week.
    You want to know what weather to expect along the route.
    You're flexible on exact dates but need to travel sometime in the next 7 days.

  initial_query: "What's the weather going to be like for a road trip from Phoenix to SF?"

  clarification_behavior:
    # Information the user knows and can provide if asked
    known_facts:
      - "Leaving from Phoenix, Arizona"
      - "Destination is San Francisco, California"
      - "Flexible on dates within the next 7 days"
      - "Will be driving, takes about 10-12 hours"
      - "Prefer to avoid rain if possible"

    # Information the user doesn't know (should say "I don't know")
    unknown_facts:
      - "Exact route preferences (I-10 vs I-40)"
      - "Specific times of day for travel"
      - "Hotel locations along the way"

    # Personality traits affecting responses
    traits:
      patience: medium     # Will answer 2-3 clarifying questions
      verbosity: concise   # Gives brief answers unless asked for details
      expertise: novice    # Doesn't know technical weather terminology

  max_turns: 10
```

### Understanding Clarification Behavior

**known_facts**: When the agent asks questions, the synthetic user will provide this information naturally. For example:
- Agent: "When are you planning to leave?"
- User: "Sometime in the next 7 days, I'm flexible"

**unknown_facts**: The user will honestly say they don't know. For example:
- Agent: "Which route will you take?"
- User: "I'm not sure, I haven't decided yet"

**traits**: Affect how the user responds:
- `patience: low` - Gets frustrated after 1-2 clarifying questions
- `patience: medium` - Patient for 2-3 questions
- `patience: high` - Will answer many questions

- `verbosity: concise` - Short, direct answers
- `verbosity: medium` - Normal conversational responses
- `verbosity: verbose` - Detailed, elaborate responses

- `expertise: novice` - No technical jargon, may misunderstand complex questions
- `expertise: intermediate` - Some domain knowledge
- `expertise: expert` - Deep domain knowledge, uses technical terms

## Step 3: Define Complete Correctness Criteria

Specify exactly what the final answer must include:

```yaml
evaluation:
  correctness_criteria:
    - Provides weather forecast for Phoenix area
    - Provides weather forecast for San Francisco area
    - Mentions temperature ranges or specific temperatures
    - Mentions precipitation likelihood or conditions
    - Covers multiple days (not just a single day)
    - Acknowledges the trip context (not just standalone city forecasts)
```

Each criterion should be:
- **Specific**: "Mentions precipitation" not "provides good weather info"
- **Measurable**: The judge can clearly evaluate true/false
- **Relevant**: Directly relates to the user's goal

## Step 4: Add Failure Criteria

Define what should NOT happen:

```yaml
evaluation:
  failure_criteria:
    - Provides weather for wrong cities
    - Only provides current weather, not forecast
    - Makes up specific numbers without using weather tools
    - Asks more than 3 clarifying questions before providing any answer
    - Gets stuck in a loop asking the same questions repeatedly
    - Confuses Phoenix with another city
```

Failure criteria are "any one triggers failure" - if any of these happen, the test fails regardless of correctness criteria.

Use failure criteria for:
- Critical mistakes (wrong data)
- Bad UX (too many questions, loops)
- Hallucination (making up data)
- Logic errors (misunderstanding the task)

## Step 5: Specify Tool Usage Expectations

Define which MCP tools should be used and how:

```yaml
evaluation:
  tool_usage:
    required_tools:
      - "get_weather_forecast"    # Must use this tool

    optional_tools:
      - "get_current_weather"     # May use but not required
      - "get_location_coordinates" # May use for geocoding

    prohibited_tools:
      - "send_email"              # Should never use this

    tool_call_criteria:
      - tool: "get_weather_forecast"
        assertions:
          - "location parameter includes 'Phoenix' or coordinates near Phoenix (33.4, -112.0)"
          - "location parameter includes 'San Francisco' or coordinates near SF (37.7, -122.4)"
          - "forecast_days parameter is at least 3"
          - "Called at least twice (once for each city)"
```

### Understanding Tool Usage

**required_tools**: The agent MUST call these tools at least once. If it doesn't, the test fails.

**optional_tools**: The agent may call these, and it's okay either way.

**prohibited_tools**: If the agent calls any of these, the test fails immediately.

**tool_call_criteria**: Specific assertions about how tools should be called. Each assertion is evaluated by the judge against the actual tool calls made during the conversation.

## Step 6: Add Efficiency Targets (Optional)

Set performance expectations:

```yaml
evaluation:
  efficiency:
    max_tool_calls: 6              # Don't make excessive API calls
    max_conversation_turns: 6       # Keep it concise
    max_llm_tokens: 4000           # Token budget
```

These are soft limits - exceeding them lowers the score but doesn't necessarily fail the test.

## Complete Scenario

Here's the full `weather_trip.yaml`:

```yaml
name: Trip Weather Planning
description: User planning a road trip needs weather forecasts for multiple cities

synthetic_user:
  persona: |
    You are planning a road trip from Phoenix to San Francisco next week.
    You want to know what weather to expect along the route.
    You're flexible on exact dates but need to travel sometime in the next 7 days.

  initial_query: "What's the weather going to be like for a road trip from Phoenix to SF?"

  clarification_behavior:
    known_facts:
      - "Leaving from Phoenix, Arizona"
      - "Destination is San Francisco, California"
      - "Flexible on dates within the next 7 days"
      - "Will be driving, takes about 10-12 hours"
      - "Prefer to avoid rain if possible"

    unknown_facts:
      - "Exact route preferences (I-10 vs I-40)"
      - "Specific times of day for travel"
      - "Hotel locations along the way"

    traits:
      patience: medium
      verbosity: concise
      expertise: novice

  max_turns: 10

evaluation:
  correctness_criteria:
    - Provides weather forecast for Phoenix area
    - Provides weather forecast for San Francisco area
    - Mentions temperature ranges or specific temperatures
    - Mentions precipitation likelihood or conditions
    - Covers multiple days (not just a single day)
    - Acknowledges the trip context (not just standalone city forecasts)

  failure_criteria:
    - Provides weather for wrong cities
    - Only provides current weather, not forecast
    - Makes up specific numbers without using weather tools
    - Asks more than 3 clarifying questions before providing any answer
    - Gets stuck in a loop asking the same questions repeatedly
    - Confuses Phoenix with another city

  tool_usage:
    required_tools:
      - "get_weather_forecast"
    optional_tools:
      - "get_current_weather"
      - "get_location_coordinates"
    prohibited_tools: []

    tool_call_criteria:
      - tool: "get_weather_forecast"
        assertions:
          - "location parameter includes 'Phoenix' or coordinates near Phoenix"
          - "location parameter includes 'San Francisco' or coordinates near SF"
          - "forecast_days parameter is at least 3"

  efficiency:
    max_tool_calls: 6
    max_conversation_turns: 6

tags:
  - weather
  - multi-city
  - clarification
```

## Step 7: Validate the Scenario

Check for syntax errors:

```bash
mcprobe validate weather_trip.yaml
```

Expected output:
```
Validated 1 scenario(s) successfully.
  - Trip Weather Planning
```

If validation fails, check:
- YAML syntax (indentation, colons, dashes)
- Required fields are present
- Enum values are valid (patience: low/medium/high, etc.)
- Lists use proper YAML list syntax

## Step 8: Run the Scenario

Test against a simple agent (no MCP tools):

```bash
mcprobe run weather_trip.yaml --verbose
```

The test will likely FAIL because the simple agent can't actually call weather tools. This is expected!

Sample output:
```
Result: FAILED (score: 0.30)
Reasoning: The agent attempted to provide weather information but did not
use the required get_weather_forecast tool. Instead, it provided generic
advice without specific forecast data. This fails the required tool usage
criterion.

Suggestions:
  - The agent should be configured with access to weather forecast tools
  - Tool descriptions should clearly indicate when to use forecasts vs current weather
```

## Step 9: Test with a Real MCP Agent

To properly test this scenario, you need an agent with access to weather MCP tools. This requires:

1. **An MCP server** that provides weather tools
2. **An agent implementation** that can call MCP tools

### Option A: Using Gemini ADK

If you have a Gemini ADK agent with weather MCP tools:

```bash
mcprobe run weather_trip.yaml \
  --agent-type adk \
  --agent-factory my_weather_agent.py
```

### Option B: Building Your Own Agent

Create a custom agent that implements the `AgentUnderTest` interface and connects to your MCP server. See the [Custom Agents Guide](../integration/custom-agents.md) for details.

## Step 10: Iterate and Improve

After running the scenario several times, you'll likely want to adjust:

### Too Strict?

If the test fails but the conversation seems good, your criteria might be too strict:

**Problem**: "Covers multiple days" fails even though the agent mentioned a 3-day forecast.

**Solution**: Make the criterion more specific:
```yaml
correctness_criteria:
  - "Provides forecast for at least 3 days"
```

### Too Loose?

If the test passes but the quality is poor, tighten your criteria:

**Problem**: Agent only mentions "it might rain" without specifics.

**Solution**: Add more detailed requirements:
```yaml
correctness_criteria:
  - "Provides specific precipitation percentages or likelihood (e.g., '60% chance of rain')"
```

### Wrong Failure Triggers?

Monitor which failure criteria trigger most often:

**Problem**: "Asks more than 3 clarifying questions" triggers frequently.

**Solution**: Either increase the limit if questions are reasonable, or investigate why the agent needs so many clarifications (might indicate poor tool descriptions).

## Understanding Results

When you run the scenario, pay attention to different aspects of the output:

### Score Breakdown

- **0.0-0.3**: Major failures, critical criteria not met
- **0.3-0.5**: Some criteria met but significant issues
- **0.5-0.7**: Most criteria met, minor issues
- **0.7-0.9**: Nearly all criteria met, good quality
- **0.9-1.0**: All criteria met, excellent execution

### Quality Metrics

Verbose output shows:
- **Clarifications**: How many times the user had to provide additional info
- **Backtracks**: How often the agent changed direction or corrected itself
- **Turns to first answer**: Conversation efficiency
- **Answer completeness**: How complete the final answer was

### Suggestions

The judge provides actionable feedback:
- Tool description improvements
- Parameter schema clarifications
- Agent behavior recommendations
- Scenario adjustments

## Best Practices

### Writing Personas

**Do**:
```yaml
persona: |
  You are a busy parent planning a family beach vacation.
  You have two young kids (ages 5 and 8) and want to avoid
  extreme heat. Your budget is limited.
```

**Don't**:
```yaml
persona: "A user planning a trip"
```

### Writing Criteria

**Do**:
```yaml
correctness_criteria:
  - "Recommends destinations with temperatures between 70-85°F"
  - "Mentions family-friendly activities"
  - "Acknowledges budget constraints in recommendations"
```

**Don't**:
```yaml
correctness_criteria:
  - "Provides good recommendations"
  - "Responds appropriately"
```

### Clarification Facts

**Do**:
```yaml
known_facts:
  - "Traveling in July"
  - "Prefer beach destinations"
  - "Budget is $3000 for a family of four"

unknown_facts:
  - "Specific dates (only know 'sometime in July')"
  - "Whether kids can swim"
```

**Don't**:
```yaml
known_facts:
  - "Everything about the trip"

unknown_facts:
  - "Nothing"
```

## Common Pitfalls

### Overfitting to a Single Model

**Problem**: Your criteria are tuned to how one specific model responds.

**Solution**: Test with multiple models to ensure criteria are model-agnostic.

### Testing Implementation Instead of Interface

**Problem**: Criteria like "Uses the geocoding API before the weather API"

**Solution**: Focus on outcomes, not implementation: "Correctly identifies city coordinates"

### Unrealistic User Behavior

**Problem**: Synthetic user always provides perfect, complete information immediately.

**Solution**: Model realistic user behavior - ambiguity, partial info, evolving requirements.

## Next Scenario Ideas

Now that you've built a comprehensive scenario, try these variations:

**Edge Case**: User provides city name that exists in multiple states (e.g., "Springfield")

**Multi-Tool**: Requires combining weather, hotel availability, and flight data

**Error Handling**: Weather API returns an error for one city

**Adversarial**: User changes destination mid-conversation

**Efficiency**: Same task but with strict token/tool call limits

## Advanced Topics

Ready to go deeper? Explore:

- [Multi-Tool Scenarios](../advanced/multi-tool-scenarios.md)
- [Custom Evaluation Logic](../advanced/custom-evaluation.md)
- [Adversarial Testing](../advanced/adversarial-testing.md)
- [Trend Analysis](../cli-reference/trend-analysis.md)

## Summary

You've learned how to:
- Structure a complete test scenario
- Define realistic personas and clarification behavior
- Write specific, measurable evaluation criteria
- Set tool usage expectations
- Iterate based on test results

The key to effective MCP testing is creating scenarios that mirror real user interactions while clearly defining success criteria. Start simple, run tests, and progressively add complexity.

Happy testing!
