#!/bin/bash
# Small Council tmux wrapper - starts council in detached tmux session
# Output captured to file, survives parent process death
#
# Usage: council-tmux-start.sh -p "prompt" [-f file1.ts] [-f file2.ts]
#        council-tmux-start.sh -P /path/to/prompt-file [-f file1.ts]
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

# Parse arguments
PROMPT=""
PROMPT_FILE=""
FILES=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--prompt)
            PROMPT="$2"
            shift 2
            ;;
        -P|--prompt-file)
            PROMPT_FILE="$2"
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

# -P (prompt file) takes precedence over -p (inline prompt)
if [[ -n "$PROMPT_FILE" ]]; then
    if [[ ! -f "$PROMPT_FILE" ]]; then
        echo "ERROR: Prompt file not found: $PROMPT_FILE" >&2
        exit 1
    fi
    PROMPT="$(cat "$PROMPT_FILE")"
fi

if [[ -z "$PROMPT" ]]; then
    echo "ERROR: No prompt provided. Use -p 'your prompt' or -P /path/to/prompt-file" >&2
    exit 1
fi

# Write prompt to a temp file so it never passes through eval/shell interpretation
PROMPT_TMPFILE="/tmp/${SESSION_ID}-prompt.txt"
printf '%s' "$PROMPT" > "$PROMPT_TMPFILE"

# Write file args to a temp file (one per line) so they don't need shell escaping either
FILES_TMPFILE="/tmp/${SESSION_ID}-files.txt"
if [[ ${#FILES[@]} -gt 0 ]]; then
    printf '%s\n' "${FILES[@]}" > "$FILES_TMPFILE"
else
    : > "$FILES_TMPFILE"
fi

# Write API key to a temp file with restricted permissions (Bug 3 fix)
# This prevents the key from appearing in shell error traces, command strings, or /tmp/*.out files
APIKEY_TMPFILE="/tmp/${SESSION_ID}-apikey"
printf '%s' "$OPENROUTER_API_KEY" > "$APIKEY_TMPFILE"
chmod 600 "$APIKEY_TMPFILE"

# Create the wrapper script that will run in tmux
# No eval, no embedded secrets — all data read from temp files
WRAPPER_SCRIPT="/tmp/${SESSION_ID}-wrapper.sh"
cat > "$WRAPPER_SCRIPT" << 'WRAPPER_EOF'
#!/bin/bash
OUTPUT_FILE="$1"
DONE_FILE="$2"
PID_FILE="$3"
ERROR_FILE="$4"
PROMPT_TMPFILE="$5"
FILES_TMPFILE="$6"
APIKEY_TMPFILE="$7"

# Record our PID
echo $$ > "$PID_FILE"

# Load API key from file (never appears in command strings or error traces)
export OPENROUTER_API_KEY="$(cat "$APIKEY_TMPFILE")"

# Build the command as an array — no eval, no shell interpretation of prompt text
CMD=(small-council -a)

# Add file arguments
while IFS= read -r file; do
    [[ -n "$file" ]] && CMD+=(-f "$file")
done < "$FILES_TMPFILE"

# Add the prompt (read from file, never shell-interpreted)
CMD+=("$(cat "$PROMPT_TMPFILE")")

# Run council, capture output
{
    "${CMD[@]}" 2>&1
    EXIT_CODE=$?
    if [[ $EXIT_CODE -ne 0 ]]; then
        echo "EXIT_CODE=$EXIT_CODE" > "$ERROR_FILE"
    fi
} | tee "$OUTPUT_FILE"

# Clean up API key file
rm -f "$APIKEY_TMPFILE"

# Signal completion
date '+%Y-%m-%d %H:%M:%S' > "$DONE_FILE"
echo "COMPLETED" >> "$DONE_FILE"
WRAPPER_EOF
chmod +x "$WRAPPER_SCRIPT"

# Start tmux session — wrapper script path and temp file paths are safe (no user content)
# The prompt, files, and API key are all read from temp files inside the wrapper
tmux new-session -d -s "$SESSION_ID" \
    "$WRAPPER_SCRIPT" "$OUTPUT_FILE" "$DONE_FILE" "$PID_FILE" "$ERROR_FILE" "$PROMPT_TMPFILE" "$FILES_TMPFILE" "$APIKEY_TMPFILE"

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
