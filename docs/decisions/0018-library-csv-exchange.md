# 0018. Library CSV exchange

- Status: Proposed
- Date: 2026-10-28
- Spec sections: Inputs (1. Device library, commodity catalogues); ADR 0008 (library update
  packages), ADR 0010 (input models), ADR 0017 (alternatives and catalogue brands)

## Context

Ali wants to edit the device library in the app, and to export the whole library as CSV and
import it back, so engineers can work on it in Excel (backlog points 1 and 10, plan M16).
The library is nested: a device has ports, children, terminal rules and loose items, and the
commodity catalogues (MCB, aux contact, terminal blocks, busbars, housekeeping) are separate
tables. Alternatives are linked by A2's `alt_group` key on devices, and catalogue brands by a
brand `id` (ADR 0017, M13).

Excel is the reader and the writer, so the format has to survive Excel: it cannot open a zip,
it shows `TRUE`/`FALSE`, it converts `1E3` and `1-2` into numbers and dates, drops leading
zeros, and in a decimal-comma locale it writes `;` as the delimiter. A `.bomlib` import already
has a dry-run (ADR 0008 amendments); a CSV import must be as safe as that one.

## Decision

**One CSV per table, in a zip (or a folder).** An export writes
`<name>-<version>-csv.zip`; an import reads that zip or a folder holding the same files.
One file per table keeps each sheet's header meaningful and each column typed. One CSV with a
`record_type` column was rejected: it needs the union of about 40 columns, most blank on every
row, and an engineer cannot tell which columns belong to the row in front of them. Cells never
hold JSON.

| File | One row per | Key columns |
|---|---|---|
| `library.csv` | setting (`key,value`) | `csv_format` (1), `library_name`, `based_on_version`, `schema_version`, `enclosure_u` |
| `devices.csv` | device | `part_id`; every scalar field of `DeviceType`, including `alt_group`, `tier`, `inrush_a`, `inrush_ms` |
| `device_ports.csv` | port group | `part_id`, `seq`, then `PortGroup` fields |
| `device_children.csv` | child rule | `part_id`, `seq`, `child_part_id`, `qty` (a number, or `cores`) |
| `device_terminals.csv` | terminal rule | `part_id`, `seq`, then `TerminalRule` fields |
| `device_loose_items.csv` | loose item | `part_id`, `seq`, `item_part_id`, `qty`, `tag` |
| `mcb.csv` | MCB brand | `catalogue_id`, then the MCB fields (`family`, `make`, `poles`, `ratings_a`, `code_pattern`, `trip_curve`, `magnetic_trip_multiple`, `magnetic_trip_multiple_dc`, `dc_rating_v`) |
| `mcb_codes.csv` | rating of a brand that lists `codes` | `catalogue_id`, `rating_a`, `code` |
| `aux_contacts.csv` | aux-contact brand | `catalogue_id`, `make`, `model`, `ordering_code` |
| `terminal_blocks.csv` | block type of a brand | `catalogue_id`, `name`, `type`, `make`, `ordering_code` |
| `busbars.csv` | busbar role of a brand | `catalogue_id`, `name`, `role`, `description`, `tag` |
| `housekeeping.csv` | role of a brand | `catalogue_id`, `name`, `role`, `part_id`, `airflow_m3h` (fan), `rating_a` (socket) |

- **Nested rows** are child tables keyed by the parent's `part_id` plus `seq`, the 1-based
  position in the list, so list order survives a sort in Excel. The child tables name the
  referenced part in their own column (`child_part_id`, `item_part_id`) because `part_id` is
  the parent.
- **Catalogue brands.** `catalogue_id` is `default` for today's single catalogue entry, else
  the brand `id` from ADR 0017. A brand's `name` repeats on each of its rows; the import
  fails if one `catalogue_id` carries two names. Housekeeping `role` is one of `lamp`,
  `door_switch`, `fan`, `vent_filter`, `thermostat`, `ipr_kit`, `socket`,
  `change_over_diode_negative`, `change_over_diode_positive`.
- **Alternatives.** The only link is the `alt_group` column of `devices.csv`. Sort or filter
  on it in Excel to see every alternative of a device together; the app lists the members of
  a group from the same key. The model rules (same category, key pattern) are checked by the
  library validation, not re-implemented in the CSV code. A group with one member is a
  warning.
- **Cells.** Blank means "not given" (`None`); a blank in a required field is a row error.
  Booleans are `true`/`false`, read case-insensitively (Excel shows `TRUE`). Numbers use `.`.
  Enums are their value strings. The one list-valued cell, `ratings_a`, is `6|10|16`.
  Multi-line text follows RFC 4180 quoting. The export uses CRLF line endings.
- **Encoding** is UTF-8 with a BOM, which Excel opens without the import wizard. The import
  reads UTF-8 with or without a BOM. Text that is not valid UTF-8 (Excel's plain "CSV" saves
  in the system code page) is refused with the hint to save as "CSV UTF-8". The delimiter is
  read from the header row: `,` or `;`. With `;` a decimal comma is accepted in numeric
  columns. The export always writes `,` and `.`.
- **Round trip.** For every valid library, `import(export(library)) == library`, including
  list order and device order. Files that are not part of `library.yaml` (for example
  `device-db/`) are not in the CSV; an import carries them over unchanged from the version
  it is based on. YAML comments in `library.yaml` are not kept, because the new version's
  file is written from the model.

**What an import produces.** A new local library version, never an overwrite. The new version
has the same `name` as the version the CSV was exported from, the base version's
`schema_version` and `min_app_version`, a regenerated `library.yaml`, the base version's other
files, `release_notes` starting `Local edit from <base version>:` with the change counts, and
a fresh manifest with checksums. The version is the base version plus a local segment,
`<base>+local.<n>` (1.0.0+local.1, then 1.0.0+local.2), where `n` is one more than the
highest local number installed on that base. These order after their base and before the next
official release (1.0.0 < 1.0.0+local.1 < 1.0.1), unlike semver build metadata, which does
not order. An official package therefore keeps plain semver, a local version is marked
wherever it is shown, and it cannot collide with an official number. It is activated the way
a `.bomlib` import is, and `rollback` goes back to the old version, which stays installed.
The library `Version` type learns to parse and order the suffix in the code PR.

**Dry-run.** `preview_csv_import` returns the same `Check` list as `preview_library_import`
and follows its rules: a failed check skips the rest and leaves `files` empty.

| Check | Fails when |
|---|---|
| `files` | the zip or folder cannot be read, or `devices.csv` or a default catalogue table is missing |
| `encoding` | a file is not UTF-8 |
| `columns` | a required column is missing; unknown columns and missing optional columns only warn and are ignored or defaulted, so a CSV exported by an older app still imports |
| `rows` | a cell cannot be read; each message names the file, the Excel row number, the part and the column, and the first 20 are listed |
| `links` | duplicate `part_id`, a `seq` gap or duplicate, a child table row for a part that does not exist, a catalogue id with two names |
| `cells` | warns when a text cell looks like Excel changed it (`1.5E+03`, `2-Jan`) or starts with `=`, `+` or `@` |
| `library` | the assembled library fails the model and loader checks that a `.bomlib` import runs |
| `base` | warns when `based_on_version` is not the active version, because edits made since will be replaced |
| `changes` | never fails; lists devices and catalogue entries added, changed and removed against the active version, and warns when there are none (no version is created) |
| `version` | the computed local version already exists |

The `changes` check is the main protection against Excel damage that cannot be detected
cell by cell, such as dropped leading zeros: the engineer sees "42 ordering codes changed"
before importing.

**One save path.** The edit service (add, edit or delete a device or catalogue entry, validated
against the model) and the CSV import both end in the same function: write a new local version
from a `Library` and a base version. The `.bomlib` backup of an edited library is the existing
`pack` run over that version.

## Consequences

- Engineers edit in Excel with one sheet per table, and the dry-run tells them what changed
  before anything is installed. The cost is several files instead of one, which the zip hides.
- The CSV columns track the model: a new model field needs a column in the same PR that adds
  the field. A round-trip test that builds a library with every field set catches a missing
  column.
- Local versions carry `+local.<n>`, so the version parser (`versions.py`), the manifest check
  and the `.bomlib` import accept the suffix. When a `.bomlib` import would replace an active
  local version, its dry-run warns: your local edits in 1.0.0+local.2 stay installed but are
  no longer active, and a rollback keeps them in use. A `.bomlib` backup of an edited
  library carries the `+local.<n>` version and imports on another machine like any package.
- The shape of the brand tables follows ADR 0017 as agreed with A2 on 2026-10-28 (including
  `codes` as an alternative to `code_pattern`, which `mcb_codes.csv` covers; `ratings_a` stays
  required and the model rejects `codes` keys that differ from it). If M13 changes a
  field, this ADR is amended in the PR that builds the code.
- The CSV code is not built until M13 is on main.

## Amendment: edit operations (2026-10-28)

The app edits the library through a pending set (`docs/ui/editing.md`, Library editing), so
the engine takes edits, not whole libraries. An edit is plain JSON: `{"op": "set" | "insert" |
"remove", "path": [...], "value": ..., "index": ...}`. A path is a list of segments: a string
is a mapping key or, in a list, the item's `part_id` (devices) or `id` (catalogue brands); an
integer is a position. `["devices", "SW-1", "ports", 0, "count"]` is the count of the first
port group of SW-1. Every model field is therefore editable without one function per field.

- `apply_edits` applies the edits in order to a copy and checks the result with the model and
  the loader's cross-record rules. The answer is the new library or every problem, located as
  `devices[SW-1].voltage_v`. Deleting a part another part uses is a problem.
- `check_field(library, path, value)` is the per-field validation: the message the change
  would cause, or nothing. Problems the library already had are not blamed on the field.
- `save_edits` applies the edits to an installed version and saves the result as the next
  `+local.<n>` version, with the same refusals as a CSV import. `bomgen library export` and
  `LibraryStore.export_package` write any installed version as the `.bomlib` backup.
- A CSV import yields the same kind of change set (rows added, changed and removed, and rows
  with problems), so the app can add the valid rows to its pending set instead of saving at
  once. The all-or-nothing import in this ADR remains the command-line behaviour.

## Amendment: how the import reads the tables (2026-10-28)

Settled while building `preview_csv_import` and `import_csv`; where this differs from the
checks table above, this wins.

- **Partial files.** A table the file lacks is left as the installed version has it, so the
  person can export only devices or only catalogues. A column the file lacks keeps the
  installed values (a warning), so a CSV from an older app never wipes a newer field. A table
  the file has replaces the library's rows of that table: a device with no row is removed,
  and the `changes` check lists it. The device tables need `devices.csv`; `mcb_codes.csv`
  needs `mcb.csv`.
- **Row problems.** Each is `{table, row, column, message, key}` with the row number Excel
  shows. By default any problem fails the `rows` check. With `skip_invalid` the rows are left
  out (an existing device keeps its installed values) and the check is a warning, which is how
  the app adds the valid rows to its pending set.
- **Checks** run in this order: `files`, `encoding`, `columns`, `rows`, `links`, `cells`,
  `library`, `base`, `changes`. There is no separate `version` check; `changes` says which
  version a save would create.
- **Result.** Besides the checks, the preview carries the changes as `LibraryDiff` lists and
  as per-value `{area, key, field, old, new}` entries, the same changes as edit operations
  (see the previous amendment) for the app's pending set, and the library the rows describe.
  `import_csv` saves that library, in the order of the file's rows, so the round trip keeps
  device order.
- **Numbers.** A numeric column accepts `12`, `12.5` and, in a `;` file, `12,5`.
