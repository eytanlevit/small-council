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
chairman_model: google/gemini-3-pro-preview
```

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
| `--quiet` | `-q` | Suppress progress, show only final result |
| `--config` | `-c` | Path to config file |
| `--models` | | Override council models (comma-separated) |
| `--chairman` | | Override chairman model |
| `--version` | `-V` | Show version |
