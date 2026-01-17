# Synthetic User Configuration

This guide explains how to configure the synthetic user that simulates real user behavior during agent testing.

## Overview

The synthetic user is an LLM-powered simulation that:
- Initiates conversations with the agent being tested
- Responds to the agent's questions and clarifications
- Behaves according to defined personality traits
- Provides or withholds information based on configuration

## Configuration Structure

```yaml
synthetic_user:
  persona: string                 # Required: Character description
  initial_query: string           # Required: First message
  max_turns: integer             # Optional: Conversation limit (default: 10)
  clarification_behavior:        # Optional: Response behavior
    known_facts: [...]
    unknown_facts: [...]
    traits: {...}
```

## Field Details

### `persona`

**Purpose:** Defines the character and role the synthetic user plays.

**Type:** String (required)

**Guidelines:**
- Describe the user's role, goals, and context
- Include relevant background that affects behavior
- Be specific about the user's situation
- Avoid generic descriptions

**Good Examples:**
```yaml
persona: |
  A software developer debugging a production issue at 2 AM.
  Stressed and needs quick answers. Has access to logs but
  not familiar with this particular service.
```

```yaml
persona: |
  A non-technical marketing manager trying to generate a
  report for tomorrow's executive meeting. Unfamiliar with
  technical terminology but knows what data is needed.
```

```yaml
persona: |
  An experienced database administrator who prefers precise,
  technical responses. Comfortable with SQL and command-line
  tools. Values efficiency over hand-holding.
```

**Poor Examples:**
```yaml
persona: "A user"  # Too vague

persona: "Someone who needs help"  # No context

persona: "A person"  # Useless
```

**Tips:**
- Include the user's domain expertise level
- Mention time constraints or urgency if relevant
- Specify what the user can/cannot do
- Describe emotional state if it affects interaction

### `initial_query`

**Purpose:** The first message the synthetic user sends to start the conversation.

**Type:** String (required)

**Guidelines:**
- Match the level of detail to your test goals
- For clarification tests: use ambiguous queries
- For happy path tests: provide complete information
- For adversarial tests: include contradictions or edge cases
- Use natural language that fits the persona

**Examples by Test Type:**

**Ambiguous (tests clarification):**
```yaml
initial_query: "I need the weather"
# Missing: location, timeframe, units
```

**Complete (tests happy path):**
```yaml
initial_query: "What's the weather forecast for Seattle, WA tomorrow? I prefer Fahrenheit."
# All information provided
```

**Adversarial (tests edge cases):**
```yaml
initial_query: "What's the weather in Nowhere, XX?"
# Invalid location
```

**Multi-step (tests complex workflows):**
```yaml
initial_query: |
  I need to analyze sales data from Q4 2025, compare it to Q4 2024,
  and generate a report showing the top 5 products by revenue growth.
# Complex request requiring multiple tools
```

### `max_turns`

**Purpose:** Limits conversation length to prevent infinite loops.

**Type:** Integer (optional, default: 10)

**Constraints:** Between 1 and 100

**Guidelines:**
- Set based on expected conversation complexity
- Simple queries: 3-5 turns
- Clarification scenarios: 6-10 turns
- Complex workflows: 10-20 turns
- Allow buffer beyond expected minimum

**Examples:**
```yaml
# Simple greeting
max_turns: 3

# Weather query with one clarification
max_turns: 5

# Complex multi-step workflow
max_turns: 15

# Adversarial scenario with retries
max_turns: 20
```

**Warning:** If `max_turns` is reached, the scenario fails. Set it higher than the expected conversation length.

## Clarification Behavior

Controls how the synthetic user responds when the agent asks questions.

### `known_facts`

**Purpose:** Information the user knows and will provide when asked.

**Type:** List of strings (optional, default: empty)

**Guidelines:**
- List specific pieces of information
- Use natural language descriptions
- Cover different levels of detail
- Include synonyms if relevant

**Examples:**
```yaml
known_facts:
  - "I'm in San Francisco"
  - "I need the forecast for tomorrow"
  - "I prefer Fahrenheit"
  - "Specifically the Richmond District"
  - "Morning forecast is most important"
```

**Use Cases:**
- Testing if agent asks appropriate clarifying questions
- Verifying agent uses information correctly after receiving it
- Ensuring agent doesn't make assumptions

### `unknown_facts`

**Purpose:** Information the user doesn't know (will say so if asked).

**Type:** List of strings (optional, default: empty)

**Guidelines:**
- List what the user cannot or will not provide
- Helps test agent's handling of missing information
- Forces agent to use defaults or alternative approaches

**Examples:**
```yaml
unknown_facts:
  - "The exact postal code"
  - "Whether to show hourly or daily forecast"
  - "The latitude/longitude coordinates"
  - "The airport code"
```

**Use Cases:**
- Testing fallback behavior
- Verifying agent doesn't fail on missing optional info
- Checking if agent offers reasonable defaults

**Example Scenario:**
```yaml
clarification_behavior:
  known_facts:
    - "I'm looking for a file about the quarterly report"
    - "It's a PDF file"
    - "Created sometime last month"
  unknown_facts:
    - "The exact filename"
    - "Who created it"
    - "The exact date"
```

## User Traits

Personality characteristics that affect how the synthetic user communicates.

### `patience`

**Purpose:** How tolerant the user is of clarifying questions and delays.

**Type:** Enum: `"low"`, `"medium"`, `"high"` (default: `"medium"`)

**Behaviors:**

**`low`:**
- Gets frustrated after 1-2 clarifying questions
- May provide dismissive or short responses
- Might abandon the conversation if too many questions
- Use for testing agent efficiency and decision-making

```yaml
traits:
  patience: low

# Expected user behavior:
# Agent: "What city are you in?"
# User: "San Francisco"
# Agent: "What temperature units do you prefer?"
# User: "Just give me the weather, I don't care!"
```

**`medium`:**
- Willing to answer a reasonable number of questions
- Stays engaged but may show slight impatience
- Balanced responses
- Good for most scenarios

```yaml
traits:
  patience: medium

# Expected user behavior:
# Agent: "What city are you in?"
# User: "San Francisco"
# Agent: "Do you want Fahrenheit or Celsius?"
# User: "Fahrenheit is fine"
# Agent: "Today or tomorrow?"
# User: "Today, please"
```

**`high`:**
- Very patient, will answer many questions
- Provides thoughtful, complete responses
- Stays engaged even in long conversations
- Use for complex scenarios requiring extensive interaction

```yaml
traits:
  patience: high

# Expected user behavior:
# Agent: "What city are you in?"
# User: "I'm in San Francisco, California, specifically in the Richmond District near Golden Gate Park"
# Agent: "What temperature units?"
# User: "I'd prefer Fahrenheit, as that's what I'm used to"
```

### `verbosity`

**Purpose:** How much detail the user provides in responses.

**Type:** Enum: `"concise"`, `"medium"`, `"verbose"` (default: `"concise"`)

**Behaviors:**

**`concise`:**
- Minimal, direct answers
- Single words or short phrases when possible
- No elaboration unless asked

```yaml
traits:
  verbosity: concise

# Agent: "What city are you in?"
# User: "Seattle"

# Agent: "What did the error message say?"
# User: "Connection timeout"
```

**`medium`:**
- Balanced responses
- Complete sentences
- Some context but not excessive

```yaml
traits:
  verbosity: medium

# Agent: "What city are you in?"
# User: "I'm in Seattle, Washington"

# Agent: "What did the error message say?"
# User: "I got a connection timeout error when trying to connect to the database"
```

**`verbose`:**
- Detailed, chatty responses
- Extra context and background
- May include tangential information

```yaml
traits:
  verbosity: verbose

# Agent: "What city are you in?"
# User: "I'm currently in Seattle, Washington. I live in the Capitol Hill neighborhood, which is near downtown. It's been pretty rainy lately."

# Agent: "What did the error message say?"
# User: "Well, I was trying to run the morning report like I do every day, and suddenly I got this connection timeout error. It said something about the database server not responding. This has never happened before in the three years I've been running this report."
```

### `expertise`

**Purpose:** The user's technical knowledge level.

**Type:** Enum: `"novice"`, `"intermediate"`, `"expert"` (default: `"novice"`)

**Behaviors:**

**`novice`:**
- Uses non-technical, everyday language
- May misuse technical terms
- Describes things by effect, not mechanism
- Needs guidance and explanation

```yaml
traits:
  expertise: novice

# User: "My computer won't connect to the internet thingy"
# User: "The page is broken, it just shows a bunch of code"
# User: "I clicked the button but nothing happened"
```

**`intermediate`:**
- Understands basic technical concepts
- Uses common technical terms correctly
- May need help with advanced topics
- Can follow technical instructions

```yaml
traits:
  expertise: intermediate

# User: "I'm getting a 404 error on the dashboard page"
# User: "The API endpoint is returning empty results"
# User: "Can you help me configure the environment variables?"
```

**`expert`:**
- Deep technical understanding
- Uses precise technical terminology
- Provides detailed technical context
- May skip basic explanations

```yaml
traits:
  expertise: expert

# User: "The GET /api/v2/users endpoint is returning a 503. The load balancer health check is passing but the upstream service is timing out after 30s."
# User: "I need to optimize this N+1 query. It's generating 500+ individual SELECT statements instead of using a JOIN."
# User: "Can you help me configure connection pooling for the PostgreSQL client? I'm seeing connection exhaustion under load."
```

## Complete Examples

### Novice User Needing Clarification

```yaml
synthetic_user:
  persona: |
    A small business owner with no technical background trying to
    understand why their website is down. Anxious and needs reassurance.

  initial_query: "My website isn't working! Can you help?"

  max_turns: 8

  clarification_behavior:
    known_facts:
      - "The website URL is myshop.example.com"
      - "It stopped working about an hour ago"
      - "I haven't made any changes recently"

    unknown_facts:
      - "What a 'server' is"
      - "How to check error logs"
      - "The hosting provider details"

    traits:
      patience: medium
      verbosity: verbose
      expertise: novice
```

### Expert User, Efficient Interaction

```yaml
synthetic_user:
  persona: |
    A senior DevOps engineer debugging a production incident.
    Time-critical situation. Knows exactly what information is needed.

  initial_query: |
    Need to query prod DB for user session data. User ID 12345,
    last 24h, include auth events and API calls. Export as JSON.

  max_turns: 5

  clarification_behavior:
    known_facts:
      - "User ID is 12345"
      - "Need last 24 hours of data"
      - "Prefer JSON format"
      - "Production database"

    unknown_facts: []  # Expert knows everything needed

    traits:
      patience: low
      verbosity: concise
      expertise: expert
```

### Impatient User with Incomplete Information

```yaml
synthetic_user:
  persona: |
    A busy executive assistant trying to book travel between meetings.
    Needs quick answers. Slightly stressed about time pressure.

  initial_query: "I need a flight to New York tomorrow"

  max_turns: 6

  clarification_behavior:
    known_facts:
      - "Traveling from San Francisco"
      - "Need to arrive before 2 PM"
      - "Prefer non-stop flights"

    unknown_facts:
      - "Exact departure time preference"
      - "Airline preference"
      - "Whether to include return flight"

    traits:
      patience: low
      verbosity: concise
      expertise: intermediate
```

### Patient User Learning New System

```yaml
synthetic_user:
  persona: |
    A new employee exploring the company's internal tools for the
    first time. Eager to learn, willing to try different approaches.

  initial_query: "How do I request time off?"

  max_turns: 12

  clarification_behavior:
    known_facts:
      - "I want to request vacation for next month"
      - "I'm in the Engineering department"
      - "I report to Sarah Chen"

    unknown_facts:
      - "The formal process or approval chain"
      - "How many vacation days I have available"
      - "Whether there's a blackout period"

    traits:
      patience: high
      verbosity: medium
      expertise: novice
```

## Best Practices

### Match Persona to Traits

Ensure personality traits align with the persona:

```yaml
# Consistent ✓
persona: "A senior database administrator with 15 years experience"
traits:
  expertise: expert
  verbosity: concise
  patience: low

# Inconsistent ✗
persona: "A senior database administrator with 15 years experience"
traits:
  expertise: novice  # Contradicts "senior" and "15 years"
  verbosity: verbose  # DBAs typically prefer concise
```

### Set Realistic known_facts

Include facts the persona would reasonably know:

```yaml
# Realistic ✓
persona: "A customer checking their order status"
known_facts:
  - "My order number is #12345"
  - "I ordered it last Tuesday"

# Unrealistic ✗
persona: "A customer checking their order status"
known_facts:
  - "The order is in the warehouse management system database"
  - "The shipment tracking UUID is abc-123-def-456"
```

### Use unknown_facts Strategically

Test edge cases and fallback behavior:

```yaml
# Forces agent to handle missing info ✓
initial_query: "Find my file"
unknown_facts:
  - "The exact filename"
  - "When it was created"
  - "What folder it's in"

# Agent must use search/heuristics to find it
```

### Set Appropriate max_turns

Allow room for the expected interaction:

```yaml
# Too tight ✗
initial_query: "What's the weather?"  # Needs clarification
max_turns: 2  # Only allows 1 question/answer

# Better ✓
initial_query: "What's the weather?"
max_turns: 6  # Allows 2-3 clarifications comfortably
```

## Common Patterns

### Testing Clarification Handling

```yaml
synthetic_user:
  persona: "A user with incomplete information"
  initial_query: "What's the weather?"  # Intentionally vague
  clarification_behavior:
    known_facts:
      - "I'm in Boston"
    traits:
      patience: medium
```

### Testing Error Tolerance

```yaml
synthetic_user:
  persona: "A user who might provide invalid input"
  initial_query: "Show me the weather for INVALID_CITY_12345"
  clarification_behavior:
    known_facts:
      - "Actually I meant Chicago"
    traits:
      patience: high
```

### Testing Efficiency

```yaml
synthetic_user:
  persona: "An expert who provides all info upfront"
  initial_query: "Weather for Chicago, IL, tomorrow, Fahrenheit"
  max_turns: 3  # Should be done quickly
  traits:
    patience: low
    expertise: expert
```

## Next Steps

- [Understand evaluation criteria](./evaluation.md)
- [See complete scenario examples](./examples.md)
- [Return to format reference](./format.md)
