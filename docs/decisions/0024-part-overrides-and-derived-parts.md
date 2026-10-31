# 0024. Part overrides and derived parts

- Status: Proposed
- Date: 2026-10-31
- Spec sections: Inputs the tool needs (2. Substation and its panels); Data model and generation
  order (step 0); Derivation rules (group C, SFPs)

## Context

The Parts page (design `docs/superpowers/specs/2026-10-31-part-picking-design.md`, approved by Ali
2026-10-31, decisions a, b and h) lets a substation pick a library part per device, print its own
part number on the BOM, override the part's library data for this design and pick one SFP model
per port speed and media. The library is shared by every project that uses it, so these values
belong to the substation, not the library. Every engine step (BOM rows, SFP sizing, MCB sizing,
power and heat) reads a panel row's part from the library by `part_id`.

## Decision

An equipment entry gains `ordering_code`, `overrides` (any of `height_u`, `unit_power_w`,
`supply_type`, `voltage_v`, `power_supplies`, `inrush_a`, `load_type`) and `sfp` (L1 and L2
switches only). Each needs a `part_id`: a sized L1 switch with no pick cannot be overridden.

The loader turns each entry that sets any of them into a **derived part**: a copy of the library
part with those values, id `<part_id>+<equipment id>` (`+` because `PartId` allows it and `~` it
does not), `derived_from` naming the library part, and the SFP choice in `sfp_choice`. The copy is
validated as a library part, so an override that breaks a library rule is reported on the entry
with the library's message. It is added to that substation's resolved library only; the library
file is never written, and a library file holding `derived_from` or `sfp_choice` is refused.

The layout places the derived id for the entry (L1 and L2 included), so every later step reads
the derived part unchanged. The L1 ranking leaves derived parts out. The SFP sizing uses the
host's choice for the allocation's speed and media, else today's pick; a choice that does not fit
is an engine error.

New equipment roles label the Parts page rows (`time_server`, `operator_ws`, `engineering_ws`,
`da_server`, `kvm`, `console`, `annunciator`, `time_accessory`) and are sized as `other`. New
categories `kvm` and `console`. `defaults.layout` holds `waist_height_mm` (1000) and
`rack_start_mm` (200), both ASSUMED, for M21.

Rejected: threading the override fields through every engine step (touches each pipeline step and
the sheets); saving overrides as new parts in a local library version (one design's change would
reach every project using that library).

## Consequences

- No engine step changes except the layout's part lookup and the SFP pick; hand-written panels
  still name library parts.
- Generated panel files name the derived id. When the override is later removed or the entry
  renamed, that id no longer exists and the project would not load, so `bomgen layout` could not
  rewrite the file. The loader therefore puts a row of a `generated: true` panel naming
  `<library part>+<entry>` with no derived part back on the library part, in memory only.
  Hand-written and manual panels stay strict: such an id there is an unknown part.
- A placed entry with no part number whose library part has no ordering code is printed with the
  library model; the check report warns about it. The example's `hwio` entry (SEL-2240, no
  ordering code) is such an entry, so the example's check report gains one warning (4 instead
  of 3, 68 items instead of 67); no spec-cited golden value moves.
- The derived part's id appears in the panel files and the check report; the BOM shows its
  ordering code, model and make as before.
