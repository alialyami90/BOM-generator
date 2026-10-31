"""Power Consumption rows (spec: Power Consumption sheet -> Which BOM rows appear,
Columns, Formulas; Data model and generation order, step 4)."""

import pytest
from engine_factories import device, library, powered

from bomgen.engine.errors import EngineError
from bomgen.engine.power import cabinet_power, external_power, power_consumption
from bomgen.models.bom import BomLine, Group, LooseTable, PanelBom
from bomgen.models.library import LoadType, SupplyType
from bomgen.models.project import DesignConstants

LIB = library(
    powered("SW", "network_switch", unit_power_w=77),
    device("SFP", "sfp"),
    device(
        "FAN-AC",
        "fan",
        supply_type="VAC",
        voltage_v=230,
        unit_power_w=87,
        load_type="INTERMITTENT",
    ),
    powered("ANN", "annunciator", power_supplies=1, unit_power_w=100),
)


def bom(*lines: BomLine) -> PanelBom:
    return PanelBom(title=("t", "t"), lines=lines, panel_id="psa1", sheet_name="1")


def line(part_id: str | None, group: Group, qty: int = 1) -> BomLine:
    return BomLine(group=group, description=str(part_id), qty=qty, part_id=part_id)


def test_only_powered_rows_appear_dc_then_ac_in_bom_order() -> None:
    table = bom(
        line(None, Group.A),
        line("SW", Group.B, 6),
        line("SFP", Group.C, 27),
        line("FAN-AC", Group.D, 2),
    )
    cabinet = cabinet_power(table, LIB, DesignConstants())
    assert cabinet.dc is not None
    assert cabinet.ac is not None
    assert [(p.source.line, p.qty, p.unit_w, p.voltage_v) for p in cabinet.dc.lines] == [
        (1, 6, 77, 125)
    ]
    assert [(p.source.line, p.supply_type, p.load_type) for p in cabinet.ac.lines] == [
        (3, SupplyType.VAC, LoadType.INTERMITTENT)
    ]
    assert cabinet.dc.total_w == pytest.approx(6 * 77 * 1.25)


def test_a_part_without_a_voltage_takes_the_system_voltage() -> None:
    lib = library(powered("SW", "network_switch", voltage_v=None, unit_power_w=77))
    constants = DesignConstants(dc_voltage_v=110)
    cabinet = cabinet_power(bom(line("SW", Group.B)), lib, constants)
    assert cabinet.dc is not None
    assert cabinet.dc.lines[0].voltage_v == 110


def test_a_part_with_its_own_voltage_is_drawn_at_that_voltage() -> None:
    # ADR 0028: Power Consumption divides by the voltage the branch MCB is sized at.
    lib = library(
        powered(
            "GW", "gateway", supply_type="VAC", voltage_v=120, unit_power_w=73, power_supplies=0
        )
    )
    cabinet = cabinet_power(bom(line("GW", Group.B)), lib, DesignConstants())
    assert cabinet.ac is not None
    assert (cabinet.ac.lines[0].voltage_v, cabinet.ac.lines[0].supply_label) == (120, "120V")


C_CURVE = {"trip_curve": "C", "magnetic_trip_multiple": 5}


def test_p_is_the_rating_of_the_rows_own_branch_mcb() -> None:
    # ADR 0028: 12 A inrush / 5 = 2.4 A -> the 6 A branch group F prints, not ROUNDUP(O).
    lib = library(powered("GW", "gateway", unit_power_w=73, inrush_a=12), mcb=C_CURVE)
    cabinet = cabinet_power(bom(line("GW", Group.B, 2)), lib, DesignConstants())
    assert cabinet.dc is not None
    assert (cabinet.dc.lines[0].branch_mcb_a, cabinet.dc.lines[0].device_mcb_a) == (6, 6)


def test_p_of_a_running_current_row_is_the_floor() -> None:
    cabinet = cabinet_power(bom(line("SW", Group.B)), LIB, DesignConstants())
    assert cabinet.dc is not None
    assert cabinet.dc.lines[0].branch_mcb_a == 2  # min_branch_mcb_a, as Q1.n prints


def test_p_of_a_vac_device_is_its_ac_branch_rating() -> None:
    lib = library(
        powered(
            "GW", "gateway", supply_type="VAC", voltage_v=230, unit_power_w=73, power_supplies=0
        )
    )
    cabinet = cabinet_power(bom(line("GW", Group.B)), lib, DesignConstants())
    assert cabinet.ac is not None
    assert cabinet.ac.lines[0].branch_mcb_a == 2  # ADR 0025, the AC catalogue floor


def test_housekeeping_on_a_shared_circuit_has_no_branch_rating() -> None:
    cabinet = cabinet_power(bom(line("FAN-AC", Group.D, 2)), LIB, DesignConstants())
    assert cabinet.ac is not None
    assert cabinet.ac.lines[0].branch_mcb_a is None
    assert cabinet.ac.lines[0].device_mcb_a == 1  # P stays ROUNDUP(O)


def test_a_loose_load_fed_from_a_panel_takes_its_qcod_rating() -> None:
    loose = LooseTable(title=("t", "t"), lines=(line("ANN", Group.B),), host_panel="ws")
    fed = external_power(loose, LIB, DesignConstants(), fed={"ANN"})
    unfed = external_power(loose, LIB, DesignConstants())
    assert fed is not None
    assert unfed is not None
    assert (fed.lines[0].branch_mcb_a, unfed.lines[0].branch_mcb_a) == (2, None)


def test_cabinet_without_ac_loads_has_no_ac_block() -> None:
    assert cabinet_power(bom(line("SW", Group.B)), LIB, DesignConstants()).ac is None


def test_external_block_holds_dc_loose_loads_at_125v() -> None:
    # plan Q22: the External Equipment row divides by 125 V.
    loose = LooseTable(
        title=("t", "t"), lines=(line("ANN", Group.B), line("SFP", Group.B)), host_panel="ws"
    )
    block = external_power(loose, LIB, DesignConstants())
    assert block is not None
    assert [(p.source.panel_id, p.source.line, p.voltage_v) for p in block.lines] == [
        (None, 0, 125)
    ]
    assert block.total_w == 125


def test_summary_sums_dc_blocks_with_external_and_ac_blocks() -> None:
    table = bom(line("SW", Group.B), line("FAN-AC", Group.D))
    loose = LooseTable(title=("t", "t"), lines=(line("ANN", Group.B),), host_panel="ws")
    power = power_consumption([table, table], loose, LIB, DesignConstants())
    assert power.dc_total_w == pytest.approx(2 * 77 * 1.25 + 125)
    assert power.ac_total_w == pytest.approx(2 * 87 * 1.25)
    assert power.total_w == pytest.approx(power.dc_total_w + power.ac_total_w)


def test_lot_quantity_on_a_powered_row_is_an_error() -> None:
    table = bom(BomLine(group=Group.B, description="x", qty="1 Lot", part_id="SW"))
    with pytest.raises(EngineError, match="1 Lot"):
        cabinet_power(table, LIB, DesignConstants())
