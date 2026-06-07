#!/usr/bin/env bash
# Publish CDN content to cdn.hanzo.ai (Cloudflare Worker + R2).
#
# Two ways:
#  (A) Existing tool — uploads the whole hanzo/ tree (incl. market/):
#        cd ~/work/hanzo/cdn-worker && ./upload.sh ~/work/hanzo/cdn/hanzo hanzo
#  (B) Self-contained (this script) — pushes just the market data via wrangler.
#        export CLOUDFLARE_API_TOKEN=...  CLOUDFLARE_ACCOUNT_ID=...
#        R2_BUCKET=pub ./deploy.sh        # bucket behind cdn.hanzo.ai (pub/hanzo/*)
#
# cdn.hanzo.ai/<path>  <-  R2  pub/hanzo/<path>  <-  repo  hanzo/<path>
set -euo pipefail
cd "$(dirname "$0")"
BUCKET="${R2_BUCKET:-pub}"
find hanzo/market -type f | while read -r f; do
  ct="application/json"; case "$f" in *.html) ct="text/html";; esac
  echo "  -> ${BUCKET}/${f}"
  npx --yes wrangler@latest r2 object put "${BUCKET}/${f}" \
    --file="$f" --content-type="$ct" --remote
done
echo "Done. Verify: https://cdn.hanzo.ai/market/index.json"
