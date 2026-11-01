"""Expected groups E-H rows of the example project (plan M3).

Rows are (ITEM DESIGNATION, DESCRIPTION, QUANTITY, MAKE, MODEL, ORDERING CODE, HWIO) as in
``expected_groups_a_d.py``, transcribed from the example workbook's master sheets; the
trailing comment is the workbook row. Quantities, makes, models, codes and HWIO are the
workbook's, apart from the fixes of plan Q22. Descriptions are written one way for
every cabinet where the workbook varies its spelling (plan Q34):

- MCBs read "<r>A, 2P MCB For <load>" ('Panel 1'!C28 reads "1A,2P ...", C29 "2A, 2P ...");
  spares read "SPARE" ('Panel 3'!C34 "Spare PS1", 'Aux'!C20 "Spare").
- A terminal strip has one description in every cabinet, the cabinet-001 wording
  without doubled spaces ('Panel 3'!C53 "DC COR Circuits", 'Aux'!C34 "AC Circuits").
- The console's CINC reads "Main Auxiliary AC Supply" ('Aux'!C17 "Non-UPS AC Supply") and
  its branch loads are named by tag ('Aux'!C25 "OAS PS1" for WS-SRV/OAS/EAS).
- Branch loads and plates name devices by their ADR 0030 tags (L2_GPS_A01, EXT_FW_A01), not
  the workbook's (GPS, EXT_FW_A).
- DC branches follow group B order (Derivation rules -> DC distribution): in cabinet 003
  RTAC (row 5) is Q1.2 and HWIO (row 6) Q1.3; the workbook has them the other way round.
"""

from expected_groups_a_d import Row

MCB = "Schneider"
AUX_CONTACT = (MCB, "A9A26924", "A9A26924")
TERMINALS = "Phoenix"
BLOCK_CODES = {"UT-16": "3044199", "UT-2.5-MTD": "3064085", "UT-2.5-MT": "3046362"}

AC_SAFETY_GROUND = (
    "POWER/AC SAFETY GROUNDING BUSBAR - TINNED COPPER\n"
    "For all exposed metal surfaces of cabinets, racks, chassis ground.\n"
    "Wire type: 14AWG, Green with yellow tracer insulation"
)
# 'Panel 1'!C77: trailing space after line 1 trimmed.
INSTRUMENT_GROUND = (
    "INSTRUMENT GROUNDING BUSBAR - TINNED COPPER\n"
    "For all wire shields and DC common\n"
    "Wire type: 14AWG, Green insulation"
)
POWER_GROUND = (
    "Power Safety Grounding Busbar-Tinned Copper\n"
    "Interface: For all exposed metal surfaces of cabinets, racks, and chassis ground.\n"
    "Wire Type: Wire type: min. 14AWG, Green with yellow tracer insulation"
)


def mcb(tag: str, rating: int, load: str) -> Row:
    code = f"A9F742{rating:02d}"  # Breaker part numbers
    return (tag, f"{rating}A, 2P MCB For {load}", 1, MCB, code, code, 0)


def strip(tag: str, circuits: str, qty: int, block: str = "UT-2.5-MTD") -> Row:
    description = circuits if circuits.startswith("Knife") else f"Terminal Blocks For {circuits}"
    return (tag, description, qty, TERMINALS, block, BLOCK_CODES[block], 0)


def busbar(tag: str, description: str) -> Row:
    return (tag, description, 1, None, None, None, 0)


# ADR 0026: one row per panel after the busbars, qty = the panel's tagged group B units.
# The part is A4's NAMEPLATE-0828805 (data/device-db/housekeeping.yaml).
NAMEPLATE = (
    "Device nameplate, white PVC plate 60 x 30 mm, self-adhesive",
    "Phoenix Contact",
    "US-EMLP (60X30)",
    "0828805",
)  # description, make, model, code


def nameplate(qty: int) -> Row:
    description, make, model, code = NAMEPLATE
    return (None, description, qty, make, model, code, 0)


def dc_feed(prefix: str, feed: int, main_a: int, loads: list[str], spares: int) -> list[Row]:
    used = [mcb(f"{prefix}-Q{feed}.{n}", 2, f"{load} PS{feed}") for n, load in enumerate(loads, 1)]
    spare = [
        mcb(f"{prefix}-Q{feed}.{n}", 2, "SPARE")
        for n in range(len(loads) + 1, 1 + len(loads) + spares)
    ]
    return [mcb(f"{prefix}-Q{feed}", main_a, f"Main DC supply-{feed}"), *used, *spare]


def network_cabinet(prefix: str, lan: str, socket: bool) -> list[Row]:
    """Cabinets 001 ('Panel 1' rows 27-77) and 002 ('Panel 2' rows 28-80)."""
    loads = [
        f"L2_ESW_{lan}01",
        *(f"L1_ESW_{lan}{n}" for n in range(11, 17)),
        f"EXT_ESW_{lan}01",
        f"L2_GW_{lan}01",
        f"EXT_FW_{lan}01",
    ]
    ac = [
        mcb(f"{prefix}-CINC", 16 if socket else 6, "Main Auxiliary AC Supply"),
        mcb(f"{prefix}-C1", 1, "Illumination Lamp"),
        mcb(f"{prefix}-C2", 2, "Fan-1 and TH-1"),
        mcb(f"{prefix}-C3", 2, "Fan-2 and TH-2"),
        mcb(f"{prefix}-C4", 1, "TH-3"),
        *([mcb(f"{prefix}-C5", 10, "Aux PS")] if socket else []),
        mcb(f"{prefix}-C{6 if socket else 5}", 2, "SPARE"),
        (None, "AC Auxiliary Contacts (for MCB CINC, C2, C3)", 3, *AUX_CONTACT, 3),
    ]
    dc = [
        *dc_feed(prefix, 1, 16, loads, 3),
        *dc_feed(prefix, 2, 16, loads, 3),
        (None, "DC Auxiliary Contacts (For MCB Q1, Q2, Q1.10, Q2.10)", 4, *AUX_CONTACT, 2),
    ]
    terminals = [
        strip(f"{prefix}-X-AC", "AC Input Circuits", 6, "UT-16"),
        strip(f"{prefix}-X3-AC", "AC Distribution Circuits", 14 if socket else 12),
        strip(f"{prefix}-TBL", "Lighting Circuits", 4),
        strip(f"{prefix}-THF", "Fan and Thermostat Circuits", 12),
        strip(f"{prefix}-XSD", "Smoke Detector", 4),
        # Plan Q22: PSA2-XPS uses 3064085 ('Panel 2'!G72 reads 3064086).
        *([strip(f"{prefix}-XPS", "Power Socket", 4)] if socket else []),
        strip(f"{prefix}-X-DC1", "DC1 Circuits", 6, "UT-16"),
        strip(f"{prefix}-X-DC2", "DC2 Circuits", 6, "UT-16"),
        strip(f"{prefix}-X4-DC1", "DC1 Distribution Circuits", 32),
        strip(f"{prefix}-X4-DC2", "DC2 Distribution Circuits", 32),
        strip(f"{prefix}-XIP", "Interpanel Wiring", 40, "UT-2.5-MT"),
    ]
    grounding = [
        busbar("AC SAFETY POWER-GROUND", AC_SAFETY_GROUND),
        busbar("INSTRUMENT-GROUND", INSTRUMENT_GROUND),
    ]
    return [*ac, *dc, *terminals, *grounding, nameplate(11)]


PSA1_E_TO_H = network_cabinet("PSA1", "A", socket=False)
PSA2_E_TO_H = network_cabinet("PSA2", "B", socket=True)

# 'Panel 3' rows 22-68; plan Q22: the XRTAC strips sit before grounding (rows 65-68).
PSA3_E_TO_H: list[Row] = [
    mcb("PSA3-CINC", 6, "Main Auxiliary AC Supply"),  # 22
    mcb("PSA3-C1", 1, "Illumination Lamp"),  # 23
    mcb("PSA3-C2", 2, "Fan-1 and TH-1"),  # 24
    mcb("PSA3-C3", 2, "Fan-2 and TH-2"),  # 25
    mcb("PSA3-C4", 1, "TH-3"),  # 26
    mcb("PSA3-C5", 2, "SPARE"),  # 27
    (None, "AC Auxiliary Contacts (for MCB CINC, C2, C3)", 3, *AUX_CONTACT, 3),  # 28
    *dc_feed("PSA3", 1, 6, ["L2_GPS_A01", "L2_RTAC_A01", "HWIO"], 1),  # 30-34
    *dc_feed("PSA3", 2, 6, ["L2_GPS_A01", "L2_RTAC_A01", "HWIO"], 1),  # 35-39
    mcb("PSA3-QCOD-1", 2, "Annunciator"),  # 40
    mcb("PSA3-QCOD-2", 2, "SPARE"),  # 41
    (None, "DC Auxiliary Contacts (For MCB Q1, Q2)", 2, *AUX_CONTACT, 2),  # 42
    strip("PSA3-X-AC", "AC Input Circuits", 6, "UT-16"),  # 44
    strip("PSA3-X3-AC", "AC Distribution Circuits", 12),  # 45
    strip("PSA3-TBL", "Lighting Circuits", 4),  # 46
    strip("PSA3-THF", "Fan and Thermostat Circuits", 12),  # 47
    strip("PSA3-XSD", "Smoke Detector", 4),  # 48
    strip("PSA3-X-DC1", "DC1 Circuits", 6, "UT-16"),  # 49
    strip("PSA3-X-DC2", "DC2 Circuits", 6, "UT-16"),  # 50
    strip("PSA3-X4-DC1", "DC1 Distribution Circuits", 10),  # 51
    strip("PSA3-X4-DC2", "DC2 Distribution Circuits", 10),  # 52
    strip("PSA3-X4-COD", "Change-over Circuits", 8),  # 53
    strip("PSA3-X-ANN", "Annunciator Circuits", 4),  # 54
    *(
        strip(
            f"PSA3-XDIP{slot}",
            f'Knife Disconnect Terminal Blocks For Axion "{slot} Slot" (DI)',
            58,
            "UT-2.5-MT",
        )
        for slot in "DEFG"
    ),  # 55-58
    strip("PSA3-XDIN", "Knife Disconnect Terminal Blocks For DI Negative", 40, "UT-2.5-MT"),  # 59
    *(
        (
            "PSA3-XRTAC-C" + str(n),
            "Terminal Blocks for RTAC COM Port",
            5,
            TERMINALS,
            "UT-2.5-MT",
            "3046362",
            0,
        )
        for n in range(1, 7)
    ),  # 60-61, 65-68
    busbar("AC SAFETY POWER-GROUND", AC_SAFETY_GROUND),  # 63
    busbar("INSTRUMENT-GROUND", INSTRUMENT_GROUND),  # 64
    nameplate(3),  # L2_GPS_A01, L2_RTAC_A01, HWIO (ADR 0026, ADR 0030)
]

# 'Aux' rows 17-45. The console's DC rows follow the spec order Q1, Q1.n, Q2, Q2.n
# (the workbook lists Q1, Q2 first, rows 23-24) and its strips the order of the PSA
# cabinets' group G rows (rows 33-43 differ); its HWIO is 0 (plan Q34).
WS_E_TO_H: list[Row] = [
    mcb("WS-CINC", 6, "Main Auxiliary AC Supply"),  # 17
    mcb("WS-C1", 1, "Illumination Lamp"),  # 18
    mcb("WS-C2", 1, "TH-1"),  # 19
    mcb("WS-C3", 1, "SPARE"),  # 20
    (None, "AC Auxiliary Contacts (for MCB CINC)", 1, *AUX_CONTACT, 0),  # 21
    *dc_feed("WS", 1, 6, ["L2_SRV/OAS/EAS_A01"], 1),  # 23, 25-26
    *dc_feed("WS", 2, 6, ["L2_SRV/OAS/EAS_A01"], 1),  # 24, 27-28
    # Plan Q22: the QCOD MCBs are 2 A, A9F74202 ('Aux'!F29:G30 read A9F74201).
    mcb("WS-QCOD-1", 2, "Monitor"),  # 29
    mcb("WS-QCOD-2", 2, "SPARE"),  # 30
    (None, "DC Auxiliary Contacts (For MCB Q1, Q2)", 2, *AUX_CONTACT, 0),  # 31
    strip("WS-X-AC", "AC Input Circuits", 4, "UT-16"),  # 33
    strip("WS-X3-AC", "AC Distribution Circuits", 8),  # 34
    strip("WS-TBL", "Lighting Circuits", 4),  # 42
    strip("WS-THF", "Fan and Thermostat Circuits", 5),  # 43
    strip("WS-XSD", "Smoke Detector", 4),  # 41 ("WS-X-SD")
    strip("WS-X-DC1", "DC1 Circuits", 4, "UT-16"),  # 35
    strip("WS-X-DC2", "DC2 Circuits", 4, "UT-16"),  # 36
    strip("WS-X4-DC1", "DC1 Distribution Circuits", 6),  # 37
    strip("WS-X4-DC2", "DC2 Distribution Circuits", 6),  # 38
    strip("WS-X4-COD", "Change-over Circuits", 6),  # 39
    strip("WS-XIP", "Interpanel Wiring", 12),  # 40
    busbar("POWER-GROUND", POWER_GROUND),  # 45
    nameplate(3),  # L2_SRV/OAS/EAS_A01, MONITOR, Keyboard & Mouse (ADR 0026)
]
