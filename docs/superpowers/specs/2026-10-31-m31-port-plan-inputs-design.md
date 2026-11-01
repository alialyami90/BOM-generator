# M31 Port plan inputs for a fresh project (design note)

- Status: Built with option C (A1, 2026-11-01): RTAC COM ports stay 0, firewall SFPs follow
  its SFP slots; Ali's card on the defaults is open
- Date: 2026-10-31
- Audit finding: ENG-3 (audit 2026-10-31, `engine.md`)
- Spec sections: Inputs, 2 (network port plan); Network accessories (group C)

## Problem

The network accessories come from three equipment fields that no app path writes:

| field | feeds | example value |
| --- | --- | --- |
| `l2_ports`, `l2_speed`, `l2_media` | L2 downlink SFPs (R2) | gateway 1, firewall 1, GPS 1 at 100M, RTAC 2 |
| `port_plan.downlinks` | the device's own SFPs | firewall: 2 x 1G MM |
| `port_plan.serial_ports` | SEL-C607 cables and XRTAC strips | RTAC 6 |

The model defaults are 0 and None (`models/substation.py:106-112`). `start_parts` writes only
the role, the part and `redundant`, and no screen calls `api.set_port_plan`. So a fresh
substation gets no device SFPs, no serial cables and no XRTAC strips, and the layout prints
"0 of 16 usable ports used". The example gets them only because its YAML is hand-written.

## Options

**A. Defaults only, from the library part.** The engine derives the fields from the part when
the row leaves them out.
- For: no UI work.
- Against: the library can't supply the numbers. 17 of the 19 shipped psa-devices gateway, RTAC
  and GPS parts have no `ports` at all. Where `ports` is given, it says what the device *has*,
  not how many links go to the L2 switch or how many COM ports are wired. A hidden engine
  default also changes the BOM silently, which is what the audit is about.

**B. Per-row input only.** The Parts page row gets "L2 links", "speed/media" and, for an RTAC,
"COM ports used". The values are written to the existing YAML fields.
- For: explicit, and it matches the example's hand-written values.
- Against: every row starts at 0, so a user who skips the fields gets the same silent gap.

**C. (Recommended) Per-row input, seeded with category defaults when the row is created.**
- When `start_parts` or `set_equipment_part` writes a row, it also writes defaults keyed by the
  library part's `category`. The category is used rather than the role, because gateway, RTAC
  and GPS rows all have role `other`. The defaults are visible in the YAML and on the row, and
  editable.
- The Parts page shows the three inputs on every row whose part is networked. It calls the
  existing `set_port_plan` and a new `set_l2_link` writer.
- A part change resets the seeded values only if the user hasn't edited them. This reuses the
  M23 rule for `OLD_PART_KEYS`.
- A check-report WARN names any networked row with `l2_ports: 0`, so a gap is never silent.

## Proposed category defaults (per unit; Ali to confirm)

These come from the example, which is the only reference so far.

| library category | `l2_ports` | speed / media | `port_plan` |
| --- | --- | --- | --- |
| gateway | 1 | 1G MM | none |
| firewall | 1 | 1G MM | downlinks 2 x 1G MM when the part has SFP slots |
| gps_clock | 1 | 100M MM | none |
| rtac | 2 | 1G MM | serial_ports 0 (the input asks for it) |
| workstation, da_server | 1 | 1G MM | none |
| io_chassis, annunciator, kvm, console | 0 | none | none |

The RTAC's COM ports default to 0, because the count depends on the serial IEDs (the example's 6
is project-specific). The row shows the input as required, the same way the L2 switch is
required today.

## Where the code goes

- `io/parts_edit.py`: a `CATEGORY_LINKS` table, used by `start_parts` and `set_equipment_part`,
  and a `set_l2_link` writer.
- `app/`: three inputs on the Part row (UI owner: A2). Designed with the impeccable skill, per
  CLAUDE.md "UI work".
- `checks.py`: the `l2_link` WARN.
- The engine is unchanged: `layout.py` already reads these fields.

## Open questions

1. Is a category default acceptable in the first place, given that it is visible and editable?
   Or should every networked row start empty and required?
2. Are the defaults in the table right? Mainly the RTAC's 2 links and the workstation's 1.
3. Should the firewall's own SFP downlinks follow from its part's SFP slots (2 on FGR-60F), or
   always be 2?
