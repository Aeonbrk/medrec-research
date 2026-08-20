# input-group

2026-08-13, golden pair via the shadcn CLI, retargeted the pristine composition to Base Button and Input.

## Changed

- `src/components/ui/input-group.tsx:87` narrows the composed Button `type` prop to the native `button`, `submit`, or `reset` union required by Base UI.
- The wrapper now composes the already migrated Base Button and Input wrappers without changing layout, focus delegation, or semantic-token classes.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/input-group.tsx` is clean.

## Left alone

- Input-group consumers required no changes because their native input, textarea, and button props remain supported.
- The click-to-focus behavior on non-button addons is unchanged.

## Behavior changes

None for current consumers. TypeScript now rejects arbitrary string values for the nested button's native `type`.

## Verify by hand

- Click inline-start and inline-end addons and confirm the input receives focus unless the click targets a nested button.
- Tab through embedded buttons and inputs and verify focus order and rings.
- Check horizontal and block-aligned groups with disabled and invalid controls in both themes.
