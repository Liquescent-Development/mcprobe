# MCProbe

> A conversational testing framework for MCP servers using synthetic users and LLM-based evaluation.

## What is MCProbe?

MCProbe is a testing framework that validates whether MCP (Model Context Protocol) servers provide sufficient information for LLM agents to answer real-world questions correctly. Unlike traditional testing approaches that use canned responses, MCProbe employs synthetic users that can naturally respond to clarification requests and adapt to the conversation flow.

## Key Features

### Scenario-Based Testing
Define realistic test scenarios in YAML that describe user personas, goals, and success criteria. MCProbe orchestrates natural conversations between synthetic users and your MCP-powered agents.

### Synthetic Users
Realistic user simulation that can:
- Respond naturally to unexpected clarification requests
- Maintain persona consistency throughout conversations
- Know when to provide information vs. say "I don't know"
- Express appropriate frustration or satisfaction

### Automated Evaluation
LLM-based judges evaluate conversations against correctness criteria, tool usage expectations, and efficiency targets, providing detailed feedback and suggestions.

### Prompt & Schema Tracking
Automatically track agent system prompts and MCP tool schemas across test runs with SHA256-based change detection. HTML reports display visual badges when prompts or schemas change, helping correlate test performance with configuration modifications.

### Trend Analysis
Track test performance over time to identify regressions, improvements, and patterns in your MCP server's behavior.

### Flaky Test Detection
Automatically detect scenarios with inconsistent results, helping you improve test reliability and identify non-deterministic behavior.

### CI/CD Integration
Seamlessly integrate with pytest and GitHub Actions for continuous testing of your MCP servers.

### AI Assistant Integration
Built-in MCP server (`mcprobe serve`) exposes test results and control to AI assistants like Claude Code, enabling interactive test-driven development of MCP servers.

## Quick Install

```bash
pip install mcprobe
```

## Basic Example

Create a simple scenario file `greeting.yaml`:

```yaml
name: Simple Greeting Test
description: Test that the agent responds appropriately to greetings

synthetic_user:
  persona: A casual user looking for friendly interaction
  initial_query: "Hello! Can you help me today?"
  max_turns: 5

evaluation:
  correctness_criteria:
    - The agent responds with a greeting
    - The agent offers to help
  failure_criteria:
    - The agent ignores the user
    - The agent responds rudely
```

Run the scenario:

```bash
# Option 1: With Ollama (local)
ollama pull llama3.2
mcprobe run greeting.yaml

# Option 2: With OpenAI (cloud)
export OPENAI_API_KEY="sk-your-key"
mcprobe run greeting.yaml --provider openai --model gpt-4
```

Output:

```
Found 1 scenario(s)
Agent type: simple

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Simple Greeting Test                           ┃
┃ Test that the agent responds appropriately... ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Result: PASSED (score: 0.95)
Reasoning: The agent provided a warm greeting and clearly offered assistance...
```

## Documentation

### Getting Started
- [Installation](getting-started/installation.md) - Prerequisites and setup
- [Quickstart](getting-started/quickstart.md) - 5-minute guide to your first test
- [First Scenario](getting-started/first-scenario.md) - Deep dive into creating scenarios

### Agents
- [Agent Overview](agents/overview.md) - Agent types and architecture
- [Simple Agent](agents/simple-agent.md) - Text-only LLM agent guide
- [ADK Agent](agents/adk-agent.md) - Gemini ADK with MCP tools
- [Custom Agents](agents/custom-agents.md) - Building your own agent wrapper

### Core Concepts
- Scenario Definition - Writing effective test scenarios
- Synthetic Users - How persona simulation works
- Evaluation Criteria - Defining success and failure conditions
- Tool Usage Testing - Validating MCP tool interactions

### CLI Reference
- [CLI Reference](cli/reference.md) - Complete command reference for all 9 commands
- [Running Tests](cli/run.md) - Execute scenarios against your agents
- [Generating Scenarios](cli/generate.md) - Auto-create tests from MCP schemas
- [Analysis & Reporting](cli/analysis.md) - Reports, trends, and flaky test detection
- [MCP Server](cli/serve.md) - AI assistant integration with Claude Code

### Analysis
- [Trend Analysis](analysis/trends.md) - Track performance trends and detect regressions
- [Flaky Test Detection](analysis/flaky-detection.md) - Identify inconsistent test scenarios
- [Stability Checking](analysis/stability.md) - Verify scenario consistency and reliability

### Integration
- [Claude Code](integration/claude-code.md) - AI-assisted MCP development with Claude Code
- [Pytest Plugin](pytest/integration.md) - Use MCProbe in your test suite
- CI/CD Setup - GitHub Actions and other platforms
- Custom Agents - Integrate with any LLM/MCP stack

### Advanced Usage
- Custom Evaluation - Write complex judgment logic
- Multi-Tool Scenarios - Test tool composition
- Performance Testing - Efficiency benchmarking
- Adversarial Testing - Edge cases and error handling

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                MCProbe                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │   Test       │    │  Synthetic   │    │   System Under Test      │  │
│  │   Scenario   │───▶│  User LLM    │◀──▶│   (Agent + MCP Server)   │  │
│  │   (YAML)     │    │              │    │                          │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘  │
│         │                   │                        │                 │
│         │                   │                        │                 │
│         ▼                   ▼                        ▼                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Conversation Log                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                   │
│                                    ▼                                   │
│                         ┌──────────────────┐                           │
│                         │    Judge LLM     │                           │
│                         │                  │                           │
│                         │  • Correctness   │                           │
│                         │  • Tool Usage    │                           │
│                         │  • Efficiency    │                           │
│                         └──────────────────┘                           │
│                                    │                                   │
│                                    ▼                                   │
│                         ┌──────────────────┐                           │
│                         │   Test Report    │                           │
│                         └──────────────────┘                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Use Cases

**MCP Server Development**: Validate that your tool descriptions are clear enough for LLMs to use correctly.

**Agent Testing**: Ensure your LLM-powered agents can handle realistic user interactions and edge cases.

**Quality Assurance**: Catch regressions in conversational behavior before deploying changes.

**Performance Benchmarking**: Track efficiency metrics across different models and configurations.

**Documentation Validation**: Verify that tool documentation matches actual behavior.

## Community & Support

- **GitHub**: [github.com/Liquescent-Development/mcprobe](https://github.com/Liquescent-Development/mcprobe)
- **Issues**: Report bugs and request features
- **Discussions**: Share scenarios and best practices
- **Contributing**: See CONTRIBUTING.md

## License

MCProbe is released under the AGPL-3.0 license. See LICENSE for details.

## Next Steps

Ready to start testing? Head to the [Installation Guide](getting-started/installation.md) to set up MCProbe, or jump straight to the [Quickstart](getting-started/quickstart.md) for a hands-on tutorial.
