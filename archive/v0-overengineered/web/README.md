# MedRec Research Console

React, Vite, Tailwind CSS v4, and shadcn/ui source for the production research console.

The production build is committed under `src/medrec_research/web/` and served by the Python harness. Node.js is a development and build dependency only.

## Verification

```bash
npm ci
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e
npm run build:check
npm run lighthouse
```

`npm run test:e2e` launches the Python production harness. It never treats the Vite development server as delivery evidence.
