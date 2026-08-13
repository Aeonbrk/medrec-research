# button

2026-08-13, golden pair via the shadcn CLI, migrated the pristine wrapper to the official Base UI target.

## Changed

- `src/components/ui/button.tsx:1` now uses `@base-ui/react/button` instead of the Radix `Slot` primitive.
- The wrapper now exposes Base UI's `render` composition API through `ButtonPrimitive.Props`; all local variants and semantic-token classes are unchanged.
- No consumer used Radix's `asChild` prop, so the app-code sweep required no edits.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/button.tsx` is clean.

## Left alone

- Button consumers retain their existing variants, sizes, disabled state, event handlers, and Tabler icons.
- Other UI wrappers remain under their own component-level migrations.

## Behavior changes

- Future element replacement uses Base UI's `render` prop instead of Radix's `asChild`. Current consumers do not replace the native button.

## Verify by hand

- Tab through primary, secondary, outline, ghost, and destructive buttons and confirm a visible focus ring.
- Confirm disabled buttons cannot be activated with pointer or keyboard.
- Activate icon-only and text buttons and verify their accessible names and pressed feedback in both themes.
