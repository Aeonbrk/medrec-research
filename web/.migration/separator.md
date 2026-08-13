# separator

2026-08-13, golden pair via the shadcn `radix-nova` and `base-nova` registries, migrated cleanly to Base UI.

## Changed

- `src/components/ui/separator.tsx:3` now imports `@base-ui/react/separator`, uses the callable Base UI primitive, and adopts its `SeparatorPrimitive.Props` type.
- Removed Radix's `decorative` prop. No consumer supplied it, and Base UI exposes the separator's accessible semantics through its own orientation-aware primitive.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/separator.tsx` is clean.

## Left alone

- Separator consumers were not changed because their existing orientation and class props are compatible with the Base UI wrapper.
- Other UI wrappers remain on their current primitives until their own golden-pair migrations and reports are complete.

## Behavior changes

None for current consumers. Horizontal and vertical layout data attributes remain compatible with the existing Tailwind classes.

## Verify by hand

- Open the production console in both themes and confirm horizontal separators remain one pixel high.
- Collapse and expand the desktop sidebar and confirm its vertical boundary remains continuous.
- Inspect one rendered separator and confirm its orientation semantics match its visual direction.
