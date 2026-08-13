# toggle

2026-08-13, golden pair via the shadcn CLI, migrated the pristine wrapper to the official Base UI target.

## Changed

- `src/components/ui/toggle.tsx:3` now imports the Base UI toggle primitive and adopts `TogglePrimitive.Props`.
- Existing variants, sizes, semantic-token classes, `aria-pressed` styling, and public exports are unchanged.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/toggle.tsx` is clean.

## Left alone

- Toggle consumers required no prop changes because both wrappers expose controlled and uncontrolled pressed state compatibly.
- `toggle-group` remains separate until its root and array value semantics are migrated and verified.

## Behavior changes

None for current consumers.

## Verify by hand

- Activate a toggle with Space and Enter and confirm `aria-pressed` changes with the visual state.
- Move focus away and back to confirm the selected state persists.
- Check default and outline variants in light and dark themes, including disabled focus behavior.
