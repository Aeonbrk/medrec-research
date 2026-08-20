# input

2026-08-13, golden pair via the shadcn CLI, migrated the pristine wrapper to the official Base UI target.

## Changed

- `src/components/ui/input.tsx:1` now renders `@base-ui/react/input` instead of a native input directly.
- The existing native input props, file-input styling, semantic tokens, focus ring, invalid state, and disabled state are preserved.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/input.tsx` is clean.

## Left alone

- Input consumers required no edits because the Base primitive preserves native input event and attribute semantics.
- `input-group` is tracked separately because it composes this wrapper with Base Button.

## Behavior changes

None for current consumers.

## Verify by hand

- Focus text and search inputs with pointer and keyboard and confirm the visible focus ring.
- Confirm disabled and invalid states remain visually distinct in both themes.
- Enter, select, and clear text and verify native form events still fire once.
