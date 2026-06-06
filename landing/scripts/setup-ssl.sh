#!/usr/bin/env bash
# Obtain Let's Encrypt certificate for brieflybot.pro and enable auto-renewal.
# Run on the server as root (or with sudo).
set -euo pipefail

DOMAIN="brieflybot.pro"
EMAIL="${CERTBOT_EMAIL:-}"
WEBROOT="/var/www/certbot"
SITE_ROOT="/var/www/brieflybot.pro"
NGINX_CONF="/etc/nginx/conf.d/brieflybot.pro.conf"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LANDING_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -z "${EMAIL}" ]]; then
  echo "Set CERTBOT_EMAIL, e.g.: CERTBOT_EMAIL=you@brieflybot.pro sudo -E bash setup-ssl.sh"
  exit 1
fi

if ! command -v nginx >/dev/null 2>&1; then
  echo "nginx is not installed."
  exit 1
fi

if ! command -v certbot >/dev/null 2>&1; then
  echo "Installing certbot..."
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update
    apt-get install -y certbot
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y certbot
  else
    echo "Install certbot manually, then re-run this script."
    exit 1
  fi
fi

mkdir -p "${WEBROOT}" "${SITE_ROOT}/docs"
chown -R nginx:nginx "${WEBROOT}" "${SITE_ROOT}" 2>/dev/null || chown -R www-data:www-data "${WEBROOT}" "${SITE_ROOT}" 2>/dev/null || true

# Step 1: HTTP-only nginx (ACME + static site)
cp "${LANDING_DIR}/nginx/brieflybot.pro.http.conf" "${NGINX_CONF}"
nginx -t
systemctl reload nginx

# Step 2: Request certificate (webroot — does not touch other vhosts)
certbot certonly \
  --webroot \
  -w "${WEBROOT}" \
  -d "${DOMAIN}" \
  -d "www.${DOMAIN}" \
  --email "${EMAIL}" \
  --agree-tos \
  --no-eff-email \
  --non-interactive

# Step 3: Switch to HTTPS config
cp "${LANDING_DIR}/nginx/brieflybot.pro.conf" "${NGINX_CONF}"
nginx -t
systemctl reload nginx

# Step 4: Auto-renewal hook (reload nginx after renew)
HOOK="/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh"
mkdir -p "$(dirname "${HOOK}")"
cat > "${HOOK}" <<'EOF'
#!/bin/sh
nginx -t && systemctl reload nginx
EOF
chmod +x "${HOOK}"

# certbot.timer is installed with the package on most distros
if systemctl list-unit-files certbot.timer >/dev/null 2>&1; then
  systemctl enable --now certbot.timer
  echo "certbot.timer enabled (checks renewal twice daily)."
else
  echo "Add cron: 0 3 * * * certbot renew --quiet --deploy-hook 'nginx -t && systemctl reload nginx'"
fi

echo ""
echo "SSL ready."
echo "  https://${DOMAIN}/"
echo "  https://${DOMAIN}/privacy-policy"
echo "  https://${DOMAIN}/terms-of-service"
echo "  https://${DOMAIN}/oauth/gmail/callback  (Gmail OAuth)"
