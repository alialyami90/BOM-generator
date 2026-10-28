"""Expected groups A-D and loose-material rows of the example project.

Rows are (ITEM DESIGNATION, DESCRIPTION, QUANTITY, MAKE, MODEL, ORDERING CODE, HWIO),
columns B-H of "Columns of a panel BOM", transcribed from the example workbook's hidden
master sheets (ADR 0010 item 10; plan Q23: masters, not issued sheets). The trailing
comment is the workbook row. Cell text is trimmed. Where the generator deliberately
differs from the workbook, the value is a named constant explaining why.
"""

from bomgen.models.bom import QtySum

Row = tuple[str | None, str, int | str | QtySum, str | None, str | None, str | None, int]

# One library record has one description: rows 14 of 'Panel 1'/'Panel 2' read
# "1000BASE-X MM SFP (850nm, 500m)" for the same part as row 16 (examples/library.yaml NOTE).
SFP_SX_MM = "1000BASE-SX MM SFP (850nm, <500m)"
# 'Aux'!C7 reads "230V AC, 11W LED Illumination Lamp with Door switch" for the same lamp
# part as the PSA cabinets (examples/library.yaml NOTE).
LAMP = "Illumination Lamp with Door switch, 11W"
# 'Aux'!B3 reads "Panel"; every other enclosure row reads "PANEL" (How each panel BOM
# groups its materials, group A).

PSA_ENCLOSURE = (
    "Cabinet : H2100 x D1000 x W800 mm\nBase Frame: H100 x D950 x W750 mm\nCable Entry: Top Entry"
)
WS_ENCLOSURE = (
    "Cabinet : H1600 x D636 x W800 mm\nBase Frame: H100 x D636 x W800 mm\nCable Entry: Side Entry"
)
GPS_CLOCK = (
    "GPS Clock with Antenna and accessories (SNTP/IRIG-B), 125VDC redundant, "
    "100mbps SFP ports redundant"
)

# Example workbook, 'Panel 1' rows 3-25.
PSA1_A_TO_D: list[Row] = [
    (
        "PANEL",
        PSA_ENCLOSURE,
        1,
        "Rawabi",
        "Fixed Frame",
        "Fixed Frame",
        0,
    ),  # 3
    (
        "PSA1-FOPP-CCR-A01",
        "LC, 96 core SM FOPP for L2-L3 Interface",
        1,
        "Hubbell",
        "FEUR96LCSM",
        "FEUR96LCSM",
        0,
    ),  # 4
    (None, "Fiber Management Spool", 1, "Hubbell", None, None, 0),  # 5
    (None, "Splice Holder", 1, "Hubbell", None, None, 0),  # 6
    (None, "LC Single Mode pigtails", 96, "Hubbell", "FPLCS3SM", "FPLCS3SM", 0),  # 7
    (
        "PSA1-L2-ESW-A01",
        "LAN-A Industrial Ethernet switch (Level-2)",
        1,
        "Ruggedcom",
        "RST-2228",
        "6GK6222-6AB00-5CC0-Z A00+B06+C06+D06+E06+F06+G00",
        1,
    ),  # 8
    (
        "PSA1-L1-ESW-A11 to A16",
        "LAN-A Industrial Ethernet switch (Level-1) (24 MM FO Ports)",
        6,
        "Ruggedcom",
        "RST-2228",
        "6GK6222-6AB00-5CC0-Z A05+B05+C05+D05+E05+F05+G05",
        10,
    ),  # 9
    (
        "PSA1-EXT-ESW-A",
        "LAN-A Industrial Ethernet switch (EXT) (16 MM Ports, 4 RJ45)",
        1,
        "SEL",
        "SEL-2730M",
        "2730M#2CF9",
        1,
    ),  # 10
    (
        "PSA1-DHPCC-GW-1",
        "Protocol Gateway for Dhahran PCC connection",
        1,
        "SEL",
        "SEL-3555",
        "3555#0KVC",
        0,
    ),  # 11
    (
        "PSA1-EXT-FW-A",
        "Industrial Firewall for External Systems",
        1,
        "Fortigate",
        "FGR-60F",
        "FGR-60F",
        0,
    ),  # 12
    (
        "L2-ESW-A01 SFP (SM)",
        "1000BASE-LX SM SFP (1310nm, 10 Km)",
        2,
        "Ruggedcom",
        "6GK6000-8FG52-0AA0",
        "6GK6000-8FG52-0AA0",
        0,
    ),  # 13
    (
        "L2-ESW-A01 SFP (MM)",
        SFP_SX_MM,
        15,
        "Ruggedcom",
        "6GK6000-8FG51-0AA0",
        "6GK6000-8FG51-0AA0",
        0,
    ),  # 14
    (
        "L2-ESW-A01 SFP (MM)",
        "100BASE-FX MM SFP (1310nm, <2km)",
        2,
        "Ruggedcom",
        "6GK6000-8FE51-0AA0",
        "6GK6000-8FE51-0AA0",
        0,
    ),  # 15
    (
        "L1-ESW-A11 to A16 SFP (MM)",
        "1000BASE-SX MM SFP (850nm, <500m)",
        QtySum(parts=(24, 3)),
        "Ruggedcom",
        "6GK6000-8FG51-0AA0",
        "6GK6000-8FG51-0AA0",
        0,
    ),  # 16
    (
        "EXT-FW-A SFP (MM)",
        "Industrial SFP (1Gig, MM)",
        2,
        "Fortigate",
        "FR-TRAN-SX",
        "FR-TRAN-SX",
        0,
    ),  # 17
    (
        "Cable Manager",
        "Brush Type Cable Manager",
        9,
        "Marshcom",
        "PL1U12NEBK",
        "PL1U12NEBK",
        0,
    ),  # 18
    (
        "PSA1-IL",
        "Illumination Lamp with Door switch, 11W",
        1,
        "Rittal",
        "SZ 2500.210, SZ 2500.470",
        "SZ 2500.210, SZ 2500.470",
        0,
    ),  # 19
    (
        "PSA1-FAN-1,2",
        "230V AC Inlet and Exhaust Fan, Throughput: 716 m3/h, 87W",
        2,
        "Rittal",
        "SK 3243.100",
        "SK 3243.100",
        0,
    ),  # 20
    ("PSA1-TH-1,2,3", "Thermostat, 30W", 3, "Rittal", "SK 3110.000", "SK 3110.000", 0),  # 21
    (
        "PSA1-IPR",
        "Interposing Relay for High Temp Alarm",
        1,
        "Phoenix",
        "2903685",
        "2903685",
        0,
    ),  # 22
    (None, "IPR Relay Base", 1, "Phoenix", "2900934", "2900934", 0),  # 23
    (None, "Suppression Module", 1, "Phoenix", "2900944", "2900944", 0),  # 24
    (None, "Retaining Bracket - RIF-RH-2", 1, "Phoenix", "2900954", "2900954", 0),  # 25
]

# Example workbook, 'Panel 2' rows 3-26.
PSA2_A_TO_D: list[Row] = [
    (
        "PANEL",
        PSA_ENCLOSURE,
        1,
        "Rawabi",
        "Fixed Frame",
        "Fixed Frame",
        0,
    ),  # 3
    (
        "PSA2-FOPP-CCR-B01",
        "LC, 96 core SM FOPP for L2-L3 Interface",
        1,
        "Hubbell",
        "FEUR96LCSM",
        "FEUR96LCSM",
        0,
    ),  # 4
    (None, "Fiber Management Spool", 1, "Hubbell", None, None, 0),  # 5
    (None, "Splice Holder", 1, "Hubbell", None, None, 0),  # 6
    (None, "LC Single Mode pigtails", 96, "Hubbell", "FPLCS3SM", "FPLCS3SM", 0),  # 7
    (
        "PSA2-L2-ESW-B01",
        "LAN-B Industrial Ethernet switch (Level-2)",
        1,
        "Ruggedcom",
        "RST-2228",
        "6GK6222-6AB00-5CC0-Z A00+B06+C06+D06+E06+F06+G00",
        1,
    ),  # 8
    (
        "PSA2-L1-ESW-B11 to B16",
        "LAN-B Industrial Ethernet switch (Level-1) (24 MM FO Ports)",
        6,
        "Ruggedcom",
        "RST-2228",
        "6GK6222-6AB00-5CC0-Z A05+B05+C05+D05+E05+F05+G05",
        10,
    ),  # 9
    (
        "PSA2-EXT-ESW-B",
        "LAN-B Industrial Ethernet switch (EXT) (16 MM Ports, 4 RJ45)",
        1,
        "SEL",
        "SEL-2730M",
        "2730M#2CF9",
        1,
    ),  # 10
    (
        "PSA2-DHPCC-GW-2",
        "Protocol Gateway for Dhahran PCC connection",
        1,
        "SEL",
        "SEL-3555",
        "3555#0KVC",
        0,
    ),  # 11
    (
        "PSA2-EXT-FW-B",
        "Industrial Firewall for External Systems",
        1,
        "Fortigate",
        "FGR-60F",
        "FGR-60F",
        0,
    ),  # 12
    (
        "L2-ESW-B01 SFP (SM)",
        "1000BASE-LX SM SFP (1310nm, 10 Km)",
        2,
        "Ruggedcom",
        "6GK6000-8FG52-0AA0",
        "6GK6000-8FG52-0AA0",
        0,
    ),  # 13
    (
        "L2-ESW-B01 SFP (MM)",
        SFP_SX_MM,
        15,
        "Ruggedcom",
        "6GK6000-8FG51-0AA0",
        "6GK6000-8FG51-0AA0",
        0,
    ),  # 14
    (
        "L2-ESW-B01 SFP (MM)",
        "100BASE-FX MM SFP (1310nm, <2km)",
        2,
        "Ruggedcom",
        "6GK6000-8FE51-0AA0",
        "6GK6000-8FE51-0AA0",
        0,
    ),  # 15
    (
        "L1-ESW-B11 to B16 SFP (MM)",
        "1000BASE-SX MM SFP (850nm, <500m)",
        QtySum(parts=(24, 3)),
        "Ruggedcom",
        "6GK6000-8FG51-0AA0",
        "6GK6000-8FG51-0AA0",
        0,
    ),  # 16
    (
        "EXT-FW-B SFP (MM)",
        "Industrial SFP (1Gig, MM)",
        2,
        "Fortigate",
        "FR-TRAN-SX",
        "FR-TRAN-SX",
        0,
    ),  # 17
    (
        "Cable Manager",
        "Brush Type Cable Manager",
        9,
        "Marshcom",
        "PL1U12NEBK",
        "PL1U12NEBK",
        0,
    ),  # 18
    (
        "PSA2-IL",
        "Illumination Lamp with Door switch, 11W",
        1,
        "Rittal",
        "SZ 2500.210, SZ 2500.470",
        "SZ 2500.210, SZ 2500.470",
        0,
    ),  # 19
    (
        "PSA2-FAN-1,2",
        "230V AC Inlet and Exhaust Fan, Throughput: 716 m3/h, 87W",
        2,
        "Rittal",
        "SK 3243.100",
        "SK 3243.100",
        0,
    ),  # 20
    ("PSA2-TH-1,2,3", "Thermostat, 30W", 3, "Rittal", "SK 3110.000", "SK 3110.000", 0),  # 21
    (
        "PSA2-IPR",
        "Interposing Relay for High Temp Alarm",
        1,
        "Phoenix",
        "2903685",
        "2903685",
        0,
    ),  # 22
    (None, "IPR Relay Base", 1, "Phoenix", "2900934", "2900934", 0),  # 23
    (None, "Suppression Module", 1, "Phoenix", "2900944", "2900944", 0),  # 24
    (None, "Retaining Bracket - RIF-RH-2", 1, "Phoenix", "2900954", "2900954", 0),  # 25
    (
        "PSA2-AUX PS",
        "Power Socket for Auxiliary Power Supply",
        1,
        "Legrand",
        "730076",
        "730076",
        0,
    ),  # 26
]

# Example workbook, 'Panel 3' rows 3-20.
PSA3_A_TO_D: list[Row] = [
    (
        "PANEL",
        PSA_ENCLOSURE,
        1,
        "Rawabi",
        "Fixed Frame",
        "Fixed Frame",
        0,
    ),  # 3
    (
        "PSA3-GPS",
        GPS_CLOCK,
        1,
        "SEL",
        "SEL-2488",
        "2488#J544",
        1,
    ),  # 4
    (
        "PSA3-RTAC",
        "PSA RTAC and Data Concentrator for DCS",
        1,
        "SEL",
        "SEL-3555",
        "3555#F2R2",
        0,
    ),  # 5
    ("PSA3-HWIO", "Axion IO and Non-IEC Protocol Gateway", 1, "SEL", "SEL-2240", None, 0),  # 6
    (None, "Chassis/Backpane", 1, "SEL", "SEL-2242", "2242#5DPM", 0),  # 7
    (None, "RTAC", 1, "SEL", "SEL-2241", "2241#4D2J", 0),  # 8
    (None, "Power Coupler (125V DC)", 2, "SEL", "SEL-2243", "224311X0", 0),  # 9
    (None, "Digital Input Module-24DI (125V DC)", 4, "SEL", "SEL-2244-2", "22442424X0", 0),  # 10
    (
        "COM-CABLE",
        "RJ-45 port serial cables for RTAC COM port connection",
        6,
        "SEL",
        "SEL-C607",
        "C607#DM6B",
        0,
    ),  # 11
    (
        "PSA3-IL",
        "Illumination Lamp with Door switch, 11W",
        1,
        "Rittal",
        "SZ 2500.210, SZ 2500.470",
        "SZ 2500.210, SZ 2500.470",
        0,
    ),  # 12
    (
        "PSA3-FAN-1,2",
        "230V AC Inlet and Exhaust Fan, Throughput: 716 m3/h, 87W",
        2,
        "Rittal",
        "SK 3243.100",
        "SK 3243.100",
        0,
    ),  # 13
    ("PSA3-TH-1,2,3", "Thermostat, 30W", 3, "Rittal", "SK 3110.000", "SK 3110.000", 0),  # 14
    (
        "PSA3-IPR",
        "Interposing Relay for High Temp Alarm",
        1,
        "Phoenix",
        "2903685",
        "2903685",
        0,
    ),  # 15
    (None, "IPR Relay Base", 1, "Phoenix", "2900934", "2900934", 0),  # 16
    (None, "Suppression Module", 1, "Phoenix", "2900944", "2900944", 0),  # 17
    (None, "Retaining Bracket - RIF-RH-2", 1, "Phoenix", "2900954", "2900954", 0),  # 18
    (
        "PSA3-COD-1",
        "Change Over Diodes (Negative)",
        1,
        "Ruttonsha",
        "IRND150F12",
        "IRND150F12",
        0,
    ),  # 19
    (
        "PSA3-COD-2",
        "Change Over Diodes (Positive)",
        1,
        "Ruttonsha",
        "IRMD150F12",
        "IRMD150F12",
        0,
    ),  # 20
]

# Example workbook, 'Aux' rows 3-15.
WS_A_TO_D: list[Row] = [
    (
        "PANEL",
        WS_ENCLOSURE,
        1,
        "Rittal",
        "PC 5386.050",
        "PC 5386.050",
        0,
    ),  # 3
    (
        "WS-SRV/OAS/EAS",
        "PSA DA Server/Operator/Engineering Automation Workstation",
        1,
        "SEL",
        "SEL-3355",
        "3355#F5P8",
        0,
    ),  # 4
    ("WS-MONITOR", '23" Desktop Monitor', 1, "Ultraview", "NAP-F23", "NAP-F23-125VDC", 0),  # 5
    (
        "Keyboard & Mouse",
        "Industrial Keyboard & Mouse",
        1,
        "Key-Tek",
        "K-TEK-A420TP-KP-FN-MDT",
        "K-TEK-A420TP-KP-FN-MDT",
        0,
    ),  # 6
    ("WS-IL", LAMP, 1, "Rittal", "SZ 2500.210, SZ 2500.470", "SZ 2500.210, SZ 2500.470", 0),  # 7
    ("WS-FILTER", "Ventilation Filter", 2, "Rittal", "SK 3238.200", "SK 3238.200", 0),  # 8
    ("WS-TH-1", "Thermostat, 30W", 1, "Rittal", "SK 3110.000", "SK 3110.000", 0),  # 9
    (
        "WS-IPR",
        "Interposing Relay for High Temp Alarm",
        1,
        "Phoenix",
        "2903685",
        "2903685",
        0,
    ),  # 10
    (None, "IPR Relay Base", 1, "Phoenix", "2900934", "2900934", 0),  # 11
    (None, "Suppression Module", 1, "Phoenix", "2900944", "2900944", 0),  # 12
    (None, "Retaining Bracket - RIF-RH-2", 1, "Phoenix", "2900954", "2900954", 0),  # 13
    (
        "WS-COD-1",
        "Change Over Diodes (Negative)",
        1,
        "Ruttonsha",
        "IRND150F12",
        "IRND150F12",
        0,
    ),  # 14
    (
        "WS-COD-2",
        "Change Over Diodes (Positive)",
        1,
        "Ruttonsha",
        "IRMD150F12",
        "IRMD150F12",
        0,
    ),  # 15
]

# Example workbook, 'Aux' rows 49-62.
LOOSE: list[Row] = [
    (
        '55" LCD Alarm Annunciator',
        '55" LCD Alarm Annunciator (Touch)  - Wall Mounted',
        1,
        "Ultraview",
        "NAP-K55",
        "NAP-K55",
        0,
    ),  # 49
    (None, "Wall Mount Kit", 1, "Lumi", "LPA37-696", "LPA37-696", 0),  # 50
    (
        "SRV/OAS -HMI Software",
        "Zenon Energy Edition Sever/Client with Editor Studio",
        1,
        "COPADATA",
        "Zenon V12",
        "Zenon V12",
        0,
    ),  # 51
    ("SRV/OAS -MS Office", "Microsoft Office 2021", 1, "MS", "2021", "2021", 0),  # 52
    ("ANN-Display Cable", "Display Cable for Annunciator", 1, None, "10m", "10m", 0),  # 58
    ("ANN-USB Cable", "USB cable for Annunciator", 1, None, "10m", "10m", 0),  # 59
    ("MON-DVI Cable", "DVI Cable for Monitor", 1, None, "3m", "3m", 0),  # 60
    ("MON-USB Cable", "USB Cable for Monitor", 1, None, "3m", "3m", 0),  # 61
    ("FO", "Fiber Optic Patch Cords", "1 Lot", None, None, None, 0),  # 62
    # GPS clock loose items (rows 53-57) follow the project's items (plan Q30).
    (
        "Time Server Accessories",
        "GPS/GLONASS Antenna",
        1,
        "SEL",
        "SEL-9524B",
        "Included with SEL-2488",
        0,
    ),  # 53
    (None, "50 ft (15 Meters) LMR-400 cable", 1, "SEL", "SEL-C961-050", None, 0),  # 54
    (
        None,
        "Gas Tube Coaxial Surge Protector and Mounting Kit",
        1,
        "SEL",
        "915900139",
        None,
        0,
    ),  # 55
    (None, "25 ft (7 Meters) LMR-400 cable", 1, "SEL", "SEL-C961-025", None, 0),  # 56
    (None, "Antenna Pipe-Mounting Kit", 1, "SEL", "915900043", None, 0),  # 57
]
