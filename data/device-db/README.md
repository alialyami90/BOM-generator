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

The package keeps the YAML files under `device-db/`. `pack` checks every record
against the field rules below and refuses to build a package that breaks them; import
does not re-check them.

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

`contractor-2026-10-31/` holds the contractor's consolidated library delivery of 2026-10-31 as it
arrived, for reference only: CSV tables, evidence ledgers and manifests. It is not read by the
generator, `build.py` or `pack`, which take only the YAML files above. The 82 source PDFs (about
220 MB) and the review workbook stay out of git; `pdf_manifest.csv` lists each PDF with its SHA-256.
Its parts reach the library only through the records above, one reviewed step at a time
([review](https://claude.ai/artifact/AZ8CXFEtk6a91J1uDTy745)).
`contractor-return-2026-10-31.md` and its CSV list what still goes back to the contractor.

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
          low:  {model, ordering_code, description, unit_power_w, url, notes, verified,
                 height_u, mounting_kind, supply_type, voltage_v, input_v_min, input_v_max,
                 supply_option, supply_ok, power_supplies, power_basis, power_note,
                 inrush_a, inrush_ms, inrush_basis, inrush_note, port_groups, airflow_m3h,
                 ratings, sources}
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
- **Port groups:** `ports` (label), `count` (positive int), `speed`
  (`10M | 100M | 1G | 2.5G | 5G | 10G | 25G`; 2.5G, 5G and 25G are never sized for SFPs,
  ADR 0027), `media`, `kind` (`fixed | sfp_slot`) and `usable_for` (`ied | uplink | any`) are all
  given; `note` is optional. `media` is `MM`, `SM` or `RJ45` on fixed ports and the cage
  type (`SFP`, `SFP+`) on SFP slots.
- `height_u` is a whole number, at least 1 for `rack` and 0 for every other mounting.

### Electrical data for the library (M14)

Each alternative tier carries what a library device needs, so it can become a pickable
part and its branch MCB can be sized from its own data:

- `height_u` and `mounting_kind` as on the datasheet. A rack part whose height was not
  found leaves `height_u` out rather than writing 0.
- `supply_type` (`VDC | VAC | none`) and `voltage_v`, the supply the BOM would use
  (125 V DC station DC, 230 V AC auxiliary). `input_v_min` and `input_v_max` give the DC
  input range of the chosen supply variant where the datasheet states one.
- `supply_option` names the power-supply option the ordering code selects;
  `supply_ok: false` means no variant takes 125 V DC (or 230 V AC for an AC part), so the
  part needs a converter. `power_supplies` is 2 when the code includes a redundant supply.
- `unit_power_w` with `power_basis`: `datasheet_max`, `datasheet_typical`, `computed`
  (current × voltage, with the arithmetic in `power_note`) or `assumed` (reason in
  `power_note`).
- `inrush_a` (peak A) and `inrush_ms` where a datasheet gives them, with `inrush_basis`
  (`datasheet | not_given | assumed`) and `inrush_note`. Most datasheets give none.
- `port_groups` on switches and firewalls, as on the datasheet. `airflow_m3h` on fans:
  the figure with the outlet filter.
- `ratings` is free-form: MCB trip data (`trip_curve`, `magnetic_trip_multiple` and
  `magnetic_trip_multiple_dc`, the lower bound of the magnetic trip band in multiples of
  In, plus `dc_rating_v` for the poles in series), terminal cross-sections, socket
  ratings and the like.
- `sources` lists the pages for that tier's figures.

The original part's datasheet carries the same inrush and input-range keys. They go into
the shipped library, `data/library/psa-devices.yaml`, which `data/library/build.py`
generates from `examples/library.yaml` and these records (plan Q38); the example library
leaves them out so its golden values stay those of the example workbook. Run
`python data/library/build.py` after changing either. An MCB
record's `datasheet.ratings.same_brand_dc_range` gives the Schneider C60H-DC code for that
rating, the DC-rated range in the original's brand.

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
They also check that every alternative states its mounting and supply, that a powered
one says where its power figure comes from, that a DC input range contains the nominal
voltage, and that every MCB gives its trip curve and a DC magnetic multiple at or above
the AC one.
