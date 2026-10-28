# M9 design brief: bomgen desktop app

Status: **approved by Ali, 2026-10-28** (English only). Product truth is in `docs/plan.md` (M8–M11),
ADR 0007 (pywebview app) and ADR 0008 (`.bomlib` packages). Rules stay in the
engine; the UI only shows what the engine returns.

## Job and audience

- **Who:** a small team of substation engineers who prepare SCADA/PSA BOMs, plus
  occasional non-engineers (reviewers, procurement) who open a project to check
  and build it. Mode: **operate** (task tool, not a marketing surface).
- **Context:** Windows 10/11 desktop, offline, usually a laptop; results end up
  as printed A4 sheets.
- **Job:** go from a project to a correct, issued `.xlsx` workbook, trust the
  numbers on the way, and keep every installed copy on the same device library.

## Outcome and proof

- Success: open a project, fix anything the checks flag, preview the cabinet
  BOMs and calculations, and save the workbook without leaving the app.
- Real content to design with: the example project (4 cabinets, 70+ BOM rows per
  cabinet, power 2,177.5 W DC / 1,090.3 W AC, HWIO 17/17/6) and the device
  library with datasheet and alternatives data from the device database work.

## Selected direction

- **Look:** industrial and calm. A deep navy top bar and footer, cobalt for
  actions and links, cool off-white working surface, flat square-cornered
  controls, thin outlined fields, light-weight navy headings, small uppercase labels
  only for table columns and navigation groups. Colours were sampled from the screenshots Ali supplied of SEL's
  site; used as inspiration only, with no SEL logo, name or trademark in the
  app.
- **Theme:** light first, with a full dark theme from the same tokens.
- **Density:** dense data tables inside quiet chrome, with plain-language
  guidance around them for non-engineers.
- **Type:** a free open neo-grotesque bundled with the app, plus a free
  monospace for part numbers and tags. Chosen: Hanken Grotesk and JetBrains Mono (ADR 0011).

## Scope and boundaries

- Fidelity: full clickable HTML/CSS prototype of every screen and its states,
  built on the example project. Design only: no app code, no `src/` changes.
- Screens: project home; project settings; panels list and panel editor (form
  and YAML tab); device library (browse, datasheet, alternatives); library
  import and versions; checks; BOM and calculation preview; build and save.
- Entering data: forms generated from the models' JSON Schema with a label and
  help override file, plus a YAML tab. The YAML tab edits project and panel
  files only. The library is read-only and changes only by importing a
  `.bomlib`. One device picker, fed by the active library version.
- Alternatives: browse only (two brands, low/mid/high each, with the
  `verified` level shown). Swapping a device for an alternative is documented as
  a later extension and needs a schema change, so it is not designed in.
- Library import screen is built around the `import --dry-run` diff: parts
  added, changed and removed, and changed device-db files.
- Not in scope: installer, packaging, anything under `src/`, `examples/` or
  `data/device-db/`.

## States and ranges

First run with no project, empty panel, loading a project, validation errors
and warnings (located by file and field), library out of date versus the
project's recorded version, import refused (downgrade, bad checksum, schema
mismatch), build success and failure, unsaved changes. Ranges: 1–10 panels,
up to roughly 150 BOM rows per panel, library of about 45 to a few hundred parts.

## Interaction and layout

- Shell: navy top bar (project name, library version, theme toggle), left
  navigation in workflow order (Project, Panels, Library, Checks, Preview,
  Build), content area, status footer with unsaved and validation state.
- Validation is always visible as a count; clicking a message jumps to the field
  or the YAML line. Preview and Build work without opening any editor.
- Keyboard-first tables, visible focus, 4.5:1 text contrast, no information by
  colour alone (status also uses icon and text), 125% and 150% Windows scaling,
  minimum window 1280 x 720.

## Open decisions

- Language: English only for the first release (decided by Ali).
- Alternatives and datasheet field names follow the device-database records
  (A3, confirmed by A1). Still to confirm with A3: the meaning of each `verified`
  level and of `same_as`; the Alternatives table shows `verified` as a badge and
  does not use `same_as` until then.
- Swapping a part for an alternative is a later extension. It needs a schema
  change (A2) and data (A3); the design only documents where it would go.
