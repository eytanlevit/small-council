#!/bin/bash
# Small Council tmux wrapper - starts council in detached tmux session
# Output captured to file, survives parent process death
#
# Usage: council-tmux-start.sh -p "prompt" [-f file1.ts] [-f file2.ts]
#
# Outputs JSON with session info:
#   {"session":"council-xxx","output":"/tmp/council-xxx.out","done":"/tmp/council-xxx.done"}

set -euo pipefail

SKILL_DIR="$HOME/.claude/skills/small-council"

# Load API key
if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
    if [[ -f "$SKILL_DIR/.env" ]]; then
        export OPENROUTER_API_KEY=$(grep OPENROUTER_API_KEY "$SKILL_DIR/.env" 2>/dev/null | cut -d= -f2 || true)
    fi
fi

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
    echo "ERROR: OPENROUTER_API_KEY not set. Add it to $SKILL_DIR/.env" >&2
    exit 1
fi

# Generate unique session ID
SESSION_ID="council-$(date +%s)-$$"
OUTPUT_FILE="/tmp/${SESSION_ID}.out"
DONE_FILE="/tmp/${SESSION_ID}.done"
PID_FILE="/tmp/${SESSION_ID}.pid"
ERROR_FILE="/tmp/${SESSION_ID}.err"

# Parse arguments to build the command
PROMPT=""
FILES=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--prompt)
            PROMPT="$2"
            shift 2
            ;;
        -f|--file)
            FILES+=("$2")
            shift 2
            ;;
        *)
            # Pass through any other arguments
            shift
            ;;
    esac
done

if [[ -z "$PROMPT" ]]; then
    echo "ERROR: No prompt provided. Use -p 'your prompt'" >&2
    exit 1
fi

# Build small-council command
COUNCIL_CMD="export OPENROUTER_API_KEY='${OPENROUTER_API_KEY}'; small-council -a"

# Add file arguments (only if files were specified)
if [[ ${#FILES[@]} -gt 0 ]]; then
    for file in "${FILES[@]}"; do
        COUNCIL_CMD="$COUNCIL_CMD -f '$file'"
    done
fi

# Add the prompt (escape single quotes)
escaped_prompt="${PROMPT//\'/\'\\\'\'}"
COUNCIL_CMD="$COUNCIL_CMD '$escaped_prompt'"

# Create the wrapper script that will run in tmux
WRAPPER_SCRIPT="/tmp/${SESSION_ID}-wrapper.sh"
cat > "$WRAPPER_SCRIPT" << 'WRAPPER_EOF'
#!/bin/bash
OUTPUT_FILE="$1"
DONE_FILE="$2"
PID_FILE="$3"
ERROR_FILE="$4"
shift 4

# Record our PID
echo $$ > "$PID_FILE"

# Run council, capture output
{
    eval "$@" 2>&1
    EXIT_CODE=$?
    if [[ $EXIT_CODE -ne 0 ]]; then
        echo "EXIT_CODE=$EXIT_CODE" > "$ERROR_FILE"
    fi
} | tee "$OUTPUT_FILE"

# Signal completion
date '+%Y-%m-%d %H:%M:%S' > "$DONE_FILE"
echo "COMPLETED" >> "$DONE_FILE"
WRAPPER_EOF
chmod +x "$WRAPPER_SCRIPT"

# Start tmux session (detached)
tmux new-session -d -s "$SESSION_ID" \
    "$WRAPPER_SCRIPT" "$OUTPUT_FILE" "$DONE_FILE" "$PID_FILE" "$ERROR_FILE" "$COUNCIL_CMD"

# Output session info as JSON
cat << EOF
{
  "session": "$SESSION_ID",
  "output": "$OUTPUT_FILE",
  "done": "$DONE_FILE",
  "pid_file": "$PID_FILE",
  "error_file": "$ERROR_FILE"
}
EOF
