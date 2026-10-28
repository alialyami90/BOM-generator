# Device database

Reference data for the parts in the example project: datasheet facts the workbook
does not carry, and two alternative brands per part with a low, mid and high tier
part number each. It is researched from manufacturer and distributor pages, and
every record lists its sources.

The generator never reads this folder. The device library it builds from is
`examples/library.yaml` (spec: Inputs the tool needs → 1. Device library), and the
library fields (category, model, ordering code, wattage, ports, children…) live there
only. Changing a part in a project means editing the library, not this folder.

A library package can carry these files, so the app's Library screen can show a
part's datasheet details and alternatives next to the library's parts. To ship
them with a library, add the folder when packing:

```bash
bomgen library pack examples/library.yaml --name psa-devices --version 1.0.0 \
  --add data/device-db
```

The package keeps the YAML files under `device-db/`, and import checks every record
against the field rules below.

Records of `kind: device` key on the library's `part_id`s, so a tool or a person can
join the two. Records of `kind: catalogue` (`MCB-*`, `AUX-*`, `TB-*`, `BUSBAR-*`,
`ENCL-*`) use ids local to this database, because the library keys MCBs by rating,
terminal blocks by type, busbars by role, and enclosures per panel. Each catalogue
record names the library catalogue entries it describes in `library_refs`, e.g.
`mcb.16`, `terminal_blocks.UT-16`, `busbars.ac_safety_ground`; enclosures have none.

`docs/device-db-findings.md` lists what the research found that disagrees with the
workbook or the spec. Those are open questions for Ali, not changes.

## Files

| File | Parts |
| --- | --- |
| `network.yaml` | Switches, firewall, SFP transceivers, fibre patch panel and its kit, cable manager |
| `sel-automation.yaml` | SEL RTACs, Axion IO modules, GPS clock and antenna kit, workstation, serial cable |
| `housekeeping.yaml` | Enclosures, lamp, fan, filter, thermostat, interposing relay kit, socket, change-over diodes |
| `electrical.yaml` | MCBs, auxiliary contact, terminal blocks, grounding busbars |
| `workstation-loose.yaml` | Monitor, annunciator and mount, keyboard, software, loose cables, patch cords |

## Record format

```yaml
schema_version: 1
area: network
title: ...
records:
  - part_id: RST2228-L1-24MM      # device: same id as examples/library.yaml; catalogue: local id
    kind: device                  # device (a library part) | catalogue (MCBs, terminals, enclosures, busbars)
    library_refs: [mcb.16]        # catalogue records only: the library catalogue entries covered
    description: ...              # BOM description, for reading the file on its own
    make: Ruggedcom               # brand as in the BOM, left out when the BOM has none
    verified: confirmed           # confirmed | partial | unverified (the original part's facts)
    datasheet:                    # whatever could be confirmed; keys are left out when unknown
      full_name, manufacturer, summary,
      power: {input, redundant_psu, typical_w, max_w},
      ratings: {...}, ports: [...], dimensions_mm: {h, w, d}, rack_units, weight_kg,
      mounting, operating_temp_c: {min, max}, certifications: [...],
      ordering_code_decoded: {...}, datasheet_url, product_url, notes,
      mounting_kind: rack,        # rack | din_rail | plug_in | enclosure | external (always given)
      height_u: 1,                # whole U in a 19-inch rack; 0 for anything not rack mounted
      height_note: ...,           # where the height came from, when it needs saying
      port_groups:                # switches only: what the layout sizer may use each port for
        - {ports: "slots 1-6", count: 24, speed: 100M, media: MM, kind: fixed, usable_for: ied}
        - {ports: "slot 0", count: 4, speed: 10G, media: SFP+, kind: sfp_slot, usable_for: uplink}
    alternatives:                 # exactly two brands, neither the original's
      - make: Moxa
        manufacturer: ...
        tiers:
          low:  {model, ordering_code, description, unit_power_w, url, notes, verified}
          mid:  {...}
          high: {..., same_as: mid}   # only when no distinct part exists for this tier
    sources: [https://...]
```

### Field rules

Readers (the tests, and the app's loader) can rely on these:

- **Always given:** `part_id`, `kind`, `description`, `verified`, `datasheet`,
  `alternatives`, `sources`; in `datasheet`, `summary`, `mounting_kind` and `height_u`;
  on each tier, `model`, `description` and `verified`.
- **Optional:** everything else, left out when unknown (never `null`). `library_refs` is
  only on catalogue records, `port_groups` only on library switches, `same_as` only on a
  tier that repeats a lower one (`low` or `mid`).
- **No other keys.** A new field is added here first, then to the files.
- **Free-form:** only `ratings`, `ports` (a list of strings) and `ordering_code_decoded`.
- **Numbers are numbers:** `power.typical_w`, `power.max_w`, `dimensions_mm.*`,
  `operating_temp_c.*`, `rack_units`, `weight_kg` and a tier's `unit_power_w` are int or
  float; `power.redundant_psu` and a tier's `verified` are booleans. Anything uncertain
  about a figure goes in `notes`, not in the value.
- **Port groups:** `ports` (label), `count` (positive int), `speed` (`100M | 1G | 10G`),
  `media`, `kind` (`fixed | sfp_slot`) and `usable_for` (`ied | uplink | any`) are all
  given; `note` is optional. `media` is `MM`, `SM` or `RJ45` on fixed ports and the cage
  type (`SFP`, `SFP+`) on SFP slots.
- `height_u` is a whole number, at least 1 for `rack` and 0 for every other mounting.

The model and ordering code the BOM uses are not repeated here; the record's
`datasheet.ordering_code_decoded` explains them where they could be decoded.

`verified` on a tier is `true` only when that exact part number was seen on a
manufacturer or distributor page during research. `false` means it came from a naming
pattern or catalogue knowledge, so check it before ordering.

Tiers: **low** is the cheapest acceptable functional equivalent, **mid** the closest
like-for-like, **high** a premium or more capable part.

`datasheet` power figures are the manufacturer's. The wattage used for the power and
heat sheets is the library's `unit_power_w`, which follows the workbook; where the two
differ, `docs/device-db-findings.md` says so.

## Rack height and port roles

`height_u` and `port_groups` feed the substations and auto-layout design (ADR 0013).
`mounting_kind` says why a part takes no rack space: `din_rail`, `plug_in` (sits in
another part: SFPs, Axion modules, the FOPP's splice kit), `enclosure` (fixed to the
cabinet body, door or profile) or `external` (outside the cabinet: wall, desk, mast,
cables, software). A multi-part assembly counts its height once, on the parent
(SEL-2240 carries the Axion chassis's 5U). Blank plates are not parts.

A port group's `usable_for` is `ied` (device downlinks), `uplink` (towards the next
level, or interlinks) or `any`. The library still holds the values the generator uses;
these are the researched source for them.

## Checks

`tests/unit/test_device_db.py` checks that the device records and the parts in
`examples/library.yaml` match both ways, that catalogue records cover every library
catalogue entry, that each
record cites a source and repeats no library field, that each has two other brands
with low, mid and high parts (a repeated part only when marked `same_as`), that each
record gives its mounting and a whole `height_u` (non-zero only for rack parts), and
that every library switch, and only a switch, lists port groups with a known role.
