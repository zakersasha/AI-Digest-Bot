#!/usr/bin/env bash
# Prefer running ON the server:
#   cd ~/AI-Digest-Bot && bash landing/scripts/server-setup.sh
#
# Remote mode (Linux/Mac with bash + ssh):
#   bash landing/scripts/deploy.sh root@37.230.114.25
set -euo pipefail

SERVER="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${SERVER}" ]]; then
  exec bash "${SCRIPT_DIR}/server-setup.sh"
fi

echo "Remote deploy → ${SERVER}"
echo "Pulling latest code and running server-setup on remote host..."

ssh "${SERVER}" 'bash -s' <<'REMOTE'
set -euo pipefail
cd ~/AI-Digest-Bot
git pull
bash landing/scripts/server-setup.sh
REMOTE

echo "Done."
