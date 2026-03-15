#!/usr/bin/env bash
set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }

errors=0

echo ""
echo "=== Small Council: Dependency Check ==="
echo ""

# 1. tmux
if command -v tmux &>/dev/null; then
  ok "tmux installed ($(tmux -V))"
else
  fail "tmux not found"
  echo "    Install: brew install tmux (macOS) or apt install tmux (Linux)"
  errors=$((errors + 1))
fi

# 2. small-council CLI
LOCAL_REPO="$HOME/projects/small-council"
if [[ -d "$LOCAL_REPO" ]] && command -v uv &>/dev/null; then
  # Local repo exists — always force-reinstall to pick up latest changes
  if uv tool install --force --reinstall "$LOCAL_REPO" 2>/dev/null; then
    ok "small-council CLI installed from local repo (force-reinstalled)"
  else
    fail "Could not install small-council CLI from local repo"
    errors=$((errors + 1))
  fi
elif command -v small-council &>/dev/null; then
  ok "small-council CLI installed"
else
  warn "small-council CLI not found — attempting install..."

  installed=false

  # Try uv tool install (PyPI / GitHub)
  if command -v uv &>/dev/null; then
    if uv tool install small-council 2>/dev/null; then
      installed=true
    elif uv tool install "git+https://github.com/eytanlevit/small-council" 2>/dev/null; then
      installed=true
    fi
  fi

  # Fallback to pipx
  if ! $installed && command -v pipx &>/dev/null; then
    if pipx install small-council 2>/dev/null; then
      installed=true
    fi
  fi

  if $installed; then
    ok "small-council CLI installed successfully"
  else
    fail "Could not install small-council CLI"
    echo "    Manual install: uv tool install small-council"
    errors=$((errors + 1))
  fi
fi

# 3. API key
if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then
  ok "OPENROUTER_API_KEY is set"
elif [[ -f "$HOME/.small-council.yaml" ]] && grep -q 'api_key' "$HOME/.small-council.yaml" 2>/dev/null; then
  ok "API key found in ~/.small-council.yaml"
else
  fail "No API key configured"
  echo "    Set OPENROUTER_API_KEY env var or add api_key to ~/.small-council.yaml"
  errors=$((errors + 1))
fi

echo ""
if [[ $errors -eq 0 ]]; then
  ok "All dependencies satisfied"
  exit 0
else
  fail "$errors issue(s) found"
  exit 1
fi
