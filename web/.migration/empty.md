# empty

2026-08-13, golden pair via the shadcn CLI, the Base UI target is byte-identical to the current wrapper.

## Changed

- `src/components/ui/empty.tsx` required no source change because the official variants are identical pure React compositions.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/empty.tsx` is clean.

## Left alone

- Empty-state consumers remain unchanged and continue to use the required `EmptyHeader`, `EmptyTitle`, `EmptyDescription`, and `EmptyContent` composition.
- Other UI wrappers remain under their own component-level migrations.

## Behavior changes

None.

## Verify by hand

- Render the pending queue empty state and confirm it stays centered without changing surrounding column geometry.
- Check icon, title, description, and action content in light and dark themes.
- Tab to the empty-state action and confirm its focus ring is visible.
