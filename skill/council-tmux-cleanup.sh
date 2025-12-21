#!/bin/bash
# Cleanup old Small Council tmux sessions and temp files
#
# Usage:
#   council-tmux-cleanup.sh                    # Cleanup sessions older than 1 hour
#   council-tmux-cleanup.sh --older-than 24    # Cleanup sessions older than 24 hours
#   council-tmux-cleanup.sh --all              # Cleanup ALL council sessions

set -euo pipefail

HOURS=1

while [[ $# -gt 0 ]]; do
    case "$1" in
        --older-than)
            HOURS="$2"
            shift 2
            ;;
        --all)
            HOURS=0
            shift
            ;;
        *)
            echo "Usage: council-tmux-cleanup.sh [--older-than HOURS] [--all]" >&2
            exit 1
            ;;
    esac
done

echo "=== Cleaning up Small Council sessions older than $HOURS hour(s) ==="

CUTOFF=$(($(date +%s) - HOURS * 3600))
CLEANED=0

# Find and kill old tmux sessions
for session in $(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep "^council-" || true); do
    # Extract timestamp from session name (council-TIMESTAMP-PID)
    TIMESTAMP=$(echo "$session" | cut -d'-' -f2)

    if [[ -n "$TIMESTAMP" ]] && [[ "$TIMESTAMP" -lt "$CUTOFF" ]]; then
        echo "Killing session: $session"
        tmux kill-session -t "$session" 2>/dev/null || true
        ((CLEANED++)) || true
    fi
done

# Clean up old temp files
for done_file in /tmp/council-*.done; do
    [[ -f "$done_file" ]] || continue

    SESSION_ID=$(basename "$done_file" .done)
    TIMESTAMP=$(echo "$SESSION_ID" | cut -d'-' -f2)

    if [[ -n "$TIMESTAMP" ]] && [[ "$TIMESTAMP" -lt "$CUTOFF" ]]; then
        echo "Removing temp files for: $SESSION_ID"
        rm -f "/tmp/${SESSION_ID}.out" "/tmp/${SESSION_ID}.done" \
              "/tmp/${SESSION_ID}.pid" "/tmp/${SESSION_ID}.err" \
              "/tmp/${SESSION_ID}-wrapper.sh" 2>/dev/null || true
        ((CLEANED++)) || true
    fi
done

echo ""
echo "Cleaned up $CLEANED items"
