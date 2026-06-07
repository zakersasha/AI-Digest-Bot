#!/usr/bin/env bash
# Deprecated wrapper — use server-setup.sh on the server.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/server-setup.sh"
