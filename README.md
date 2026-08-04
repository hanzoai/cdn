# Hanzo CDN Assets

Static assets served via Cloudflare Workers + R2 at `cdn.hanzo.ai`.

## Structure

```
hanzo/
├── brand/        Hanzo logo variants (SVG, PNG, favicon, apple, dock icons)
├── buttons/      OAuth provider login button SVGs
├── flag-icons/   271 ISO 3166-1 country flag SVGs
├── fonts/        Inter + Roboto Mono web fonts (woff2)
├── iam/models/   Face recognition models
├── img/          Social provider, payment, captcha, app logos
├── market/       Backend-less Market: agents/tools/plugins catalog (JSON)
├── partners/     Partner/ecosystem logos (AWS, NVIDIA, Techstars, etc.)
├── press/        Press kit assets
└── providers/    AI model provider icons (OpenAI, Anthropic, Mistral, etc.)
```

## Market (no backend required)

The Hanzo / Lux / Zoo desktop apps read their catalog as **static JSON** from
here, so the Market works with **no backend**. Every read is a file. Each app
bundles a trimmed copy of the same documents and falls back to it when the CDN
is unreachable, so the Market also works with no network.

| URL | Contents |
|-----|----------|
| `cdn.hanzo.ai/market/index.json` | manifest: `schema`, `version`, counts, file map |
| `cdn.hanzo.ai/market/agents.json` | agents catalog (`{products,total,page,limit,totalPages}`) |
| `cdn.hanzo.ai/market/tools.json` | tools catalog, same shape |
| `cdn.hanzo.ai/market/categories.json` | categories |
| `cdn.hanzo.ai/market/featured.json` | featured collections |
| `cdn.hanzo.ai/market/plugins.json` | plugin/integration registry (composio) |
| `cdn.hanzo.ai/market/tools/{id}.json` | per-tool detail |

**Versioning.** `index.json` carries a `schema` (bumped only on a breaking shape
change; a client that does not recognise it keeps using its bundle) and a
`version` that is a content digest over every served document. The version
changes if and only if what the CDN serves changes, which is what makes a deploy
verifiable — `deploy.sh` refuses to succeed unless the edge reports the version
the repo just built.

**CORS:** the Worker sends `Access-Control-Allow-Origin: *` so app webviews can
fetch directly.

### Regenerating

`scripts/market.py` is the only thing that writes catalog files — the CDN
documents, the apps' offline bundles and the CI gate all come from it, so they
cannot disagree about the schema or the digest.

```bash
scripts/market.py gen --from ../store \
  --bundle ../desktop/apps/hanzo-desktop/src/lib/market-catalog.json \
  --bundle ../../zoo/app/apps/lux-desktop/src/lib/market-catalog.json \
  --bundle ../../zoo/app/apps/zoo-desktop/src/lib/market-catalog.json

scripts/market.py check    # CI gate: valid JSON, manifest matches, digest matches
```

`--from` is a checkout of the curated flatfile catalog (`hanzoai/store`): one
JSON per item under `data/agents/` and `data/tools/`. That repo stays the
editorial source — a CMS or commerce backend publishes **into** this layout
rather than being queried at read time, which is what keeps reads backend-less.

## Deployment

CI (`hanzo.yml` → `hanzoai/ci`) gates the catalog on every push. Publishing is
this repo's `deploy.sh`: upload to R2, purge the Cloudflare edge for exactly the
URLs written, then verify the live manifest matches the repo.

```bash
export CLOUDFLARE_API_TOKEN=...           # R2 write + Cache Purge on the zone
export CLOUDFLARE_ZONE_ID=...             # enables purge-on-deploy
./deploy.sh                               # market catalog (default)
SUBTREE=hanzo ./deploy.sh                 # the whole asset tree
```

## Domains

- `cdn.hanzo.ai` → `pub/hanzo/*`
- `cdn.lux.network` → `pub/lux/*`
- `cdn.zoo.ngo` → `pub/zoo/*`
- `cdn.pars.network` → `pub/pars/*`

Licensed under **MIT OR Apache-2.0**, per [HIP-0137](https://github.com/hanzoai/hips/blob/main/HIPs/hip-0137-one-license.md).
