# tooltip

2026-08-13, golden pair via the shadcn CLI plus a complete consumer prop sweep, migrated provider timing and popup composition to Base UI.

## Changed

- `src/components/ui/tooltip.tsx:1` now uses Base UI Provider, Root, Trigger, Portal, Positioner, Popup, and Arrow parts.
- Popup geometry now uses Base UI's transform-origin and logical-side data attributes while retaining semantic colors and transitions.
- `src/App.tsx:178` maps Radix `delayDuration={180}` to Base UI `delay={180}`.
- `src/components/ui/sidebar.tsx:529` maps trigger `asChild` composition to Base UI `render={button}` without adding a wrapper element.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/tooltip.tsx` is clean; sidebar's remaining Radix imports belong to its pending component migration.

## Left alone

- Sidebar button composition remains in the sidebar wrapper until its own golden-pair migration, while the Tooltip trigger already uses Base UI.
- Tooltip copy, collapsed-only visibility, side, alignment, and 180 ms delay are unchanged.

## Behavior changes

- Base UI has no Radix skip-delay provider concept; this app did not configure one, so current behavior only maps the explicit delay.

## Verify by hand

- Collapse the desktop sidebar, focus and hover each icon, and confirm its tooltip appears after the same delay on the right.
- Move between adjacent icons and verify tooltips close and reopen without trapping focus.
- Confirm no tooltip appears for expanded or mobile navigation, and inspect arrow alignment in both themes.
