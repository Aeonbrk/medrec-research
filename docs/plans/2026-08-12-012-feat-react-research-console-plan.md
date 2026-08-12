# React Research Console Rebuild

## Outcome

Replace the package-owned zero-build harness page with a Chinese-first research console built from React, Vite, Tailwind CSS v4, and official shadcn/ui. The Python harness serves committed production assets from the installed wheel without Node.js.

## Invariants

- Keep `/api/status`, `/api/action-context`, `/api/harness-state`, `/api/research-loop`, and `/api/action-requests` schemas and behavior unchanged.
- The browser may generate one content-addressed Action Request through the existing gate. It cannot approve, execute, mutate research state, or add a new action.
- Preserve fail-closed `allowed`, `blocked`, `disabled`, `stale`, `malformed`, and transport-failure behavior, including duplicate-activation protection and explicit non-execution copy.
- Render scientific readiness, lineage, HITL status, authorities, and blockers only from existing API responses. A failed or stale research-loop response exposes no invented lane state.
- Keep CSP self-only, add self-hosted font permission, and admit no CDN or remote runtime asset.

## Implementation

1. Create `web/` with Vite, React, TypeScript, Tailwind CSS v4, Radix-based Nova shadcn/ui, Tabler Icons, self-hosted Geist fonts, Vitest, Playwright, and axe.
2. Build a single-entry responsive console with desktop Sidebar and mobile Sheet for 总览, 候选基线, 共享谱系, HITL 循环, and 权威摘要.
3. Persist section, global search, status filter, sort, theme, and density in URL query state. Use progressive disclosure for evidence and compact mobile table alternatives.
4. Build directly into `src/medrec_research/web/`. Extend only the harness package-resource resolver needed for hashed assets and fonts while rejecting traversal and unknown routes.
5. Add focused pure-function tests, production-harness Playwright and axe scenarios, asset drift verification, wheel-content checks, and an installed-wheel no-Node runtime smoke test.

## Verification

- Python: full pytest, Ruff check, Ruff format check.
- Frontend: TypeScript, ESLint, Vitest, production build, committed-asset drift.
- Browser: production Python harness in desktop Chromium and mobile viewport, both themes, current/stale/error states, allowed/blocked/disabled/malformed/transport action behavior, keyboard operation, and axe.
- Packaging: clean rebuild with no Git diff, clean wheel build, expected HTML/JS/CSS/font resources in wheel, and harness startup from the installed wheel without Node.js.
- Quality: WCAG 2.2 AA evidence and production-harness Lighthouse targets, with exact environment evidence if Lighthouse itself is unstable.

## Completion

Commit production assets, capture before/after desktop and mobile screenshots, push `codex/shadcn-ui-rebuild`, and open an independent reviewable PR. Do not merge it.

## Result

- The production console now uses React, Vite, Tailwind CSS v4, Radix Nova shadcn/ui, Tabler Icons, and self-hosted Geist variable font subsets.
- The Python harness admits only `/`, safe one-level hashed `/assets/*` resources, and the unchanged existing API routes. Directory traversal, missing assets, unknown types, and API/static confusion fail closed.
- Production E2E covers desktop and mobile navigation, light and dark themes, URL persistence, keyboard evidence disclosure, current/stale/malformed/transport states, and allowed/blocked/disabled/malformed/transport action outcomes. Axe reports no violations in both themes.
- A clean rebuild matches the five committed production files byte-for-byte. A clean wheel contains HTML, hashed JavaScript and CSS, two WOFF2 resources, and starts the installed Python harness with Node removed from `PATH`.
- Desktop production Lighthouse scores are Performance 99, Accessibility 100, and Best Practices 100. The initial default mobile-throttling run scored 78/100/100 with a 5 ms document response, 10 ms total blocking time, and zero layout shift; the shortfall was slow-network transfer weighting rather than server or main-thread blocking.
