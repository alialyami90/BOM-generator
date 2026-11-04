"""The IED Schedule reference sheet (plan M80, ADR 0035 amendment): the schedule rows and
the ports per speed, media and side, written when a schedule exists and the sheet is chosen."""

from dataclasses import replace
from pathlib import Path

import pytest

from bomgen.engine.pipeline import build
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.library import Media, PortSpeed
from bomgen.models.sheet import Formula, SheetModel
from bomgen.models.substation import IedRow, PortNeed
from bomgen.sheets.workbook import build_workbook

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"
ROWS = [
    IedRow(bay="E01", name="P546", qty=4),
    IedRow(
        bay="H01",
        name="Merging unit",
        qty=2,
        attachment="single_a",
        lands_on="l2",
        ports=[PortNeed(count=2, speed=PortSpeed.G1, media=Media.SM)],
    ),
]


@pytest.fixture(scope="module")
def example() -> LoadedSubstation:
    return load_substation(EXAMPLE)


def with_inputs(
    loaded: LoadedSubstation, rows: list[IedRow], include: set[str]
) -> LoadedSubstation:
    network = loaded.substation.network.model_copy(update={"ied_schedule": rows})
    output = loaded.substation.output.model_copy(update={"include": include})
    substation = loaded.substation.model_copy(update={"network": network, "output": output})
    return replace(loaded, substation=substation)


def sheet_of(loaded: LoadedSubstation) -> SheetModel | None:
    return next(
        (s for s in build_workbook(loaded, build(loaded)).sheets if s.name == "IED Schedule"), None
    )


def cell(model: SheetModel, ref: str) -> object:
    found = model.cells.get((int(ref[1:]), ord(ref[0]) - 64))
    return None if found is None else found.value


def formula(model: SheetModel, ref: str) -> Formula:
    value = cell(model, ref)
    assert isinstance(value, Formula)
    return value


def test_no_sheet_unless_chosen_and_a_schedule_exists(example: LoadedSubstation) -> None:
    assert sheet_of(with_inputs(example, ROWS, set())) is None
    assert sheet_of(with_inputs(example, [], {"ied_schedule"})) is None


def test_one_row_per_ied_row_and_port_need(example: LoadedSubstation) -> None:
    m = sheet_of(with_inputs(example, ROWS, {"ied_schedule"}))
    assert m is not None
    assert cell(m, "A1") == "GIS Substation\nIED Schedule"
    assert [cell(m, f"{c}2") for c in "ABCDEFGHIJK"] == [
        "SR.NO",
        "BAY",
        "IED",
        "QTY",
        "PORTS PER IED",
        "SPEED",
        "MEDIA",
        "ATTACHMENT",
        "LANDS ON",
        "SIDE A PORTS",
        "SIDE B PORTS",
    ]
    assert [cell(m, f"{c}3") for c in "BCDEFGHI"] == [
        "E01", "P546", 4, 1, "100M", "MM", "Dual (A and B)", "L1"
    ]  # fmt: skip
    side_a, side_b = cell(m, "J3"), cell(m, "K3")
    assert isinstance(side_a, Formula)
    assert isinstance(side_b, Formula)
    assert (side_a.text, side_a.result, side_b.result) == ("=D3*E3", 4, 4)
    assert [cell(m, f"{c}4") for c in "BHI"] == ["H01", "Side A only", "L2"]
    assert (formula(m, "J4").result, cell(m, "K4")) == (4, 0)


def test_totals_per_speed_media_and_landing(example: LoadedSubstation) -> None:
    m = sheet_of(with_inputs(example, ROWS, {"ied_schedule"}))
    assert m is not None
    assert [cell(m, f"{c}6") for c in "FGIJK"] == [
        "SPEED", "MEDIA", "LANDS ON", "SIDE A PORTS", "SIDE B PORTS"
    ]  # fmt: skip
    assert [cell(m, f"{c}7") for c in "FGI"] == ["100M", "MM", "L1"]
    total = cell(m, "J7")
    assert isinstance(total, Formula)
    assert total.text == "=SUMIFS(J$3:J$4,F$3:F$4,F7,G$3:G$4,G7,I$3:I$4,I7)"
    assert total.result == 4
    assert [cell(m, f"{c}8") for c in "FGI"] == ["1G", "SM", "L2"]
    assert (formula(m, "J8").result, formula(m, "K8").result) == (4, 0)
