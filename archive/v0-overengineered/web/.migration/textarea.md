# textarea

2026-08-13, golden pair via the shadcn CLI, the Base UI target is byte-identical to the current wrapper.

## Changed

- `src/components/ui/textarea.tsx` required no source change because the official `radix-nova` and `base-nova` files are identical native textarea compositions.
- The required leftover scan `grep -n "radix-ui\|@radix-ui" src/components/ui/textarea.tsx` is clean.

## Left alone

- Textarea consumers and the input-group composition remain unchanged because the public native props and styles are identical.
- Other UI wrappers remain under their own component-level migrations.

## Behavior changes

None.

## Verify by hand

- Resize and focus a contract or evidence text area and confirm the focus ring and minimum height.
- Enter multiline text and verify line breaks and form submission are preserved.
- Confirm invalid and disabled states in both themes.
