#!/usr/bin/env bash
# Fix: http://brieflybot.pro works, https:// redirects to CV site.
# Cause: no SSL cert / no HTTPS server block for brieflybot.pro on port 443.
#
#   cd ~/AI-Digest-Bot
#   CERTBOT_EMAIL=you@brieflybot.pro bash landing/scripts/fix-https.sh
set -euo pipefail

DOMAIN="brieflybot.pro"
EMAIL="${CERTBOT_EMAIL:-}"
CV_COMPOSE_DIR="${CV_COMPOSE_DIR:-${HOME}/cv_portfolio}"
NGINX_CONF_D="${NGINX_DIR:-${CV_COMPOSE_DIR}/nginx}/conf.d"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LANDING_DIR="${PROJECT_DIR}/landing"

WEBROOT="${CV_COMPOSE_DIR}/certbot/www"
CERT_DIR="${CV_COMPOSE_DIR}/certbot/conf"
CERT_FILE="${CERT_DIR}/live/${DOMAIN}/fullchain.pem"
DEST_CONF="${NGINX_CONF_D}/brieflybot.pro.conf"

echo "=== Fix HTTPS for ${DOMAIN} ==="

if [[ ! -f "${CERT_FILE}" ]]; then
  if [[ -z "${EMAIL}" ]]; then
    echo "ERROR: certificate missing: ${CERT_FILE}"
    echo "Run: CERTBOT_EMAIL=you@brieflybot.pro bash landing/scripts/fix-https.sh"
    exit 1
  fi
  echo "Issuing certificate..."
  mkdir -p "${WEBROOT}" "${CERT_DIR}" "${CV_COMPOSE_DIR}/certbot/work" "${CV_COMPOSE_DIR}/certbot/logs"
  certbot certonly \
    --webroot \
    -w "${WEBROOT}" \
    --config-dir "${CERT_DIR}" \
    --work-dir "${CV_COMPOSE_DIR}/certbot/work" \
    --logs-dir "${CV_COMPOSE_DIR}/certbot/logs" \
    -d "${DOMAIN}" \
    -d "www.${DOMAIN}" \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    --non-interactive
fi

echo "Installing HTTPS nginx config..."
cp "${LANDING_DIR}/nginx/brieflybot.pro.conf" "${DEST_CONF}"

echo "Testing nginx inside Docker..."
cd "${CV_COMPOSE_DIR}"
docker compose exec nginx nginx -t

echo "Reloading nginx..."
docker compose exec nginx nginx -s reload

echo ""
echo "OK. Check:"
echo "  curl -I https://${DOMAIN}/"
echo "  curl -I https://${DOMAIN}/privacy-policy"
