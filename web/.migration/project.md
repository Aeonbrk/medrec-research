# project

2026-08-13, whole-project `radix-nova` to `base-nova` golden-pair migration, all 17 registered wrappers are complete with no Radix runtime mixing.

## Changed

- `components.json` now selects `base-nova`; `package.json` and `package-lock.json` add `@base-ui/react@1.7.0` and remove the `radix-ui` package plus 69 no-longer-needed transitive packages.
- All 17 registered wrappers have component reports: alert, badge, button, collapsible, empty, input-group, input, select, separator, sheet, sidebar, skeleton, table, textarea, toggle-group, toggle, and tooltip.
- App-code sweeps migrated Collapsible, ToggleGroup, Select, Tooltip, Sheet, and Sidebar consumer props and verified that no remaining consumer uses `asChild`.
- `grep -n 'from "radix-ui"\|@radix-ui\|--radix-\|\basChild\b\|IconPlaceholder'` is clean across production source, tests, scripts, and package manifests.
- The canonical production assets were rebuilt after dependency removal and now match a clean rebuild exactly.

## Left alone

- Native H1/H2 form controls are not Radix wrappers; their structured questionnaire redesign belongs to the pending decision-workbench implementation.
- No non-Radix component libraries, scientific APIs, Action Gate semantics, or research protocol behavior were changed by this migration.
- The first sidebar registry request ended with a remote connection close; a single retry succeeded and all associated dependency rewrites were reviewed before acceptance.

## Behavior changes

- Element composition uses Base UI `render` instead of Radix `asChild`.
- Base Select registers root item data and uses Positioner geometry; Base ToggleGroup uses array values; Base Dialog, Tooltip, and Collapsible use their own transition and part models.
- Existing product state boundaries adapt these differences without changing URL query values, accessible labels, or controlled navigation state.

## Verify by hand

- Exercise sidebar collapse, mobile Sheet focus trapping, tooltip delay, Select keyboard/typeahead, ToggleGroup arrow navigation, and evidence disclosure focus in production.
- Test every migrated control in light and dark themes at desktop and mobile widths, including visible focus, disabled and invalid states, and WCAG 2.2 AA contrast.
- Run the production Playwright and axe suite against the Python harness and confirm the canonical asset drift check remains clean.

## Automated verification

- `npm run typecheck`, `npm run lint`, and `npm run format:check` pass.
- Vitest passes 15 tests, including Base Collapsible disclosure behavior and the public-evidence URL boundary.
- `npm run build` and `npm run build:check` pass; six production asset files match a clean rebuild.
- `npm ls radix-ui @base-ui/react --depth=0` reports only `@base-ui/react@1.7.0`, and `npm audit` reports zero vulnerabilities.
