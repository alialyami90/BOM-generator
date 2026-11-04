"""Every override in one list, risky ones with a reason (ADR 0040, plan M77)."""

from dataclasses import replace
from pathlib import Path

import pytest

from bomgen.checks import check_report
from bomgen.engine.overrides import Override, override_checks, overrides, risky_notes
from bomgen.engine.pipeline import build
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.bom import BuildResult
from bomgen.models.library import Category
from bomgen.models.panel import Ventilation
from bomgen.models.report import CheckStatus
from bomgen.models.substation import (
    DesignBasis,
    DeviceMove,
    Equipment,
    EquipmentRole,
    Layout,
    PartOverrides,
    SparesList,
    SparesPolicy,
)

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"
SX = "6GK6000-8FG51-0AA0"  # 84 SFPs installed


@pytest.fixture(scope="module")
def example() -> LoadedSubstation:
    return load_substation(EXAMPLE)


def with_options(loaded: LoadedSubstation, panel_id: str, **options: object) -> LoadedSubstation:
    panels = tuple(
        p.model_copy(update={"options": p.options.model_copy(update=options)})
        if p.id == panel_id
        else p
        for p in loaded.panels
    )
    return replace(loaded, panels=panels)


def with_substation(loaded: LoadedSubstation, **fields: object) -> LoadedSubstation:
    return replace(loaded, substation=loaded.substation.model_copy(update=fields))


def built(loaded: LoadedSubstation) -> tuple[LoadedSubstation, BuildResult]:
    return loaded, build(loaded)


def by_subject(loaded: LoadedSubstation) -> dict[tuple[str | None, str], Override]:
    return {(o.panel_id, o.subject): o for o in overrides(*built(loaded))}


def test_the_example_lists_the_overrides_its_panel_files_write(example: LoadedSubstation) -> None:
    found = by_subject(example)
    main = found[("psa1", "main_mcb")]
    assert (main.automatic, main.override, main.risky) == ("10 A", "16 A", False)
    xdin = found[("psa3", "terminals.XDIN")]
    assert (xdin.override, xdin.risky) == ("40", False)
    assert found[("psa3", "ventilation")].override == "fans"
    assert found[("ws", "ventilation")].override == "filters"
    assert not any(o.risky for o in found.values())


def test_a_hand_written_panel_s_override_has_no_field_to_go_to(example: LoadedSubstation) -> None:
    assert by_subject(example)[("psa1", "main_mcb")].field is None


def test_a_rating_below_the_automatic_is_risky_and_warns_without_a_reason(
    example: LoadedSubstation,
) -> None:
    loaded = with_options(example, "psa1", main_mcb_override_a=6)
    (item,) = [
        i
        for i in override_checks(*built(loaded))
        if (i.panel_id, i.subject) == ("psa1", "main_mcb")
    ]
    assert item.status is CheckStatus.WARN
    assert (
        item.message
        == "6 A instead of the automatic 10 A; below the automatic value: give a reason"
    )
    assert item.values == {"automatic": "10 A", "override": "6 A"}


def test_a_reason_makes_the_risky_override_pass_and_is_printed(example: LoadedSubstation) -> None:
    loaded = with_options(
        example,
        "psa1",
        main_mcb_override_a=6,
        override_reasons={"main_mcb": "Client's feeder is 6 A"},
    )
    (item,) = [
        i
        for i in override_checks(*built(loaded))
        if (i.panel_id, i.subject) == ("psa1", "main_mcb")
    ]
    assert item.status is CheckStatus.PASS
    assert item.message == "6 A instead of the automatic 10 A: Client's feeder is 6 A"
    assert item.values["reason"] == "Client's feeder is 6 A"


def test_an_override_at_or_above_the_automatic_passes_without_a_reason(
    example: LoadedSubstation,
) -> None:
    items = [i for i in override_checks(*built(example)) if i.check == "override"]
    assert items
    assert all(i.status is CheckStatus.PASS for i in items)


def test_a_terminal_quantity_below_its_rule_is_risky(example: LoadedSubstation) -> None:
    loaded, result = built(example)
    strip = next(s for s in result.strips if s.panel_id == "psa1").strips[0]
    loaded = with_options(example, "psa1", terminal_overrides={strip.code: strip.auto_qty - 1})
    found = by_subject(loaded)[("psa1", f"terminals.{strip.code}")]
    assert (found.automatic, found.override, found.risky) == (
        str(strip.auto_qty),
        str(strip.auto_qty - 1),
        True,
    )


def test_a_block_type_override_is_listed_but_never_risky(example: LoadedSubstation) -> None:
    loaded, result = built(example)
    strip = next(s for s in result.strips if s.panel_id == "psa1").strips[0]
    loaded = with_options(example, "psa1", terminal_block_overrides={strip.code: "UT-2.5-MT"})
    found = by_subject(loaded)[("psa1", f"terminals.{strip.code}.block")]
    assert (found.automatic, found.override, found.risky) == (strip.block, "UT-2.5-MT", False)


def test_filters_where_the_heat_wants_fans_is_risky(example: LoadedSubstation) -> None:
    loaded, result = built(example)
    assert result.heat is not None
    cabinet = next(c for c in result.heat.cabinets if c.panel_id == "psa1")
    assert cabinet.ventilation is Ventilation.FORCED
    assert not cabinet.natural.passes
    loaded = with_options(example, "psa1", ventilation=Ventilation.NATURAL)
    found = by_subject(loaded)[("psa1", "ventilation")]
    assert (found.automatic, found.override, found.risky) == ("fans", "filters", True)


def test_a_spare_quantity_below_the_policy_is_risky_with_its_reason_beside_it(
    example: LoadedSubstation,
) -> None:
    policy = SparesPolicy(percent={Category.SFP: 10}, minimum_per_part=1, categories=[Category.SFP])
    loaded = with_substation(
        example,
        design_basis=DesignBasis(spares_policy=policy),
        spares_list=SparesList(items={SX: 2}, reasons={SX: "Client holds SFP spares"}),
    )
    found = by_subject(loaded)[(None, f"spares.{SX}")]
    assert (found.automatic, found.override, found.risky, found.reason) == (
        "9",
        "2",
        True,
        "Client holds SFP spares",
    )
    assert found.field == f"spares_list.items.{SX}"


def test_a_spare_outside_the_policy_is_listed_as_not_risky(example: LoadedSubstation) -> None:
    loaded = with_substation(example, spares_list=SparesList(items={SX: 2}))
    found = by_subject(loaded)[(None, f"spares.{SX}")]
    assert (found.automatic, found.risky) == ("none (outside the policy)", False)


def test_part_overrides_name_the_library_value(example: LoadedSubstation) -> None:
    clock = next(d for d in example.library.devices if d.category is Category.GPS_CLOCK)
    row = Equipment(
        id="clock",
        part_id=clock.part_id,
        role=EquipmentRole.TIME_SERVER,
        overrides=PartOverrides(unit_power_w=12.5),
    )
    loaded = with_substation(example, equipment=[*example.substation.equipment, row])
    index = len(loaded.substation.equipment) - 1
    found = by_subject(loaded)[(None, "parts.clock.unit_power_w")]
    assert (found.automatic, found.override, found.risky) == (
        str(clock.unit_power_w),
        "12.5",
        False,
    )
    assert found.field == f"equipment[{index}].overrides.unit_power_w"


def test_layout_moves_and_removals_are_listed(example: LoadedSubstation) -> None:
    layout = Layout(overrides=[DeviceMove(device="gw", panel=2, position=1)])
    loaded = with_substation(example, layout=layout)
    found = by_subject(loaded)[(None, "layout.gw")]
    assert (found.automatic, found.override, found.field) == (
        "the layout's place",
        "panel 2, position 1",
        "layout.overrides[0]",
    )


def test_the_check_report_carries_the_overrides_group(example: LoadedSubstation) -> None:
    loaded = with_options(example, "psa1", main_mcb_override_a=6)
    report = check_report(*built(loaded))
    items = [i for i in report.items if i.check == "override"]
    assert ("psa1", "main_mcb", CheckStatus.WARN) in [
        (i.panel_id, i.subject, i.status) for i in items
    ]
    assert report.open_warnings >= 1


def test_risky_notes_are_what_an_issue_records(example: LoadedSubstation) -> None:
    loaded = with_options(
        example, "psa1", main_mcb_override_a=6, override_reasons={"main_mcb": "Feeder is 6 A"}
    )
    note = next(n for n in risky_notes(*built(loaded)) if n.panel_id == "psa1")
    assert note.model_dump() == {
        "panel_id": "psa1",
        "subject": "main_mcb",
        "automatic": "10 A",
        "override": "6 A",
        "reason": "Feeder is 6 A",
    }
    assert risky_notes(*built(example)) == []
