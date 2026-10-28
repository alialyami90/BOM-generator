"""Edit operations on a library and the per-field check the editors call (ADR 0018)."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from bomgen.io.loader import load_library
from bomgen.library_store.edit import (
    Insert,
    Remove,
    SetValue,
    apply_edits,
    check_field,
    parse_edits,
)
from bomgen.models.library import Library

EXAMPLE_LIBRARY = Path(__file__).parents[3] / "examples" / "library.yaml"
SWITCH = "RST2228-L1-24MM"  # powered, has ports
RTAC = "SEL-3555-RTAC"  # has a terminal rule
SPOOL = "FOPP-SPOOL"  # a child of other parts


@pytest.fixture(scope="module")
def library() -> Library:
    return load_library(EXAMPLE_LIBRARY)


def _device(library: Library, part_id: str) -> dict[str, Any]:
    device = library.get(part_id)
    assert device is not None
    return device.model_dump(mode="json", exclude_none=True)


def test_setting_a_field_returns_a_new_library_and_leaves_the_old_one(library: Library) -> None:
    result = apply_edits(library, [SetValue(path=["devices", SWITCH, "make"], value="Acme")])

    assert result.problems == []
    assert result.library is not None
    assert result.library.get(SWITCH).make == "Acme"  # type: ignore[union-attr]
    assert library.get(SWITCH).make != "Acme"  # type: ignore[union-attr]


def test_a_nested_list_item_is_addressed_by_position(library: Library) -> None:
    result = apply_edits(
        library, [SetValue(path=["devices", SWITCH, "ports", 0, "count"], value=3)]
    )

    assert result.library is not None
    assert result.library.get(SWITCH).ports[0].count == 3  # type: ignore[union-attr]


def test_edits_apply_in_order(library: Library) -> None:
    result = apply_edits(
        library,
        [
            SetValue(path=["devices", SWITCH, "make"], value="One"),
            SetValue(path=["devices", SWITCH, "make"], value="Two"),
        ],
    )

    assert result.library is not None
    assert result.library.get(SWITCH).make == "Two"  # type: ignore[union-attr]


def test_removing_an_optional_field_puts_back_its_default(library: Library) -> None:
    result = apply_edits(library, [Remove(path=["devices", SWITCH, "make"])])

    assert result.library is not None
    assert result.library.get(SWITCH).make is None  # type: ignore[union-attr]


def test_a_new_device_is_inserted_at_the_end_or_at_a_position(library: Library) -> None:
    new = {"part_id": "NEW-1", "category": "component", "description_template": "New part"}

    at_end = apply_edits(library, [Insert(path=["devices"], value=new)])
    first = apply_edits(library, [Insert(path=["devices"], value=new, index=0)])

    assert at_end.library is not None
    assert first.library is not None
    assert at_end.library.part_ids()[-1] == "NEW-1"
    assert first.library.part_ids()[0] == "NEW-1"
    assert len(at_end.library.devices) == len(library.devices) + 1


def test_a_device_can_be_replaced_whole(library: Library) -> None:
    device = _device(library, SPOOL) | {"make": "Replaced"}

    result = apply_edits(library, [SetValue(path=["devices", SPOOL], value=device)])

    assert result.library is not None
    assert result.library.get(SPOOL).make == "Replaced"  # type: ignore[union-attr]


def test_a_device_that_nothing_uses_can_be_removed(library: Library) -> None:
    new = {"part_id": "NEW-1", "category": "component", "description_template": "New part"}
    added = apply_edits(library, [Insert(path=["devices"], value=new)])
    assert added.library is not None

    removed = apply_edits(added.library, [Remove(path=["devices", "NEW-1"])])

    assert removed.problems == []
    assert removed.library is not None
    assert removed.library.get("NEW-1") is None


def test_removing_a_device_another_part_uses_is_a_problem(library: Library) -> None:
    result = apply_edits(library, [Remove(path=["devices", SPOOL])])

    assert result.library is None
    assert any(f"unknown part_id '{SPOOL}'" in p.message for p in result.problems)
    assert all("devices[" in p.location for p in result.problems)


def test_a_value_the_model_refuses_is_a_problem_located_by_part_id(library: Library) -> None:
    result = apply_edits(library, [SetValue(path=["devices", SWITCH, "voltage_v"], value=-5)])

    assert result.library is None
    assert [p.location for p in result.problems] == [f"devices[{SWITCH}].voltage_v"]


def test_a_duplicate_part_id_is_a_problem(library: Library) -> None:
    result = apply_edits(library, [Insert(path=["devices"], value=_device(library, SPOOL))])

    assert result.library is None
    assert any("duplicate part_id" in p.message for p in result.problems)


def test_a_path_that_leads_nowhere_is_a_problem_not_an_exception(library: Library) -> None:
    for edit in (
        SetValue(path=["devices", "NO-SUCH", "make"], value="x"),
        SetValue(path=["nonsense", "make"], value="x"),
        SetValue(path=["devices", SWITCH, "ports", 99, "count"], value=1),
        Remove(path=["devices", "NO-SUCH"]),
        Insert(path=["catalogues", "enclosure_u"], value=1),
        Insert(path=["devices"], value=1, index=999),
    ):
        result = apply_edits(library, [edit])

        assert result.library is None, edit
        assert result.problems, edit


def test_a_catalogue_cell_and_a_dictionary_key_are_editable(library: Library) -> None:
    block = {"make": "Phoenix Contact", "ordering_code": "3044076"}
    every_brand = [
        SetValue(path=["catalogue_brands", "terminal_blocks", b.id, "types", "UT-NEW"], value=block)
        for b in library.catalogue_brands.terminal_blocks
    ]
    result = apply_edits(
        library,
        [
            SetValue(path=["catalogues", "mcb", "make"], value="Acme"),
            SetValue(path=["catalogues", "terminal_blocks", "UT-NEW"], value=block),
            *every_brand,
        ],
    )

    assert result.problems == []
    assert result.library is not None
    assert result.library.catalogues.mcb.make == "Acme"
    assert result.library.catalogues.terminal_blocks["UT-NEW"].ordering_code == "3044076"


def test_removing_a_terminal_block_a_device_uses_is_a_problem(library: Library) -> None:
    used = library.get(RTAC).terminals[0].block  # type: ignore[union-attr]

    result = apply_edits(library, [Remove(path=["catalogues", "terminal_blocks", used])])

    assert result.library is None
    assert any(f"unknown terminal block '{used}'" in p.message for p in result.problems)


def test_a_brand_is_added_to_a_catalogue_and_found_by_its_id(library: Library) -> None:
    mcb = library.catalogues.mcb.model_dump(mode="json", exclude_none=True)
    brand = {**mcb, "id": "abb-s200", "name": "ABB S200", "make": "ABB"}

    added = apply_edits(library, [Insert(path=["catalogue_brands", "mcb"], value=brand)])
    assert added.library is not None
    renamed = apply_edits(
        added.library, [SetValue(path=["catalogue_brands", "mcb", "abb-s200", "make"], value="X")]
    )

    shipped = [b.id for b in library.catalogue_brands.mcb]
    assert added.library.brand_ids("mcb") == ["default", *shipped, "abb-s200"]
    assert renamed.library is not None
    assert renamed.library.catalogue_brands.mcb[-1].make == "X"


def test_a_second_brand_with_the_same_id_is_a_problem(library: Library) -> None:
    mcb = library.catalogues.mcb.model_dump(mode="json", exclude_none=True)
    brand = {**mcb, "id": "abb-s200"}

    result = apply_edits(
        library,
        [Insert(path=["catalogue_brands", "mcb"], value=brand)] * 2,
    )

    assert result.library is None
    assert result.problems


def test_an_empty_list_of_edits_returns_the_library_unchanged(library: Library) -> None:
    result = apply_edits(library, [])

    assert result.library == library


def test_edits_arrive_as_plain_json(library: Library) -> None:
    edits = parse_edits(
        [
            {"op": "set", "path": ["devices", SWITCH, "make"], "value": "Acme"},
            {"op": "insert", "path": ["devices"], "value": {"part_id": "N"}, "index": 0},
            {"op": "remove", "path": ["devices", "N"]},
        ]
    )

    assert [type(e) for e in edits] == [SetValue, Insert, Remove]


@pytest.mark.parametrize(
    "raw",
    [
        {"op": "rename", "path": ["devices"]},
        {"op": "set", "path": [], "value": 1},
        {"op": "set", "path": ["devices", 1.5], "value": 1},
        {"op": "set", "path": "devices.make", "value": 1},
        {"op": "set", "value": 1},
        {"op": "remove", "path": ["devices", "X"], "value": 1},
    ],
)
def test_malformed_edits_are_refused(raw: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        parse_edits([raw])


def test_a_good_value_has_no_message(library: Library) -> None:
    assert check_field(library, ["devices", SWITCH, "make"], "Acme") is None


def test_a_bad_value_gets_the_models_message(library: Library) -> None:
    message = check_field(library, ["devices", SWITCH, "voltage_v"], -5)

    assert message is not None
    assert "greater than 0" in message


def test_a_rule_between_fields_is_reported_on_the_field_being_edited(library: Library) -> None:
    message = check_field(library, ["devices", SWITCH, "supply_type"], None)

    assert message is not None
    assert "supply_type" in message


def test_a_problem_that_was_already_there_is_not_blamed_on_the_field(library: Library) -> None:
    data = library.model_dump(mode="json")
    data["devices"][0]["children"] = [{"part_id": "GONE", "qty": 1}]
    flawed = Library.model_validate(data)  # the model allows it; the cross-record check does not

    assert apply_edits(flawed, []).problems
    assert check_field(flawed, ["devices", SPOOL, "make"], "Acme") is None


def test_an_unusable_path_is_reported_as_a_message(library: Library) -> None:
    message = check_field(library, ["devices", "NO-SUCH", "make"], "x")

    assert message is not None
    assert "NO-SUCH" in message
