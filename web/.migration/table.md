# table

2026-08-13, golden pair via the shadcn CLI, the Base UI target is byte-identical to the current wrapper.

## Changed

- `src/components/ui/table.tsx` required no source change because the official variants are identical native table compositions.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/table.tsx` is clean.

## Left alone

- Table consumers remain unchanged; the horizontal overflow container and row/cell semantic slots are preserved.
- Other UI wrappers remain under their own component-level migrations.

## Behavior changes

None.

## Verify by hand

- Open a Decision Packet table with narrow viewport width and confirm horizontal scrolling is available without page overflow.
- Inspect header, body, footer, caption, and selected-row styling in both themes.
- Navigate table controls with keyboard and confirm focus remains visible inside the scroll container.
