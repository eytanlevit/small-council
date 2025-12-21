#!/bin/bash
# Check status of Small Council tmux sessions
#
# Usage:
#   council-tmux-status.sh <session_id>    # Check specific session
#   council-tmux-status.sh --list          # List all council sessions
#
# Exit codes:
#   0 = session found/completed
#   1 = session running
#   2 = session not found

set -euo pipefail

# List all council sessions
if [[ "${1:-}" == "--list" || "${1:-}" == "-l" ]]; then
    echo "=== Active Small Council Sessions ==="
    tmux list-sessions 2>/dev/null | grep "^council-" || echo "(none)"

    echo ""
    echo "=== Completed Sessions (output files) ==="
    ls -la /tmp/council-*.done 2>/dev/null | head -20 || echo "(none)"
    exit 0
fi

SESSION_ID="${1:-}"

if [[ -z "$SESSION_ID" ]]; then
    echo "Usage: council-tmux-status.sh <session_id> | --list" >&2
    exit 2
fi

OUTPUT_FILE="/tmp/${SESSION_ID}.out"
DONE_FILE="/tmp/${SESSION_ID}.done"
PID_FILE="/tmp/${SESSION_ID}.pid"
ERROR_FILE="/tmp/${SESSION_ID}.err"

# Check completion first
if [[ -f "$DONE_FILE" ]]; then
    COMPLETION_TIME=$(head -1 "$DONE_FILE")
    OUTPUT_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || echo "0")

    echo "Status: COMPLETED"
    echo "Completed at: $COMPLETION_TIME"
    echo "Output file: $OUTPUT_FILE ($OUTPUT_SIZE bytes)"

    if [[ -f "$ERROR_FILE" ]]; then
        echo "Warning: Process had errors (see $ERROR_FILE)"
    fi

    exit 0
fi

# Check if session exists
if tmux has-session -t "$SESSION_ID" 2>/dev/null; then
    OUTPUT_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || echo "0")
    PID=$(cat "$PID_FILE" 2>/dev/null || echo "unknown")

    echo "Status: RUNNING"
    echo "Session: $SESSION_ID"
    echo "PID: $PID"
    echo "Output so far: $OUTPUT_SIZE bytes"
    echo ""
    echo "To view live output: tmux attach -t $SESSION_ID"
    echo "To detach: Ctrl-B D"

    exit 1
fi

# Session not found
echo "Status: NOT FOUND"
echo "Session '$SESSION_ID' does not exist and has no completion marker"
exit 2
