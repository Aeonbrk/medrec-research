# select

2026-08-13, golden pair via the shadcn CLI plus a complete consumer sweep, migrated registered option data and popup positioning to Base UI.

## Changed

- `src/components/ui/select.tsx:2` now uses Base UI Root, Group, Value, Trigger, Positioner, Popup, List, Item, indicator, and scroll-arrow parts.
- Radix positioning variables and `position` mode are replaced by Base UI anchor dimensions, available height, transform origin, and `alignItemWithTrigger`.
- `src/components/console-toolbar.tsx:30` defines stable label/value arrays for sorting and status, supplies each through the required root `items` prop, and renders items inside `SelectGroup`.
- Toolbar popups map Radix `position="popper"` to `alignItemWithTrigger={false}`; nullable changes are ignored so query state remains valid.
- The required leftover scan `grep -n "radix-ui\|@radix-ui"` is clean for the wrapper and both consumers.

## Left alone

- H1 and H2 native form controls are not consumers of this wrapper and were intentionally left for the structured-contract workflow work.
- Sort and status URL values, labels, Tabler icons, and semantic-token classes are unchanged.

## Behavior changes

- Base UI requires registered item data on the root and uses its Positioner rather than Radix's content positioning mode.

## Verify by hand

- Open each toolbar select with Enter, move with arrow keys, use typeahead, select with Enter, and confirm focus returns to the trigger.
- Confirm sorting and status query parameters update once and survive reload.
- Test each popup near viewport edges in desktop and mobile layouts and verify selected-item checks and scroll arrows in both themes.
