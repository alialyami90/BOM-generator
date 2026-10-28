# 0010. Input schema details and validation behaviour

- Status: Proposed
- Date: 2026-10-28
- Spec sections: Inputs the tool needs; How each panel BOM groups its materials
  (mirroring paragraph); Data model and generation order (entities)

## Context

`docs/plan.md` section 3 sketches the three YAML files. Building the M1 models
showed places where the sketch was ambiguous or would duplicate data, and the
loader needs a defined behaviour for mirroring and for reporting mistakes in
hand-written YAML.

## Decision

1. **One source per part.** Housekeeping catalogue entries (lamp, door switch,
   fan, vent filter, thermostat, IPR kit, change-over diodes, socket) refer to
   device records by `part_id`. Make, model, code and wattage live only on the
   device record; the catalogue adds only what is specific to the role (fan
   `airflow_m3h` per fan, socket `rating_a`).
2. **Port allocations are lists.** `uplinks_l3`, `uplinks` and `downlinks` in a
   port plan are always lists of `{count, speed, media, spare}`. RTAC serial
   ports used in a panel are `port_plans.<rtac>.serial_ports`.
3. **Terminal rules** carry their block type (`block`, a key of
   `catalogues.terminal_blocks`), a repeat basis (`per: unit | serial_port`)
   and, for slot-lettered strips such as `XDIP{slot}`, a `first_slot` letter.
4. **Child quantities** are a whole number per parent unit or `cores`
   (the parent's `cores` field). The sketch's `per_unit:N` form is dropped as
   redundant.
5. **Power exclusion default.** `excluded_from_power` defaults to true for a
   part with no `supply_type` and false otherwise, so passive parts need no
   power fields.
6. **Mirroring** (`mirror_of`) copies kind, enclosure, devices and port plans
   from the original panel, takes identity, document and revision from the
   mirror file, and merges `options` key by key over the original's. Tag
   overrides and port-plan keys that start with the original's prefix are
   rewritten: prefix swapped, LAN letter swapped in the last tag segment, and a
   LAN-index suffix (`-1`) swapped (`-2`). Only originals can be mirrored.
7. **Errors.** Every problem becomes `file:line: path: message` (path in
   `devices[2].part_id` form). The loader collects problems from all files
   before stopping. Duplicate YAML keys, a UTF-8 byte-order mark and unquoted
   `rev: 0` / `sheet_name: 1` are handled deliberately (error, accepted,
   accepted).
8. **Project revision.** `project.rev` feeds the default file name
   `{doc_no}_PSA_BOM_Rev{rev}.xlsx` (OUT-2), which names a project-level rev the
   sketch did not have.
9. **JSON Schemas** for the three files are generated from the models
   (`bomgen schema`) and committed under `schemas/`; a test fails when they
   are stale. Example files point editors at them.
10. **Example provenance.** `examples/` is transcribed from the example
    workbook (plan Q1). Values the workbook does not give carry a trailing
    `# ASSUMED` comment.
11. **Fields the workbook needs.** `make` and `model` are optional on a device
    record (kit children and cables without them exist). The enclosure base
    frame has its own H × D × W. A panel device can override its row's HWIO
    total (`hwio_points`; the six L1 switches carry 10). Loose items and loose
    extras can carry their column-B designation (`tag`).

## Consequences

Wattage changes happen in one place. Mirrored panels stay in sync with their
original automatically. Errors point at the exact line, which matters for
engineers editing YAML by hand and for the desktop UI later. The schema files
must be regenerated whenever a model changes (the test enforces it).
