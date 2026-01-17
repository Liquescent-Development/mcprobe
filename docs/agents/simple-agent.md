# Simple LLM Agent Guide

## Overview

The **Simple LLM Agent** is a text-only conversational agent that uses an LLM provider for generating responses without any tool calling capabilities. It's ideal for baseline testing, LLM evaluation, and Phase 1 scenarios that don't require external tools.

## What the Simple Agent Does

The simple agent:

1. Maintains conversation history across multiple turns
2. Sends messages to an LLM provider (via Ollama-compatible API)
3. Returns pure text responses without tool invocations
4. Tracks conversation state and completion status
5. Supports custom system prompts for behavior customization

## When to Use Simple Agent

### Ideal Use Cases

- **Baseline Testing** - Establish LLM performance without tool complexity
- **Conversation Quality** - Test dialogue flow, coherence, and helpfulness
- **Phase 1 Scenarios** - Scenarios that require only text responses
- **LLM Comparison** - Compare different models' conversational abilities
- **Rapid Prototyping** - Quick scenario validation before implementing tools

### Not Suitable For

- MCP server validation (requires tool calling)
- Tool selection/usage testing
- Complex multi-step tasks requiring external data
- Phase 2+ scenarios with explicit tool requirements

## Configuration Options

### CLI Configuration

```bash
mcprobe run scenario.yaml \
  --agent-type simple \
  --model llama3.2 \
  --base-url http://localhost:11434 \
  --verbose
```

**Parameters:**

- `--agent-type simple` - Selects the simple agent (default)
- `--model <name>` - LLM model name in Ollama (e.g., `llama3.2`, `mistral`)
- `--base-url <url>` - Ollama API endpoint (default: `http://localhost:11434`)
- `--verbose` - Show detailed conversation logs

### System Prompt Customization

While the CLI doesn't expose system prompt configuration directly, you can customize agent behavior through scenario setup instructions:

```yaml
# scenario.yaml
scenario:
  name: "Customer Support Test"
  goal: "Handle customer inquiries professionally"
  setup: |
    You are a professional customer support agent for Acme Corp.
    Be helpful, empathetic, and solution-oriented.
    Always maintain a friendly tone.
```

The setup text is incorporated into the agent's context.

## Implementation Details

### Class: `SimpleLLMAgent`

**Location:** `src/mcprobe/agents/simple.py`

```python
from mcprobe.agents.simple import SimpleLLMAgent
from mcprobe.providers.base import LLMProvider

agent = SimpleLLMAgent(
    provider: LLMProvider,           # LLM provider instance
    system_prompt: str | None = None, # Optional behavior instructions
    agent_name: str = "SimpleLLMAgent", # Display name
)
```

### Core Methods

#### `send_message(message: str) -> AgentResponse`

Sends a user message and generates a response.

```python
response = await agent.send_message("What's the capital of France?")

# Response structure:
# {
#     "message": "The capital of France is Paris.",
#     "tool_calls": [],  # Always empty for simple agent
#     "is_complete": True,
#     "metadata": {
#         "usage": {"prompt_tokens": 15, "completion_tokens": 8},
#         "finish_reason": "stop"
#     }
# }
```

**Behavior:**
- Appends user message to conversation history
- Calls LLM provider with full history
- Appends assistant response to history
- Determines completion status (see below)
- Returns `AgentResponse` with text and metadata

**Raises:**
- `OrchestrationError` - If LLM generation fails

#### `reset() -> None`

Clears conversation state for a new test.

```python
await agent.reset()  # Conversation history cleared
```

**Behavior:**
- Clears all conversation history
- Preserves system prompt (if set)
- Resets to initial state

#### `get_available_tools() -> list`

Returns empty list (simple agent has no tools).

```python
tools = agent.get_available_tools()  # Returns []
```

### Conversation History

The agent maintains an internal message list:

```python
# Accessible via property (read-only)
history = agent.conversation_history

# Example history:
[
    Message(role="system", content="You are a helpful assistant."),
    Message(role="user", content="Hello!"),
    Message(role="assistant", content="Hi! How can I help you?"),
    Message(role="user", content="What's 2+2?"),
    Message(role="assistant", content="2+2 equals 4."),
]
```

## Conversation Completion Detection

The simple agent uses a heuristic to determine if a conversation is complete:

```python
is_complete = not response.content.strip().endswith("?")
```

**Logic:**
- If response ends with `?` → Not complete (agent is asking a question)
- Otherwise → Complete (agent provided an answer)

**Examples:**

```python
# Complete responses:
"The capital is Paris."          → is_complete = True
"That's a great question!"       → is_complete = True
"Here are three options for you." → is_complete = True

# Incomplete responses:
"What would you like to know?"   → is_complete = False
"Can you clarify that?"          → is_complete = False
"Which option do you prefer?"    → is_complete = False
```

This heuristic helps the orchestrator determine when to get user feedback vs. continue the conversation flow.

## Example Usage Scenarios

### Scenario 1: Baseline LLM Testing

Test if an LLM can answer factual questions correctly:

```yaml
scenario:
  name: "Geography Knowledge"
  goal: "Correctly answer geography questions"

test_case:
  - user: "What's the capital of Japan?"
    expected_behavior: "States that Tokyo is the capital"

  - user: "Which ocean is between Europe and America?"
    expected_behavior: "Identifies the Atlantic Ocean"
```

Run with:
```bash
mcprobe run geography.yaml -t simple -m llama3.2
```

### Scenario 2: Conversation Quality

Evaluate dialogue coherence and helpfulness:

```yaml
scenario:
  name: "Tech Support Conversation"
  goal: "Help user troubleshoot Wi-Fi issues"
  setup: |
    You are a tech support agent helping users with internet connectivity.

test_case:
  - user: "My Wi-Fi isn't working"
    expected_behavior: "Asks clarifying questions about the issue"

  - user: "The router lights are all on but I can't connect"
    expected_behavior: "Suggests relevant troubleshooting steps"
```

### Scenario 3: Model Comparison

Compare different models' responses to the same prompts:

```bash
# Test with LLaMA 3.2
mcprobe run ethics.yaml -t simple -m llama3.2 > llama_results.json

# Test with Mistral
mcprobe run ethics.yaml -t simple -m mistral > mistral_results.json

# Compare results
diff llama_results.json mistral_results.json
```

## Limitations

### No Tool Calling

The simple agent cannot:
- Invoke MCP tools or any external functions
- Access real-time data (weather, news, etc.)
- Perform calculations beyond LLM reasoning
- Execute code or system commands

**Workaround:** Use the ADK agent with MCP tools for these scenarios.

### No Structured Output

Responses are free-form text only:
- No guaranteed JSON structure
- No schema validation
- Relies on LLM's natural language understanding

**Workaround:** Use few-shot examples in the system prompt to encourage structured responses.

### Limited Context Window

Constrained by the underlying LLM's context window:
- Long conversations may exceed limits
- Older messages may be truncated

**Workaround:** Design scenarios with reasonable turn limits.

### Heuristic Completion Detection

Uses simple question mark heuristic:
- May misclassify rhetorical questions as incomplete
- Cannot detect partial answers to complex questions

**Workaround:** Monitor conversation turns and adjust max_turns in scenarios.

## Performance Considerations

### Latency

Response time depends on:
- LLM model size (smaller = faster)
- Ollama server performance
- Context length (longer history = slower)

**Typical latencies:**
- Small models (7B parameters): 100-500ms
- Medium models (13B parameters): 500-2000ms
- Large models (70B+ parameters): 2000-10000ms

### Resource Usage

- Memory: Proportional to model size
- CPU/GPU: Depends on Ollama configuration
- Network: Minimal (local API calls)

### Optimization Tips

1. **Use smaller models** for faster iteration during development
2. **Limit conversation turns** to manage context length
3. **Run Ollama locally** to avoid network latency
4. **Configure GPU acceleration** in Ollama for better performance

## Troubleshooting

### "Connection refused" Error

**Problem:** Cannot connect to Ollama API.

**Solutions:**
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve

# Verify model is available
ollama list
```

### "Model not found" Error

**Problem:** Specified model not available in Ollama.

**Solutions:**
```bash
# Pull the model
ollama pull llama3.2

# List available models
ollama list

# Use correct model name in CLI
mcprobe run scenario.yaml -m llama3.2
```

### Slow Response Times

**Problem:** Agent responses take too long.

**Solutions:**
- Use a smaller model (e.g., `llama3.2` instead of `llama3.2:70b`)
- Enable GPU acceleration in Ollama
- Reduce scenario complexity
- Limit max conversation turns

### Incomplete Responses

**Problem:** Agent responses are cut off mid-sentence.

**Solutions:**
- Check Ollama's context window settings
- Reduce conversation history length
- Use a model with larger context window

## Next Steps

- [ADK Agent Guide](adk-agent.md) - Upgrade to tool-enabled agent
- [Custom Agents](custom-agents.md) - Build your own agent type
- [Writing Scenarios](../scenarios/writing-scenarios.md) - Create effective tests
- [Agent Overview](overview.md) - Compare all agent types
