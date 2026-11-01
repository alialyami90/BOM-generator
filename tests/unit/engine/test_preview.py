"""Device preview: every generated unit with its U, MCBs and strips (M24)."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from bomgen.checks import check_report
from bomgen.engine import preview as preview_module
from bomgen.engine.errors import EngineError
from bomgen.engine.layout import layout_preview
from bomgen.engine.pipeline import build
from bomgen.engine.preview import device_preview
from bomgen.io.derived import derive_parts
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.library import Category
from bomgen.models.preview import DevicePreview, PreviewUnit
from bomgen.models.substation import DeviceMove
from bomgen.models.substation import Layout as LayoutInputs

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"


@pytest.fixture(scope="module")
def example() -> LoadedSubstation:
    return load_substation(EXAMPLE)


def with_entry(loaded: LoadedSubstation, device: str, **fields: Any) -> LoadedSubstation:
    """The example with equipment ``device`` changed and its derived part in the library."""
    equipment = [
        e.model_validate({**e.model_dump(exclude_unset=True), **fields}) if e.id == device else e
        for e in loaded.substation.equipment
    ]
    substation = loaded.substation.model_copy(update={"equipment": equipment})
    library, problems = derive_parts(loaded.library, substation)
    assert problems == []
    return replace(loaded, substation=substation, library=library)


def with_part(loaded: LoadedSubstation, part_id: str, **fields: Any) -> LoadedSubstation:
    """The example with library part ``part_id`` changed."""
    devices = [
        d.model_copy(update=fields) if d.part_id == part_id else d for d in loaded.library.devices
    ]
    return replace(loaded, library=loaded.library.model_copy(update={"devices": devices}))


def unit(preview: DevicePreview, device: str, side: str | None = None) -> PreviewUnit:
    return next(x for p in preview.panels for x in p.units if x.device == device and x.side == side)


def test_preview_lists_every_unit_with_its_top_u(example: LoadedSubstation) -> None:
    preview = device_preview(example)
    fills = layout_preview(example).fills
    assert [p.panel_id for p in preview.panels] == ["psa1", "psa2"]
    assert preview.panels[0].units[0].device == "gps"
    assert preview.panels[0].units[0].top_u == 32
    assert sum(len(p.units) for p in preview.panels) == sum(len(f.units) for f in fills)
    assert (preview.waist_u, preview.capacity_u) == (18, example.panel_capacity_u)
    fw = unit(preview, "ext-fw", "a")
    assert (fw.din_rail, fw.top_u, fw.placed) == (True, None, True)
    assert preview.panels[0].units[-1] == fw  # DIN rail last


def test_a_redundant_entry_lists_both_sides(example: LoadedSubstation) -> None:
    preview = device_preview(example)
    a, b = unit(preview, "l2", "a"), unit(preview, "l2", "b")
    assert (a.tag, b.tag) == ("PSA1-L2-ESW-A01", "PSA2-L2-ESW-B01")
    assert [p.panel_id for p in preview.panels if a in p.units or b in p.units] == [
        "psa1",
        "psa2",
    ]


def test_preview_gives_each_unit_its_two_dc_mcbs(example: LoadedSubstation) -> None:
    preview = device_preview(example)
    l2 = unit(preview, "l2", "a")
    laid_out = replace(example, panels=(*layout_preview(example).panels,))
    records = {(m.unit_tag, m.feed): m for m in build(laid_out).branch_mcbs}
    assert l2.ps1 is not None
    assert l2.ps2 is not None
    assert (l2.ps1.tag, l2.ps2.tag) == ("PSA1-Q1.1", "PSA1-Q2.1")
    assert l2.ps1.rating_a == records[(l2.tag, 1)].rating_a
    assert l2.ps1.at_minimum is True  # 2 A, the floor
    assert unit(preview, "fopp", "a").ps1 is None  # passive


def test_a_single_fed_unit_has_one_mcb(example: LoadedSubstation) -> None:
    preview = device_preview(with_entry(example, "gps", overrides={"power_supplies": 1}))
    gps = unit(preview, "gps")
    assert gps.ps1 is not None
    assert "QCOD" in gps.ps1.tag
    assert gps.ps2 is None


def test_preview_marks_overridden_values_and_the_part_number(example: LoadedSubstation) -> None:
    changed = with_entry(example, "gw", overrides={"unit_power_w": 90}, ordering_code="GW-CODE")
    gw = unit(device_preview(changed), "gw", "a")
    assert gw.overridden == ("unit_power_w",)
    assert (gw.watts, gw.bom_code, gw.has_part_number) == (90, "GW-CODE", True)
    assert (gw.part_id, gw.library_part_id) == ("SEL-3555-GW+gw", "SEL-3555-GW")
    assert gw.supply == "125 VDC"
    gps = unit(device_preview(with_part(example, "SEL-2488", ordering_code=None)), "gps")
    assert (gps.bom_code, gps.has_part_number, gps.overridden) == (None, False, ())


def test_preview_lists_the_unit_strips(example: LoadedSubstation) -> None:
    preview = device_preview(example)
    assert unit(preview, "hwio").strips == ("XDIPD", "XDIPE", "XDIPF", "XDIPG")  # its DI slots
    assert unit(preview, "rtac").strips == ()  # serial-port strips are the panel's


def test_a_kvm_pinned_away_from_waist_height_is_a_warning(example: LoadedSubstation) -> None:
    kvm = with_part(example, "SEL-2488", category=Category.KVM)
    anchored = unit(device_preview(kvm), "gps")
    assert (anchored.waist, anchored.top_u, anchored.away_from_waist) == (True, 18, False)
    pinned = LayoutInputs(overrides=[DeviceMove(device="gps", panel=1, top_u=30)])
    preview = device_preview(kvm, pinned)
    gps = unit(preview, "gps")
    assert (gps.top_u, gps.pinned, gps.away_from_waist) == (30, True, True)
    warnings = [i for i in preview.issues if i.kind == "pinned-away-from-waist"]
    assert [(i.severity, i.message, i.device, i.panel) for i in warnings] == [
        ("warning", "gps#1 is pinned at U30, away from waist height (U18)", "gps", 1)
    ]


def test_a_layout_error_names_its_panel(example: LoadedSubstation) -> None:
    pinned = LayoutInputs(overrides=[DeviceMove(device="gps", panel=1, top_u=40)])
    issues = device_preview(example, pinned).issues
    [issue] = [i for i in issues if i.kind == "pin-outside-rack"]
    assert (issue.severity, issue.panel, issue.subject) == ("error", 1, "panel 1")


def test_an_engine_error_is_one_issue(
    example: LoadedSubstation, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(_loaded: LoadedSubstation) -> None:
        raise EngineError("no SFP for 10G SM")

    monkeypatch.setattr(preview_module, "build", fail)
    preview = device_preview(example)
    assert preview.panels == ()
    assert [(i.severity, i.kind, i.message) for i in preview.issues] == [
        ("error", "engine", "no SFP for 10G SM")
    ]


def test_preview_takes_candidate_overrides_without_writing(example: LoadedSubstation) -> None:
    before = EXAMPLE.read_text("utf-8")
    moved = LayoutInputs(overrides=[DeviceMove(device="gps", panel=2)])
    preview = device_preview(example, moved)
    assert [p.panel_id for p in preview.panels if unit(preview, "gps") in p.units] == ["psa2"]
    assert unit(preview, "gps").pinned is True
    assert example.substation.layout.overrides == []
    assert EXAMPLE.read_text("utf-8") == before


AC_GW = {"overrides": {"supply_type": "VAC", "voltage_v": 230, "power_supplies": 0}}


def test_preview_gives_a_vac_unit_its_ac_mcb(example: LoadedSubstation) -> None:
    preview = device_preview(with_entry(example, "gw", **AC_GW))
    a, b = unit(preview, "gw", "a"), unit(preview, "gw", "b")
    assert a.ps1 is not None
    assert b.ps1 is not None
    assert (a.ps1.tag[:6], b.ps1.tag[:6], a.ps2, b.ps2) == ("PSA1-C", "PSA2-C", None, None)
    assert a.supply == "230 VAC"


def test_an_ac_branch_mcb_is_reported_with_its_numbers(example: LoadedSubstation) -> None:
    loaded = with_entry(example, "gw", **AC_GW)
    laid_out = replace(loaded, panels=(*layout_preview(loaded).panels,))
    items = [
        x
        for x in check_report(laid_out, build(laid_out)).items
        if x.check == "branch_mcb" and "L2_GW_A01" in x.message
    ]
    assert [(x.panel_id, x.message) for x in items] == [
        ("psa1", "2 A for L2_GW_A01: running 0.41 A, floor 2 A; set by floor")
    ]
