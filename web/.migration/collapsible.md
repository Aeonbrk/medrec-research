# collapsible

2026-08-13, golden pair via the shadcn CLI plus a consumer prop sweep, migrated disclosure behavior to Base UI.

## Changed

- `src/components/ui/collapsible.tsx:3` now uses Base UI Root, Trigger, and Panel parts; the public `CollapsibleContent` export maps to `Panel`.
- `src/components/evidence-disclosure.tsx:84` replaces Radix `asChild` composition with Base UI `render={<Button />}>`, preserving one native button and its accessible name.
- `src/components/evidence-disclosure.test.ts:28` verifies the collapsed content is absent, activation reveals it, and `aria-expanded` plus the trigger label update.
- The required leftover scan `grep -n "radix-ui\|@radix-ui"` is clean for the wrapper and consumer.

## Left alone

- Evidence URL allowlisting and credential rejection remain unchanged.
- Other UI wrappers remain under their own component-level migrations.

## Behavior changes

- Base UI renders the disclosure content through `Collapsible.Panel`; current consumers observe the same mounted-when-open behavior.

## Verify by hand

- Focus the evidence count and press Space and Enter; confirm the list opens once and focus remains on the trigger.
- Confirm `aria-expanded` and the Chinese expand/collapse accessible label change with visual state.
- Open and close public evidence in both themes and verify the chevron rotation and external links.
