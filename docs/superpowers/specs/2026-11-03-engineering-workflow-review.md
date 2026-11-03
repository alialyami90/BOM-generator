# Engineering workflow review: the SCADA engineer's BOM

2026-11-03 · Ali. Source: [Claude Doc](https://claude.ai/artifact/MU3mY4cebv4Y59Ugx4BURT).

Reviewed against v0.3.4 (`main` at the release), spec v2.1, `docs/ui/screens.md`, `docs/ui/editing.md` and the app source. The companion document, *Implementation plan for AI agents*, turns this review into milestones.

## Verdict

The app is a strong BOM generator and a weak BOM workflow. It reproduces the example workbook exactly, sizes switches, breakers, terminals and cooling from rules, and lets the engineer pick parts, drag devices into panels and change brands. But a SCADA engineer completing a real BOM starts from a design basis, an IED schedule and a client's vendor list, and hands over a procurement summary, a spare parts list and a cable schedule with a revision history. None of those exist. In between, 18 derived quantities can't be seen or changed on screen (the earlier review lists them, SFP counts first).

The fix is not more settings. It is a workflow with a front door (a design basis that drives every default), a visible rule behind every automatic number, and the outputs an engineer is asked for after the panel BOMs. Three changes carry most of the value:

1. **A design basis per substation** (voltages, redundancy, standards, vendor list, spares policy) entered once, which every later screen reads as its default.
2. **The override contract on every derived value**: shown, explained ("27 = 24 links + 3 spare"), overridable in place, resettable. Today it exists on constants and panel options only.
3. **Issue outputs**: a consolidated summary BOM, a spare parts list, a cable and patch cord schedule, and a revision history sheet, all built from the data the engine already has.

The library needs an owner's tools more than new fields: a data-quality gate before a part can be picked, a per-client approved vendor list, obsolescence and a source for every number.

## What a SCADA engineer needs to complete a BOM

A substation SCADA BOM is the last document of a design chain. The engineer brings inputs from the client and the system design, makes a fixed set of decisions, and hands over more than the panel BOMs. The table lists each, and whether the app has a home for it today.

| Phase | What the engineer brings or decides | In the app today |
| --- | --- | --- |
| Design basis | Client, project and substation names; station DC voltage (110, 125, 220 V) and AC voltage; redundancy scheme (duplicated LAN-A/B, PRP, HSR); Purdue levels in scope; time sync (GPS, PTP); approved vendor list; spares policy; standards and tagging convention; language and units | Names, logo, voltages as constants. No redundancy choice, vendor list, spares policy or tagging convention |
| IED schedule | Bays and the IEDs in each, with ports per IED (count, speed, media, single or dual attached), protocol, location | One number, `ied_count` |
| External connections | Links to the control centre, PCC, DMS, third parties: count, media, speed, which switch they land on, firewall or not | `l2_ports` per equipment row; the ext\_switch and firewall roles |
| Hardwired I/O | Alarm and status points to the station RTU or I/O chassis: count, type, source | `hwio_points` per device, summed; `di_inputs` on the I/O module |
| Equipment selection | One part per role, alternatives, the part number to print, quantities, what is redundant | Parts page, well covered |
| Panel design | How many panels, what goes where, enclosure per panel, cable entry, housekeeping, power distribution, terminals, grounding, nameplates, labels | Layout and drag; one enclosure for all; housekeeping and terminals fixed |
| Power and cooling | Branch and main breakers per feed, change-over for single-fed loads, fans or filters | Computed; shown in Preview; limited overrides |
| Loose material | Antenna kit, software, cables, patch cords, consumables | A list typed by hand |
| Spares | Commissioning spares and operation spares per the client's policy (often 10% or minimum 1 per type) | None |
| Cable schedule | Fibre and copper patch cords by length and type, from the links | None |
| Document control | Document numbers, revisions, issue dates, prepared/checked/approved, revision history, what changed | Register, revision, compare with previous file. No history sheet or names |
| Handover | Panel BOMs, a consolidated summary by part number for procurement, calculation sheets, a spare parts list, a cable list | Panel BOMs and calculations only |

The gap is at both ends: no structured front door for the design basis and the IED schedule, and no procurement-side outputs at the back. The middle (selection, layout, sizing) is where the app is strong.

## The target workflow

*(The Claude Doc version shows this as a diagram: 12 steps, 3 new, 4 extended. The table below is the same content.)*

The engineer enters the design basis and the IED schedule once, the engine sizes and lays out from them, and the engineer reviews and overrides at each later step. Checks loops back to any step until the substation is clean. Issue builds the workbook and the new outputs; Handover exports, compares and records the revision.

| Step | Screen | What the engineer does | What the engine does |
| --- | --- | --- | --- |
| 1 Design basis | Substation › Design basis (new tab, first on a new substation) | States voltages, redundancy scheme, Purdue scope, vendor list, spares policy, tagging convention | Seeds constants, brands, spares, the tag rules and the housekeeping defaults from it |
| 2 IED schedule | Parts › IED schedule (new section, replaces the single count) | Lists bays and IED types with ports per IED, or types one count as today | Sums ports per speed and media per side; the schedule is the source of `ied_count` |
| 3 Network sizing | Parts › Network | Reviews topology, uplinks, rings; sets external links | Picks L1 and L2 counts and port plans; now shows the port budget per switch |
| 4 Parts | Parts › Devices | Picks a part per role, part number, overrides, SFP part and quantity, BOM text per row | Derived parts, SFP counts with their rule, cable managers |
| 5 Layout preview | Device preview, Panels | Drags, pins, removes; sets panel count limits | Panel fill, waist anchor, blank plates, MCB per unit |
| 6 Panel detailing | Panel editor (per panel) | Enclosure and kind per panel, housekeeping, power distribution, terminals, grounding, nameplates, labels | Groups D to H with the rule behind each quantity |
| 7 Loose and cables | Loose material | Kits and free text as today; accepts or edits the suggested patch cords | Suggests cables from the port plans and lengths |
| 8 Spares list | Spares (new page) | Sets the policy (percent, minimum, which categories), edits the list | Builds the list from every panel BOM and loose item |
| 9 Checks | Checks | Fixes problems from the list | File checks and engine checks, including new ones for the design basis |
| 10 Preview | Preview | Reads every sheet, marks rows as revised | All sheets, the new ones included |
| 11 Issue | Build | Builds, chooses which outputs to include | Workbook with summary BOM, spares, cable schedule and revision history sheets |
| 12 Handover | Build, Project › Backup and share | Compares with the previous issue, records the revision, exports | Revision compare, the history entry, the `.bomproj` |

## Step-by-step review

Each step: what is automatic, what the engineer controls today, and what is missing. Code references are to `src/bomgen/`.

### 1. Design basis (new)

**Today.** A new substation is seeded silently (`io/lifecycle.py` `_blank`): document numbers "TBD", the example's Rawabi enclosure, cabinet number pattern `<ID>-PSA-{n:04d}`, XIP 40, all marked ASSUMED in YAML only. Voltages live under Design constants (125 V DC, 230 V AC). There is no place to state the redundancy scheme, the client's vendor list, the spares policy or the tagging convention, so every later screen defaults to the example project.

**Missing.** A Design basis tab, shown first on a new substation and editable later: station DC voltage (110, 125, 220 V, or other), AC voltage, redundancy (duplicated LAN-A/B as today; PRP and HSR flagged as future), Purdue levels in scope (L1 only, L1+L2, with EXT), time sync (GPS clock, PTP from the clock, none), client approved vendor list (which brand sets and which library parts are allowed), spares policy (percent and minimum per category), tagging convention (prefix pattern, level letters, side letters, first numbers), enclosure family and cable entry for generated panels, and document numbering pattern. Each value feeds a default the engineer sees later with "From the design basis" as its source.

### 2. IED schedule (new)

**Today.** `network.ied_count` is one integer, and every IED is assumed dual-attached with one 100 Mb MM port per side (`engine/sizing.py`). The L1 switch is sized from it; copper IEDs, 1G IEDs, single-attached IEDs and bay grouping don't exist.

**Missing.** An IED schedule on Parts: rows of bay, IED type, count, ports per IED (speed, media), attachment (dual A/B or single), and whether it needs an L1 port or lands on L2. The engine sums ports per speed and media per side from it, which also fixes the SFP mix on the L1 switches. A "Quick count" mode keeps today's one number for early estimates. The schedule prints as a reference sheet (optional) so the BOM's switch count can be audited.

### 3. Network sizing

**Today.** Good: topology, ring size, uplinks per L1, A–B interlink, L3 uplinks per L2, spare port fraction, the L2 link per equipment row (`l2_ports`, speed, media). The result card shows switch counts and ports used.

**Missing.** A port budget per switch (used, reserved, spare, free) the engineer can read; external links as first-class rows (count, media, speed, lands on EXT switch or L2, through the firewall or not) instead of a port count on a device row; a switch count override ("use 8 L1 per side even if 6 fit"); a PRP RedBox or media converter role.

### 4. Parts

**Today.** The strongest screen: part per role, part number, overrides of height, power, supply, voltage, supplies, inrush and load, SFP part per speed and media, cable manager, L2 link, brands, move up and down.

**Missing.** SFP quantities (used, spare, extra per speed and media, with the rule shown; the model refuses a hand-written port plan on L1 and L2 today); BOM text per row (purpose, tag override, type code, first number, HWIO points, alarm on branch trip) which exist in the model but not on screen; rack priority per row; a part filter by the vendor list; a "why this quantity" hover on sized rows.

### 5. Layout preview

**Today.** Drag, pin, remove, waist anchor, blank plates, MCB per unit, U meter; `top_u` and `position` through drag.

**Missing.** A maximum panel count or a fixed panel count ("this station has 3 PSA panels, make it fit or tell me"); common devices steered to a chosen panel without pinning each unit; a per-panel note that prints on the BOM title or header.

### 6. Panel detailing (extended)

**Today.** Enclosure shared by all generated panels; options per panel (spares, ventilation, diodes, main MCB override, socket, inter-panel terminals, smoke detector); port plans of non-switch devices; document. Housekeeping counts, AC branch ratings, terminal quantities and grounding busbars are fixed in the engine or YAML-only (`engine/housekeeping.py`, `engine/ac_dist.py`, `engine/terminals.py`, `engine/grounding.py`).

**Missing.** Enclosure and kind per panel, bottom cable entry, IP rating and colour on the PANEL row; a Housekeeping section (each item's quantity and breaker, heater and hygrostat roles, smoke detector supplied or by others, socket pick list); a Terminals tab (each strip with its rule, override, spare percent, fused or test terminals as block types); grounding busbars as checkboxes; spare breaker ratings; DC aux contact alarm per device; nameplate and label text rules; a per-panel free-text row ("miscellaneous: cable ties, labels, 1 lot").

### 7. Loose material and cables (extended)

**Today.** Library parts with kits and free text, fed-from panel, host document. Patch cords are typed as "1 Lot".

**Missing.** Suggested cables from the port plans (one row per speed, media and connector pair, quantity from links, length from a per-substation default), editable afterwards; a cable schedule sheet (from, to, type, length) when the engineer wants it; per-item notes.

### 8. Spares list (new)

**Today.** Nothing. Client specifications almost always ask for commissioning spares and two-year operation spares.

**Missing.** A Spares page: policy from the design basis (percent per category, minimum per part, categories included), the computed list (part, installed quantity, spare quantity, rule), edits with the override marker, and a Spare Parts sheet in the workbook.

### 9. Checks

**Today.** File problems with "Go to field", engine checks (SFP vs port plan, main MCB vs feed current, airflow, DI capacity, branch MCB lines, float voltage, duplicate tags, untagged devices, library version).

**Missing.** Checks for the design basis (a part outside the vendor list, a brand set not allowed, a document number still "TBD", a panel over the count limit), a data-quality check (a picked part whose library record is unverified), and a warnings summary the engineer can mark "accepted" with a reason that prints in the history.

### 10. Preview

**Today.** Every sheet, group chips, HWIO switch, revised cells after a compare.

**Missing.** The new sheets (summary BOM, spares, cable schedule, revision history); "Mark as revised" on a row for changes the compare can't see; a note column visible in preview only.

### 11. Issue (extended)

**Today.** One workbook: panel BOMs, Loose Material, Nameplates, Power, Heat Dissipation, Heat Calculations; file name from the pattern; compare with a previous file.

**Missing.** A Summary BOM sheet consolidated by part number across panels and loose material (quantity, make, model, ordering code, where used), which procurement needs; the Spare Parts and Cable Schedule sheets; a Revision History sheet (rev, date, prepared, checked, approved, description of change); prepared/checked/approved names in the header or on a cover sheet; a choice of which sheets to include per issue; an optional PDF export of the issued sheets.

### 12. Handover (extended)

**Today.** Export `.bomproj`, backups, compare with the previous issue at build time.

**Missing.** A recorded issue: when the engineer builds "as issued", the app stores the revision, date, file hash and the compare result in the substation, so the next issue compares automatically and the history sheet fills itself; a change log the engineer can read before issuing; a procurement extract (the summary BOM as CSV).

## The library: organisation and maintenance

**Today.** One shipped library, psa-devices 1.15.0: 381 parts in 25 categories, five commodity catalogues with brand sets, alternatives by `alt_group`, a device database with datasheet facts and a confirmed / partial / unverified quality flag per record. The app edits parts and catalogues into local versions (`1.15.0+local.n`), exports and imports CSV, imports `.bomlib` packages, and keeps every version installed. Contractor deliveries come in as CSV tables and reach the library through `data/library/additions.yaml` one reviewed step at a time.

That is a sound base. What it lacks is the organisation an engineer needs when the library is the thing they trust least: who owns a record, whether a number has a source, whether a part may be used on this client's job, and whether it is still made.

### How to organise it

| Layer | What it holds | Who maintains it | Where |
| --- | --- | --- | --- |
| Official library | Released versions (1.x.0) built from `data/library/`, reviewed parts only | The library owner (Ali, or a named engineer), through a release PR | Shipped with the installer, `.bomlib` updates |
| Local edits | Fixes and additions an engineer makes on one PC (`+local.n`) | Each engineer | The app's library store, exported as CSV or `.bomlib` to send back |
| Project overrides | Part number, overrides and SFP choices for one design (ADR 0024) | The project engineer | The substation file, never the library |
| Client vendor list | Which brand sets and parts a client allows | The project engineer, from the client's specification | The project file (`defaults.vendor_list`), referenced by the design basis |
| Device database | Datasheet facts, sources, quality flag, alternatives | The library owner and the contractor | Packaged with the library, read-only in the app |

### What each part record needs

- **A source for every number.** `unit_power_w`, `inrush_a`, `height_u` and `input_v_max` each carry a source (datasheet page, contractor ledger line, or "assumed") and a date. The device database has this per record; the library record does not. A part with an assumed power is picked today without a warning.
- **A lifecycle state**: `draft`, `reviewed`, `released`, `obsolete`, with a successor part for obsolete ones. Checks warns when a picked part is draft or obsolete, and Parts offers the successor.
- **Ownership and change notes**: who added or changed a record and why, from the local-version release notes, shown on the record.
- **Classification for search**: manufacturer, family, category (exists), function tags ("L1 access switch", "24-port"), and the roles it can fill on Parts.

### How to maintain it

1. **Intake.** A contractor CSV goes through the existing CSV import into a local version, not into `additions.yaml` by hand. The review page shows the diff; the owner accepts rows into `draft`.
2. **Review.** A Library › Review queue lists draft records with missing sources or an unverified quality flag. Each is reviewed to `released` or sent back with a note.
3. **Release.** The owner packs an official version. The changelog is the release notes. Projects pinned to an older version see the warning they see today.
4. **Field feedback.** A project override that changes a library value (power, inrush, height) can be sent back as a proposed library edit from Parts ("Propose for the library"), so field knowledge reaches the library without YAML.
5. **Health.** A Library › Health tab: parts by state, parts without a source, parts with no alternative, obsolete parts in use by projects on this PC, catalogue brands with gaps (an MCB set missing a rating the sizing asks for).

The library screens exist for most of this; the new work is the state and source fields, the queue, the health tab and the vendor list.

## Features missing entirely

These have no screen, model or sheet today. Each is listed with what it reads, what it produces and where it belongs.

| # | Feature | Reads | Produces | Belongs on |
| --- | --- | --- | --- | --- |
| F1 | Design basis | The engineer | Defaults for constants, brands, spares, tags, enclosure, documents; checks against them | Substation › Design basis |
| F2 | IED schedule | The engineer, or an imported CSV from the protection design | Ports per speed, media and side; `ied_count`; the L1 SFP mix | Parts › IED schedule |
| F3 | External links | The engineer | EXT switch and L2 ports, firewall ports, SFPs, patch cords | Parts › Network |
| F4 | SFP quantities | Port plans, spares policy, the engineer's extras | Group C rows as `=used+spare+extra` | Parts, per switch |
| F5 | Housekeeping editor | Design basis, heat check, the engineer | Groups D, E, G rows with their rules | Panel editor › Options |
| F6 | Terminals tab | Rules, spare percent, overrides | Group G rows with the rule shown | Panel editor › Terminals |
| F7 | Per-panel enclosure and kind | The engineer | Group A row, kind-dependent quantities, heat check | Panel editor › Enclosure |
| F8 | Spares list | Every BOM row and loose item, the spares policy | A Spare Parts sheet; the list editable | Spares page |
| F9 | Summary BOM | Every panel BOM and loose item | One sheet consolidated by ordering code with where-used; CSV extract | Build (sheet choice), Preview |
| F10 | Cable schedule | Port plans, link media, lengths | Suggested loose rows; a Cable Schedule sheet | Loose material, Build |
| F11 | Revision history | Recorded issues, compare results, accepted warnings | A Revision History sheet; prepared, checked, approved in headers | Build, Settings › Documents |
| F12 | Vendor list and part states | Client specification, library owner | Checks warnings; filtered part pickers; successor offers | Project, Library |
| F13 | Library review queue and health | Local edits, device database | Draft to released flow; a health tab | Library |
| F14 | Templates | A finished substation | A new substation from a client template (design basis, brands, options, loose list), beyond today's copy | New substation dialog |
| F15 | Panel count control | The engineer | A fixed or maximum panel count the layout must respect, with a clear error when it can't | Parts › Network or Panels |
| F16 | Per-panel and per-row notes | The engineer | A notes column in Preview and an optional notes sheet; never printed on the BOM unless chosen | Panel editor, Parts |

Two things were considered and left out on purpose. **Pricing** belongs to procurement, not the BOM: the summary BOM's CSV extract is the hand-off, and a price column stays out of the workbook. **Multi-user editing** is out of scope while the app is one engineer on one PC with `.bomproj` exchange.

## The automation contract

The right mix of automation and manual input is one rule applied everywhere, not a setting per feature. Every value the engine derives follows this contract on the screen that shows it:

1. **Computed first.** The engine fills it; the engineer never starts from blank.
2. **Explained in place.** The value shows its rule in one line: "27 = 24 L1 links + 3 spare", "16 A: next standard size above 7.1 A", "12 = 2 × 6 AC MCBs". The rule text comes from the engine with the value, so the UI never re-implements a rule.
3. **Overridable where shown.** Clicking the value makes it an input. The override is stored as an override (never as a copy of the computed value), so the computed value keeps moving under it and a change in inputs is still visible.
4. **Marked and resettable.** An overridden value carries the marker the app already uses and a "Use automatic" reset, and Checks lists every override in one place with its reason.
5. **Sourced.** A default that came from the design basis, the project or the library says so ("From the design basis"), as Settings does for constants today.
6. **Reasoned when risky.** An override that weakens a check (a smaller breaker, fewer spares than the policy) asks for a one-line reason, stored with it and printed in the revision history.

Where the app already follows the contract: Design constants, panel options, part overrides on Parts. Where it stops at step 1: SFP counts, housekeeping, terminals, grounding, spare ratings, switch counts, cable managers' count, the heat check's fan choice. The implementation plan applies the contract to each of these with the same component (`components.md` should get a "Derived value" component: value, rule, override input, marker, reset).

## Priorities, phasing and questions

Ordered by what blocks a real BOM first, and by dependencies: the contract component and the design basis come first because every later feature uses them.

| Phase | Content | Why this order |
| --- | --- | --- |
| A. Foundations | The derived-value component; SFP quantities (F4); per-panel enclosure and kind (F7); new-substation setup instead of ASSUMED seeds | Unblocks the most common wrong BOMs; proves the contract on one feature |
| B. Design basis | Design basis tab (F1); vendor list and part states (F12); checks for both; templates (F14) | Every later default reads from it |
| C. Panel detailing | Housekeeping editor (F5); terminals tab (F6); grounding, spare ratings, alarm toggles, BOM text per row | The spec's fixed quantities become inputs with defaults; needs ADRs |
| D. Network inputs | IED schedule (F2); external links (F3); panel count control (F15) | Replaces the one-number network with the engineer's real inputs |
| E. Issue outputs | Summary BOM (F9); spares list (F8); cable schedule (F10); revision history and recorded issues (F11) | What the engineer hands over after the panel BOMs |
| F. Library | Review queue and health (F13); sources and lifecycle on records; propose-from-project | Makes the library trustworthy at the pace the data arrives |

Phases C and D change rules the spec states as fixed or single-valued (housekeeping counts, AC branch ratings, terminal quantities, one IED count). Those need an ADR each and Ali's go-ahead before code, as CLAUDE.md requires. Phases A, B, E and F add inputs and outputs without moving golden values when the new inputs are unset.

**Questions for Ali** (each also asked as a card in the thread):

- [ ] Phase order: start with A then B as proposed, or with E (issue outputs) because handover documents are the visible gap to a client?
- [ ] Summary BOM: consolidated per substation only, or also across the project's substations?
- [ ] Spares policy: percent per category with a minimum of one (recommended), or a fixed list typed per project?
- [ ] IED schedule: rows typed in the app (recommended), CSV import from the protection design, or both?
- [ ] Prepared, checked, approved names: in the page header, on a cover sheet, or only on the revision history sheet?
