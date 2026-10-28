# Device database

Reference data for the parts in the example project: datasheet facts the workbook
does not carry, and two alternative brands per part with a low, mid and high tier
part number each. It is researched from manufacturer and distributor pages, and
every record lists its sources.

The generator never reads this folder. The device library it builds from is
`examples/library.yaml` (spec: Inputs the tool needs → 1. Device library), and the
library fields (category, wattage, ordering code used in the BOM, ports, children…)
live there only. Records here key on the same `part_id`s, so a tool or a person can
join the two. Changing a part in a project means editing the library, not this folder.

`FINDINGS.md` lists what the research found that disagrees with the workbook or the
spec. Those are open questions for Ali, not changes.

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
  - part_id: RST2228-L1-24MM      # same id as examples/library.yaml
    kind: device                  # device (a library part) | catalogue (MCBs, terminals, enclosures, busbars)
    description: ...              # BOM description, for reading the file on its own
    make: Ruggedcom               # as in the BOM
    model: RST-2228
    ordering_code: ...
    verified: confirmed           # confirmed | partial | unverified (the original part's facts)
    datasheet:                    # whatever could be confirmed; keys are left out when unknown
      full_name, manufacturer, summary,
      power: {input, redundant_psu, typical_w, max_w},
      ratings: {...}, ports: [...], dimensions_mm: {h, w, d}, rack_units, weight_kg,
      mounting, operating_temp_c: {min, max}, certifications: [...],
      ordering_code_decoded: {...}, datasheet_url, product_url, notes
    alternatives:                 # exactly two brands, neither the original's
      - make: Moxa
        manufacturer: ...
        tiers:
          low:  {model, ordering_code, description, unit_power_w, url, notes, verified}
          mid:  {...}
          high: {...}
    sources: [https://...]
```

`verified` on a tier is `true` only when that exact part number was seen on a
manufacturer or distributor page during research. `false` means it came from a naming
pattern or catalogue knowledge, so check it before ordering.

Tiers: **low** is the cheapest acceptable functional equivalent, **mid** the closest
like-for-like, **high** a premium or more capable part.

`datasheet` power figures are the manufacturer's. The wattage used for the power and
heat sheets is the library's `unit_power_w`, which follows the workbook; where the two
differ, `FINDINGS.md` says so.

## Checks

`tests/unit/test_device_db.py` checks that every workbook part has a record, that each
record cites a source, and that each has two other brands with low, mid and high parts.
