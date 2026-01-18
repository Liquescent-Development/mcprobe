# Quickstart Guide

Get up and running with MCProbe in 5 minutes. This guide walks you through running your first test scenario.

## Step 1: Install MCProbe

If you haven't already, install MCProbe:

```bash
pip install mcprobe
```

Verify the installation:

```bash
mcprobe --help
```

## Step 2: Set Up an LLM Provider

MCProbe needs an LLM provider for the synthetic user and judge. Choose one:

### Option A: Ollama (Local, Free)

**Install Ollama**:
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows: Download from ollama.ai
```

**Start the service**:
```bash
ollama serve
```

Leave this running in a terminal.

**Pull a model**:
```bash
ollama pull llama3.2
```

This downloads the Llama 3.2 model (about 2GB). It's used for the synthetic user and judge.

### Option B: OpenAI (Cloud, Requires API Key)

**Set your API key**:
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

That's it! No additional setup needed. You'll use `--provider openai --model gpt-4` when running tests.

**Note**: The examples below use Ollama by default. To use OpenAI instead, add `--provider openai --model gpt-4` to the commands.

## Step 3: Create Your First Scenario

Create a file named `greeting.yaml`:

```yaml
name: Simple Greeting Test
description: Test that the agent can respond to a greeting appropriately

synthetic_user:
  persona: A casual user looking for friendly interaction
  initial_query: "Hello! Can you help me today?"
  max_turns: 5
  clarification_behavior:
    known_facts:
      - I want general assistance
    unknown_facts:
      - Specific technical details
    traits:
      patience: medium
      verbosity: concise
      expertise: novice

evaluation:
  correctness_criteria:
    - The agent responds with a greeting
    - The agent offers to help
  failure_criteria:
    - The agent ignores the user
    - The agent responds rudely
  tool_usage:
    required_tools: []
    prohibited_tools: []
  efficiency:
    max_conversation_turns: 5

tags:
  - basic
  - greeting
```

### Understanding the Scenario

**synthetic_user**: Defines who the simulated user is and what they want.
- `persona`: Background and context for the user
- `initial_query`: The first message the user sends
- `max_turns`: Maximum conversation length
- `clarification_behavior`: How the user responds to questions

**evaluation**: Defines what makes the test pass or fail.
- `correctness_criteria`: Things that must be true (all required)
- `failure_criteria`: Things that must not happen (any one causes failure)
- `tool_usage`: Expected MCP tool interactions (none for this simple test)
- `efficiency`: Optional performance targets

## Step 4: Run the Scenario

Execute the test:

**With Ollama** (default):
```bash
mcprobe run greeting.yaml
```

**With OpenAI**:
```bash
mcprobe run greeting.yaml --provider openai --model gpt-4
```

You'll see output like:

```
Found 1 scenario(s)
Agent type: simple

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Simple Greeting Test                             ┃
┃ Test that the agent can respond to a greeting... ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Running conversation...

Result: PASSED (score: 0.95)
Reasoning: The agent provided a warm, friendly greeting and clearly offered
to help the user. The response was appropriate for a casual interaction
and met all correctness criteria.

Test Summary
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━┓
┃ Scenario           ┃ Status ┃ Score ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━┩
│ Simple Greeting... │  PASS  │  0.95 │
└────────────────────┴────────┴───────┘

Total: 1/1 passed
```

## Step 5: Understand the Output

**Result**: PASSED or FAILED based on evaluation criteria

**Score**: 0.0 to 1.0 indicating quality of the response
- 0.0-0.5: Poor
- 0.5-0.7: Acceptable
- 0.7-0.9: Good
- 0.9-1.0: Excellent

**Reasoning**: The judge's explanation of why the test passed or failed

### Verbose Output

See the full conversation and evaluation details:

```bash
mcprobe run greeting.yaml --verbose
```

This shows:
- Complete conversation transcript
- Individual correctness criterion results
- Failure condition checks
- Quality metrics (clarifications, backtracks, etc.)
- Efficiency statistics
- Detailed suggestions for improvement

Example verbose output:

```
Conversation:
[USER]: Hello! Can you help me today?
[ASSISTANT]: Hello! Of course, I'd be happy to help you today.
  What can I assist you with?

Correctness:
  The agent responds with a greeting: PASS
  The agent offers to help: PASS

Failure Conditions:
  The agent ignores the user: OK
  The agent responds rudely: OK

Quality Metrics:
  Clarifications: 0
  Backtracks: 0
  Turns to first answer: 1
  Answer completeness: 100%

Efficiency:
  Total tokens: 127
  Tool calls: 0
  Turns: 2
```

## Step 6: Validate Scenarios

Before running, you can validate scenario files for syntax errors:

```bash
mcprobe validate greeting.yaml
```

Output:
```
Validated 1 scenario(s) successfully.
  - Simple Greeting Test
```

This checks:
- YAML syntax is correct
- Required fields are present
- Field types match expected schemas
- No invalid enum values

## Common Issues

### "Connection refused" Error

**Problem**: Ollama is not running.

**Solution**: Start Ollama in another terminal:
```bash
ollama serve
```

Or switch to OpenAI:
```bash
export OPENAI_API_KEY="sk-your-key"
mcprobe run greeting.yaml --provider openai --model gpt-4
```

### "Model not found" Error

**Problem**: The llama3.2 model hasn't been downloaded (Ollama).

**Solution**: Pull the model:
```bash
ollama pull llama3.2
```

### "OpenAI API key not found" Error

**Problem**: Using OpenAI provider without setting the API key.

**Solution**: Set the environment variable:
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

Or provide it in your configuration (see [Configuration Reference](../configuration/reference.md)).

### Test Fails Unexpectedly

**Problem**: The default simple agent doesn't always produce perfect responses.

**Reason**: Simple agents don't have MCP tools or special capabilities - they're just basic LLM responses.

**Solution**: This is normal for simple tests. The goal is to establish baselines. For more complex scenarios, you'll test real agents with MCP tools (covered in the next tutorial).

## Next Steps

Congratulations! You've run your first MCProbe test. Here's what to learn next:

### 1. Create a More Complex Scenario

Try the [First Scenario Tutorial](first-scenario.md) to learn:
- How to define realistic user personas
- Setting up clarification behavior
- Testing tool usage with MCP servers
- Writing effective evaluation criteria

### 2. Test a Real MCP Agent

Learn how to test agents that use MCP tools:
- Connect to MCP servers
- Define tool usage expectations
- Validate tool call parameters
- Test multi-tool scenarios

### 3. Generate Test Reports

Create shareable HTML reports:

```bash
# Run a scenario (saves results automatically)
mcprobe run greeting.yaml

# Generate HTML report
mcprobe report --format html --output report.html
```

### 4. Track Trends Over Time

Run the same scenario multiple times and analyze trends:

```bash
# Run the scenario several times
for i in {1..10}; do mcprobe run greeting.yaml; done

# View trends
mcprobe trends --scenario "Simple Greeting Test"
```

### 5. Detect Flaky Tests

Identify scenarios with inconsistent results:

```bash
mcprobe flaky --min-runs 5
```

## Tips for Writing Good Scenarios

**Start Simple**: Begin with basic interactions before testing complex workflows.

**Be Specific**: Vague criteria like "responds well" are hard to evaluate. Use specific, measurable criteria.

**Test Edge Cases**: Don't just test happy paths - include scenarios where users are confused, provide incomplete info, or make mistakes.

**Define Clear Personas**: Give your synthetic users realistic backgrounds and constraints.

**Balance Criteria**: Too strict = tests fail unnecessarily. Too loose = tests pass when they shouldn't.

## Example Scenarios to Try

After the greeting test, try these progressively complex scenarios:

**Information Retrieval**: User asks a simple question, agent retrieves and formats an answer.

**Clarification Handling**: User provides ambiguous request, agent asks for clarification, user responds, agent provides answer.

**Multi-Step Tasks**: User needs multiple pieces of information that require different tools.

**Error Recovery**: Tools return errors or partial data, agent handles gracefully.

**Adversarial**: User changes requirements mid-conversation or provides contradictory info.

## Getting Help

**Documentation**: See the full docs at [docs/index.md](../index.md)

**CLI Reference**: For complete CLI documentation, see:
- [CLI Reference](../cli/reference.md) - All commands with options and examples
- [Running Tests](../cli/run.md) - Detailed guide for the `run` command
- [Generating Scenarios](../cli/generate.md) - Auto-generate tests from MCP servers
- [Analysis & Reporting](../cli/analysis.md) - Reports, trends, and flaky test detection

**Examples**: Check the `examples/scenarios/` directory for more sample scenarios

**Community**: Open an issue on GitHub for questions or bug reports

Ready to dive deeper? Continue to the [First Scenario Tutorial](first-scenario.md).
