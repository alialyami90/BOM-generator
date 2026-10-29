# Role 3 reference (detail behind STATE/NEXT; written by B3 on 2026-10-29)

This file is background. STATE.md and NEXT.md are the live summary. Facts stated in the
repo's docs are linked here, not copied.

## 1. What role 3 owns and how the pieces fit

| Piece | Path | Source of truth | Who reads it |
| --- | --- | --- | --- |
| Device database (reference data) | `data/device-db/*.yaml` and its `README.md` | Web research, every figure sourced | Humans; `build.py`; packed into `.bomlib` with `--add data\device-db` |
| Findings | `docs/device-db-findings.md`, items 1–31 | Research notes | Ali, A1/B1 |
| Database checks | `tests/unit/test_device_db.py` (18 tests) | README "Record format", "Field rules", "Checks" | CI |
| Example library | `examples/library.yaml` | The spec's example workbook, plus M14 alternatives | **B2's file**; goldens |
| Shipped library | `data/library/psa-devices.yaml` | **Generated** by `data/library/build.py` | `release.yml` packs it as psa-devices 1.1.0 |
| Shipped library checks | `tests/unit/test_shipped_library.py` (role 3, 5 tests) and `tests/unit/engine/test_engine_shipped_library.py` (role 9, 6 tests, #171) | — | CI |

- Ownership is in `docs/agents.md` → Roles, row 3 (`data/library/` was added in #168).
- The engine never reads `data/device-db/` directly. See `docs/agents.md` "A3 — Device
  database researcher".

## 2. data/device-db layout

The files hold 63 records with 126 alternatives (2 brands × low/mid/high tiers each):

| File | Records | Alternatives |
| --- | --- | --- |
| `electrical.yaml` | 11 | 22 |
| `housekeeping.yaml` | 13 | 26 |
| `network.yaml` | 13 | 26 |
| `sel-automation.yaml` | 15 | 30 |
| `workstation-loose.yaml` | 11 | 22 |

- Each record has a `part_id` (a library part id, or a local catalogue id such as `MCB-*`,
  `AUX-*`, `TB-*` or `BUSBAR-*` with `library_refs`), `kind`, `datasheet`, `alternatives`
  and `sources`.
- Each alternative tier has `make`/`model`/`ordering_code`, `verified`, the electrical
  keys (see README "Electrical data for the library (M14)") and `sources`.
- The field names and rules are in `data/device-db/README.md`. Read it before editing.

## 3. How M14 turned the database into library parts (#130)

The generator is off-repo, in `/mnt/project-files/handoff/03-device-db/`:
- `library_entries.py`. Usage: `python3 <path>/library_entries.py .` from the repo root.
  It imports `bomgen.io.round_trip` from `src/`, so do not run it with `-I`.
- `m14_merge.py`, imported by it.
- `assemble.py` and `layout_data.py`, which merged the research output into
  `data/device-db`.
- `research-m14/`: the briefs (`BRIEF.md`, `BRIEF-catalogues.md`), inputs and raw outputs.

`library_entries.py` was written against the **pre-M14** `examples/library.yaml`, so it is
**not idempotent**: running it on today's file appends a second copy. To add parts now,
either:
- edit `examples/library.yaml` by hand following the rules below (with B2's OK), or
- adapt the script to skip existing ids.

Rules it applied:
- **Part id.** `f"{original}.{slug(make)}-{TIER}"`, upper case, e.g.
  `SEL-2730M-EXT.MOXA-LOW`, `SEL-2244-2.HITACHI-ENERGY-MID`.
- **Groups and tiers.** Every original gets `alt_group: <its part_id>  # M14 (ADR 0017)`
  right after `category:`. Alternatives get the same `alt_group` and `tier: low|mid|high`.
  A tier marked `same_as` (the same part as another tier) is not a separate part.
- **Copied from the original:** `description_template`, `tag_type`, `purdue_level`,
  `tag_pattern`, `load_type`, `alarm_on_branch_mcb`, `hwio_points`, `cores`, `terminals`.
  **Not copied:** `di_inputs` (finding 31) and `min_branch_mcb_a` (deprecated by Q35).
- **Children and loose items** map to the same-brand, same-tier alternative of the child
  where one exists; otherwise to the original child.
- **Supply.** VDC or VAC gives `voltage_v`, `unit_power_w` and `load_type`; VDC also gives
  `power_supplies` (1 or 2). It adds `inrush_a`/`inrush_ms`/`input_v_min`/`input_v_max`
  when the tier states them.
- **Rack height.** A rack part with unknown height leaves `height_u` out; the loader
  rejects 0.
- **Ports.** `port_groups` become `ports`. SFP slots get `media: null`.
- **Skipped:** a powered tier with no power figure (11 of them; finding 30).
- **Catalogue brands** (ids are lower case):
  - `mcb`:
    - `schneider-c60h-dc`: `codes` for 1/2/6/10/16 A (no 8 A) and `ac_rated: false`.
    - `abb-s200m-uc`: `code_pattern` `2CDS272061R0{rating:02d}4`.
    - `siemens-5sy5`: `code_pattern` `5SY52{rating:02d}-7`.
    - All three carry `trip_curve: C`, `magnetic_trip_multiple` (AC, absent for the
      C60H-DC), `magnetic_trip_multiple_dc` and `dc_rating_v`.
  - `aux_contact`: `schneider-c60h-dc` A9N26924, `abb-s2c-h6r` 2CDS200912R0001, and
    `siemens-5st3010`.
  - `terminal_blocks`: `weidmuller` and `wago`. Each brand must list every default type
    (UT-16, UT-2.5-MTD, UT-2.5-MT); the loader enforces this.
  - `busbars`: `phoenix-contact` and `nvent-erico`, with entries for every default role.
  - `housekeeping`: `alternatives-a` and `alternatives-b`, built from the mid tiers.
- **Default MCB.** iC60N, which stays the default (Q37), gets `trip_curve: C`,
  `magnetic_trip_multiple: 6.4` (8 In ±20 %) and `magnetic_trip_multiple_dc: 9.05`.
- **Output.** The text is normalised with `dump_text(load_text(text))` and checked
  idempotent; `tests/unit/test_round_trip.py` requires that fixed point.

## 4. The shipped library (Q38, #161)

- **What `data/library/build.py` does:**
  - `datasheets()` reads every record's `datasheet` for `inrush_a`, `inrush_ms`,
    `input_v_min` and `input_v_max`.
  - `build(example_text, figures)` inserts them into each **original** (no `tier`) after
    `alt_group`, with a `# datasheet (data/device-db)` comment on the first. It raises if
    the example already has the key.
  - It then swaps the example's header for a GENERATED header.
- **What it adds today:** input ranges to 11 originals (RST2228-L2, RST2228-L1-24MM,
  SEL-2730M-EXT, FGR-60F, SEL-3555-GW, SEL-3555-RTAC, SEL-2488, SEL-2240, SEL-3355,
  NAP-F23 and NAP-K55), and inrush to the 5 SEL ones (20, 20, 8, 17 and 20 A).
- **Effect (pinned by #171):**
  - The SEL-3555-GW/RTAC and SEL-3355 branches size to 6 A, because 20 A inrush exceeds
    2 A × 9.05.
  - The other branches stay at the 2 A floor and the mains do not change.
  - `dc_float` warns for the iC60N (Q37) and for the FGR-60F (Q41).
- **Release.** `release.yml` packs it with `--add data\device-db` as psa-devices 1.1.0.
  The name and version must match `examples/project.yaml` `library:`
  (`test_packaging.py`). Packaging is B6's.

## 5. PR history for role 3

| PR | What |
| --- | --- |
| #6, #18 | Initial database; rack heights, mounting and switch port roles |
| #30 | FOPP-96SM is 1U (Q33) |
| #40, #42 | README field rules; `pack` checks records |
| #121 | M14 research: electrical data for every alternative and the DC MCB ranges; findings 22–29 |
| #130 | M14 library entries: 279 alternatives and the brand sets; psa-devices 1.1.0; findings 30–31; 10 tests outside the role |
| #144, #172 | Handoff checkpoints |
| #161 | Q38 shipped library and build script; C60H-DC `ac_rated: false`; release.yml and ADR 0009 |

## 6. Decisions (all resolved; see plan.md §6)

- **Q33.** FOPP-96SM is 1U.
- **Q35.** Branch MCB rule: 1.3 × running current, inrush ÷ magnetic multiple, 2 A floor;
  the DC multiple applies to DC loads.
- **Q37.** iC60N stays the default; the DC-rated ranges are brand sets; the float warns.
- **Q38.** Datasheet inrush and input ranges go in the shipped library only.
- **Q39 / ADR 0023.** Separate `mcb_dc` choice; a DC-only brand (`ac_rated: false`) is
  valid only there.
- **Q41.** The FGR-60F stays, and its float warning is accepted; no DC-rated firewall
  alternative is researched.
