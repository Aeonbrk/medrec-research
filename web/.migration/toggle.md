# toggle

2026-08-13, golden pair via the shadcn CLI, migrated the pristine wrapper to the official Base UI target.

## Changed

- `src/components/ui/toggle.tsx:3` now imports the Base UI toggle primitive and adopts `TogglePrimitive.Props`.
- `src/components/ui/toggle.tsx:7` uses paired `bg-foreground` and `text-background` semantic tokens for pressed state so hover preserves WCAG AA contrast in both themes.
- Existing variants, sizes, and public exports are unchanged.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/toggle.tsx` is clean.

## Left alone

- Toggle consumers required no prop changes because both wrappers expose controlled and uncontrolled pressed state compatibly.
- `toggle-group` has its own migration report and remains outside this wrapper's scope.

## Behavior changes

None for current consumers.

## Verify by hand

- Activate a toggle with Space and Enter and confirm `aria-pressed` changes with the visual state.
- Move focus away and back to confirm the selected state persists.
- Check default and outline variants in light and dark themes, including disabled focus behavior.
