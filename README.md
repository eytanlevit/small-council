# Small Council

CLI tool for multi-LLM deliberation via OpenRouter.

## How It Works

Small Council runs a 3-stage deliberation:

1. **Stage 1**: Multiple LLMs independently answer your question
2. **Stage 2**: Each LLM anonymously ranks all responses
3. **Stage 3**: A chairman LLM synthesizes the final answer

## Installation

```bash
uv tool install .
```

Or for development:

```bash
uv sync
```

## Configuration

Set your OpenRouter API key:

```bash
export OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Or create `~/.small-council.yaml`:

```yaml
api_key: sk-or-v1-your-key-here
council_models:
  - openai/gpt-5.2
  - google/gemini-3-pro-preview
  - anthropic/claude-opus-4.5
  - x-ai/grok-4
chairman_model: openai/gpt-5.2-pro
```

Note: The chairman is separate from council members - it only synthesizes the final answer and doesn't participate in ranking.

## Usage

```bash
# Basic usage
small-council "What is the best programming language for beginners?"

# Pipe from stdin
echo "Explain quantum computing" | small-council

# JSON output
small-council --json "Compare Python and Rust" > result.json

# Markdown output
small-council --markdown "Design patterns overview" > patterns.md

# Override models
small-council --models "gpt-5.2,claude-opus-4.5" --chairman "gemini-3-pro" "Your question"

# Quiet mode (no progress, just final answer)
small-council -q "Your question"
```

## Options

| Flag | Short | Description |
|------|-------|-------------|
| `--json` | `-j` | Output as JSON |
| `--markdown` | `-m` | Output as Markdown |
| `--answer-only` | `-a` | Output only the final synthesized answer |
| `--quiet` | `-q` | Suppress progress, show only final result |
| `--config` | `-c` | Path to config file |
| `--models` | | Override council models (comma-separated) |
| `--chairman` | | Override chairman model |
| `--version` | `-V` | Show version |

## Agent-Friendly Features

Small Council is designed to work well with coding agents and scripts:

**Auto-detect piped output**: When stdout is piped (not a TTY), automatically outputs JSON:
```bash
# These are equivalent when piped
small-council "query" | jq '.stage3.response'
small-council --json "query" | jq '.stage3.response'
```

**Progress on stderr**: Progress indicators and errors go to stderr, keeping stdout clean:
```bash
# Progress visible, JSON to file
small-council "query" > result.json

# Hide progress entirely
small-council "query" 2>/dev/null > result.json
```

**Answer-only mode**: Get just the final synthesized answer:
```bash
# Perfect for agents that just need the answer
ANSWER=$(small-council -a "What's the capital of France?")

# Pipe to clipboard
small-council -a "Summarize this code" | pbcopy
```
