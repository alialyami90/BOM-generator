# 0017. Alternatives as library parts; catalogue brand sets

- Status: Accepted (Ali, 2026-10-28)
- Date: 2026-10-28
- Spec sections: Inputs the tool needs (1. Device library; commodity catalogues),
  Electrical rules (branch MCBs)

## Context

Backlog points 1–3 (`docs/backlog.md`). The alternatives in `data/device-db/` are
reference notes, so a panel cannot use them. The commodity catalogues (`catalogues.mcb`,
`aux_contact`, `terminal_blocks`, `busbars`, `housekeeping`) each name one brand, so a
project cannot pick another. M15 (ADR 0019) sizes branch MCBs from device data, so it
needs inrush current on devices and the trip curve on the MCB catalogue. Ali's sizing rule
is Q35. ADR 0018 carries the same fields in the library CSV.

## Decision

1. **Alternatives are devices.** Any device may name `alt_group`, a stable key
   (`^[A-Z0-9][A-Z0-9-]*$`, e.g. `L1-SWITCH-24P`). Every device with the same key is an
   interchangeable full library part, today's part included. All members of a group
   share one category. `tier: low | mid | high` is optional. `Library.alt_group(key)`
   and `Library.alternatives(part_id)` list the members in file order. Catalogue entries
   carry no `alt_group`, because their alternatives are brand sets (point 2).
2. **Brand sets.** `catalogues` stays as it is and is the brand `default`. A new optional
   `catalogue_brands` holds a list per catalogue. Each entry has an `id`
   (`^[a-z0-9][a-z0-9-]*$`, unique per catalogue, never `default`) and an optional `name`:
   - `mcb` and `aux_contact` entries have their catalogue's fields.
   - `terminal_blocks` has `types` and `busbars` has `entries`. Both are keyed like the
     default and must cover every key the default has.
   - `housekeeping` has the same roles as today. Each part must be a library device.
3. **Choice.** `catalogue_choice: {mcb: abb-s200m, ...}` goes on the project `defaults`
   and on a substation. It merges key by key, and the substation wins. An unset key means
   `default`. The loader reports an unknown id at its line, with the ids the library has.
   It then gives each `LoadedSubstation` a library whose `catalogues` hold the chosen sets
   as plain catalogue models, so the engine is unchanged. With no choice, the substation
   gets the very same library object, and the example builds as before.
4. **MCB sizing fields.**
   - **Devices:** optional `inrush_a` (peak) and `inrush_ms` (duration).
   - **MCB catalogue and brands:**
     - `trip_curve: B | C | D | K | Z` and `magnetic_trip_multiple`, the AC value. When both
       are given, the multiple must lie in the curve's band: B 3–5, C 5–10 and D 10–20
       (IEC 60898-1), K 8–14 and Z 2–3 (IEC 60947-2).
     - `magnetic_trip_multiple_dc`. The DC threshold is higher, so this value is not
       band-checked, but it must not be below the AC value.
     - `dc_rating_v`, the whole MCB with its poles in series.
     - `codes: {rating: code}` as an alternative to `code_pattern`. Exactly one of the
       two is given, and `codes` lists exactly `ratings_a`.
   - **`McbCatalogue.magnetic_multiple`** gives the written AC multiple, otherwise the
     curve's lower bound.
   - **Design constants:** `min_branch_mcb_a = 2` and `inrush_min_ms = 10`.
   - `DeviceType.min_branch_mcb_a` still parses. The rule that uses these fields is
     ADR 0019's.

## Consequences

- Old libraries and projects load unchanged.
- A brand set is a whole catalogue. Mixing brands inside one catalogue (e.g. one
  terminal type from another maker) needs a new set.
- `LoadedSubstation.library` may differ from `LoadedProject.library`. Code that looks up
  catalogues must use the substation's.
- The library CSV (ADR 0018), the Library screen and the M14 data follow these names.
