# sidebar

2026-08-13, golden pair via the shadcn CLI with dependency-drift review, migrated all Radix Slot composition to Base UI.

## Changed

- `src/components/ui/sidebar.tsx:4` replaces Radix Slot with Base UI `useRender` and `mergeProps`.
- Group labels, group actions, menu buttons, menu actions, and submenu links now expose Base UI `render` composition while retaining their default native tags and all state-driven classes.
- Tooltip composition is integrated through the already migrated Base trigger without an extra DOM wrapper.
- The configured cookie, keyboard shortcut, controlled desktop/mobile state, Base Sheet integration, dimensions, variants, Tabler icon, and public exports are unchanged.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/sidebar.tsx` is clean, and no consumer used the removed `asChild` prop.

## Left alone

- `src/components/app-sidebar.tsx` keeps the product navigation, labels, action handlers, and public-safe authority copy because its existing props remain valid.
- CLI dependency rewrites were reviewed; previously verified Separator, Sheet, and Tooltip behavior was preserved rather than accepting unrelated generator drift.

## Behavior changes

- Future element replacement on five sidebar extension points uses Base UI `render` instead of Radix `asChild`. Current product consumers use default elements.

## Verify by hand

- Toggle the desktop sidebar by button, rail, and Control/Command+B; confirm layout, cookie persistence, active row, and focus remain correct.
- In collapsed mode, navigate all menu buttons by keyboard and confirm labels appear through Base tooltips.
- On mobile, open the Base sheet, choose every navigation item, confirm it closes, and verify focus returns to the opener.
