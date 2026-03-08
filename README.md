# Small Council

*Throw humanity's smartest AIs at any problem your coding agent has.*

Inspired by [Andrej Karpathy's LLM Council](https://github.com/karpathy/llm-council).

**Small Council** is a Claude Code skill + CLI tool that lets coding agents consult multiple frontier AI models for feedback, reviews, and second opinions. When your agent is stuck, unsure, or needs validation — it can ask the council.

## Use Cases

- **Code Review**: Get 4 expert perspectives on your implementation
- **Architecture Decisions**: "Should we use microservices or keep the monolith?"
- **Breaking Out of Loops**: When your agent keeps failing, get fresh perspectives
- **Plan Validation**: Review implementation plans before writing code
- **Hard Problems**: Tackle complex bugs or design challenges with collective intelligence

## How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Your Question                               │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 1: Independent Responses                                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                 │
│  │ GPT-5.4 │ │GPT-5.4  │ │ Gemini  │ │ Claude  │                 │
│  │         │ │  pro    │ │3.1 Pro  │ │ Opus 4.6│                 │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘                 │
└───────┼──────────┼──────────┼──────────┼─────────────────────────┘
        │          │          │          │
        ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 2: Anonymous Peer Ranking                                    │
│  Each model ranks all responses (A, B, C, D) without                │
│  knowing which model wrote which response                           │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 3: Chairman Synthesis                                        │
│  ┌───────────────┐                                                  │
│  │ Claude Opus   │ → Synthesizes final consensus answer             │
│  │     4.6       │                                                  │
│  └───────────────┘                                                  │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Final Answer                                │
└─────────────────────────────────────────────────────────────────────┘
```

**Council Members**: GPT-5.4, GPT-5.4-Pro, Gemini 3.1 Pro, Claude Opus 4.6
**Chairman**: Claude Opus 4.6 (synthesizes only, doesn't participate in ranking)

---

## Claude Code Skill

The primary way to use Small Council is as a Claude Code skill.

### Quick Install

```bash
# 1. Install CLI
uv tool install git+https://github.com/eytanlevit/small-council

# 2. Install skill (via skills.sh)
npx skills add eytanlevit/small-council

# 3. Set API key
export OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### Using the Skill

In Claude Code, just say:
- "Ask the small council to review this code"
- "Consult the council on this architecture"
- "I'm stuck — what does the small council think?"

The skill runs deliberation in tmux via `small-council tmux` commands (survives session restarts) and returns the synthesized consensus.

---

## CLI Tool

You can also use Small Council directly from the command line.

### Installation

```bash
# From source
git clone https://github.com/eytanlevit/small-council.git
cd small-council
uv tool install .
```

### Configuration

Get an API key from [OpenRouter](https://openrouter.ai/) and set it:

```bash
export OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Or create `~/.small-council.yaml`:

```yaml
api_key: sk-or-v1-your-key-here
council_models:
  - openai/gpt-5.4
  - openai/gpt-5.4-pro
  - google/gemini-3.1-pro-preview
  - anthropic/claude-opus-4.6
chairman_model: anthropic/claude-opus-4.6
```

### Usage

```bash
# Basic question
small-council "What's the best way to handle authentication in a microservices architecture?"

# Code review with files
small-council -f src/auth.py -f src/middleware.py "Review this authentication implementation"

# Include files by glob
small-council -i "src/**/*.py" "What's the architecture of this codebase?"

# Answer only (for scripts/agents)
small-council -a "Your question"

# JSON output
small-council --json "Your question" > result.json
```

### Options

| Flag | Short | Description |
|------|-------|-------------|
| `--file` | `-f` | Include file contents (repeatable) |
| `--include` | `-i` | Include files by glob pattern (repeatable) |
| `--answer-only` | `-a` | Output only the final synthesized answer |
| `--json` | `-j` | Output as JSON |
| `--markdown` | `-m` | Output as Markdown |
| `--quiet` | `-q` | Suppress progress output |
| `--models` | | Override council models (comma-separated) |
| `--chairman` | | Override chairman model |
| `--config` | `-c` | Path to config file |
| `--version` | `-V` | Show version |

### Agent-Friendly Features

- **Auto-JSON**: When stdout is piped, automatically outputs JSON
- **Stderr progress**: Progress goes to stderr, results to stdout
- **Answer-only mode**: `-a` returns just the final answer for easy parsing

---

## JSON Output Schema

```json
{
  "query": "Your question",
  "stage1": [
    {"model": "openai/gpt-5.4", "response": "..."},
    {"model": "google/gemini-3.1-pro-preview", "response": "..."}
  ],
  "stage2": [
    {"model": "openai/gpt-5.4", "ranking": "...", "parsed_ranking": ["Response B", "Response A", "Response C", "Response D"]}
  ],
  "stage3": {
    "model": "anthropic/claude-opus-4.6",
    "response": "Final synthesized answer..."
  },
  "metadata": {
    "label_to_model": {"Response A": "openai/gpt-5.4", ...},
    "aggregate_rankings": [
      {"model": "google/gemini-3.1-pro-preview", "average_rank": 1.5},
      {"model": "openai/gpt-5.4", "average_rank": 2.0}
    ]
  }
}
```

## Reasoning Policy

Small Council enforces high reasoning effort for:
- `openai/*gpt-5.4*`
- `anthropic/claude-opus-*`

These requests are sent with:

```json
{
  "reasoning": {"effort": "xhigh"}
}
```

## License

MIT
