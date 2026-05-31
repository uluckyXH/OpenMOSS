# OpenMOSS on Cloudflare

This directory contains a Cloudflare-native OpenMOSS implementation:

- **Cloudflare Worker**: API runtime and SPA shell
- **Cloudflare D1**: task/agent/review/log persistence
- **Pages-style UI**: static single page served by the Worker

## Deploy

```bash
cd cloudflare
npx wrangler d1 execute openmoss-prod --file schema.sql --remote
npx wrangler deploy
```

Required secrets/vars:

```bash
npx wrangler secret put OPENMOSS_ADMIN_PASSWORD
npx wrangler secret put OPENMOSS_REGISTRATION_TOKEN
```

The deployed API is compatible with the core OpenMOSS endpoints under `/api`.
