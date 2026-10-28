# Plan: Substation SCADA BOM generator

Status: **draft for review** (no implementation code until Ali approves).
Spec: [`docs/spec/generator-spec-v2.md`](spec/generator-spec-v2.md). Sections are
cited by name; this plan does not restate them.

## 1. Scope and approach

`bomgen` reads three YAML input sets (device library, panel definitions, project
settings) and writes the single .xlsx workbook the spec describes, plus a check
report. The pipeline follows "Data model and generation order" and is split into
three layers (ADR 0005):

```
YAML ──load/validate──▶ input models ──engine (steps 1–11, 15)──▶ BomLines, PowerLines,
                                                                   HeatLines, HeatChecks
      ──sheets (steps 12–13)──▶ sheet models (cells, formulas, styles, merges, print, header/footer)
      ──writer (step 14)──▶ .xlsx
```

Python computes every value (so rules and golden numbers are tested without
Excel), and the sheet layer emits the same values as live formulas (OUT-5).

The generator is delivered as a CLI first (M1–M7), then as an installable
Windows desktop app with shareable device-library update packages (M8–M11).

Stack: as briefed (ADR 0002), with one agreed deviation: write the file with
**XlsxWriter** because openpyxl cannot put the logo picture in the page header
(ADR 0003). openpyxl stays for reading files back in tests.

## 2. Module breakdown

### 2.1 Package layout

```
src/bomgen/
  models/
    library.py      DeviceType, PortGroup, ChildRule, TerminalRule, LooseItem,
                    commodity catalogues (MCB, aux contact, terminal blocks,
                    busbars, housekeeping kits)
    panel.py        Panel, Enclosure, DeviceInstance, PortPlan, PanelOptions,
                    DocumentInfo, RevisionMarks
    project.py      Project, DesignConstants, OutputSettings, LooseExtra
    bom.py          Group (A–H), BomLine, Qty (int | "1 Lot" | formula), MergeSpan
    calc.py         PowerLine, HeatLine, ForcedVentCheck, NaturalConvCheck
    sheet.py        SheetModel, Cell, StyleToken, PrintSetup, SheetHeaderFooter
  io/
    loader.py       YAML → models; resolves file references and panel mirroring
    errors.py       readable validation errors (file, path, message)
  engine/
    units.py        step 1  expand instances into units (multi-qty, mirroring)
    tags.py         step 1  tag + description building ("Tag naming conventions")
    kits.py         step 2  child kit rows, loose items
    network.py      step 3  SFPs per host switch, FOPP pigtails, cable managers,
                            serial cables
    power.py        step 4a per-device power, current, MCB sizing columns (N–R)
    thermal.py      step 4b forced-vent and natural-convection checks, ventilation choice
    housekeeping.py step 5  group D kit
    ac_dist.py      step 6  group E
    dc_dist.py      step 7  group F (mains from ΣQ, branches, spares, QCOD, aux)
    terminals.py    step 8  group G
    grounding.py    step 9  group H
    hwio.py         step 10 HWIO per row, per panel, DI capacity
    assemble.py     step 11 order A→H, separators, SR.NO, parent/child merges
    pipeline.py     runs steps 1–11 per panel, then 12, 15; returns BuildResult
  sheets/
    styles.py       style tokens from "Formatting" (fonts, fills, borders, sizes)
    bom_sheet.py    step 12 panel BOM sheet (+ loose-material table on the WS sheet)
    power_sheet.py  step 12 Power Consumption
    heat_diss_sheet.py  step 12 Heat Dissipation
    heat_calc_sheet.py  step 12 Heat Calculations
    header_footer.py    step 13 page header / footer per sheet
  writer/
    xlsx.py         step 14 SheetModel → .xlsx (only module importing XlsxWriter)
  checks.py         step 15 check report
  revision.py       OUT-8 revised-cell highlighting
  library_store/    M8  .bomlib pack/import/verify, installed-library store, diff, rollback
  app/              M10 Windows desktop app: pywebview window + Python API for the UI
    __init__.py     import-free (ADR 0009), so launcher.py never pulls in the window
    launcher.py     M11 frozen-app entry points (app_main, cli_main, --self-test);
                    M10 plugs the window in here, M8 the .bomlib import
    ui/             M9 HTML/CSS/JS from the impeccable design
  cli.py            typer app: build, validate, library pack/import/list/rollback
packaging/          M11 PyInstaller spec, Inno Setup script, icons
```

### 2.2 Mapping to "Data model and generation order"

| Spec step | What | Module(s) | Produces |
| --- | --- | --- | --- |
| Entities: Project, DeviceType, Panel, DeviceInstance | input entities | `models/*`, `io/loader.py` | validated models |
| 1 | expand units, build tags | `engine/units.py`, `engine/tags.py` | group A–B `BomLine`s |
| 2 | child kit rows, loose items | `engine/kits.py` | child `BomLine`s (parent link), loose list |
| 3 | network accessories | `engine/network.py` | group C `BomLine`s |
| 4 | device power, heat checks, ventilation | `engine/power.py`, `engine/thermal.py` | `PowerLine`s, `HeatLine`s, checks, ventilation mode |
| 5 | housekeeping kit | `engine/housekeeping.py` | group D |
| 6 | AC distribution | `engine/ac_dist.py` | group E |
| 7 | DC distribution, mains from ΣQ | `engine/dc_dist.py` | group F |
| 8 | terminal strips | `engine/terminals.py` | group G |
| 9 | grounding busbars | `engine/grounding.py` | group H |
| 10 | HWIO sums, DI coverage | `engine/hwio.py` | per-row `hwio`, panel totals |
| 11 | ordering, SR.NO, separators, merges | `engine/assemble.py` | ordered `BomLine`s with `sr_no`, `merge span` |
| 12 | calc sheets, loose-material table | `sheets/*.py` | `SheetModel`s |
| 13 | page header/footer | `sheets/header_footer.py` | `SheetHeaderFooter` per sheet |
| 14 | write .xlsx | `writer/xlsx.py` | the workbook |
| 15 | check report | `checks.py` | report (text/JSON), CLI exit code |
| Entity: BomLine | | `models/bom.py` | |
| Entity: PowerLine / HeatLine | | `models/calc.py` | |
| Entity: SheetHeaderFooter | | `models/sheet.py` | |

Step 4 needs groups D–E (fans and thermostats draw AC power) before it can
decide whether those fans exist. `thermal.py` resolves this explicitly; see open
question Q4.

## 3. Input file schemas

`bomgen build --project examples/project.yaml` loads the project file, which
points at the library and panel files with paths relative to itself. All models
use `extra="forbid"` so typos fail validation. `bomgen validate` runs loading
plus engine checks without writing a workbook. JSON Schemas are exported from
the models (for editor completion and the UI).

### 3.1 `project.yaml` (spec: Inputs → 3. Project settings)

```yaml
project:
  name: "<project name>"               # header centre line 1
  substation: "GIS Substation"         # BOM title line 2
  doc_no: "<project doc no.>"          # OUT-2 default file name
  rev: "0"                             # OUT-2 default file name
  logo: assets/logo.png                # header left (&G)
library: library.yaml
panels:                                # panel order = sheet order (OUT-3)
  - panels/psa1.yaml
  - panels/psa2.yaml
  - panels/psa3.yaml
  - panels/ws.yaml
documents:                             # calc sheets; BOM docs live on each panel
  power_consumption:   { doc_no: "...", rev: "0", issue_date: 2026-10-28, scope: "..." }
  heat_dissipation:    { doc_no: "...", rev: "0", issue_date: 2026-10-28, scope: "..." }
  heat_calculations:   { doc_no: "...", rev: "0", issue_date: 2026-10-28, scope: "..." }
output:
  file_name: "{doc_no}_PSA_BOM_Rev{rev}.xlsx"   # OUT-2
  sheet_names:
    power_consumption: "Power Consumption"
    heat_dissipation: "Heat Dissipation"
    heat_calculations: "Heat Calculations"
constants:                             # defaults = spec values; override per project
  dc_voltage_v: 125
  ac_voltage_v: 230
  power_margin: 0.25
  current_factor: 1.3
  btu_per_w: 3.41
  t_max_c: 35
  t_int_c: 25
  air_constant_m3k_per_wh: 4.1
  steel_coefficient_w_per_m2c: 5.5
  min_main_mcb_a: 6
loose_material:                        # extras not tied to a device
  host_panel: ws                       # table sits under this panel's BOM
  items:
    - { part_id: ANNUNCIATOR-WALL, qty: 1, children: [ANN-MOUNT-KIT], fed_from: psa3 }  # Q13
    - { part_id: HMI-SW, qty: 1 }
    - { part_id: FO-PATCH-CORDS, qty: "1 Lot" }
```

### 3.2 `library.yaml` (spec: Inputs → 1. Device library)

```yaml
devices:
  - part_id: RST2228-L1-24MM
    category: network_switch           # enum; decides group A–H and rules
    make: Ruggedcom
    model: RST-2228
    ordering_code: "6GK6222-6AB00-5CC0-Z A05+B05+C05+D05+E05+F05+G05"
    description_template: "LAN-{lan} Industrial Ethernet switch (Level-1) (24 MM FO Ports)"
    tag_type: ESW
    purdue_level: L1                   # L1 | L2 | EXT | L3 | null
    tag_pattern: null                  # optional, see Q12 (FOPP, gateway)
    supply_type: VDC                   # VDC | VAC | null
    voltage_v: 125
    unit_power_w: 77
    load_type: CONTINUOUS              # CONTINUOUS | INTERMITTENT
    power_supplies: 2                  # 2 dual feed | 1 via change-over diodes | 0 passive
    min_branch_mcb_a: 2
    alarm_on_branch_mcb: false
    hwio_points: 1
    ports:
      - { count: 24, speed: 100M, media: MM, kind: fixed }
      - { count: 4, speed: 1G, kind: sfp_slot }
    cores: null                        # fibre cores, for children with qty "cores"
    children: []                       # [{ part_id, qty: <per parent unit> | "cores" }]
    terminals: []                      # [{ strip: "XDIP{slot}", block: UT-2.5-MT, count: 58,
                                       #    per: unit | serial_port, first_slot: D }]
    loose_items: []                    # [{ part_id, qty }]
    excluded_from_power: false

catalogues:
  mcb:          { family: "Acti9 2P", make: Schneider, ratings_a: [1, 2, 6, 10, 16],
                  code_pattern: "A9F742{rating:02d}" }
  aux_contact:  { make: Schneider, model: A9A26924, ordering_code: A9A26924 }
  terminal_blocks:
    UT-16:      { make: Phoenix Contact, ordering_code: "3044199" }
    UT-2.5-MTD: { make: Phoenix Contact, ordering_code: "3064085" }
    UT-2.5-MT:  { make: Phoenix Contact, ordering_code: "3046362" }
  busbars:
    ac_safety_ground:  { description: "AC SAFETY POWER-GROUND ..." }
    instrument_ground: { description: "INSTRUMENT-GROUND ..." }
  housekeeping:                        # part_ids of device records (ADR 0010)
    lamp:        { part_id: ... }
    door_switch: { part_id: ... }        # optional; omit when the lamp part includes it
    fan:         { part_id: ..., airflow_m3h: 358 }   # per fan (Q8)
    vent_filter: { part_id: ... }
    thermostat:  { part_id: ... }
    ipr_kit:     { part_id: ... }        # its device record lists relay, base, suppression, bracket
    change_over_diodes: { negative: ..., positive: ... }   # COD-1, COD-2
    socket:      { part_id: ..., rating_a: 10 }
```

### 3.3 `panels/<id>.yaml` (spec: Inputs → 2. Panel definition)

```yaml
id: psa1
cabinet_number: 861-GIS01-PSA-0001
cabinet_name: "PSA Cabinet - 001"
tag_prefix: PSA1
lan: A                                 # A | B | null
sheet_name: "1"
kind: network                          # network | control | console (selects terminal defaults)
enclosure:
  make: Rawabi
  model: "..."
  ordering_code: "..."
  h_mm: 2100
  d_mm: 1000
  w_mm: 800
  base_frame: { h_mm: 100, d_mm: 950, w_mm: 750 }   # optional plinth
  cable_entry: top                     # top | side
devices:                               # group B display order
  - { part_id: FOPP-96SM, qty: 1, purpose: "L2-L3 uplink to CCR" }
  - { part_id: RST2228-L2, qty: 1 }
  - { part_id: RST2228-L1-24MM, qty: 6 }
  - { part_id: RST2228-EXT, qty: 1 }
  - { part_id: GW-DHPCC, qty: 1, purpose: "for Dhahran PCC connection" }
  - { part_id: FW-EXT, qty: 1 }
port_plans:                            # per device, by part_id or tag; allocations are lists
  RST2228-L2:
    uplinks_l3: [{ count: 2, speed: 1G, media: SM }]
    downlinks:
      - { count: 6, speed: 1G, media: MM }
      - { count: 1, speed: 100M, media: MM }   # GPS clock
  RST2228-L1-24MM:
    uplinks: [{ count: 24, speed: 1G, media: MM, spare: 3 }]   # → "=24+3"
  # SEL-3555: { serial_ports: 6 }      # RTAC COM ports used (psa3)
options:
  aux_socket_a: null                   # e.g. 10 in psa2
  smoke_detector: true
  change_over_diodes: auto             # auto | true | false
  ventilation: auto                    # auto | forced | natural
  dc_spare_branches_per_feed: 3        # default 1
  ac_spare_branches: 1
  main_mcb_override_a: null
  inter_panel_terminals: 40
  terminal_overrides: {}               # e.g. { X4-DC1: 32 } where the spec gives no rule
  grounding_busbars: [ac_safety_ground, instrument_ground]
document:                              # this panel's BOM header/footer
  doc_no: "..."
  rev: "0"
  issue_date: 2026-10-28
revision:
  highlight: []                        # [{ tag: PSA1-Q1.3, columns: [D] }] → yellow (OUT-8)
```

Mirroring (spec: "What changes by panel type", last paragraph; rules in ADR 0010):

```yaml
id: psa2
mirror_of: psa1                        # copy devices, port plans, options
cabinet_number: 861-GIS01-PSA-0002
cabinet_name: "PSA Cabinet - 002"
tag_prefix: PSA2
lan: B                                 # swaps A→B and 1→2 in tags
sheet_name: "2"
options: { aux_socket_a: 10 }          # merged over the mirrored options
document: { doc_no: "...", rev: "0", issue_date: 2026-10-28 }
```

## 4. Milestones

Each milestone is one PR, starts with failing tests, and ends with lint, mypy and
tests green. Golden values come from the spec and are listed in section 5.

### M0 — Repo, spec, plan, CI (this PR)
Scaffold, spec in `docs/spec/`, ADRs, this plan, CI with docs-only gating.
**Done when:** Ali approves the plan; CI's `ci-status` is green.

### M1 — Input models, loaders, examples, `bomgen validate`
- pydantic models for library, panels, project (section 3); YAML loader with
  relative paths, mirroring, readable errors; JSON Schema export.
- `examples/` reproducing the spec's example project (needs Q1 answered).
- Minimal typer app with `validate`.
- Tests: schema accept/reject cases, mirroring swaps LAN and prefix, every
  example file loads, unknown `part_id` is reported with file and path.

### M2 — BOM groups A–D
- Steps 1, 2, 3, 5: enclosure row, group B units and tags (range tags, LAN/level
  tokens, gateway numbering, FOPP tag), kit children and loose items, SFPs per
  host switch from port plans (`=24+3` formula quantities), cable managers,
  RTAC serial cables, housekeeping kit with ventilation taken from the panel
  option (auto arrives in M4).
- Tests: one per rule in "Tag naming conventions" and "Network accessories
  (group C)"; golden group A–D rows for all four cabinets.

### M3 — BOM groups E–H, HWIO, assembly
- Steps 6–11: AC distribution, DC distribution (branch numbering in group B
  order, spares, QCOD, aux contacts, mains from ΣQ), terminal strips, grounding,
  HWIO per row and per panel, ordering with separators, SR.NO, parent/child merges.
- Tests: one per rule in "Derivation rules" (DC, AC, breaker part numbers,
  terminal block table, HWIO); golden: Q1.1–Q1.13, CINC/Q1/Q2 ratings, every
  terminal quantity in the table, HWIO totals 17/17/6, SR.NO 1…71 on cabinet 001.

### M4 — Power and heat engine
- Step 4 in full: PowerLines (DC/AC/external blocks), sizing columns N–R,
  block totals with margin, HeatLines, forced-vent airflow, natural-convection
  ΔT, combined line-up check, automatic ventilation choice feeding groups D/E/G.
- Tests: formulas from "Power Consumption sheet" and "Heat Dissipation and Heat
  Calculations sheets"; golden 2,177.5 W DC, 1,090.3 W AC, 3,267.8 W total;
  391/391/172 m³/h vs 716; Σ 954.8 vs 2,148 m³/h; WS A = 4.848 m², ΔT = 6.96 °C.

### M5 — Sheet models with live formulas
- Steps 12–13: BOM sheet (incl. loose-material table), Power Consumption,
  Heat Dissipation, Heat Calculations as `SheetModel`s with formulas built from
  resolved addresses; page header/footer per sheet.
- Tests: every OUT-5 formula present at the right cell and pointing at the right
  source row; evaluating the formulas (Q15) gives the M4 numbers; header/footer
  strings per "Output requirements".

### M6 — Excel writer
- Step 14: XlsxWriter translation of sheet models: fonts, fills, borders,
  widths, heights, merges, number formats, hidden column H, print setup
  (A4, orientation, fit/scale, margins, print area, repeat rows 1:2,
  page-break preview), header logo, full recalculation on load.
- Tests reopen the file with openpyxl and assert formulas, styles, merges, print
  settings, header/footer strings; check the zip holds the header image; check
  no `.xlsx` lands in the repo.

### M7 — Check report, revision highlighting, CLI polish, docs
- Step 15 check report (SFPs vs port plans, mains vs ΣQ, airflow vs required,
  DI capacity vs HWIO) as text and JSON; non-zero exit on failures.
- OUT-8 yellow highlighting from panel `revision.highlight` and/or a comparison
  with the previous issue (Q10).
- `bomgen build` final options (`--out`, `--sheet-name`, `--compare`),
  README usage, example walkthrough.

### M8 — Library update packages
Ali wants the device library updated on every installed copy by sharing an
update package (ADR 0008).
- `.bomlib` package format: a zip holding `manifest.json` (library name,
  version, schema version, minimum app version, release notes, SHA-256 of
  each file) plus `library.yaml` and any assets.
- Installed library store per Windows user under
  `%LOCALAPPDATA%\bomgen\libraries\<name>\<version>\`, with an
  `active` pointer and the previous versions kept for rollback.
- CLI: `bomgen library pack`, `bomgen library import <file.bomlib>`,
  `bomgen library list`, `bomgen library rollback`. Import validates the
  manifest, checksums and schema, shows added / changed / removed parts, and
  refuses downgrades unless forced.
- Projects record the library name and version they were built with; the
  check report warns when a project is rebuilt against a different version.
- `pack --add <dir>` carries extra directories such as `data/device-db/`;
  `import --dry-run` shows the diff without installing (the M10 import screen
  previews the same way).
- Tests: pack/import round-trip, corrupted or tampered package rejected,
  schema-version mismatch rejected, diff summary, rollback.
- Delivered in M8: `bomgen.library_store`, registered as `bomgen library ...`.
  `import` (and `import --dry-run`) validate the package's library with
  `bomgen.io.loader.load_library`, so a schema-invalid library is never
  installed. Recording the library name and version in projects needs the
  project model and the check report, so M7 wires `library_mismatch()` into the
  check report. Refusals carry a `RefusalKind` for the M10 import screen.

### M9 — UI design with impeccable
Use the `impeccable` skill to design the screens and elements: open or create a
project, edit panels and project settings, browse the installed device library
and import an update package, validate with readable errors, preview BOM groups
and the check report, build and save the .xlsx. Deliverables in `docs/ui/`:
- design tokens (colour, type, spacing, radius, elevation) in `tokens.json`
  (W3C design-tokens style);
- component specs (states, sizes, behaviour, accessibility notes) and screen
  layouts with the user flows;
- a clickable HTML/CSS prototype. With the desktop stack in ADR 0007 this
  prototype is the starting point of the real UI, not a throwaway.
Finish with an impeccable critique pass and Ali's review.

### M10 — Windows desktop app
Build the approved design as a Windows desktop app (ADR 0007): the M9 HTML/CSS
UI rendered in a native window with `pywebview` (Microsoft Edge WebView2),
calling `bomgen` in-process through a small Python API. No browser, no local
server port, works offline. The business rules stay in the engine. Ends with an
impeccable polish/audit pass against the M9 design.

### M11 — Windows installer and releases
- Freeze the app with PyInstaller (one folder) and wrap it in an Inno Setup
  installer: per-user install (no admin rights), Start-menu shortcut,
  uninstaller, `.bomlib` file association so double-clicking an update
  package imports it, and a bundled default library.
- GitHub Actions job on `windows-latest` builds the installer on version tags
  and attaches `bomgen-setup-<version>.exe` and the default `.bomlib` to a
  GitHub Release, so sharing is one download link.
- Code-sign the installer if a certificate is available (Q19), otherwise
  document the SmartScreen "More info → Run anyway" step.
- Tests: smoke test that the frozen app starts and builds the example
  workbook on the Windows runner.

*Built early (ADR 0009):* the installer pipeline landed before M1, M8 and M10,
with placeholders in `bomgen.app.launcher` for the CLI, library import and the
window. The release workflow already installs, checks and uninstalls the
installer on the runner; the "builds the example workbook" smoke step is added
once `bomgen build` exists (M7), and the bundled default library once M8 writes
`out/default.bomlib`. The app icon comes with the M9 design
(`packaging/icons/bomgen.ico`).

## 5. Testing strategy

- **Unit (TDD):** one test per rule, named after it, in `tests/unit/`.
- **Golden (`tests/golden/`, marker `golden`):** build from `examples/` and assert
  the values the spec states. Initial list:

  | Area | Expected (spec section) |
  | --- | --- |
  | Tags | PSA1-L2-ESW-A01; PSA1-L1-ESW-A11 to A16; PSA1-EXT-ESW-A; PSA1-EXT-FW-A; PSA1-FOPP-CCR-A01; PSA1-DHPCC-GW-1; PSA2-L2-ESW-B01; PSA2-L1-ESW-B11 to B16; PSA2-DHPCC-GW-2 (Tag naming conventions) |
  | DC branches | 13 per feed in 001/002 (10 used + 3 spare), Q1.2–Q1.7 = six L1 switches, firewall on Q1.10/Q2.10; 4 per feed in 003, 2 in WS (Derivation rules → DC) |
  | MCB ratings | branches 2 A; Q1/Q2 16 A in 001/002, 6 A in 003/WS; CINC 6/16/6/6 A; AC branches per the AC rule; codes A9F742xx, aux A9A26924 |
  | Aux contacts | DC 4/4/2/2; AC 3/3/3/1 |
  | Terminal blocks | every cell of the "Terminal block quantities (group G)" table |
  | HWIO | 17, 17, 6 |
  | Power | DC 2,177.5 W, AC 1,090.3 W, total 3,267.8 W |
  | Heat | 391, 391, 172 m³/h vs 716; Σ 954.8 vs 2,148 m³/h; WS A 4.848 m², ΔT 6.96 °C |

- **Writer:** reopen the generated file with openpyxl; assert formulas, styles,
  merges, hidden column H, print settings, header/footer strings.
- **Formula evaluation:** evaluate the written formulas in tests so the live
  workbook gives the same totals as the engine (Q15).

## 6. Open questions

Each has a proposed default that the plan assumes until Ali answers.

**Q1 — Example data is not in the spec (blocks M1 and the golden tests).**
*Resolved 2026-10-28:* Ali uploaded the example workbook; `examples/` is transcribed
from it (ADR 0010). The workbook itself stays out of git.
Still to add: `examples/assets/logo.png` (binary, not yet committed). `logo:` is
commented out in `examples/project.yaml` until it lands; the header writer
milestone needs it.

The spec gives rules and totals but not the per-device data behind them: most
unit wattages, full group B/C/D row lists, ordering codes, descriptions, port
plans, the WS console and loose-material rows, the enclosure codes, document
numbers, and the logo. Without them `examples/` can't reproduce 2,177.5 W /
1,090.3 W except by back-solving.
*Ask:* please upload the example workbook (.xlsx) the spec was written from, or
a device list with wattages. I'll transcribe it into `examples/` and keep the
workbook out of git (or under an explicit, git-allowed `tests/reference/` if you
want a cell-by-cell comparison).

**Q2 — Hidden masters + issued copies, or one sheet per cabinet?**
"Workbook map" lists hidden masters and issued copies; OUT-3/OUT-4 say one BOM
sheet per cabinet with HWIO hidden. *Default:* OUT-4, one sheet per cabinet
(ADR 0004), title row 90 pt, sheets named `1`–`4`.

**Q3 — Main MCB sizing rule doesn't reproduce 16 A.**
"Next standard size above ΣQ, minimum 6 A" with the catalogue sizes 1/2/6/10/16 A
gives 10 A for ΣQ ≈ 7.1 A, but the example uses 16 A. *Default:* implement the
rule with a configurable factor (e.g. size above 2 × ΣQ, or a minimum-16 A rule
for network cabinets) only after you confirm which one; until then the example
uses `main_mcb_override_a: 16` on 001/002 and the check report flags it.

**Q4 — Cabinet 003 ventilation contradicts the rule, and the rule is circular.**
Cabinet 003 needs 172 m³/h ⇒ about 420 W. With the 001 enclosure size
(2100 × 1000 × 800, not stated for 003) natural convection gives
A ≈ 7.92 m², ΔT ≈ 9.6 °C ≤ 10 °C, so the rule picks filters, yet the example
has fans, three thermostats and a 12-way THF strip. Also, the fans and
thermostats are themselves AC loads in the heat total. *Default:* decide
ventilation from the heat of everything except the ventilation parts, apply the
rule, and set `ventilation: forced` on 003 in the example. Alternatively the
rule may need a margin (e.g. ΔT ≤ 0.9 × (TMax − TInt)).

**Q5 — HWIO contributions don't add up to 17.**
*Workbook:* the rows are L2 switch 1, the six-L1-switch row 10, EXT switch 1, AC aux
contacts 3, DC aux contacts 2 (= 17); cabinet 003 is GPS 1 + 3 + 2 (= 6). The example
sets the L1 row's 10 as a per-row override until the rule behind it is known.

The listed contributions (1 per L2/EXT switch, 3 AC aux, 2 DC aux) give 7 for
cabinet 001, while the library example gives an L1 switch `hwio_points: 1`.
*Default:* per-row values come from the library (`hwio_points` per unit) and
from the commodity catalogue for aux contacts; I'll fit them to 17/17/6 once
Q1's data arrives. Note XDIN = 40 = 17 + 17 + 6, so XDIN looks like "total
project HWIO"; confirm, and confirm the WS console contributes 0.

**Q6 — Terminal quantities without a stated rule.**
X4-DC1/DC2 "rounded up to 32 in network cabinets" (from 28; rounding step
unknown), THF 12 vs 5, X-AC and X-DC 6 vs 4, XIP 40/40/12, XDIN 40.
*Default:* implement the rules that are stated; for the rest, take defaults by
panel `kind` (network/control/console) from the example values, overridable by
`terminal_overrides`. Please give the real rules if they exist.

**Q7 — Branch MCB rating.** Column P is ⌈O⌉ but the catalogue only has
1/2/6/10/16 A. *Default:* rating = smallest catalogue size ≥ max(min_branch_mcb_a, ⌈O⌉).

**Q8 — Fan throughput: per fan or per cabinet?** 716 m³/h is compared with each
cabinet's requirement and 3 × 716 is used for the line-up, but each cabinet has
2 fans. *Default:* 716 m³/h is the cabinet's total (the fan pair); the library
`fan.airflow_m3h` is per fan and the check uses the pair's figure. Please confirm.

**Q9 — Fixed print areas.** A1:L97, A1:M66, A1:N70 fit the example only.
*Default:* compute print areas from the last used row and column.

**Q10 — Revision comparison input (OUT-8).** *Default:* both a manual list in
the panel file (`revision.highlight`) and `bomgen build --compare previous.xlsx`
that highlights cells whose value changed.

**Q11 — Calculation sheet header details.** The `<scope>` in "Power Consumption
for <scope>" and the calc-sheet header font size are not defined. *Default:*
scope is a per-document field in `project.yaml` (e.g. "GIS Substation PSA
System"); project name bold at 20 pt on calculation sheets.

**Q12 — Tags that don't fit `<PANEL>-<LEVEL>-<TYPE>-<LAN><NN>`.** FOPP
(`PSA1-FOPP-CCR-A01`) and gateways (`PSA1-DHPCC-GW-1`, numbered by LAN index).
*Default:* optional `tag_pattern` per library device with fields `{prefix}`,
`{level}`, `{type}`, `{lan}`, `{lan_index}`, `{nn}`; panel `tag` override wins.

**Q13 — Single-fed external DC loads.** The annunciator is loose material but its
QCOD-1, X-ANN strip and change-over diodes sit in cabinet 003. *Default:*
`loose_material.items[].fed_from: psa3` decides which panel gets the QCOD
circuit, and the load appears in "Power Consumption for External Equipment" and
"PSA Auxiliary Equipment" (excluded from the fan check).

**Q14 — Merge examples mix sheets.** "Formatting → Merges" lists cell ranges from
different sheets (B4:B7 FOPP on 001, B6:B10 Axion on 003, B49:B50 annunciator on
sheet 4). *Default:* merges are computed from parent/child spans; the listed
ranges become golden assertions per sheet once Q1's data fixes row positions.

**Q15 — How to evaluate formulas in tests.** *Default:* `pycel` (pure Python,
dev dependency) to evaluate the workbook in pytest; optionally a LibreOffice
headless recalc job later to prove "opens without repair" (OUT-1).

**Q16 — UI platform.** *Resolved 2026-10-28:* Ali wants an installable,
shareable Windows app whose UI is designed with the impeccable skill, with
device-library updates shipped as packages (M8–M11). *Proposed stack:* ADR 0007
(pywebview + PyInstaller + Inno Setup) and ADR 0008 (`.bomlib` packages).

**Q17 — Writer library (ADR 0003).** *Resolved 2026-10-28:* Ali chose
XlsxWriter for writing and openpyxl for reading back in tests.

**Q18 — Who publishes library updates, and must they be signed?** *Default:*
you (or a named owner) build `.bomlib` packages with `bomgen library pack`;
packages carry checksums but no signature. If packages will travel by email or
shared drives, I suggest signing them with an Ed25519 key you hold, so the app
rejects tampered or unofficial libraries.

**Q19 — Installer code signing.** Unsigned installers trigger a Windows
SmartScreen warning. *Default:* ship unsigned with instructions; add signing if
you have (or buy) a code-signing certificate or use Azure Trusted Signing.

**Q20 — Install scope and Windows versions.** *Default:* per-user install, no
admin rights, Windows 10 (21H2+) and 11, 64-bit; WebView2 runtime is part of
both and the installer bootstraps it if it's missing.

**Q21 — Should projects travel with the library?** *Default:* a project file
records the library name and version; when sharing a project with someone on
an older library, the app tells them which `.bomlib` to import. Alternatively
a project can be exported as a bundle that includes its library snapshot.


**Q22 — Mistakes in the example workbook.** *Resolved 2026-10-28:* Ali: "fix it". The
generator writes the corrected values and the golden tests expect them: cabinet-1
Power Consumption AC rows reference cabinet 1's own BOM (the workbook points at
`Panel 3`); the External Equipment DC row divides by 125 V (not 230 V); `PSA2-XPS`
uses UT-2.5-MTD code 3064085 (not 3064086); `Panel 3`'s title reads 003; the
XRTAC-C1…C6 strips sit with the other group G strips before grounding; the WS QCOD
branch MCBs are 2 A, A9F74202 (the workbook text says 2A but uses the 1 A code).

**Q23 — Issued sheets differ from their masters.** Issued sheets `1`/`2` list the EXT
switch as a Ruggedcom RST-2228 and the L2 1G/100M MM SFPs as 18/6; the masters list a
SEL-2730M and 15/2. *Default:* the masters, because Power Consumption reads them and
they reproduce the spec's totals. Waiting for Ali.
