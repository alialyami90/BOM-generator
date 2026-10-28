# 0022. Free-text loose items

- Status: Proposed
- Date: 2026-10-28
- Spec sections: Inputs the tool needs (3. Project settings, loose material); How each
  panel BOM groups its materials ("Loose material"); Columns of a panel BOM

## Context

Until now every loose-material row named a library part, and the row's description,
make, model and ordering code came from it. A4's Loose material page
(`docs/ui/editing.md`, "Loose material (v0.2)") adds *Add free text…*: a row typed in
by hand for something the library does not hold, such as a site item or one supplied
by others. Its banner tells the person that such a row has no ordering code, make or
model on the sheet. The sheet now stands on its own (ADR 0020).

## Decision

1. **Model.** `loose_material.items[]` takes `part_id` *or* `description`, exactly one
   of them. A blank description counts as none.
   - A library item works as before: `part_id`, `qty`, `tag`, `children`, `fed_from`.
   - A free-text item has `description`, `qty` (a number or `"1 Lot"`) and `tag`.
   - The page's *Designation* is the existing `tag`, the text printed in the Tag column.
     No new key is added.
2. **No library data, so no derived rows.** A free-text item cannot have `children` or
   `fed_from`. The model refuses both with "needs a library part". Kit rows, the feeding
   panel's DC branch, change-over diodes, the annunciator count, power and heat all come
   from library data that a free-text item does not have.
3. **What the sheet prints.** The row is printed in its place in the table:
   - SR.NO and Tag as for any row, with the Tag column holding `tag` or staying empty.
   - DESCRIPTION is `description` exactly as written.
   - QUANTITY is `qty`.
   - MAKE, MODEL and ORDERING CODE are **left empty**. No placeholder such as "TBD" or
     "-" is printed, because the sheet must not suggest an ordering code exists.
   - The hidden HWIO column is 0.
   - Revision comparison matches the row by tag, then description, as for any row
     (ADR 0016).
4. **Writers** (`io/loose_edit.py`, following ADR 0021):
   - `add_loose_item`, with an optional index. The first item starts `loose_material`
     and needs `host_panel`.
   - `set_loose_item`. Replacing an item drops the keys it no longer has, so switching
     between a part and free text leaves no stray keys.
   - `remove_loose_item` and `move_loose_item`. Removing the last item leaves
     `items: []`, so the host panel and title are kept.
   - `set_host_panel`.
   - `validate_loose_item`: a dry run that returns the engine's messages by field
     (`part_id`, `fed_from`, `children[0]`). The key `""` holds a rule over the whole
     item, such as neither a part nor a description.
   - `fed_from` must name a panel in the substation, as the loader already checks. The
     page offers only the generated cabinets.

## Consequences

- Existing substation files load unchanged.
- The engine's loose-item code paths (A9) check `part_id` before looking a part up.
  Each one ignores a free-text item except `kits.py`, which prints it.
- A free-text row adds no load or heat. If an item needs power, it has to be added to
  the library first, which the page's banner says.
- The library's own `loose_items` on a device stay library parts. This decision covers
  only the substation's list.
- With `items: []` the engine still returns a loose table with no lines. The sheet is to
  be written only while there are items (`docs/ui/editing.md`); that is A9's and A10's
  side.
