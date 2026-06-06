#!/usr/bin/env bash
# Sync landing files to the server. Does not replace main nginx.conf — only conf.d snippet.
set -euo pipefail

SERVER="${1:-}"
REMOTE_DIR="/var/www/brieflybot.pro"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LANDING_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${LANDING_DIR}/.." && pwd)"

if [[ -z "${SERVER}" ]]; then
  echo "Usage: ./deploy.sh user@your-server"
  echo "Example: ./deploy.sh root@178.170.249.108"
  exit 1
fi

# Keep PDFs in sync from docs/
mkdir -p "${LANDING_DIR}/docs"
cp "${ROOT_DIR}/docs/Briefly Privacy Policy.pdf" "${LANDING_DIR}/docs/briefly-privacy-policy.pdf"
cp "${ROOT_DIR}/docs/Briefly Terms of Service.pdf" "${LANDING_DIR}/docs/briefly-terms-of-service.pdf"
cp "${ROOT_DIR}/briefly-landing.html" "${LANDING_DIR}/index.html"

ssh "${SERVER}" "mkdir -p ${REMOTE_DIR}/docs /var/www/certbot"

rsync -avz --delete \
  "${LANDING_DIR}/index.html" \
  "${LANDING_DIR}/docs/" \
  "${SERVER}:${REMOTE_DIR}/"

echo "Files deployed to ${SERVER}:${REMOTE_DIR}"
echo "Nginx snippet: landing/nginx/brieflybot.pro.conf → /etc/nginx/conf.d/brieflybot.pro.conf"
echo "First-time SSL: CERTBOT_EMAIL=you@brieflybot.pro sudo -E bash landing/scripts/setup-ssl.sh"
