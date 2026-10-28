"""Device library model: DeviceType, port groups, rules and catalogues."""

import copy
from typing import Any

import pytest
from pydantic import ValidationError

from bomgen.models.library import (
    DeviceType,
    Library,
    McbCatalogue,
    PortGroup,
    TerminalRule,
)

SWITCH_CODE = "6GK6222-6AB00-5CC0-Z A05+B05+C05+D05+E05+F05+G05"


def switch_dict() -> dict[str, Any]:
    return {
        "part_id": "RST2228-L1-24MM",
        "category": "network_switch",
        "make": "Ruggedcom",
        "model": "RST-2228",
        "ordering_code": SWITCH_CODE,
        "description_template": "LAN-{lan} Industrial Ethernet switch (Level-1) (24 MM FO Ports)",
        "tag_type": "ESW",
        "purdue_level": "L1",
        "supply_type": "VDC",
        "voltage_v": 125,
        "unit_power_w": 77,
        "load_type": "CONTINUOUS",
        "power_supplies": 2,
        "min_branch_mcb_a": 2,
        "hwio_points": 1,
        "ports": [
            {"count": 24, "speed": "100M", "media": "MM", "kind": "fixed"},
            {"count": 4, "speed": "1G", "kind": "sfp_slot"},
        ],
    }


def passive_dict() -> dict[str, Any]:
    return {
        "part_id": "SFP-1G-SM",
        "category": "sfp",
        "make": "Ruggedcom",
        "model": "SFP-1G-SM",
        "description_template": "1G SM SFP transceiver",
    }


def minimal_library_dict() -> dict[str, Any]:
    ref = {"part_id": "X"}
    return {
        "devices": [switch_dict(), passive_dict()],
        "catalogues": {
            "mcb": {
                "family": "Acti9 iC60N",
                "make": "Schneider",
                "ratings_a": [1, 2, 6, 10, 16],
                "code_pattern": "A9F742{rating:02d}",
            },
            "aux_contact": {"make": "Schneider", "model": "iACT24", "ordering_code": "A9A26924"},
            "terminal_blocks": {"UT-16": {"make": "Phoenix", "ordering_code": "3044199"}},
            "busbars": {"PE": {"description": "PE busbar"}},
            "housekeeping": {
                "lamp": ref,
                "door_switch": ref,
                "fan": {"part_id": "X", "airflow_m3h": 110.0},
                "vent_filter": ref,
                "thermostat": ref,
                "ipr_kit": ref,
                "change_over_diodes": ref,
                "socket": {"part_id": "X", "rating_a": 10},
            },
        },
    }


def device(**overrides: Any) -> DeviceType:
    data = switch_dict()
    data.update(overrides)
    return DeviceType.model_validate(data)


def test_l1_switch_record_from_spec_validates() -> None:
    d = DeviceType.model_validate(switch_dict())
    assert d.part_id == "RST2228-L1-24MM"
    assert d.category == "network_switch"
    assert d.code == SWITCH_CODE
    assert d.unit_power_w == 77
    assert d.voltage_v == 125
    assert d.supply_type == "VDC"
    assert d.load_type == "CONTINUOUS"
    assert d.power_supplies == 2
    assert d.min_branch_mcb_a == 2
    assert d.hwio_points == 1
    assert d.excluded_from_power is False
    assert [(p.count, p.speed, p.media, p.kind) for p in d.ports] == [
        (24, "100M", "MM", "fixed"),
        (4, "1G", None, "sfp_slot"),
    ]


def test_code_falls_back_to_model_when_no_ordering_code() -> None:
    assert device(ordering_code=None).code == "RST-2228"


def test_child_part_may_omit_make_and_model() -> None:
    data = passive_dict()
    del data["make"], data["model"]
    part = DeviceType.model_validate(data)
    assert (part.make, part.model) == (None, None)
    no_make = passive_dict()
    del no_make["make"]
    assert DeviceType.model_validate(no_make).make is None


def test_code_is_none_without_ordering_code_or_model() -> None:
    assert device(ordering_code=None, model=None).code is None
    assert device(ordering_code="X-1", model=None).code == "X-1"


def test_passive_part_defaults_to_excluded_from_power() -> None:
    assert DeviceType.model_validate(passive_dict()).excluded_from_power is True


def test_explicit_excluded_from_power_is_kept() -> None:
    assert device(excluded_from_power=True, power_supplies=0).excluded_from_power is True


@pytest.mark.parametrize("missing", ["supply_type", "unit_power_w", "load_type"])
def test_powered_device_requires_supply_power_and_load_type(missing: str) -> None:
    data = switch_dict()
    del data[missing]
    data["excluded_from_power"] = False
    with pytest.raises(ValidationError, match=missing):
        DeviceType.model_validate(data)


def test_dual_feed_requires_vdc() -> None:
    with pytest.raises(ValidationError, match="VDC"):
        device(supply_type="VAC", voltage_v=230)


def test_excluded_device_cannot_have_power_supplies() -> None:
    with pytest.raises(ValidationError, match="power_supplies"):
        device(excluded_from_power=True)


def test_cores_child_requires_parent_cores() -> None:
    data = passive_dict()
    data["children"] = [{"part_id": "PIGTAIL", "qty": "cores"}]
    with pytest.raises(ValidationError, match="cores"):
        DeviceType.model_validate(data)
    data["cores"] = 12
    assert DeviceType.model_validate(data).children[0].qty == "cores"


def test_child_quantity_defaults_to_one() -> None:
    data = passive_dict()
    data["children"] = [{"part_id": "SPOOL"}]
    assert DeviceType.model_validate(data).children[0].qty == 1


def test_unknown_key_is_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        device(colour="red")
    assert [e["type"] for e in excinfo.value.errors()] == ["extra_forbidden"]


def test_device_is_frozen() -> None:
    d = device()
    with pytest.raises(ValidationError):
        setattr(d, "make", "Other")  # noqa: B010


def test_description_template_rejects_unknown_placeholder() -> None:
    with pytest.raises(ValidationError, match="'colour'"):
        device(description_template="LAN-{lan} {colour}")


def test_tag_pattern_rejects_unknown_placeholder() -> None:
    with pytest.raises(ValidationError, match="'colour'"):
        device(tag_pattern="{prefix}-{colour}")
    assert device(tag_pattern="{prefix}-{level}{type}-{lan}{nn}").tag_pattern is not None


def test_part_id_rejects_spaces() -> None:
    with pytest.raises(ValidationError):
        device(part_id="bad id")


def test_fixed_port_group_requires_media() -> None:
    with pytest.raises(ValidationError, match="media"):
        PortGroup.model_validate({"count": 4, "speed": "1G", "kind": "fixed"})
    assert PortGroup.model_validate({"count": 4, "speed": "1G", "kind": "sfp_slot"}).media is None


def test_port_speed_values_are_the_yaml_strings() -> None:
    assert PortGroup.model_validate({"count": 1, "speed": "10G", "kind": "sfp_slot"}).speed == "10G"
    with pytest.raises(ValidationError):
        PortGroup.model_validate({"count": 1, "speed": "10", "kind": "sfp_slot"})


def test_slot_strip_requires_first_slot() -> None:
    with pytest.raises(ValidationError, match="first_slot"):
        TerminalRule.model_validate({"strip": "XDIP{slot}", "block": "UT-2.5-MTD", "count": 58})
    rule = TerminalRule.model_validate(
        {"strip": "XDIP{slot}", "block": "UT-2.5-MTD", "count": 58, "first_slot": "A"}
    )
    assert rule.first_slot == "A"


def test_first_slot_without_slot_placeholder_is_rejected() -> None:
    with pytest.raises(ValidationError, match="slot"):
        TerminalRule.model_validate(
            {"strip": "XRTAC-C{n}", "block": "UT-2.5-MT", "count": 5, "first_slot": "A"}
        )


@pytest.mark.parametrize("bad", ["a", "AB", "1", ""])
def test_first_slot_must_be_one_uppercase_letter(bad: str) -> None:
    with pytest.raises(ValidationError):
        TerminalRule.model_validate(
            {"strip": "XDIP{slot}", "block": "UT", "count": 1, "first_slot": bad}
        )


def test_terminal_strip_rejects_unknown_placeholder() -> None:
    with pytest.raises(ValidationError, match="'colour'"):
        TerminalRule.model_validate({"strip": "X{colour}", "block": "UT", "count": 1})


def test_terminal_rule_defaults_per_unit() -> None:
    rule = TerminalRule.model_validate({"strip": "XRTAC-C{n}", "block": "UT", "count": 5})
    assert rule.per == "unit"
    assert rule.first_slot is None


def mcb(**overrides: Any) -> McbCatalogue:
    data = copy.deepcopy(minimal_library_dict()["catalogues"]["mcb"])
    data.update(overrides)
    return McbCatalogue.model_validate(data)


def test_mcb_code_for_rating() -> None:
    cat = mcb()
    assert cat.code_for(1) == "A9F74201"
    assert cat.code_for(16) == "A9F74216"
    assert cat.poles == 2
    with pytest.raises(ValueError, match="3"):
        cat.code_for(3)


def test_mcb_ratings_must_increase() -> None:
    with pytest.raises(ValidationError, match="increasing"):
        mcb(ratings_a=[2, 1])
    with pytest.raises(ValidationError, match="increasing"):
        mcb(ratings_a=[2, 2])
    with pytest.raises(ValidationError):
        mcb(ratings_a=[])


def test_mcb_code_pattern_must_use_only_rating() -> None:
    with pytest.raises(ValidationError, match="'amps'"):
        mcb(code_pattern="A9F{amps}")
    with pytest.raises(ValidationError, match="rating"):
        mcb(code_pattern="A9F74201")
    with pytest.raises(ValidationError, match="code_pattern"):
        mcb(code_pattern="A9F{rating:s}")


@pytest.mark.parametrize("pattern", ["A{rating.foo}", "A{rating[0]}", "A{rating!z}"])
def test_mcb_code_pattern_rejects_access_that_cannot_be_formatted(pattern: str) -> None:
    with pytest.raises(ValidationError, match="code_pattern cannot be formatted"):
        mcb(code_pattern=pattern)


def test_library_get_returns_device_or_none() -> None:
    lib = Library.model_validate(minimal_library_dict())
    found = lib.get("SFP-1G-SM")
    assert found is not None
    assert found.model == "SFP-1G-SM"
    assert lib.get("NOPE") is None
    assert lib.part_ids() == ["RST2228-L1-24MM", "SFP-1G-SM"]


def test_library_requires_devices_and_catalogue_entries() -> None:
    data = minimal_library_dict()
    data["devices"] = []
    with pytest.raises(ValidationError):
        Library.model_validate(data)
    data = minimal_library_dict()
    data["catalogues"]["terminal_blocks"] = {}
    with pytest.raises(ValidationError):
        Library.model_validate(data)
    data = minimal_library_dict()
    data["catalogues"]["busbars"] = {}
    with pytest.raises(ValidationError):
        Library.model_validate(data)


def test_housekeeping_fan_needs_airflow_and_socket_needs_rating() -> None:
    data = minimal_library_dict()
    del data["catalogues"]["housekeeping"]["fan"]["airflow_m3h"]
    with pytest.raises(ValidationError, match="airflow_m3h"):
        Library.model_validate(data)
    data = minimal_library_dict()
    data["catalogues"]["housekeeping"]["socket"]["rating_a"] = 0
    with pytest.raises(ValidationError, match="rating_a"):
        Library.model_validate(data)
