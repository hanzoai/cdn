# cdn

**Org:** hanzoai  ·  **Ecosystem:** hanzo  ·  **Path:** `/Users/a/work/hanzo/hanzoai/cdn`
**Origin:** https://github.com/hanzoai/cdn.git

## Discovery

This file (`CLAUDE.md`) is the canonical agent-facing readme; `LLM.md` is a symlink to it. Update either name and both stay in sync.

## Where to look first

- `README.md` — human-facing overview (if present)
- `package.json` / `Cargo.toml` / `pyproject.toml` / `go.mod` — language & deps
- `.github/workflows/` — CI surface
- `docs/` — extended docs (if present)

## Market — the backend-less catalog

`hanzo/market/*` is the Market catalog the Hanzo / Lux / Zoo desktop apps read.
It is **the read plane, and it is only files**: no API, no database, no service
to be down. Apps fetch CDN-first and fall back to a bundled copy when offline.

- `scripts/market.py` is the **only** writer of catalog files. `gen` builds the
  CDN documents *and* each app's `src/lib/market-catalog.json` bundle from one
  source; `check` is the CI gate. Schema and version digest live in that one
  file, so the CDN, the bundles and CI cannot drift apart.
- `hanzo.yml` + `.github/workflows/cicd.yml` = canonical CI (`hanzoai/ci`). This
  repo has no `images:`/`deploy:` — it is static assets, so `test:` is the gate.
- `deploy.sh` publishes: R2 upload → Cloudflare edge purge for exactly the URLs
  written → verify the live `index.json` version matches the repo. It **fails**
  if the edge disagrees, so a silent no-op deploy is impossible.
- Editorial source is `hanzoai/store`'s `data/{agents,tools}/*.json` (the curated
  PR workflow). A CMS/commerce backend publishes **into** this layout; it is
  never queried at read time. That is what keeps reads backend-less.
- Do NOT hand-edit `hanzo/market/*` — regenerate. `plugins.json` is the one
  pass-through (composio registry) and is preserved across regeneration.
- Upstream icon URLs are expired presigned R2 links carrying an AWS credential +
  signature; `market.py` strips them rather than republish them world-readable.

## Sibling repos

See the org-level `LLM.md` at `/Users/a/work/hanzo/hanzoai/LLM.md` for the full inventory of sibling repos and inter-repo dependencies.

## License

Dual-licensed **MIT OR Apache-2.0** (`LICENSE-MIT`, `LICENSE-APACHE`), replacing the
previous BSD-3-Clause declaration. Original Hanzo work standardises on this pair per
HIP-0137 "One License" (`hanzoai/hips`, `HIPs/hip-0137-one-license.md`); forks keep
their upstream licence unchanged.
