# 0030. Every device tag has level, type, side and number

- Status: Accepted (Ali, 2026-11-01)
- Date: 2026-11-01
- Spec sections: Tag naming conventions; Derivation rules (MCB descriptions); Device nameplates
  (ADR 0026)

## Context

"Tag naming conventions" gives `<PANEL>-<LEVEL>-<TYPE>-<LAN><NN>`, but only the L1 and L2
switches follow it. EXT devices carry the LAN letter only (PSA1-EXT-ESW-A). The gateway numbers
by LAN (PSA1-DHPCC-GW-1). The GPS clock, RTAC and workstation have no level and no number
(PSA3-GPS, WS-SRV/OAS/EAS). As a result:

- Two gateways in one panel get the same tag (audit 2026-10-31, ENG-1).
- The operator workstation, engineering workstation and DA server all come from one library
  part, so a new project prints three identical SRV/OAS/EAS tags and plates (APP-9).
- Nothing checks that tags are unique.

Ali's nameplate request gave the tag he expects for the time server: L2_GPS_A01 (audit
ALI-6, ALI-16). On 2026-11-01 he chose "Yes, every device": every device gets level, type,
side and a running number (L2_GPS_A01, L2_OWS_A01, L2_EWS_A01), with an ADR and a duplicate-tag
check.

## Decision

1. **Form.** A group B device whose part has a `purdue_level` is tagged
   `<PANEL>-<LEVEL>-<TYPE>-<SIDE><NN>`. The plate and the MCB load name drop the panel prefix
   and use underscores, as before (`short_tag`): L2_GPS_A01. EXT devices follow the same form
   (PSA1-EXT-ESW-A01). A library `tag_pattern` or a panel row's `tag` still wins over the rule.
2. **Level** is the library part's `purdue_level`. Gateway, GPS clock, RTAC and workstation
   parts get `purdue_level: L2` and drop their `tag_pattern`. This applies to the originals and
   the alternatives in `examples/library.yaml`, and to the contractor's SEL-3530-4, SEL-3350-1
   (RTAC) and SEL-2407 (GPS) in `data/library/additions.yaml`, which had no tag. The shipped
   library becomes psa-devices 1.10.0.
3. **Side** is the row's LAN letter. In a panel with no LAN (PSA3, WS) it is A, as in Ali's
   L2_GPS_A01.
4. **Type** is the library's `tag_type`. A panel row's new optional `tag_type` replaces it. The
   layout writes OWS, EWS and SRV on the rows of the `operator_ws`, `engineering_ws` and
   `da_server` roles, because the three share one library part. SRV is the server code of the
   example's SRV/OAS/EAS.
5. **Number.** NN counts per panel, level, type and side, starting at the level's first number
   (L1 at 11, the others at 01). That gives GW-A01 and GW-B01 in the two LAN panels, and GW-A01,
   GW-A02 for two gateways in one panel.
6. **Duplicate check.** The check report fails (`duplicate_tag`) for any tag that two device
   units share anywhere in the substation. Units of parts with no type code carry a label, not
   a device tag, and are not checked. Examples are "Keyboard & Mouse" and "Cable Manager".

### Golden values that move

The example's tags, and with them the MCB load names, SFP host rows and plates:

| was (full tag) | now |
| --- | --- |
| PSA1-EXT-ESW-A, PSA2-EXT-ESW-B | PSA1-EXT-ESW-A01, PSA2-EXT-ESW-B01 |
| PSA1-EXT-FW-A, PSA2-EXT-FW-B | PSA1-EXT-FW-A01, PSA2-EXT-FW-B01 |
| PSA1-DHPCC-GW-1, PSA2-DHPCC-GW-2 | PSA1-L2-GW-A01, PSA2-L2-GW-B01 |
| PSA3-GPS | PSA3-L2-GPS-A01 |
| PSA3-RTAC | PSA3-L2-RTAC-A01 |
| WS-SRV/OAS/EAS | WS-L2-SRV/OAS/EAS-A01 |

Unchanged: the L1 and L2 switches, PSA1-FOPP-CCR-A01, PSA3-HWIO, WS-MONITOR, Keyboard & Mouse
and every housekeeping tag (IL, FAN, TH, IPR, COD, FILTER, AUX PS). `tests/golden/` cites this
ADR where the values moved.

### Open questions (plan Q56 to Q60)

These device types have no clear level, side or type code, so they keep today's tag until Ali
decides:

- Q56: HWIO (the Axion I/O chassis). Is it L1 (bay I/O) or L2?
- Q57: MONITOR. It is a workstation peripheral with no network link.
- Q58: FOPP-CCR-A01. CCR stands where the level goes. Should it become L2 or L3?
- Q59: The example's one combined SRV/OAS/EAS computer keeps its type code. Is SRV the right code
  for the DA server?
- Q60: Housekeeping and accessories (IL, FAN, TH, IPR, COD, FILTER, Keyboard & Mouse, Cable
  Manager) stay as they are.

Ali answered all five on 2026-11-01: each keeps today's tag.

## Consequences

- Every device unit has its own tag, plate and MCB load name. A duplicate fails the build's
  checks instead of passing silently.
- The example workbook no longer matches the issued workbook's tags. The spec's "Tag naming
  conventions" text is updated to match (Ali accepted on 2026-11-01).
- A user library that still carries the old `tag_pattern` keeps its old tags. The duplicate
  check catches any clash.
