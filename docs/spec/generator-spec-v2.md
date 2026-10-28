# Substation SCADA BOM – Generator Spec v2

Oct 28, 2026 · @ALI

## Overview

The tool must produce one Excel workbook (.xlsx) containing a panel-by-panel Bill of Materials for a GIS substation SCADA / PSA (Protection, SCADA & Automation) system, plus three calculations derived from it: power consumption, heat dissipation and cabinet cooling. Every printed sheet carries a page header and page footer. Every calculation row traces back to a device row in a panel BOM, so the tool only needs a device library, a panel list and a few design constants to rebuild the file.

The example covers 4 cabinets and 1 loose-material list:

- **PSA Cabinet 001** (861-GIS01-PSA-0001) – LAN-A network: Level-2 and Level-1 switches, external switch, PCC gateway, firewall
- **PSA Cabinet 002** (861-GIS01-PSA-0002) – LAN-B mirror of Cabinet 001, plus an auxiliary power socket
- **PSA Cabinet 003** (861-GIS01-PSA-0003) – GPS clock, RTAC data concentrator, Axion hardwired-IO chassis
- **WS Console** (861-GIS01-PSA-0010) – server/operator workstation, monitor, keyboard
- **Loose material** – wall annunciator, HMI software, GPS antenna kit, cables, fibre patch cords

Read this spec in order: sheet map, BOM grouping, columns, naming, derivation rules, the three calculation sheets, formatting, output requirements, then the input schema for the tool.

## Workbook map

The workbook holds hidden master BOMs that drive the calculations, visible issued copies of those BOMs, and three visible calculation sheets.

| Sheet | Visible | Represents | Feeds / fed by |
| --- | --- | --- | --- |
| Panel 1 | Hidden | Master BOM, PSA Cabinet 001 (LAN-A network), with HWIO column H | Feeds Power Consumption rows by cell reference |
| Panel 2 | Hidden | Master BOM, PSA Cabinet 002 (LAN-B network), with HWIO column H | Feeds Power Consumption |
| Panel 3 | Hidden | Master BOM, PSA Cabinet 003 (time sync, RTAC, hardwired IO), with HWIO column H | Feeds Power Consumption |
| Aux | Hidden | Master BOM, WS Console (0010) + loose material table below it | Feeds Power Consumption |
| 1 | Visible | Issued BOM for Cabinet 001 (no HWIO column) | Copy of Panel 1 |
| 2 | Visible | Issued BOM for Cabinet 002 | Copy of Panel 2 |
| 3 | Visible | Issued BOM for Cabinet 003 | Copy of Panel 3 |
| 4 | Visible | Issued BOM for WS Console + loose material | Copy of Aux |
| Power Consumption | Visible | DC and AC load per cabinet, 25% margin totals, plus hidden MCB/COR sizing columns | Reads master BOMs; feeds Heat Dissipation |
| Heat Dissipation | Visible | W and BTU/h per powered device per cabinet | Reads Power Consumption; feeds Heat Calculations |
| Heat Calculations | Visible | Fan airflow check for the 3 PSA cabinets, natural-convection check for the WS console | Reads Heat Dissipation totals |

All printable sheets use A4 and page-break preview. Panel BOMs print portrait; the three calculation sheets print landscape.

## How each panel BOM groups its materials

Every cabinet BOM lists the same eight groups in the same order, top to bottom. Groups E–H are separated by one empty bordered row; groups A–D run together without a gap. Serial numbers continue across the gaps.

| # | Group | What goes in it | Example rows (Cabinet 001) |
| --- | --- | --- | --- |
| A | Enclosure | One PANEL row: cabinet H x D x W, base frame, cable entry | PANEL – Rawabi fixed frame, H2100 x D1000 x W800, top entry |
| B | Main equipment | The functional devices, network devices first, then gateways/firewalls/RTAC/IO. A device with sub-parts is a parent row followed by child rows with a blank designation | FOPP → spool, splice holder, 96 pigtails; L2 switch; L1 switches x6; EXT switch; PCC gateway; firewall |
| C | Network and IO accessories | SFPs grouped per host switch, cable managers, serial cables | L2-ESW SFPs (SM, MM 1G, MM 100M), L1-ESW SFPs, firewall SFPs, 9 cable managers |
| D | Cabinet housekeeping | Lamp, fans or vent filters, thermostats, high-temp interposing relay kit (relay, base, suppression module, bracket), change-over diodes, aux socket | IL, FAN-1,2, TH-1,2,3, IPR + 3 children |
| E | AC distribution | Incoming AC MCB (CINC), one branch MCB per AC load or load pair, spares, AC MCB auxiliary contacts | CINC 6A, C1 lamp, C2 fan-1+TH-1, C3 fan-2+TH-2, C4 TH-3, C5 spare, 3 aux contacts |
| F | DC distribution | DC1 main (Q1) then one Q1.n per device PS1, spares; DC2 main (Q2) then Q2.n per device PS2, spares; change-over MCBs (QCOD) where diodes exist; DC aux contacts | Q1 16A + Q1.1–Q1.13; Q2 16A + Q2.1–Q2.13; 4 aux contacts |
| G | Terminal blocks | One row per terminal strip: AC input, AC distribution, lighting, fan/thermostat, smoke detector, socket, DC1/DC2 input, DC1/DC2 distribution, change-over, annunciator, IO knife-disconnect per IO slot, DI negative, RTAC COM, inter-panel | X-AC, X3-AC, TBL, THF, XSD, X-DC1, X-DC2, X4-DC1, X4-DC2, XIP |
| H | Grounding | AC safety ground busbar and instrument ground busbar (description only, no make/model) | AC SAFETY POWER-GROUND, INSTRUMENT-GROUND |

**What changes by panel type**

- **Network cabinets (001/002):** group B is FOPP + switches + gateway + firewall; group C is SFP-heavy; 13 DC branch MCBs per feed (10 used, 3 spare).
- **Control cabinet (003):** group B is GPS clock, RTAC, and an Axion IO chassis whose children are chassis, CPU, 2 power couplers and 4 DI modules; group D adds change-over diodes; group F adds QCOD MCBs; group G adds 58 knife-disconnect blocks per Axion DI slot (D–G), DI negative blocks and RTAC COM blocks.
- **WS console (0010):** a smaller Rittal console; group B is workstation, monitor, keyboard/mouse; ventilation filters replace fans; one thermostat; only one ground busbar.
- **Loose material:** a second table on sheet 4, under the console, with its own grey title block and header row. It holds items not mounted in any cabinet: wall annunciator and mount kit, HMI and Office software, GPS antenna kit, display/USB/DVI cables, and fibre patch cords as "1 Lot".

The network content also splits by LAN: Cabinet 001 holds every LAN-A device, Cabinet 002 the identical LAN-B set. A generator can create 002 by mirroring 001 and swapping A→B, 1→2 in tags.

## Columns of a panel BOM

Each material row has 7 columns (A–G) on issued sheets and 8 (A–H) on hidden masters. Row 1 is a merged title A1:G1; row 2 is the column header; materials start at row 3.

| Col | Header | Content rule | Example |
| --- | --- | --- | --- |
| A | SR.NO | 1 on the first row, then `=<cell above>+1`; skips the blank separator rows so numbering is continuous | 1, 2 … 71 |
| B | ITEM DESIGNATION | Tag of the device or circuit (rules in the next section). Blank on child rows; the parent tag cell is merged down over its children (e.g. B4:B7, B22:B25). Non-tagged commodity rows use a plain label | PSA1-L2-ESW-A01, PSA1-Q1.3, Cable Manager |
| C | DESCRIPTION | Function + key rating, written "\<rating>, \<poles> MCB For \<load>" for breakers and "Terminal Blocks For \<circuit>" for strips. Devices state LAN, Purdue level and port mix | 2A,2P MCB For L1\_ESW\_A11 PS1 |
| D | QUANTITY | Integer, or "1 Lot". May be a formula when built from a count (SFP qty `=24+3`) | 27 |
| E | MAKE | Manufacturer short name | Ruggedcom, SEL, Schneider |
| F | MODEL | Catalogue model or family; for SFPs and simple parts it equals the ordering code | RST-2228, SEL-3555, UT-2.5-MTD |
| G | ORDERING CODE | Full order string including option suffixes; equal to MODEL when no options. Merged F/G cells allowed over child rows with no code | 6GK6222-6AB00-5CC0-Z A05+B05+C05+D05+E05+F05+G05 |
| H | HWIO (masters only, hidden) | Number of hardwired alarm inputs this row sends to the Axion DI cards. H1 = SUM(H3:Hn) gives the panel's HWIO total | Switch = 1 per unit, AC aux contacts = 3, DC aux contacts = 2 |

Title cell text is two lines: line 1 the cabinet document/tag number, line 2 "\<Substation> - \<Cabinet name>", e.g. "861-GIS01-PSA-0001 / GIS Substation - PSA Cabinet - 001". On masters the panel's HWIO total sits in H1 next to the title.

Project name, document title, supplier document number and revision are not cells; they go in the page header (see Output requirements).

## Tag naming conventions

Device tags follow `<PANEL>-<LEVEL>-<TYPE>-<LAN><NN>`, and every circuit or terminal strip is tagged `<PANEL>-<CIRCUIT CODE>`. The panel prefix is PSA1, PSA2, PSA3 or WS. Rows with quantity > 1 use a range or list in one tag instead of one row per unit.

**Network devices and Purdue levels**

| Level token | Meaning | LAN-A tags (Cabinet 001) | Numbering rule |
| --- | --- | --- | --- |
| L2 | Purdue Level 2 – station/supervisory backbone switch | PSA1-L2-ESW-A01 | LAN letter + 01 |
| L1 | Purdue Level 1 – bay/IED access switches (24 MM FO ports) | PSA1-L1-ESW-A11 to A16 | LAN letter + 11, 12, …; one row, range tag "A11 to A16" |
| EXT | External-systems switch (16 MM + 4 RJ45) | PSA1-EXT-ESW-A | LAN letter only |
| EXT (FW) | Firewall for external systems | PSA1-EXT-FW-A | LAN letter only |
| L2-L3 | Uplink to Level 3 / control room, via single-mode FOPP | PSA1-FOPP-CCR-A01 | CCR = central control room |

LAN-B devices in Cabinet 002 swap the prefix and LAN letter: PSA2-L2-ESW-B01, PSA2-L1-ESW-B11 to B16. Gateways number by LAN: PSA1-DHPCC-GW-1, PSA2-DHPCC-GW-2.

**Other device type codes:** GPS (clock), RTAC (data concentrator), HWIO (Axion IO), IL (lamp), FAN-1,2, TH-1,2,3, IPR (interposing relay), COD-1/-2 (change-over diodes neg/pos), AUX PS (socket), FILTER, MONITOR, SRV/OAS/EAS (workstation).

**Circuit and strip codes**

| Code | Meaning |
| --- | --- |
| CINC | Incoming AC MCB |
| C1, C2 … | AC branch MCBs, in load order: lamp, fan-1+TH-1, fan-2+TH-2, TH-3, socket, spare |
| Q1 / Q2 | DC main MCB, feed 1 / feed 2 |
| Q1.n / Q2.n | DC branch MCB for device PS1 / PS2; same n on both feeds = same device |
| QCOD-n | MCB after the change-over diodes (single-fed loads, e.g. annunciator, monitor) |
| X-AC, X-DC1, X-DC2 | Incoming AC / DC1 / DC2 strips (UT-16) |
| X3-AC, X4-DC1, X4-DC2, X4-COD | AC / DC1 / DC2 / change-over distribution strips (UT-2.5-MTD) |
| TBL, THF, XSD, XPS, X-ANN | Lighting, fan+thermostat, smoke detector, socket, annunciator strips |
| XDIPD…XDIPG, XDIN | Knife-disconnect DI strips per Axion slot D–G, DI negative |
| XRTAC-Cn | RTAC serial COM port n |
| XIP | Inter-panel wiring |

Inside MCB descriptions the load is named without the panel prefix and with underscores: "2A,2P MCB For L1\_ESW\_A11 PS1". SFP rows are tagged by host switch without the panel prefix: "L2-ESW-A01 SFP (SM)".

## Derivation rules: what follows from the devices

Only groups A–C are chosen by the engineer; groups D–H and the HWIO column are almost fully derived from them. These are the rules the example follows, with the observed values so the tool can be tested against this file.

**DC distribution (group F)**

- Every DC-powered device has two supplies, PS1 and PS2. Each gets one 2A 2P branch MCB on feed 1 (Q1.n) and one on feed 2 (Q2.n), with the same n on both feeds.
- n follows group B order, and a multi-quantity row expands to one MCB per unit (6 L1 switches → Q1.2–Q1.7).
- Spare branches are added per feed: 3 in Cabinets 001/002 (10 used), 1 in Cabinet 003 and the WS console. Make spare count a panel input.
- Branch rating: 2A for every device branch. The per-device current with 30% margin (1.3 × W / 125 V) is under 1 A, so 2A acts as a minimum rating.
- Main MCB (Q1/Q2) rating: 16A where the per-feed design current ΣQ ≈ 7.1 A (Cabinets 001/002), 6A where ΣQ ≈ 1.5 A (Cabinet 003, WS). Implement as "next standard size above ΣQ, minimum 6A" with a manual override.
- Single-fed DC loads (annunciator, monitor) are fed through change-over diodes: add COD-1 (neg), COD-2 (pos), QCOD-1 for the load, QCOD-2 spare, and an X4-COD strip.
- DC auxiliary contacts: one per main MCB, plus one per branch whose trip must be alarmed (firewall Q1.10/Q2.10 in 001/002). Qty 4 in 001/002, 2 elsewhere.

**AC distribution (group E)**

- CINC = 6A normally; 16A when the cabinet has a 10A auxiliary socket (Cabinet 002).
- Branches in this order: C1 lamp 1A; C2 fan-1 + TH-1 2A; C3 fan-2 + TH-2 2A; C4 TH-3 1A; socket 10A if present; one 2A spare. The WS console (no fans) has C1 lamp, C2 TH-1, C3 spare, all 1A.
- AC auxiliary contacts: one on CINC and one on each fan circuit (C2, C3) → 3; WS console 1 (CINC only).

**Breaker part numbers.** All MCBs are Schneider Acti9 2-pole, part `A9F742` + 2-digit rating: 1A = A9F74201, 2A = A9F74202, 6A = A9F74206, 10A = A9F74210, 16A = A9F74216. Aux contacts are A9A26924.

**Terminal block quantities (group G)**

| Strip | Type / code | Rule seen in the file | 001 | 002 | 003 | WS |
| --- | --- | --- | --- | --- | --- | --- |
| X-AC | UT-16 / 3044199 | Fixed per cabinet | 6 | 6 | 6 | 4 |
| X3-AC | UT-2.5-MTD / 3064085 | 2 × number of AC MCBs incl. CINC | 12 | 14 | 12 | 8 |
| X-DC1, X-DC2 | UT-16 / 3044199 | Fixed per cabinet, each | 6 | 6 | 6 | 4 |
| X4-DC1, X4-DC2 | UT-2.5-MTD / 3064085 | 2 × (branches per feed + 1), each; rounded up to 32 in network cabinets | 32 | 32 | 10 | 6 |
| TBL | UT-2.5-MTD | Lamp, fixed | 4 | 4 | 4 | 4 |
| THF | UT-2.5-MTD | Fans + thermostats | 12 | 12 | 12 | 5 |
| XSD | UT-2.5-MTD | Smoke detector, fixed | 4 | 4 | 4 | 4 |
| XPS | UT-2.5-MTD | Only if socket | – | 4 | – | – |
| X4-COD | UT-2.5-MTD | Only if change-over diodes | – | – | 8 | 6 |
| X-ANN | UT-2.5-MTD | Annunciator feed | – | – | 4 | – |
| XDIPD–XDIPG | UT-2.5-MT / 3046362 | 58 per Axion DI slot, one row per slot | – | – | 4 × 58 | – |
| XDIN | UT-2.5-MT | DI negative common | – | – | 40 | – |
| XRTAC-C1…C6 | UT-2.5-MT | 5 per RTAC serial port, one row per port | – | – | 6 × 5 | – |
| XIP | UT-2.5-MT (UT-2.5-MTD on WS) | Inter-panel wiring | 40 | 40 | – | 12 |

**Network accessories (group C)**

- FOPP: 96-core SM patch panel → child rows spool (1), splice holder (1), LC SM pigtails (qty = cores, 96).
- SFPs are sized per host switch from its port allocation: L2 switch = 2 × 1000BASE-LX SM for the L3 uplink, 1G MM per 1G downlink, 100BASE-FX MM per 100 Mb device (GPS). L1 switches: 27 × 1000BASE-SX MM, entered as `=24+3` (24 uplink ports + 3 spare). Firewall: 2 MM SFPs.
- Cable managers: 9 per network cabinet (roughly one per rack-mounted switch/patch panel).
- RTAC serial cables (SEL-C607): one per used COM port (6), matching the 6 XRTAC strips.

**Housekeeping kit (group D).** Every cabinet gets lamp + door switch, interposing relay kit (relay, base, suppression module, bracket) for the high-temperature alarm, and either 2 fans + 3 thermostats (forced ventilation) or vent filters + 1 thermostat (natural convection). The choice follows from Heat Calculations.

**HWIO points (hidden column H).** Each row contributes its hardwired alarm inputs: 1 per L2/EXT switch, 1 for the GPS clock, 3 for the AC aux contacts, 2 for the DC aux contacts on the mains. Panel totals in the example are 17, 17 and 6. Summed across panels, they give the hardwired DI count that the Axion DI modules in Cabinet 003 must cover.

## Power Consumption sheet

The sheet lists every powered device once per cabinet, split into a 125 V DC block and a 230 V AC block, and totals each block with a 25% margin. Result in the example: 2,177.5 W DC + 1,090.3 W AC = 3,267.8 W.

**Layout, top to bottom**

1. Per cabinet, in BOM order (Cabinet-1, Cabinet-2, Cabinet-3, Workstation Cabinet): a title row "Power Consumption for \<cabinet>" merged A:L.
2. A "DC LOAD" label (B:C merged), a header row, one row per DC device, then a "TOTAL POWER (W)" row.
3. An "AUX AC LOAD" label, header, one row per AC device, total row.
4. A last block "Power Consumption for External Equipment" for loose items that draw station DC (the annunciator), DC only.
5. "TOTAL POWER CONSUMPTION SUMMARY": 125V DC LOAD, 230V AUX AC LOAD, TOTAL POWER (W); then NOTES (25% margin; datasheet rated values) and a printer footnote.

**Which BOM rows appear:** only rows that draw power. DC block = group B devices (switches, gateway, firewall, GPS, RTAC, Axion, workstation, monitor); FOPP, SFPs, cables and passive parts are excluded. AC block = lamp, fans, thermostats, interposing relay.

**Columns**

| Col | Header | Source |
| --- | --- | --- |
| B | S.NO | 1…n within the block |
| C | POWER SUPPLY | "125V" or "230V" (typed) |
| D | INPUT TYPE | "VDC" or "VAC" |
| E | COMPONENT DESCRIPTION | Reference to master BOM DESCRIPTION, e.g. `='Panel 1'!C8` |
| F | QTY | Reference to BOM QUANTITY |
| G | MAKE | Reference to BOM MAKE |
| H | MODEL NUMBER | Reference to BOM MODEL |
| I | UNIT POWER CONSUMPTION (W) | Typed, from datasheet (device library value) |
| J | TOTAL POWER (W) | `=F*I` |
| K | TYPE OF LOAD | CONTINUOUS (DC devices, annunciator) or INTERMITTENT (AC housekeeping) |
| M–N (hidden), O–R (outside print area) | MCB / COR sizing | See formulas below; header row 6 only |

Print area is A1:L97, so columns M–R never print; they are the engineer's breaker-sizing helper.

**Formulas**

```latex
J = F \times I \qquad \text{Block total} = 1.25 \times \sum J
```

```latex
N = \frac{I}{V} \quad (V = 125 \text{ for DC}, 230 \text{ for AC}) \qquad O = 1.3\,N \qquad P = \lceil O \rceil \qquad Q = O \times F \qquad R = Q
```

- N “Required Load” = per-unit current (A); O = +30%; P = per-device MCB rating; Q = contribution to the main MCB (A); R = continuous current for change-over (COR) diode selection.
- V comes from the device's supply type: 125 for DC loads, 230 for AC loads.
- Summary: DC = sum of every DC block total including External Equipment; AC = sum of the four AC block totals.
- Heat Dissipation reads columns C, D, E, F, G, H, I of this sheet, so this sheet is the single list of powered devices for the whole workbook.

## Heat Dissipation and Heat Calculations sheets

Heat Dissipation converts every powered device to heat with no margin; Heat Calculations uses the cabinet totals to prove the fans (PSA cabinets) or natural convection (WS console) are enough. In the example the PSA cabinets need 391, 391 and 172 m³/h against 716 m³/h fans, and the console rises 6.96 °C, under the 10 °C limit.

**Heat Dissipation layout.** One block per cabinet (Cabinet-1, -2, -3, Workstation, then "PSA Auxiliary Equipment"), each with a title row merged A:L, a header row, one row per powered device (DC rows first, then AC rows, in one table), and a TOTAL row. Then CALCULATIONS and NOTES text: unit heat = W × 3.41; auxiliary equipment is outside the panels and excluded from the fan check.

| Col | Header | Source |
| --- | --- | --- |
| B | S.NO | 1…n |
| C, D | POWER SUPPLY / INPUT TYPE | From Power Consumption C, D |
| E | COMPONENT DESCRIPTION | From Power Consumption E |
| F, G | MAKE, MODEL NUMBER | From Power Consumption G, H |
| H | QTY | From Power Consumption F |
| I | UNIT W | From Power Consumption I |
| J | UNIT HEAT DISSIPATION (BTU/HR) | `=(L*3.41)/H` |
| K | TOTAL HEAT DISSIPATION (BTU/HR) | `=H*J`; total row = SUM |
| L | TOTAL HEAT DISSIPATION (W) | `=I*H`; total row = SUM |

**Heat Calculations – forced ventilation (PSA cabinets 1–3).** Constants sit in the top-right box: TMax = 35 °C, TInt = 25 °C, air constant k = 4.1 m³K/Wh. Per cabinet:

```latex
P_{W} = \frac{\text{Total BTU/h}}{3.41} \qquad \dot V_{req} = \frac{P_{W} \times k}{T_{max} - T_{int}} \;[\text{m}^3/\text{h}]
```

The result is compared with the selected fan throughput (716 m³/h). A combined check then treats the three line-up cabinets as one internally open volume: Σ required = 954.8 m³/h against 3 × 716 = 2,148 m³/h, and prints a pass sentence.

**Heat Calculations – natural convection (WS console).** Heat transfer coefficient for sheet steel = 5.5 W/m²°C. Cabinet H = 1.6 m, W = 0.8 m, D = 0.636 m.

```latex
A = 1.8\,H\,(W + D) + 1.4\,W\,D \qquad \Delta T = \frac{P_{W}}{A \times 5.5}
```

A = 4.848 m² and ΔT = 6.96 °C; because ΔT < 10 °C the sheet concludes natural convection is enough, which is why the console BOM has vent filters and no fans.

**Rule for the tool:** compute both checks for every cabinet. If natural-convection ΔT ≤ (TMax − TInt), specify filters + 1 thermostat; otherwise specify fans whose throughput ≥ required airflow, plus the fan thermostats and their AC branches. That decision feeds back into groups D, E and G of the BOM.

## Relationships between sheets

The workbook is one chain: master BOM → Power Consumption → Heat Dissipation → Heat Calculations, linked by live cell references. The heat check's ventilation choice (fans or filters) is fed back into the BOM, and the issued BOM sheets are copies of the masters for printing.

&#91;embedded content: workbook data flow · 5 sheet groups\]

The panel ↔ power relationship is row-for-row: every powered BOM row has exactly one Power Consumption row that reuses its description, quantity, make and model, and adds only unit watts and supply type. Branch MCB ratings from Power Consumption's sizing columns set the ratings in BOM group F.

## Formatting

The whole workbook uses Calibri, thin black borders on BOM sheets and medium-framed grey-header tables on calculation sheets. Colours come from the Office 2007 theme: grey = Background 1 darkened 35% (≈ #A6A6A6) or 15% (≈ #D9D9D9); dark blue = Text 2 (#1F497D). Sizes below are point sizes; widths are Excel character units; heights are points. Page header and footer content is specified under Output requirements.

**Panel BOM sheets (1–4; masters are the same unless noted)**

| Element | Font | Fill | Alignment | Border | Size |
| --- | --- | --- | --- | --- | --- |
| Title A1:G1 (merged), two lines | 24 bold | #A6A6A6 | Centre / middle, wrap | Thin all sides | Row 90 (masters 66–76) |
| Header row 2 | 20 bold | None | Centre / middle, wrap | Thin | Row 26.25 (53.1 on sheet 4) |
| SR.NO, QUANTITY, MAKE, MODEL, ORDERING CODE | 20 regular | None | Centre / middle; G wraps | Thin | Row 26.25–30 |
| ITEM DESIGNATION | 20 **bold** | None | Left / middle, wrap | Thin | – |
| DESCRIPTION | 20 regular | None | Left / middle, wrap | Thin | – |
| Rows with long order codes (switches) | Same | None | Same | Thin | Row 52.5 |
| Grounding rows (long wrapped text) | Same | White | Left, wrap | Thin | Row 78.75–131.25 |
| Separator row between groups | – | None | – | Thin (row stays boxed) | Same as body |
| Revised cells since last issue | Same | Yellow #FFFF00 | Same | Thin | – |
| Loose-material title (sheet 4, A47:G47) | 24 bold | #A6A6A6 | Centre, wrap | Thin | Row 90 |

Column widths on issued sheets: A 12.29, B 53.71, C 108.71, D 23.14, E 22.29, F 43.43, G 60.57. Masters add H (HWIO) ≈ 23–30 wide, hidden, and a 4.57-wide spacer column.

Merges: A1:G1; a parent tag merged down over its child rows (FOPP B4:B7, IPR kit B22:B25, Axion B6:B10, annunciator + mount B49:B50, GPS accessories B53:B57); F/G merged over child rows with no code (F4:F6, G4:G6); G53:G57 holds "Included with SEL-2488".

Page setup: A4 portrait, fit to page (scale ≈ 29%), centred horizontally; margins left/right 1.0 cm, top 3.0 cm, bottom 2.0 cm; rows 1:2 repeat on every page; page-break preview at 60–70% zoom.

**Calculation sheets (Power Consumption, Heat Dissipation)**

| Element | Font | Fill | Border | Row height |
| --- | --- | --- | --- | --- |
| Cabinet title (merged A:L) | 18 bold, single underline, dark blue | None | None | 23.25 |
| Block label "DC LOAD" / "AUX AC LOAD" (merged B:C) | 15 bold, dark blue | #D9D9D9 | Medium box | 20.25 |
| Table header | 12 bold, dark blue, centred, wrap | #D9D9D9 | Medium outer, thin inner | 32.25 (48 on Heat Dissipation) |
| Data rows | 12 bold black; description left + wrap, others centred | None | Thin inner, medium outer frame | 18.75 |
| TOTAL row (label + value) | 12 bold, dark blue | #D9D9D9 | Medium | 18.75 |
| Summary table (Power Consumption) | 12 bold | Total cell #D9D9D9 | Medium all cells | – |
| Notes / calculation text | 11 regular | None | None | Default |

Number formats: General on Power Consumption; 0.00 on Heat Dissipation heat columns and totals.

Column widths – Power Consumption: A 8.29, B 10.86, C 13.86, D 12, E 65.57, F 7.29, G 25, H 33, I 34.29, J 25.57, K 19.29, L 8.71 (M–N hidden). Heat Dissipation: A 6, B 11.71, C 14, D 10, E 61.71, F 17.86, G 34.86, H 9.71, J 30.29, K 28.57, L 22.71, M 3.57.

Page setup: A4 landscape, scale 49–50%, margins 1.8 cm sides / 1.9 cm top and bottom, print areas A1:L97 and A1:M66.

**Heat Calculations.** Plain 11 pt text laid out as worked equations across columns B–H, no fills. Each cabinet's working is boxed with a medium border; the constants (TMax, TInt, k) sit in a medium-bordered box at J3:L5 and the steel coefficient at I53:M53. Landscape A4 at 78%, print area A1:N70.

## Output requirements

The tool shall write a single Excel workbook in which every printed sheet has a page header and a page footer filled from project and panel data. Header and footer are Excel print headers/footers (Page Layout), not worksheet cells.

**Excel workbook**

| ID | Requirement |
| --- | --- |
| OUT-1 | Output is one .xlsx file (Office Open XML, no macros) that opens in Excel 2016 or later without a repair prompt. |
| OUT-2 | File name is configurable; default `<project doc no.>_PSA_BOM_Rev<rev>.xlsx`. |
| OUT-3 | Sheet order: one BOM sheet per cabinet in panel order (loose material as a second table on the WS console sheet), then Power Consumption, Heat Dissipation, Heat Calculations. Sheet names are configurable. |
| OUT-4 | Each BOM sheet carries the HWIO column hidden, so no separate master sheets are needed. |
| OUT-5 | Calculated cells are live Excel formulas, not pasted values: SR.NO, Power Consumption references to BOM cells, J = F × I, block totals × 1.25, summary sums, Heat Dissipation references and heat formulas, Heat Calculations airflow and ΔT. The workbook is set to recalculate fully on open. |
| OUT-6 | Formatting follows the Formatting section: fonts, fills, borders, column widths, row heights, merges, number formats. |
| OUT-7 | Print setup per sheet: A4, orientation, scale or fit-to-page, margins, print area, repeating title rows 1:2 on BOM sheets, page-break preview view. |
| OUT-8 | Cells changed since the previous revision can be highlighted yellow (#FFFF00) when a revision comparison is requested. |

**Page header (every printed sheet, every page)**

| Zone | BOM sheets | Calculation sheets | Excel code / source |
| --- | --- | --- | --- |
| Left | Company logo | Company logo | `&G` picture; logo file from project settings |
| Centre, line 1 | Project name, Calibri bold 28 pt | Project name, bold | Project settings |
| Centre, line 2 | "Bill of Materials for \<cabinet number>" | "Power Consumption for \<scope>", "Heat Dissipation for \<scope>", "Heat Calculations for \<scope>" | Panel record / sheet type |
| Centre, line 3 | "Supplier Doc # \<BOM doc no.>" | "Supplier Doc # \<calc doc no.>" | Project settings, one number per document |
| Right | "Rev : \<rev>" | "Rev : \<rev>" | Revision of that document |

**Page footer (every printed sheet, every page)**

| Zone | Content | Excel code / source |
| --- | --- | --- |
| Left | Document number | Project settings |
| Centre | "Page \<n> of \<total>" | `Page &P of &N` |
| Right | "Rev \<rev> – \<issue date>" | Revision and issue date from project settings |

- The same header and footer apply to the first page and all following pages (no different first page, no odd/even split).
- Header and footer must fit within the top margin (3.0 cm BOM, 1.9 cm calculations) and bottom margin (2.0 cm BOM, 1.9 cm calculations) so they never overlap the table.
- Page numbering restarts on each sheet.

## Inputs the tool needs

Three input sets rebuild the whole workbook: a device library (one record per part number), a panel definition (which devices go in which cabinet), and project settings (header/footer data and design constants). Everything else in this spec is derived.

**1. Device library – one record per orderable part**

| Field | Why it is needed | Example (L1 switch) |
| --- | --- | --- |
| part\_id | Key used by panels | RST2228-L1-24MM |
| category | Decides BOM group (A–H) and which rules apply | network\_switch |
| make | BOM col E | Ruggedcom |
| model | BOM col F, Power col H | RST-2228 |
| ordering\_code | BOM col G (full option string) | 6GK6222-6AB00-5CC0-Z A05+B05+C05+D05+E05+F05+G05 |
| description\_template | BOM col C, with {lan}, {level} placeholders | LAN-{lan} Industrial Ethernet switch (Level-1) (24 MM FO Ports) |
| tag\_type | Tag building | ESW |
| purdue\_level | Tag + description: L1, L2, EXT, L3 | L1 |
| supply\_type, voltage | Power block (DC/AC) and current calc | VDC, 125 |
| unit\_power\_w | Power and heat sheets | 77 |
| load\_type | Power col K | CONTINUOUS |
| power\_supplies | 2 = dual feed (Q1.n + Q2.n); 1 = via change-over diodes; 0 = passive | 2 |
| min\_branch\_mcb\_a | Branch MCB rating | 2 |
| alarm\_on\_branch\_mcb | Adds DC aux contacts for its branches | false (true for firewall) |
| hwio\_points | Hardwired alarm DIs (col H) per unit | 1 |
| ports | Count and type per port group, for SFP sizing | 24 × 100FX MM fixed; 4 × 1G SFP slots |
| children | Kit parts added as child rows, with qty rule | – (FOPP: spool 1, splice holder 1, pigtails = cores) |
| terminals | Strip code + count per unit it adds | – (DI module: XDIP‹slot› × 58; RTAC port: XRTAC-Cn × 5) |
| loose\_items | Parts shipped loose, not in the panel | – (GPS clock: antenna, LMR-400 cables, surge kit, mount) |
| excluded\_from\_power | True for SFPs, FOPP, cables, passives | false |

The library also holds the commodity catalogues: MCBs by rating (1/2/6/10/16 A → A9F742xx), aux contact, terminal blocks by type (UT-16, UT-2.5-MTD, UT-2.5-MT → order codes), busbars, and housekeeping kits (lamp, fan with m³/h, filter, thermostat with W, IPR kit, change-over diodes, socket).

**2. Panel definition – one record per cabinet**

- Identity: cabinet number (861-GIS01-PSA-0001), cabinet name, tag prefix (PSA1), LAN letter (A/B or none), sheet name and order.
- Enclosure: make, model/code, H × D × W, base frame size, cable entry (top/side).
- Device list in display order: part\_id, quantity, tag override (optional), purpose text (e.g. "for Dhahran PCC connection"), LAN.
- Network port plan for each switch: downlinks by speed and media (feeds SFP counts), uplinks to L3 (SM).
- Options: aux socket (rating), smoke detector, change-over diodes (auto when single-PSU DC loads exist), ventilation mode (auto from heat check, or forced), spare branches per DC feed and on AC, main MCB override, inter-panel terminal count, grounding busbars.
- BOM document data for its page header/footer: supplier document number, revision, issue date.
- Revision: changed rows/cells to highlight yellow.

**3. Project settings**

- Header and footer data: project name, substation name, company logo image, supplier document numbers for Power Consumption, Heat Dissipation and Heat Calculations, revision and issue date per document.
- Output: file name pattern, sheet names.
- Design constants: DC 125 V, AC 230 V, power margin 25%, current factor 1.3, BTU factor 3.41, TMax 35 °C, TInt 25 °C, air constant 4.1 m³K/Wh, steel coefficient 5.5 W/m²°C, minimum main MCB 6 A.
- Loose material extras not tied to a device: HMI software, Office licence, annunciator, cables, patch cords.

## Data model and generation order

Build one BOM sheet per cabinet with the HWIO column hidden, and let the calculation sheets reference those cells with live formulas, so the BOM and the calculations always describe the same equipment.

**Entities**

| Entity | Key fields |
| --- | --- |
| Project | name, substation, logo, doc numbers, revisions, issue dates, output file name, design constants |
| DeviceType (library) | fields listed under Inputs → Device library |
| Panel | number, name, prefix, LAN, enclosure, options, port plans, sheet name and order, BOM doc no. / rev |
| DeviceInstance | panel, device type, qty, display order, tag override, purpose text |
| BomLine (generated) | panel, group A–H, sr\_no, tag, description, qty (value or formula), make, model, ordering\_code, hwio, parent line, merge span, revised flag |
| PowerLine / HeatLine (generated) | panel, block (DC/AC), source BomLine, unit W, load type, V |
| SheetHeaderFooter (generated) | sheet, header left/centre/right, footer left/centre/right |

**Generation order**

1. Expand each panel's device instances into units and build tags from prefix, level, type code, LAN and number.
2. Add each device's child kit rows and loose items.
3. Size network accessories from each switch's port plan: SFPs by speed and media, FOPP pigtails = cores, cable managers.
4. Compute device power, then run the heat checks and choose ventilation (fans + 3 thermostats, or filters + 1).
5. Add the housekeeping kit (lamp, ventilation parts, IPR kit, socket, change-over diodes if any single-supply DC loads).
6. Build AC distribution: CINC, branches in fixed order, spare, aux contacts.
7. Build DC distribution: Q1/Q2 mains, one branch per supply unit, spares, QCOD circuits, aux contacts; size the mains from ΣQ.
8. Build terminal strips from the rules table plus each device's own terminal needs.
9. Add grounding busbars.
10. Sum HWIO per panel and confirm the Axion DI modules cover the total.
11. Number SR.NO, order rows by group A→H with a separator row before groups E, F, G and H, and apply merges for parent/child rows.
12. Generate Power Consumption, Heat Dissipation, Heat Calculations and the loose-material table.
13. Build each sheet's page header and footer from project and panel data.
14. Write the .xlsx with live formulas, the formatting and print setup in this spec, and the headers and footers (Output requirements).
15. Produce a check report: SFP counts against port plans, main MCB ratings against ΣQ, fan airflow against required airflow, DI capacity against HWIO total.
