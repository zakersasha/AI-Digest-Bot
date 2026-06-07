#!/usr/bin/env bash
# Run ON the server (not from Windows without bash).
#
#   cd ~/AI-Digest-Bot
#   git pull
#   CERTBOT_EMAIL=you@brieflybot.pro bash landing/scripts/server-setup.sh
#
# Optional env:
#   NGINX_DIR=~/cv_portfolio/nginx
#   CV_COMPOSE_DIR=~/cv_portfolio
#   SSL_MODE=http|https|auto   (auto = issue cert if missing)
#   OAUTH_UPSTREAM=host.docker.internal:8080
set -euo pipefail

DOMAIN="brieflybot.pro"
EMAIL="${CERTBOT_EMAIL:-}"
SSL_MODE="${SSL_MODE:-auto}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LANDING_DIR="${PROJECT_DIR}/landing"

NGINX_DIR="${NGINX_DIR:-${HOME}/cv_portfolio/nginx}"
NGINX_CONF_D="${NGINX_DIR}/conf.d"
CV_COMPOSE_DIR="${CV_COMPOSE_DIR:-${HOME}/cv_portfolio}"

SITE_ROOT="${SITE_ROOT:-${LANDING_DIR}/www}"
WEBROOT="${WEBROOT:-${CV_COMPOSE_DIR}/certbot/www}"
CERT_DIR="${CERT_DIR:-${CV_COMPOSE_DIR}/certbot/conf}"
OAUTH_UPSTREAM="${OAUTH_UPSTREAM:-host.docker.internal:8080}"

reload_nginx() {
  if [[ -f "${CV_COMPOSE_DIR}/docker-compose.yml" ]] || [[ -f "${CV_COMPOSE_DIR}/docker-compose.yaml" ]]; then
    echo "Reloading nginx via docker compose in ${CV_COMPOSE_DIR}..."
    (cd "${CV_COMPOSE_DIR}" && docker compose exec nginx nginx -t)
    (cd "${CV_COMPOSE_DIR}" && docker compose exec nginx nginx -s reload)
    return
  fi
  if command -v nginx >/dev/null 2>&1; then
    nginx -t
    systemctl reload nginx
    return
  fi
  echo "WARN: cannot reload nginx — add volumes (see landing/README.md) and run:"
  echo "  cd ${CV_COMPOSE_DIR} && docker compose exec nginx nginx -s reload"
}

prepare_site_files() {
  bash "${SCRIPT_DIR}/sync-site.sh"
}

install_nginx_conf() {
  local src="$1"
  local dest="${NGINX_CONF_D}/brieflybot.pro.conf"
  mkdir -p "${NGINX_CONF_D}"
  sed "s|host.docker.internal:8080|${OAUTH_UPSTREAM}|g" "${src}" > "${dest}"
  echo "Nginx conf → ${dest}"
}

issue_certificate() {
  if [[ -z "${EMAIL}" ]]; then
    echo "Set CERTBOT_EMAIL to obtain SSL certificate."
    exit 1
  fi
  if ! command -v certbot >/dev/null 2>&1; then
    echo "Installing certbot..."
    apt-get update && apt-get install -y certbot
  fi
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
}

setup_renewal_hook() {
  local hook="/etc/letsencrypt/renewal-hooks/deploy/reload-brieflybot-nginx.sh"
  mkdir -p "$(dirname "${hook}")"
  cat > "${hook}" <<EOF
#!/bin/sh
cd ${CV_COMPOSE_DIR} && docker compose exec -T nginx nginx -t && docker compose exec -T nginx nginx -s reload
EOF
  chmod +x "${hook}"
  if systemctl list-unit-files certbot.timer >/dev/null 2>&1; then
    systemctl enable --now certbot.timer
  fi
}

has_certificate() {
  [[ -f "${CERT_DIR}/live/${DOMAIN}/fullchain.pem" ]]
}

echo "=== Briefly landing setup ==="
echo "Project:  ${PROJECT_DIR}"
echo "Nginx:    ${NGINX_CONF_D}"
echo "Site:     ${SITE_ROOT}"
echo "Certbot:  ${WEBROOT}"
echo ""

prepare_site_files

if [[ ! -d "${NGINX_DIR}" ]]; then
  echo "ERROR: ${NGINX_DIR} not found. Set NGINX_DIR=~/cv_portfolio/nginx"
  exit 1
fi

use_https=false
if [[ "${SSL_MODE}" == "https" ]]; then
  use_https=true
elif [[ "${SSL_MODE}" == "http" ]]; then
  use_https=false
elif has_certificate; then
  use_https=true
fi

if [[ "${use_https}" == "true" ]]; then
  install_nginx_conf "${LANDING_DIR}/nginx/brieflybot.pro.conf"
else
  install_nginx_conf "${LANDING_DIR}/nginx/brieflybot.pro.http.conf"
  if [[ "${SSL_MODE}" == "auto" ]] && [[ -n "${EMAIL}" ]]; then
    echo "Requesting Let's Encrypt certificate..."
    reload_nginx || true
    issue_certificate
    install_nginx_conf "${LANDING_DIR}/nginx/brieflybot.pro.conf"
    setup_renewal_hook
    use_https=true
  fi
fi

reload_nginx || true

echo ""
echo "Done."
echo "  Homepage:  http://${DOMAIN}/"
if [[ "${use_https}" == "true" ]]; then
  echo "  HTTPS:     https://${DOMAIN}/"
fi
echo "  Privacy:   https://${DOMAIN}/privacy-policy"
echo "  Terms:     https://${DOMAIN}/terms-of-service"
echo ""
echo "If site does not open — add Docker volumes (landing/cv_portfolio.volumes.example.txt)."
