#!/usr/bin/env bash
# Sync landing + legal HTML into landing/www/ (what nginx serves).
#
#   cd ~/AI-Digest-Bot
#   git pull
#   bash landing/scripts/sync-site.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LANDING_DIR="${PROJECT_DIR}/landing"
SITE_ROOT="${SITE_ROOT:-${LANDING_DIR}/www}"

mkdir -p "${SITE_ROOT}/assets"

cp -f "${PROJECT_DIR}/briefly-landing.html" "${SITE_ROOT}/index.html"
cp -f "${LANDING_DIR}/privacy-policy.html" "${SITE_ROOT}/privacy-policy.html"
cp -f "${LANDING_DIR}/terms-of-service.html" "${SITE_ROOT}/terms-of-service.html"
cp -f "${LANDING_DIR}/www/assets/shared.css" "${SITE_ROOT}/assets/shared.css"

echo "Synced → ${SITE_ROOT}"
ls -la "${SITE_ROOT}" "${SITE_ROOT}/assets/"
