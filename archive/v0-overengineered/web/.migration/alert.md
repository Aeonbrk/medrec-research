# alert

2026-08-13, golden pair via the shadcn CLI, the Base UI target is byte-identical to the current wrapper.

## Changed

- `.migration/alert.md:1` records the official `radix-nova` to `base-nova` comparison and the no-op result.
- `src/components/ui/alert.tsx` required no source change because both official variants are the same pure React composition.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/alert.tsx` is clean.

## Left alone

- Alert consumers were not changed because the public props, slots, roles, and styling are identical in both golden files.
- Other UI wrappers remain under their own component-level migrations.

## Behavior changes

None.

## Verify by hand

- Render default and destructive alerts in light and dark themes.
- Confirm the title and description remain readable and an alert with an action keeps its right-side spacing.
- Use a screen reader inspector to confirm the root retains `role="alert"`.
