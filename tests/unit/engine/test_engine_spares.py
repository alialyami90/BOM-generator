"""The spares list: spare quantities from the design basis policy, then the substation's
overrides, exclusions and extras (ADR 0035, plan M64, Q65)."""

from dataclasses import replace
from pathlib import Path

import pytest

from bomgen.engine.pipeline import build
from bomgen.engine.spares import spares
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.bom import SpareLine
from bomgen.models.library import Category
from bomgen.models.substation import DesignBasis, SpareExtra, SparesList, SparesPolicy

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"
SX = "6GK6000-8FG51-0AA0"  # 84 installed
LX = "6GK6000-8FG52-0AA0"  # 4 installed


@pytest.fixture(scope="module")
def example() -> LoadedSubstation:
    return load_substation(EXAMPLE)


def setup(
    loaded: LoadedSubstation, policy: SparesPolicy | None, overrides: SparesList | None = None
) -> list[SpareLine]:
    substation = loaded.substation.model_copy(
        update={
            "design_basis": DesignBasis(spares_policy=policy) if policy else None,
            "spares_list": overrides,
        }
    )
    target = replace(loaded, substation=substation)
    return list(spares(target, build(target)).lines)


SFP_10 = SparesPolicy(percent={Category.SFP: 10}, minimum_per_part=1, categories=[Category.SFP])


def by_code(lines: list[SpareLine]) -> dict[str | None, SpareLine]:
    return {line.ordering_code: line for line in lines}


def test_no_policy_and_no_overrides_is_an_empty_list(example: LoadedSubstation) -> None:
    assert setup(example, None) == []


def test_percent_with_minimum_one(example: LoadedSubstation) -> None:
    lines = by_code(setup(example, SFP_10))
    assert set(lines) == {SX, LX, "6GK6000-8FE51-0AA0", "FR-TRAN-SX"}
    assert (lines[SX].installed, lines[SX].spare) == (84, 9)
    assert lines[SX].basis == "10% of 84, min 1 = 9"
    assert (lines[LX].installed, lines[LX].spare) == (4, 1)
    assert lines[LX].basis == "10% of 4, min 1 = 1"
    assert lines[SX].percent == 10
    assert lines[SX].minimum == 1


def test_a_category_without_a_percent_gets_the_minimum(example: LoadedSubstation) -> None:
    policy = SparesPolicy(minimum_per_part=2, categories=[Category.FAN])
    (fan,) = setup(example, policy)
    assert (fan.installed, fan.spare, fan.basis) == (6, 2, "0% of 6, min 2 = 2")


def test_a_zero_result_is_left_out(example: LoadedSubstation) -> None:
    assert setup(example, SparesPolicy(categories=[Category.FAN])) == []


def test_override_replaces_computed_qty(example: LoadedSubstation) -> None:
    lines = by_code(setup(example, SFP_10, SparesList(items={SX: 12})))
    assert (lines[SX].spare, lines[SX].basis, lines[SX].overridden) == (
        12,
        "set to 12 (rule gives 9)",
        True,
    )


def test_an_override_adds_a_line_outside_the_policy(example: LoadedSubstation) -> None:
    (mcb,) = setup(example, None, SparesList(items={"A9F74202": 5}))
    assert (mcb.installed, mcb.spare, mcb.basis) == (77, 5, "set to 5")


def test_excluded_line_absent(example: LoadedSubstation) -> None:
    lines = by_code(setup(example, SFP_10, SparesList(excluded=[LX])))
    assert LX not in lines
    assert SX in lines


def test_extras_follow_with_no_installed_qty(example: LoadedSubstation) -> None:
    extras = [
        SpareExtra(part_id="SK3243-FAN", qty=2),
        SpareExtra(description="Fuse kit", qty=1),
    ]
    *_, fan, fuse = setup(example, SFP_10, SparesList(extra=extras))
    assert (fan.installed, fan.spare, fan.ordering_code, fan.basis) == (
        None,
        2,
        "SK 3243.100",
        "added",
    )
    assert (fuse.description, fuse.make, fuse.spare) == ("Fuse kit", None, 1)


def test_an_extra_needs_a_part_or_a_description() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        SpareExtra(qty=1)
