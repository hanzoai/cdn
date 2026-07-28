#!/usr/bin/env bash
# Publish CDN content to cdn.hanzo.ai (Cloudflare Worker + R2), purge the edge,
# and verify what is actually being served.
#
#   cdn.hanzo.ai/<path>  <-  Worker  <-  R2 pub/hanzo/<path>  <-  repo hanzo/<path>
#
#   export CLOUDFLARE_API_TOKEN=...        # R2 write + Cache Purge on the zone
#   ./deploy.sh                            # market catalog only (default)
#   SUBTREE=hanzo ./deploy.sh              # the whole asset tree
#
# Purge needs CLOUDFLARE_ZONE_ID. Without it the upload still succeeds and the
# edge ages out on its own — index.json is served with a short TTL, so that is
# minutes, not forever.
set -euo pipefail
cd "$(dirname "$0")"

BUCKET="${R2_BUCKET:-pub}"
SUBTREE="${SUBTREE:-hanzo/market}"
HOST="${CDN_HOST:-cdn.hanzo.ai}"
ZONE="${CLOUDFLARE_ZONE_ID:-}"
: "${CLOUDFLARE_API_TOKEN:?set CLOUDFLARE_API_TOKEN}"

[ -d "$SUBTREE" ] || { echo "no such subtree: $SUBTREE" >&2; exit 1; }

# Resolve wrangler ONCE. This previously ran `npx --yes wrangler@latest` per
# file, which re-resolved the package on every single object.
WRANGLER=(npx --yes wrangler@4)

content_type() {
  case "$1" in
    *.json)  echo "application/json" ;;
    *.html)  echo "text/html" ;;
    *.svg)   echo "image/svg+xml" ;;
    *.png)   echo "image/png" ;;
    *.jpg|*.jpeg) echo "image/jpeg" ;;
    *.webp)  echo "image/webp" ;;
    *.woff2) echo "font/woff2" ;;
    *.css)   echo "text/css" ;;
    *.js)    echo "application/javascript" ;;
    *)       echo "application/octet-stream" ;;
  esac
}

echo "==> uploading $SUBTREE -> r2://$BUCKET/$SUBTREE"
n=0
while IFS= read -r f; do
  "${WRANGLER[@]}" r2 object put "${BUCKET}/${f}" \
    --file="$f" --content-type="$(content_type "$f")" --remote >/dev/null
  n=$((n + 1))
  printf '\r    %d files' "$n"
done < <(find "$SUBTREE" -type f | sort)
echo " uploaded"

# Purge the edge for exactly what we just wrote. Cloudflare caps purge-by-url at
# 30 files per call, so send it in batches.
if [ -n "$ZONE" ]; then
  echo "==> purging edge cache on $HOST"
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  find "$SUBTREE" -type f | sed "s#^hanzo/#https://${HOST}/#" | sort > "$tmp/urls"
  split -l 30 "$tmp/urls" "$tmp/batch-"
  for batch in "$tmp"/batch-*; do
    curl -fsS -X POST \
      "https://api.cloudflare.com/client/v4/zones/${ZONE}/purge_cache" \
      -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
      -H "Content-Type: application/json" \
      --data "$(jq -R -s -c '{files: (split("\n") | map(select(length > 0)))}' < "$batch")" \
      >/dev/null
  done
  echo "    purged $n urls"
else
  echo "==> skipping purge (set CLOUDFLARE_ZONE_ID to purge on demand)"
fi

# Verify the edge serves what the repo says it should. A deploy you cannot
# observe is not a deploy.
echo "==> verifying https://${HOST}/market/index.json"
want=$(jq -r .version hanzo/market/index.json)
got=$(curl -fsS --retry 3 --retry-delay 2 "https://${HOST}/market/index.json" | jq -r .version)
[ "$want" = "$got" ] || { echo "version mismatch: repo=$want edge=$got" >&2; exit 1; }
echo "    live, version $got"
