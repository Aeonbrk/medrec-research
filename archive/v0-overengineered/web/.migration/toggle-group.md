# toggle-group

2026-08-13, golden pair via the shadcn CLI plus a consumer prop sweep, migrated single-select controls to Base UI array semantics.

## Changed

- `src/components/ui/toggle-group.tsx:3` now uses Base UI ToggleGroup and adopts its Root and Item prop types.
- `src/components/console-toolbar.tsx:123` removes Radix `type="single"`, wraps density and theme values in one-element arrays, and unwraps the first callback value.
- Empty callback arrays are ignored so the current controlled selection and URL query state cannot be accidentally cleared.
- The required leftover scan `grep -n "radix-ui\|@radix-ui"` is clean for the wrapper and consumer.

## Left alone

- Visual variants, spacing, orientation, Tabler theme icons, and accessible labels are unchanged.
- Other UI wrappers remain under their own component-level migrations.

## Behavior changes

- Base UI represents both single and multiple selection with arrays; the toolbar adapts that value at its view-state boundary.

## Verify by hand

- Use arrow keys to move between density options and confirm exactly one stays pressed.
- Switch system, light, and dark themes by keyboard and verify the URL query and document theme update once.
- Reload a URL containing density and theme parameters and confirm both groups restore their selected values.
