"""Step 15 check report (spec: Data model and generation order, step 15; plan M7, Q3)."""

import json
from typing import Any

import pytest
from engine_factories import device, library, panel, powered, switch

from bomgen.checks import (
    branch_mcb_checks,
    dc_float_checks,
    dc_main_checks,
    di_capacity_check,
    duplicate_tag_checks,
    external_ac_checks,
    l2_link_checks,
    library_check,
    part_number_checks,
    render_json,
    render_text,
    sfp_slot_checks,
    ventilation_checks,
)
from bomgen.engine.units import expand_devices
from bomgen.library_store.store import LibraryRef
from bomgen.models.bom import BomLine, Group, LooseTable, PanelBom
from bomgen.models.calc import (
    BranchMcb,
    CabinetThermal,
    DcMains,
    ForcedVentCheck,
    HeatResult,
    LineUpCheck,
    NaturalConvCheck,
)
from bomgen.models.library import CatalogueChoice, resolve_catalogues
from bomgen.models.panel import Ventilation
from bomgen.models.project import DesignConstants
from bomgen.models.report import CheckItem, CheckReport, CheckStatus
from bomgen.models.substation import Equipment

SLOTTED = switch(
    "SW",
    "L2",
    ports=[
        {"count": 2, "speed": "1G", "kind": "sfp_slot"},
        {"count": 2, "speed": "100M", "kind": "sfp_slot"},
        {"count": 4, "speed": "1G", "media": "RJ45", "kind": "fixed"},
    ],
)
NO_INVENTORY = powered("FW", "firewall", tag_type="FW", purdue_level="EXT")
SFPS = (
    device("SFP-1G", "sfp", ports=[{"count": 1, "speed": "1G", "media": "MM", "kind": "fixed"}]),
    device(
        "SFP-100M", "sfp", ports=[{"count": 1, "speed": "100M", "media": "MM", "kind": "fixed"}]
    ),
)


def sfp_items(part_id: str, *allocations: dict[str, object], qty: int = 1) -> list[CheckItem]:
    plan = {"downlinks": list(allocations)}
    p = panel([{"part_id": part_id, "qty": qty}], port_plans={part_id: plan})
    lib = library(SLOTTED, NO_INVENTORY, *SFPS)
    return sfp_slot_checks(p, expand_devices(p, lib))


def mm(count: int, speed: str = "1G", spare: int = 0) -> dict[str, object]:
    return {"count": count, "speed": speed, "media": "MM", "spare": spare}


def test_sfps_within_the_hosts_slots_pass() -> None:
    (item,) = sfp_items("SW", mm(2), mm(2, "100M"))
    assert (item.check, item.status, item.subject) == (
        "sfp_slots",
        CheckStatus.PASS,
        "PSA1-L2-ESW-A01",
    )
    assert item.values == {"sfps": 4, "slots": 4}


def test_slower_sfps_may_use_faster_slots() -> None:
    (item,) = sfp_items("SW", mm(1), mm(3, "100M"))
    assert item.status is CheckStatus.PASS


def test_faster_sfps_need_slots_of_their_speed() -> None:
    (item,) = sfp_items("SW", mm(3), mm(1, "100M"))
    assert item.status is CheckStatus.FAIL
    assert "1G" in item.message


def test_spare_sfps_are_not_fitted() -> None:
    (item,) = sfp_items("SW", mm(2, spare=3), mm(2, "100M"))
    assert item.status is CheckStatus.PASS


def test_rj45_allocations_take_no_slot() -> None:
    rj45 = {"count": 4, "speed": "1G", "media": "RJ45"}
    (item,) = sfp_items("SW", mm(2), rj45)
    assert item.values == {"sfps": 2, "slots": 4}


def test_slots_scale_with_the_rows_units() -> None:
    (item,) = sfp_items("SW", mm(4), qty=2)
    assert item.status is CheckStatus.PASS


def test_host_without_port_inventory_is_a_warning() -> None:
    (item,) = sfp_items("FW", mm(2))
    assert item.status is CheckStatus.WARN


def test_main_below_design_current_fails() -> None:
    (item,) = dc_main_checks(
        [DcMains(panel_id="p", design_current_a=7.1, rating_a=6, rule_rating_a=6)]
    )
    assert item.status is CheckStatus.FAIL


def test_main_override_differing_from_the_rule_is_a_warning() -> None:
    # Plan Q3: the example sets 16 A where the rule gives 10 A for sum Q = 7.1 A.
    (item,) = dc_main_checks(
        [DcMains(panel_id="p", design_current_a=7.1, rating_a=16, rule_rating_a=10)]
    )
    assert item.status is CheckStatus.WARN
    assert "16 A" in item.message
    assert "10 A" in item.message


def test_main_by_the_rule_passes_and_panels_without_dc_are_skipped() -> None:
    mains = [
        DcMains(panel_id="p", design_current_a=1.5, rating_a=6, rule_rating_a=6),
        DcMains(panel_id="q", design_current_a=0, rating_a=0, rule_rating_a=0),
    ]
    assert [item.status for item in dc_main_checks(mains)] == [CheckStatus.PASS]


def branch(rating: int, set_by: tuple[str, ...], **fields: object) -> BranchMcb:
    values: dict[str, object] = {
        "panel_id": "p",
        "tag": "PSA1-Q1.1",
        "load": "L2_ESW_A01 PS1",
        "rating_a": rating,
        "running_a": 0.8,
        "floor_a": 2,
        "set_by": set_by,
    }
    return BranchMcb.model_validate(values | fields)


def test_each_branch_mcb_reports_the_numbers_behind_it() -> None:
    (item,) = branch_mcb_checks(
        [branch(6, ("inrush",), inrush_a=12, trip_multiple=5, inrush_need_a=2.4)]
    )
    assert (item.check, item.status, item.subject) == ("branch_mcb", CheckStatus.PASS, "PSA1-Q1.1")
    assert item.message == (
        "6 A for L2_ESW_A01 PS1: running 0.80 A, inrush 12 A / 5 = 2.40 A, floor 2 A; set by inrush"
    )
    assert item.values == {
        "rating_a": 6,
        "running_a": 0.8,
        "inrush_a": 12,
        "trip_multiple": 5,
        "inrush_need_a": 2.4,
        "floor_a": 2,
        "set_by": "inrush",
    }


def test_a_higher_library_min_branch_mcb_a_is_a_warning() -> None:
    (item,) = branch_mcb_checks([branch(2, ("floor",), library_min_a=6)])
    assert item.status is CheckStatus.WARN
    assert "min_branch_mcb_a 6 A is no longer used (plan Q35)" in item.message
    assert "inrush" not in item.message  # no inrush figure: condition (b) does not apply


def test_no_inrush_figure_passes_without_a_warning() -> None:
    (item,) = branch_mcb_checks([branch(2, ("floor",))])
    assert item.status is CheckStatus.PASS
    assert item.message == "2 A for L2_ESW_A01 PS1: running 0.80 A, floor 2 A; set by floor"


def test_a_short_inrush_is_reported_as_too_short_to_trip() -> None:
    (item,) = branch_mcb_checks(
        [branch(2, ("floor",), inrush_a=40, inrush_ms=2, trip_multiple=5, inrush_counted=False)]
    )
    assert item.status is CheckStatus.PASS
    assert "inrush 40 A for 2 ms, too short to trip" in item.message
    assert item.values["inrush_ms"] == 2


def test_inrush_the_catalogue_cannot_check_is_a_warning() -> None:
    (item,) = branch_mcb_checks([branch(2, ("floor",), inrush_a=12)])
    assert item.status is CheckStatus.WARN
    assert "inrush 12 A, but the MCB catalogue has no trip curve" in item.message


def float_items(
    mcb: dict[str, object] | None = None, *parts: dict[str, object], dc: bool = True
) -> list[CheckItem]:
    lib = library(*parts, mcb=mcb)
    lines = [
        BomLine(
            group=Group.B, description=str(part["part_id"]), qty=1, part_id=str(part["part_id"])
        )
        for part in parts
    ]
    mains = [DcMains(panel_id="p1", design_current_a=1.0, rating_a=6 if dc else 0, rule_rating_a=6)]
    return dc_float_checks([bom(*lines)], mains, lib, DesignConstants())


def test_mcbs_rated_below_the_float_voltage_warn() -> None:
    # iC60N 2P: 125 V DC against the 140 V battery float, one item for the catalogue.
    (item,) = float_items({"dc_rating_v": 125})
    assert (item.check, item.status, item.subject) == ("dc_float", CheckStatus.WARN, "Acti9 2P")
    assert item.values == {"dc_rating_v": 125, "dc_float_v": 140}
    assert "125 V DC" in item.message
    assert "140 V float" in item.message


def test_mcbs_rated_for_the_float_voltage_pass() -> None:
    (item,) = float_items({"dc_rating_v": 250})
    assert item.status is CheckStatus.PASS


def test_mcbs_without_a_dc_rating_cannot_be_checked() -> None:
    (item,) = float_items(None)
    assert item.status is CheckStatus.WARN
    assert "no dc_rating_v" in item.message


def test_float_check_names_the_mcb_dc_choice() -> None:
    # ADR 0023: the DC set is checked against the float, not the AC set.
    dc_set = {
        "id": "c60h-dc",
        "family": "C60H-DC 2P",
        "make": "Schneider",
        "ratings_a": [2, 4, 10, 16],
        "code_pattern": "MGN61{rating:03d}",
        "dc_rating_v": 250,
    }
    lib = resolve_catalogues(
        library(mcb={"dc_rating_v": 125}, mcb_brands=[dc_set]), CatalogueChoice(mcb_dc="c60h-dc")
    )
    mains = [DcMains(panel_id="p1", design_current_a=1.0, rating_a=10, rule_rating_a=10)]
    (item,) = dc_float_checks([bom()], mains, lib, DesignConstants())
    assert (item.status, item.subject) == (CheckStatus.PASS, "C60H-DC 2P")
    assert item.values == {"dc_rating_v": 250, "dc_float_v": 140}


def test_no_dc_feeds_no_mcb_float_check() -> None:
    assert float_items({"dc_rating_v": 125}, dc=False) == []


def test_dc_fed_devices_below_the_float_voltage_warn() -> None:
    low = powered("LOW", "rtac", input_v_min=88, input_v_max=137)
    wide = powered("WIDE", "rtac", input_v_min=88, input_v_max=300)
    unknown = powered("UNK", "rtac")
    ac = powered("AC", "rtac", supply_type="VAC", voltage_v=230, input_v_max=100, power_supplies=0)
    items = float_items({"dc_rating_v": 250}, low, wide, unknown, ac)[1:]
    assert [(i.subject, i.status) for i in items] == [
        ("LOW", CheckStatus.WARN),
        ("WIDE", CheckStatus.PASS),
    ]
    assert items[0].values == {"input_v_max": 137, "dc_float_v": 140}


def thermal(
    panel_id: str, ventilation: Ventilation, required: float, delta_t: float
) -> CabinetThermal:
    return CabinetThermal(
        panel_id=panel_id,
        ventilation=ventilation,
        forced=ForcedVentCheck(panel_id=panel_id, heat_w=1, required_m3h=required, fan_m3h=716),
        natural=NaturalConvCheck(
            panel_id=panel_id,
            heat_w=1,
            h_m=2,
            w_m=1,
            d_m=1,
            area_m2=8,
            delta_t_c=delta_t,
            limit_c=10,
        ),
    )


def test_ventilation_checks_use_the_chosen_ventilation() -> None:
    heat = HeatResult(
        dissipation=(),
        cabinets=(
            thermal("psa1", Ventilation.FORCED, 391, 22),
            thermal("ws", Ventilation.NATURAL, 76, 6.96),
            thermal("hot", Ventilation.FORCED, 800, 30),
            thermal("warm", Ventilation.NATURAL, 200, 12),
        ),
        line_up=LineUpCheck(panel_ids=("psa1", "hot"), required_m3h=1191, fan_m3h=1432),
    )
    items = ventilation_checks(heat)
    assert [(i.check, i.panel_id, i.status) for i in items] == [
        ("airflow", "psa1", CheckStatus.PASS),
        ("natural_convection", "ws", CheckStatus.PASS),
        ("airflow", "hot", CheckStatus.FAIL),
        ("natural_convection", "warm", CheckStatus.FAIL),
        ("line_up", None, CheckStatus.PASS),
    ]


DI_CARD = device("DI-24", di_inputs=24)


def bom(*lines: BomLine) -> PanelBom:
    return PanelBom(panel_id="p1", sheet_name="1", title=("001", "S - P"), lines=lines)


def di_lines(cards: int, hwio: int) -> PanelBom:
    return bom(
        BomLine(group=Group.B, description="DI card", qty=cards, part_id="DI-24"),
        BomLine(group=Group.B, tag="IED", description="IED", qty=1, hwio=hwio),
    )


def test_di_capacity_covers_the_hwio_total() -> None:
    item = di_capacity_check([di_lines(2, 30), di_lines(0, 18)], library(DI_CARD))
    assert item is not None
    assert (item.check, item.status) == ("di_capacity", CheckStatus.PASS)
    assert item.values == {"di_inputs": 48, "hwio": 48}


def test_di_capacity_below_the_hwio_total_fails() -> None:
    item = di_capacity_check([di_lines(2, 49)], library(DI_CARD))
    assert item is not None
    assert item.status is CheckStatus.FAIL


def test_hwio_without_di_inputs_in_the_library_is_a_warning() -> None:
    item = di_capacity_check([di_lines(2, 10)], library(device("DI-24")))
    assert item is not None
    assert item.status is CheckStatus.WARN


def test_no_hwio_and_no_di_inputs_is_not_checked() -> None:
    assert di_capacity_check([di_lines(0, 0)], library(DI_CARD)) is None


def test_library_version_mismatch_is_a_warning() -> None:
    recorded = LibraryRef(name="lib", version="1.0.0")
    item = library_check(recorded, LibraryRef(name="lib", version="1.1.0"))
    assert item.status is CheckStatus.WARN
    assert "1.1.0" in item.message
    assert library_check(recorded, recorded).status is CheckStatus.PASS


def test_report_fails_on_any_failed_check() -> None:
    ok = CheckItem(check="x", status=CheckStatus.PASS, message="fine")
    bad = CheckItem(check="y", status=CheckStatus.FAIL, message="broken")
    warn = CheckItem(check="z", status=CheckStatus.WARN, message="look")
    assert not CheckReport(items=(ok, warn)).failed
    assert CheckReport(items=(ok, bad)).failed


def test_text_and_json_rendering() -> None:
    report = CheckReport(
        items=(
            CheckItem(check="dc_main", status=CheckStatus.PASS, panel_id="psa3", message="6 A"),
            CheckItem(check="airflow", status=CheckStatus.FAIL, panel_id="hot", message="short"),
        )
    )
    text = render_text(report)
    assert "PASS  psa3  dc_main  6 A" in text
    assert "FAIL  hot  airflow  short" in text
    assert text.rstrip().endswith("1 failed, 0 warnings, 1 passed")
    data = json.loads(render_json(report))
    assert data["failed"] is True
    assert data["items"][1] == {
        "check": "airflow",
        "status": "fail",
        "panel_id": "hot",
        "subject": None,
        "message": "short",
        "values": {},
    }


@pytest.mark.parametrize("status", list(CheckStatus))
def test_every_status_renders(status: CheckStatus) -> None:
    item = CheckItem(check="c", status=status, message="m")
    assert status.value.upper() in render_text(CheckReport(items=(item,)))


def test_a_device_without_a_part_number_warns() -> None:
    lib = library(powered("NOCODE", "rtac", ordering_code=None), powered("CODED", "rtac"))
    equipment = [
        Equipment(id="a", part_id="NOCODE", role="other"),
        Equipment(id="b", part_id="NOCODE", role="other", ordering_code="PN-1"),
        Equipment(id="c", part_id="CODED", role="other"),
        Equipment(id="l1", role="l1_switch", redundant=True),
    ]
    assert part_number_checks(equipment, lib) == [
        CheckItem(
            check="part_number",
            status=CheckStatus.WARN,
            subject="a",
            message="no part number; the BOM prints the library model",
        )
    ]


def loose_line(part: str) -> BomLine:
    return BomLine(group=Group.B, description=part, qty=2, part_id=part)


def test_an_ac_loose_load_is_reported_as_left_out_of_the_totals() -> None:
    # Power Consumption: External Equipment holds station DC loads only, so an AC loose
    # load is named rather than dropped silently.
    lib = library(
        powered(
            "PRN", "component", supply_type="VAC", voltage_v=230, unit_power_w=622, power_supplies=0
        ),
        powered("ANN", "annunciator", power_supplies=1),
        device("CABLE"),
    )
    loose = LooseTable(
        title=("t", "t"),
        lines=tuple(loose_line(p) for p in ("PRN", "ANN", "CABLE")),
        host_panel="ws",
    )
    assert external_ac_checks(loose, lib) == [
        CheckItem(
            check="external_ac",
            status=CheckStatus.WARN,
            subject="PRN",
            message="2 x 622 W AC left out of the power and heat totals: "
            "External Equipment counts station DC loads only",
        )
    ]
    assert external_ac_checks(None, lib) == []


def test_a_networked_device_without_an_l2_link_warns() -> None:
    # M31: with no L2 link the device gets no downlink SFP on the L2 switch.
    lib = library(powered("GW", "gateway"), powered("IO", "io_chassis"))
    equipment = [
        Equipment(id="gw", part_id="GW", role="other"),
        Equipment(id="gw-2", part_id="GW", role="other", l2_ports=1),
        Equipment(id="io", part_id="IO", role="other"),
        Equipment(id="l1", role="l1_switch", redundant=True),
    ]
    assert l2_link_checks(equipment, lib) == [
        CheckItem(
            check="l2_link",
            status=CheckStatus.WARN,
            subject="gw",
            message="no L2 link (l2_ports is 0), so the L2 switch gets no SFP for it",
        )
    ]


# Tag naming conventions (ADR 0030): every device unit has its own tag.

TAGGED = library(
    powered("GPS", "gps_clock", tag_type="GPS", tag_pattern="{prefix}-GPS"),
    powered("GW", "gateway", tag_type="GW", purdue_level="L2"),
    device("KBM", "peripheral", tag_pattern="Keyboard & Mouse"),
)


def tag_items(*panels: tuple[str, list[dict[str, Any]]]) -> list[CheckItem]:
    built = [panel(devices, id=pid, tag_prefix="PSA1") for pid, devices in panels]
    return duplicate_tag_checks([(p, expand_devices(p, TAGGED)) for p in built])


def test_a_tag_two_device_units_share_is_an_error() -> None:
    items = tag_items(("psa1", [{"part_id": "GPS"}]), ("psa3", [{"part_id": "GPS"}]))
    assert items == [
        CheckItem(
            check="duplicate_tag",
            status=CheckStatus.FAIL,
            panel_id="psa1",
            subject="PSA1-GPS",
            message="2 device units share this tag (psa1, psa3): each needs its own",
        )
    ]


def test_numbered_device_tags_and_untyped_labels_pass() -> None:
    # two gateways number A01, A02; "Keyboard & Mouse" is a label, not a device tag
    devices = [{"part_id": "GW"}, {"part_id": "GW"}, {"part_id": "KBM"}, {"part_id": "KBM"}]
    assert tag_items(("psa1", devices)) == []
