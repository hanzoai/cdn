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
├── partners/     Partner/ecosystem logos (AWS, NVIDIA, Techstars, etc.)
├── press/        Press kit assets
└── providers/    AI model provider icons (OpenAI, Anthropic, Mistral, etc.)
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
