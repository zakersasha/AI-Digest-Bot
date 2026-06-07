#!/usr/bin/env bash
# Copy landing + legal PDFs into landing/www/ (what nginx actually serves).
# Run on server after updating docs/ or briefly-landing.html:
#
#   cd ~/AI-Digest-Bot
#   git pull
#   bash landing/scripts/sync-site.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SITE_ROOT="${SITE_ROOT:-${PROJECT_DIR}/landing/www}"

mkdir -p "${SITE_ROOT}/docs"

cp -f "${PROJECT_DIR}/briefly-landing.html" "${SITE_ROOT}/index.html"
cp -f "${PROJECT_DIR}/docs/Briefly Privacy Policy.pdf" "${SITE_ROOT}/docs/briefly-privacy-policy.pdf"
cp -f "${PROJECT_DIR}/docs/Briefly Terms of Service.pdf" "${SITE_ROOT}/docs/briefly-terms-of-service.pdf"

# Keep landing/docs in sync (optional mirror, not served by nginx)
cp -f "${SITE_ROOT}/docs/"*.pdf "${PROJECT_DIR}/landing/docs/" 2>/dev/null || true

echo "Synced → ${SITE_ROOT}"
ls -la "${SITE_ROOT}/docs/"
if command -v md5sum >/dev/null 2>&1; then
  md5sum "${PROJECT_DIR}/docs/"*.pdf "${SITE_ROOT}/docs/"*.pdf
fi
