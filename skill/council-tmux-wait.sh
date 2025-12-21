#!/bin/bash
# Wait for Small Council tmux session to complete
#
# Usage: council-tmux-wait.sh <session_id> [timeout_seconds] [poll_interval]
#
# Outputs:
#   - If complete: the contents of the output file
#   - If still running: status message with "RUNNING" marker
#   - If error: error message
#
# Exit codes:
#   0 = completed successfully
#   1 = still running (use with --no-wait)
#   2 = error/timeout

set -euo pipefail

SESSION_ID="${1:-}"
TIMEOUT="${2:-1800}"  # Default 30 minutes
POLL_INTERVAL="${3:-10}"  # Default 10 seconds

if [[ -z "$SESSION_ID" ]]; then
    echo "Usage: council-tmux-wait.sh <session_id> [timeout_seconds] [poll_interval]" >&2
    exit 2
fi

OUTPUT_FILE="/tmp/${SESSION_ID}.out"
DONE_FILE="/tmp/${SESSION_ID}.done"
ERROR_FILE="/tmp/${SESSION_ID}.err"

# Check if session exists
if ! tmux has-session -t "$SESSION_ID" 2>/dev/null; then
    # Session doesn't exist - check if it completed
    if [[ -f "$DONE_FILE" ]]; then
        echo "=== Small Council Response ==="
        cat "$OUTPUT_FILE" 2>/dev/null || echo "(no output)"
        exit 0
    else
        echo "ERROR: Session '$SESSION_ID' not found and no completion marker" >&2
        exit 2
    fi
fi

# Poll until completion or timeout
START_TIME=$(date +%s)
while true; do
    # Check if done
    if [[ -f "$DONE_FILE" ]]; then
        echo "=== Small Council Response ==="
        cat "$OUTPUT_FILE" 2>/dev/null || echo "(no output)"

        # Check for errors
        if [[ -f "$ERROR_FILE" ]]; then
            echo ""
            echo "=== Warning: Process exited with error ==="
            cat "$ERROR_FILE"
        fi

        # Cleanup tmux session if still exists
        tmux kill-session -t "$SESSION_ID" 2>/dev/null || true
        exit 0
    fi

    # Check timeout
    ELAPSED=$(($(date +%s) - START_TIME))
    if [[ $ELAPSED -ge $TIMEOUT ]]; then
        echo "TIMEOUT: Small Council still running after ${TIMEOUT}s" >&2
        echo "Session: $SESSION_ID" >&2
        echo "Partial output:" >&2
        tail -50 "$OUTPUT_FILE" 2>/dev/null || echo "(no output yet)"
        exit 2
    fi

    # Show progress every poll
    REMAINING=$((TIMEOUT - ELAPSED))
    OUTPUT_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || echo "0")
    echo "RUNNING: Session $SESSION_ID active (${ELAPSED}s elapsed, ${REMAINING}s remaining, ${OUTPUT_SIZE} bytes output)"

    sleep "$POLL_INTERVAL"
done
