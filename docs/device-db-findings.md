# Research findings to review

The datasheet research turned up places where the example workbook (and so the spec's
example values) disagrees with the manufacturer's data, or where a part could not be
found. None of these is changed anywhere: the library and golden values still follow
the workbook. Each item is a question for Ali unless marked resolved. Details and source links are in the
matching record in `data/device-db/`.

## Could change the power, heat or airflow results

1. **Thermostat SK 3110.000 "30 W" is a switching rating, not a load.** Rittal gives
   30 W as the maximum DC switching capacity of the bimetal contact. The thermostat
   draws nothing itself. The workbook counts 3 × 30 W per PSA cabinet and 30 W in the
   console as AC load and heat. (`SK3110-TH`)
   *Resolved 2026-10-28:* Ali: the example keeps the workbook's 30 W so the golden test
   still reproduces the issued document; library defaults for new projects use 0 W
   (future plan fix).
2. **Fan SK 3243.100 airflow depends on frequency and filters.** Free-blowing it moves
   625 m³/h at 50 Hz and 716 m³/h at 60 Hz, drawing 70 W and 87 W. With one outlet filter
   (SK 3243.200) it moves 405 m³/h at 50 Hz and 460 m³/h at 60 Hz. The heat check compares
   against 716 m³/h, which is the free-blowing 60 Hz figure. (`SK3243-FAN`)
   *Resolved 2026-10-28:* Ali: the example keeps 716 m³/h; library defaults for new
   projects use the with-filter 60 Hz figure, 460 m³/h per fan-and-filter unit, and do not
   add an inlet/exhaust pair together (future plan fix).
3. **Several device wattages are not published.** SEL gives no typical power for the
   SEL-3555 (62 W and 73 W in the workbook) or the Axion system (31 W). For the SEL-2488
   it gives under 45 W per power supply, not 50 W total. For the SEL-3355 it gives only the
   supply rating (189 W continuous). The NAP-K55 lists 100 W typical but its 125 V DC module
   is rated 150 W. The workbook values are kept. (`SEL-3555-*`, `SEL-2240`, `SEL-2488`,
   `SEL-3355`, `NAP-K55`)

## Ordering codes and quantities

4. **RST2228 L1 option `A05` is not valid.** Option A only sets the service panel position
   (A00 front, A01 rear). The L2 switch uses A00. Verify on the cited Siemens page before
   acting. (`RST2228-L1-24MM`)
5. **FPLCS3SM pigtails come as 6-fibre bundles.** Hubbell lists FPLCS3SM as a 3 m bundle of
   6 OS2 LC pigtails, so a 96-fibre panel needs 16, not 96. (`FOPP-PIGTAIL-LC-SM`)
6. **Phoenix 3064086 does not exist.** PSA2-XPS uses it. It is almost certainly a typo for
   3064085 (UT 2,5-MTD). Already decided in `examples/README.md` (plan Q22).
   (`TB-UT-2.5-MTD`)
7. **UT 2,5-MTD is a feed-through block, not a knife-disconnect.** Phoenix lists 3064085 as a
   feed-through terminal block (24 A, 800 V). Only UT 2,5-MT (3046362) is a knife-disconnect
   block. The BOM uses each in the right place, but the wording in descriptions should match.
   This reading may be the wrong way round; verify on the cited Phoenix pages before acting.
   (`TB-UT-2.5-MTD`, `TB-UT-2.5-MT`)
8. **Vent filter SK 3238.200 fits the small 148.5 mm fan range.** It is right only if the
   console has an SK 3238.100 fan. As the outlet for an SK 3243.100 fan the part is
   SK 3243.200. (`SK3238-FILTER`)
9. **SEL-2488 ports are fixed fibre, not SFP.** SEL describes fixed 100BASE-FX/LX10 LC ports
   ordered in pairs. The BOM description says "100mbps SFP ports". (`SEL-2488`)
10. **SEL-2730M redundant supply is an option.** Check that `2730M#2CF9` includes the second
    power supply, since the cabinet feeds it from Q1 and Q2. (`SEL-2730M-EXT`)

## Ratings to check

11. **Legrand 730076 is a wall socket, not a DIN-rail socket.** It is a Synergy 2-gang
    13 A switched BS 1363 socket outlet. It needs a 2-gang back box or mounting plate in
    the cabinet, and its rating is 13 A where the BOM sizes a 10 A circuit. (`SOCKET-730076`)

12. **Acti9 iC60N on 125 V DC.** Schneider rates the 2P iC60N at 10 kA up to 125 V DC
    (IEC 60947-2). A 125 V station battery's float and boost voltage is typically above
    125 V (check the project's battery data; no source was found for a figure).
    The high tier of each MCB alternative is a DC-rated (UC) range for this reason.
    (`MCB-*`)
13. **Interposing relay 2903685 is a 230 V AC relay with gold contacts.** It is
    REL-IR4/L-230AC/4X21AU: four changeover contacts, 1.5 W coil. Gold contacts are rated
    50 mA / 30 V while the gold is intact. That suits a DI input, but not switching
    125 V DC loads. (`IPR-2903685`)
14. **Annunciator wall mount LPA37-696 is rated for 60–100 inch screens.** The annunciator
    is 55 inch. Load (80 kg) and VESA 600 × 400 fit. Peerless-AV SA771PU (50–90 inch,
    90.7 kg, up to VESA 800 × 400) is a closer fit. (`LPA37-696`)
15. **NAP-F23 has HDMI and VGA as standard; DVI-D is an option.** The loose material lists
    a DVI cable. An HDMI-to-DVI-D cable (StarTech HDDVIMM3M, Lindy 36273) or an HDMI cable
    avoids ordering the option. (`NAP-F23`, `MON-DVI-CABLE-3M`)
16. **No alternative display takes 125 V DC.** The Advantech and Siemens monitors run on
    12/24 V DC and the 55 inch alternatives on 100–240 V AC, so each needs a DC-DC converter
    or inverter. (`NAP-F23`, `NAP-K55`)
17. **Neither display is IEC 61850-3 or IEEE 1613 rated**, and both run 0 to 55 °C.
    The SEL-3555 literature lists no IEC 61850-3 / IEEE 1613 type tests either, unlike the
    SEL-3355 and SEL-2488. (`NAP-F23`, `NAP-K55`, `SEL-3555-*`)
18. **SZ 2500.210 lamp has a Schuko socket outlet.** Saudi sites use BS 1363. (`SZ2500-LAMP`)

19. **Some alternatives are discontinued.** Meinberg LANTIME M300, Arbiter 1088B and the
    Arbiter AS0087800 antenna are discontinued, so their successors are listed instead.

## Software

20. **Office 2021 support ended on 13 Oct 2026.** Office LTSC 2024 is the current
    perpetual release. (`MS-OFFICE-2021`)
21. **zenon 12 is from 2023; zenon 15 is current.** Check whether V12 is a project
    requirement. (`ZENON-V12`)

## Parts that could not be found online

- **Rawabi "Fixed Frame" cabinet**: no product data online, so only alternatives are given.
- **Hubbell FEUR96LCSM**: the FEUR enclosure family exists, but not this exact code.
- **Marshcom PL1U12NEBK**: neither the brand nor the part number was found.
- **Ruttonsha IRND150F12 / IRMD150F12**: no datasheet online (Ruttonsha is now RIR Power
  Electronics). Ratings are inferred from the matching Semikron SKND/SKMD 150F12 parts.
- **SEL configured codes** (`#xxxx`, e.g. 3555#0KVC) are configuration hashes; SEL does not
  publish how to decode them. The options need the SEL quote or configurator.
