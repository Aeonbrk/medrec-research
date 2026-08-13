# badge

2026-08-13, golden pair via the shadcn CLI, migrated the pristine wrapper to the official Base UI target.

## Changed

- `src/components/ui/badge.tsx:1` now composes elements with Base UI `useRender` and `mergeProps` instead of Radix `Slot`.
- The wrapper exposes Base UI's `render` prop while preserving every variant, semantic-token class, slot state, and default `span` tag.
- No consumer used Radix's `asChild` prop, so the app-code sweep required no edits.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/badge.tsx` is clean.

## Left alone

- Badge consumers retain their existing status labels and variants.
- Other UI wrappers remain under their own component-level migrations.

## Behavior changes

- Future element replacement uses Base UI's `render` prop instead of Radix's `asChild`. Current consumers use the default `span`.

## Verify by hand

- Inspect all status variants in light and dark themes and confirm text contrast and shape are unchanged.
- Confirm badges inside dense queue rows do not wrap or alter row height.
- Render a badge as a link with the Base `render` API and verify its focus ring and hover state.
