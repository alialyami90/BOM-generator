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
   `airflow_m3h` per fan, socket `rating_a`). `door_switch` is optional: leave
   it out when the lamp part includes the switch, so no second row is written.
   `change_over_diodes` names both parts, `negative` (COD-1) and `positive`
   (COD-2), so the engine looks nothing up implicitly.
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
9. **JSON Schemas** for the input files are generated from the models
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

## M1b additions (projects and substations, ADR 0012/0013)

12. **Folders.** `project.yaml` lists `substations/<id>/substation.yaml`; each
    substation lists its panel files. A substation file is loaded through the
    nearest `project.yaml` above it that lists it; without one it is an error.
13. **Library by name and version.** `library: {name, version}` resolves
    through the installed store (ADR 0008). An optional `file` loads that file
    instead (examples, tests).
14. **Document register.** `documents` on the project is a list of
    `{key, substation, doc_no, rev, issue_date}`. Each entry names a listed
    substation. Panels, mirrors, the substation (its workbook) and its
    calculation sheets name a key of their own substation. The calculation
    sheet's scope line moved to `calculations.<sheet>.scope`.
15. **Defaults key by key.** A substation's `constants` and `spares` replace
    only the keys written there; the merged constants are validated again.
    Panel `options` stay as they are; `spares` feed generated panels.
16. **Generated and manual panels.** `panels` lists the files the layout
    writes (or hand-written ones, which is the `--no-layout` path), and
    `manual_panels` lists files the layout never touches. Sheet order is
    `panels`, then `manual_panels`. `generated_panels` gives the identity
    templates of generated panels (`{n}` = panel number) and is needed when
    `equipment` is given. A generated panel file carries `generated: true`;
    a device row's `first_nn` continues a tag range across panels.
17. **Sizing inputs.** `equipment` needs exactly one redundant `l1_switch`
    and one redundant `l2_switch` (both `network_switch` parts); the L1 count
    is computed, so it takes no `qty`. Every equipment part needs `height_u`.
    The panel's usable U is computed (`enclosure_u − rack_u_reserved`), never
    written.
18. **Equipment ids.** Every equipment entry has a unique `id`. Layout
    `overrides` and `removed` name these ids, never tags, so a re-run of the
    layout or a renumbering cannot break them. A unit is picked by a 1-based
    `unit` and, on a redundant entry, a `side` (`a` or `b`); leaving either
    out means every unit or both sides. A single-device move of a redundant
    entry must name its side; a `pair` move takes both sides. A `unit` past the
    entry's `qty` is rejected (not on the computed `l1_switch`). The loader
    checks ids, sides and units, so each problem is located and all are
    reported at once.
19. **L1 switch model.** The `l1_switch` entry may leave `part_id` out; the
    tool then picks the model among library `network_switch` parts at
    `purdue_level: L1` (the UI may ask the engineer to choose). A given
    `part_id` pins the model and must be an L1 `network_switch`. Every other
    role needs `part_id`.

## Consequences

Wattage changes happen in one place. Mirrored panels stay in sync with their
original automatically. Errors point at the exact line, which matters for
engineers editing YAML by hand and for the desktop UI later. The schema files
must be regenerated whenever a model changes (the test enforces it).
