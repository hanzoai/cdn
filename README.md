# Hanzo CDN Assets

Static assets served via Cloudflare Workers + R2 at `cdn.hanzo.ai`.

## Structure

```
hanzo/
├── flag-icons/   271 ISO 3166-1 country flag SVGs
├── img/          Branding, social provider, payment, and app logos
├── buttons/      OAuth provider login button SVGs
└── iam/models/   Face recognition models
```

## Deployment

Upload to R2 via cdn-worker:

```bash
cd ~/work/hanzo/cdn-worker
./upload.sh ~/work/hanzo/cdn/hanzo hanzo
```

## Domains

- `cdn.hanzo.ai` → `pub/hanzo/*`
- `cdn.lux.network` → `pub/lux/*`
- `cdn.zoo.ngo` → `pub/zoo/*`
- `cdn.pars.network` → `pub/pars/*`
