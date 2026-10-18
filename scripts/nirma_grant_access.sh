#!/usr/bin/env bash
# Run ONCE on the Nirma GPU server, in the account the pipeline will run under, to let
# Neal's laptop (and the Claude Code session on it) log in with its SSH key:
#   bash scripts/nirma_grant_access.sh
# Revoke later by deleting the line ending in "neal-claude-nirma-dti" from ~/.ssh/authorized_keys.
set -euo pipefail

KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIB+LdUOzyFzROTIw87vC/KK1PSVv0KnL6bo2xeJyAe+p neal-claude-nirma-dti'

mkdir -p ~/.ssh && chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
if grep -qF "$KEY" ~/.ssh/authorized_keys; then
  echo "key already present"
else
  echo "$KEY" >> ~/.ssh/authorized_keys
  echo "key added to ~/.ssh/authorized_keys"
fi

echo
echo "Send these to Neal:"
echo "  user:      $(whoami)"
echo "  host:      $(hostname -f 2> /dev/null || hostname)"
echo "  addresses: $(hostname -I 2> /dev/null || echo '?')"
echo "  repo:      $(cd "$(dirname "$0")/.." && pwd)"
echo "  ssh port:  $(grep -E '^\s*Port\s' /etc/ssh/sshd_config 2> /dev/null | awk '{print $2}' | head -1 || true) (empty = 22)"
command -v tmux > /dev/null || echo "  note: tmux not installed; the scripts fall back to nohup"
