# MCProbe

A testing framework that validates MCP servers provide sufficient information for LLM agents to answer real-world questions correctly, using synthetic users and LLM judges.

## Installation

```bash
uv venv
source .venv/bin/activate
uv sync --all-extras
```

## Usage

```bash
mcprobe run scenario.yaml
mcprobe validate scenario.yaml
mcprobe providers
```

See [docs/SPEC.md](docs/SPEC.md) for the full specification.
