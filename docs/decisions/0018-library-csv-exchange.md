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
a fresh manifest with checksums. The version number is the next patch above the highest
installed version of the library (installed 1.0.0 and 1.2.0 give 1.2.1). It is activated the
way a `.bomlib` import is, and `rollback` goes back to the old version, which stays installed.

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
| `version` | the computed version already exists |

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
- Local versions use the patch number, so an official package that reuses a locally used
  number is refused by the existing "already installed" or "older than the active" check. The
  convention to keep this from happening is that official releases bump the minor number.
  Open question for A1: the convention, and whether a local version needs a marker beyond the
  `release_notes` text.
- The shape of the brand tables follows ADR 0017 as agreed with A2 on 2026-10-28 (including
  `codes` as an alternative to `code_pattern`, which `mcb_codes.csv` covers). If M13 changes a
  field, this ADR is amended in the PR that builds the code.
- The CSV code is not built until M13 is on main.
