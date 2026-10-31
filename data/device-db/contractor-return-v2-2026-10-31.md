# Still open after v2 of the contractor library

This is round two of [`contractor-return-2026-10-31.md`](contractor-return-2026-10-31.md).
It lists what v2 in `contractor-2026-10-31/` leaves open, and who owes each item. The
contractor answered every one of the 270 asks in `contractor_responses.csv`. Most of what
remains is now ours: a configured ordering code needs an engineer's choice before anyone
can research it. One row per part and ask is in
[`contractor-return-v2-2026-10-31.csv`](contractor-return-v2-2026-10-31.csv) (`part_id`,
`ask`, `owner`, `detail`).

The asks that are closed are left out:

- `resolved`, plus `documented_not_given`, where the cited document does not publish the
  value. This includes the three SEL management-port speeds and the supply inrush of the
  housekeeping parts.
- The Hager DC ratings, which are in psa-devices 1.8.0.

## For the contractor (10)

| Parts | Ask |
| --- | --- |
| NAP-F23.SIEMENS-LOW, -MID, -HIGH | The model-specific datasheet: operating range, consumption and supply inrush. Their access to IndustryMall failed. |
| NAP-F23.ADVANTECH-LOW, SEL-3555-GW.SIEMENS-LOW, -MID | `unit_power_w` with its page. v2 leaves these blank, and the library's figure is an assumed upper bound. |
| SEL-2240.HITACHI-ENERGY-MID | `height_u`, the rack height of the chassis, with its page. |
| SK3243-FAN.PFANNENBERG-LOW, IPR-2903685.FINDER-MID, -HIGH | Confirmation that the exact code exists: the factory datasheet for 11665104055, and the maker's or a distributor's confirmation for the Finder codes. |

Thirty-five other tiered rows that v2 adds also have no `unit_power_w`. The library already
carries a cited datasheet or computed figure for each of them in `data/device-db/`, so
nothing more is asked for them.

## For us (193)

| Owner's ask | Asks | What it needs |
| --- | ---: | --- |
| Configuration | 185 on 123 parts | The configured code a panel orders, chosen by an engineer or from the maker's configurator. Mostly SEL relays, RTACs, Axion nodes, computers and switches; the Nozomi parts; the zenon licence; the FOPP pigtails. The 125 V DC preference fixes the supply only. |
| Identity | 4 | SEL-3555-GW, SEL-3555-RTAC, SEL-3355 and NAP-F23: the `#` codes could not be decoded from public documents. The maker's configuration confirmation or a quote settles them. |
| Power (plan Q54) | 4 | SEL-3555-2, SEL-3355-2, SEL-3560E and SEL-3560S: SEL publishes minimum, typical and maximum figures. Which one the library uses waits on Ali's choice. |

Two configuration rows need a correction rather than a choice. RST2228-L1-24MM's code has
`A05`, which is not a valid service-panel option (finding 4 in `docs/device-db-findings.md`).
The SEL-2240 node also needs its full bill of chassis, coupler and modules.
