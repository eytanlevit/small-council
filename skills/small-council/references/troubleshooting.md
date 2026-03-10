# Small Council Troubleshooting & Technical Notes

## Technical Notes

- Council sessions run in tmux at `council-<timestamp>-<pid>`
- Output captured to `/tmp/council-<session>.out`
- Completion marker at `/tmp/council-<session>.done`
- Sessions survive Claude process termination
- Cleanup old sessions: `small-council tmux cleanup`
- The tool supports glob patterns: `-f "src/**/*.ts"` and multiple file flags

## Troubleshooting

### Tmux Session Issues

**Find existing sessions:**
```bash
small-council tmux status --list
```

**View session output in real-time:**
```bash
tmux attach -t council-SESSIONID
# Ctrl-B D to detach without killing
```

**Kill stuck session:**
```bash
tmux kill-session -t council-SESSIONID
```

**Cleanup old sessions:**
```bash
small-council tmux cleanup --older-than 2
```

### API Key Issues

- Ensure `OPENROUTER_API_KEY` environment variable is set
- Check API key is valid and has credits at openrouter.ai
- The council queries 4 models in parallel + 1 chairman, so ensure sufficient rate limits
