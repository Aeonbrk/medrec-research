# skeleton

2026-08-13, golden pair via the shadcn CLI, the Base UI target is byte-identical to the current wrapper.

## Changed

- `src/components/ui/skeleton.tsx` required no source change because the official variants are identical pure CSS placeholder compositions.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/skeleton.tsx` is clean.

## Left alone

- Loading consumers remain unchanged; they use the shared semantic muted token and pulse animation.
- Other UI wrappers remain under their own component-level migrations.

## Behavior changes

None.

## Verify by hand

- Load the pending queue with a throttled network and confirm skeleton geometry does not shift surrounding content.
- Check loading placeholders in both themes for sufficient contrast and no flashing layout.
- Confirm skeletons are removed when content becomes available.
