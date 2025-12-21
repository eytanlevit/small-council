# Small Council

*Throw humanity's smartest AIs at any problem you have.*

Inspired by [Andrej Karpathy's LLM Council](https://github.com/karpathy/llm-council). CLI tool for multi-LLM deliberation via OpenRouter.

Get consensus answers from multiple frontier AI models (GPT-5.2, GPT-5.2-pro, Gemini 3 Pro, Claude Sonnet 4, Grok 4) with anonymous peer ranking and Claude Opus 4.5 chairman synthesis.

## How It Works

Small Council runs a 3-stage deliberation:

1. **Stage 1**: Multiple LLMs independently answer your question
2. **Stage 2**: Each LLM anonymously ranks all responses
3. **Stage 3**: A chairman LLM synthesizes the final answer

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Your Question                               │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 1: Independent Responses                                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ GPT-5.2 │ │GPT-5.2  │ │ Gemini  │ │ Claude  │ │ Grok 4  │       │
│  │         │ │  pro    │ │ 3 Pro   │ │Sonnet 4 │ │         │       │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │
└───────┼──────────┼──────────┼──────────┼──────────┼────────────────┘
        │          │          │          │          │
        ▼          ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 2: Anonymous Peer Ranking                                    │
│  Each model ranks all responses (A, B, C, D, E) without             │
│  knowing which model wrote which response                           │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 3: Chairman Synthesis                                        │
│  ┌───────────────┐                                                  │
│  │ Claude Opus   │ → Synthesizes final consensus answer             │
│  │     4.5       │                                                  │
│  └───────────────┘                                                  │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Final Answer                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Installation

### From PyPI (coming soon)

```bash
uv tool install small-council
```

### From Source

```bash
git clone https://github.com/anthropics/small-council.git
cd small-council
uv tool install .
```

### For Development

```bash
git clone https://github.com/anthropics/small-council.git
cd small-council
uv sync
uv run small-council "Your question"
```

## Configuration

### API Key

Get an API key from [OpenRouter](https://openrouter.ai/) and set it:

```bash
export OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### Config File (Optional)

Create `~/.small-council.yaml` for persistent configuration:

```yaml
api_key: sk-or-v1-your-key-here
council_models:
  - openai/gpt-5.2
  - openai/gpt-5.2-pro
  - google/gemini-3-pro-preview
  - anthropic/claude-sonnet-4
  - x-ai/grok-4
chairman_model: anthropic/claude-opus-4.5
timeout: 120  # seconds per API call
```

Note: The chairman is separate from council members - it only synthesizes the final answer and doesn't participate in ranking.

## Usage

### Basic

```bash
small-council "What is the best programming language for beginners?"
```

### With Files (Code Review)

```bash
# Include specific files
small-council -f src/main.py -f src/utils.py "Review this code for bugs"

# Include files by glob pattern
small-council -i "src/**/*.py" "What's the architecture of this codebase?"
```

### Output Formats

```bash
# Rich terminal output (default)
small-council "Your question"

# JSON output
small-council --json "Your question" > result.json

# Markdown output
small-council --markdown "Your question" > result.md

# Answer only (no stages, just final answer)
small-council -a "Your question"
```

### Override Models

```bash
small-council --models "gpt-5.2,claude-opus-4.5" --chairman "gemini-3-pro" "Your question"
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
| `--file` | `-f` | Include file contents (repeatable) |
| `--include` | `-i` | Include files by glob pattern (repeatable) |
| `--version` | `-V` | Show version |

## Agent-Friendly Features

Small Council is designed to work well with coding agents and scripts:

**Auto-detect piped output**: When stdout is piped (not a TTY), automatically outputs JSON:
```bash
small-council "query" | jq '.stage3.response'
```

**Progress on stderr**: Progress indicators and errors go to stderr, keeping stdout clean:
```bash
small-council "query" > result.json  # Progress visible, JSON to file
small-council "query" 2>/dev/null > result.json  # Silent
```

**Answer-only mode**: Perfect for agents that just need the answer:
```bash
ANSWER=$(small-council -a "What's the capital of France?")
```

---

## Claude Code Skill

Use Small Council directly from Claude Code as a skill.

### Skill Installation

1. **Create the skill directory:**
   ```bash
   mkdir -p ~/.claude/skills/small-council
   ```

2. **Copy skill files:**
   ```bash
   cp -r skill/* ~/.claude/skills/small-council/
   ```

3. **Set your OpenRouter API key:**
   ```bash
   echo "OPENROUTER_API_KEY=sk-or-v1-your-key-here" > ~/.claude/skills/small-council/.env
   ```

4. **Make scripts executable:**
   ```bash
   chmod +x ~/.claude/skills/small-council/*.sh
   ```

5. **Install the CLI tool:**
   ```bash
   uv tool install small-council  # or from source: uv tool install .
   ```

### Using the Skill

In Claude Code, just say:
- "Ask the small council about this architecture decision"
- "Consult the council on this code"
- "What does the small council think about..."

The skill will:
1. Craft a comprehensive prompt
2. Gather relevant files
3. Run the 3-stage deliberation in background (survives session restarts)
4. Present the synthesized consensus

### Skill Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Instructions Claude follows when skill is triggered |
| `council-tmux-start.sh` | Starts council in tmux session |
| `council-tmux-wait.sh` | Waits for completion, returns output |
| `council-tmux-status.sh` | Check status or list sessions |
| `council-tmux-cleanup.sh` | Clean up old sessions |

---

## JSON Output Schema

```json
{
  "query": "Your question",
  "stage1": [
    {"model": "openai/gpt-5.2", "response": "..."},
    {"model": "google/gemini-3-pro-preview", "response": "..."}
  ],
  "stage2": [
    {"model": "openai/gpt-5.2", "ranking": "...", "parsed_ranking": ["Response B", "Response A", "Response C", "Response D"]}
  ],
  "stage3": {
    "model": "openai/gpt-5.2-pro",
    "response": "Final synthesized answer..."
  },
  "metadata": {
    "label_to_model": {"Response A": "openai/gpt-5.2", ...},
    "aggregate_rankings": [
      {"model": "google/gemini-3-pro-preview", "average_rank": 1.5},
      {"model": "openai/gpt-5.2", "average_rank": 2.0}
    ]
  }
}
```

## License

MIT
