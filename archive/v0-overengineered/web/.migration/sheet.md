# sheet

2026-08-13, golden pair via the shadcn CLI plus a complete consumer sweep, migrated the mobile navigation overlay to Base UI Dialog.

## Changed

- `src/components/ui/sheet.tsx:2` now uses Base UI Dialog Root, Trigger, Close, Portal, Backdrop, Popup, Title, and Description parts.
- Radix open/closed animation hooks are replaced with Base UI starting/ending style hooks; side-specific slide geometry and semantic colors are preserved.
- The close control uses Base UI `render={<Button />}>`, preserving one native button and its accessible name.
- The mobile sidebar already provides a hidden title and description and required no consumer prop changes.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/sheet.tsx` is clean.

## Left alone

- Mobile sidebar open state remains controlled by `SidebarProvider`; the sheet does not own navigation state.
- Sheet width, side, hidden header, and close-button visibility in the sidebar are unchanged.

## Behavior changes

- Base UI uses Backdrop and Popup transition state rather than Radix Overlay and Content open/closed state attributes.

## Verify by hand

- On a mobile viewport, open the sidebar, tab through its controls, and confirm focus cannot escape the sheet.
- Close with Escape, the backdrop, and the close button; each path must return focus to the opener.
- Confirm the hidden title and description appear in the accessibility tree and the left/right sheet animations work in both themes.
