"""Cable suggestions from the port plans: one cord per link, counted once at the link's
upper end (Q71), with the design basis lengths per link class (Q66, plan M65)."""

from dataclasses import replace
from pathlib import Path

import pytest

from bomgen.engine.cables import CableSuggestion, loose_item, suggest_cables
from bomgen.engine.pipeline import build
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.library import Category, DeviceType, Media, PortSpeed
from bomgen.models.project import CableRef, LooseExtra
from bomgen.models.substation import CableDefaults, DesignBasis, ExternalLink, Topology

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"


@pytest.fixture(scope="module")
def example() -> LoadedSubstation:
    return load_substation(EXAMPLE)


def rows(loaded: LoadedSubstation) -> list[CableSuggestion]:
    return list(suggest_cables(loaded, build(loaded)).rows)


def with_substation(loaded: LoadedSubstation, **update: object) -> LoadedSubstation:
    return replace(loaded, substation=loaded.substation.model_copy(update=update))


def find(found: list[CableSuggestion], from_tag: str, to_tag: str) -> CableSuggestion:
    return next(r for r in found if (r.from_tag, r.to_tag) == (from_tag, to_tag))


def test_one_cord_per_l1_uplink_per_side(example: LoadedSubstation) -> None:
    found = rows(example)
    for side, panel in (("A", "PSA1"), ("B", "PSA2")):
        row = find(found, f"{panel}-L2-ESW-{side}01", f"{panel}-L1-ESW-{side}11 to {side}16")
        assert (row.qty, row.speed, row.media, row.length_class) == (
            6,
            PortSpeed.G1,
            Media.MM,
            "in_cabinet",
        )


def test_the_example_counts_each_link_once_at_its_upper_end(example: LoadedSubstation) -> None:
    found = rows(example)
    totals: dict[tuple[Media | None, str], int] = {}
    for row in found:
        key = (row.media, row.length_class)
        totals[key] = totals.get(key, 0) + row.qty
    # per side: L2 downlinks 15 1G + 2 100M MM (8 to its own L1 and firewall), 2 SM L3
    # uplinks; the six L1 A-B interlinks once, on side A
    assert totals == {
        (Media.MM, "in_cabinet"): 16,
        (Media.MM, "inter_cabinet"): 18 + 6,
        (Media.SM, "external"): 4,
    }


def test_l1_interlinks_count_once_from_side_a(example: LoadedSubstation) -> None:
    row = find(rows(example), "PSA1-L1-ESW-A11 to A16", "PSA2-L1-ESW-B11 to B16")
    assert (row.qty, row.length_class, row.length_m) == (6, "inter_cabinet", 5)
    assert not [r for r in rows(example) if r.from_tag.startswith("PSA2-L1")]


def test_length_class_from_design_basis(example: LoadedSubstation) -> None:
    cables = CableDefaults(in_cabinet_m=1.5, inter_cabinet_m=10, external_m=80)
    found = rows(with_substation(example, design_basis=DesignBasis(cables=cables)))
    lengths = {r.length_class: r.length_m for r in found}
    assert lengths == {"in_cabinet": 1.5, "inter_cabinet": 10, "external": 80}


def test_the_default_lengths_are_two_and_five_metres(example: LoadedSubstation) -> None:
    lengths = {r.length_class: r.length_m for r in rows(example)}
    assert lengths == {"in_cabinet": 2, "inter_cabinet": 5, "external": None}


def test_an_external_link_uses_its_own_cable_length(example: LoadedSubstation) -> None:
    link = ExternalLink(name="CCR", count=1, media=Media.SM, cable_length_m=120)
    network = example.substation.network.model_copy(update={"external_links": [link]})
    found = rows(with_substation(example, network=network))
    for panel, side in (("PSA1", "A"), ("PSA2", "B")):
        row = find(found, f"{panel}-L2-ESW-{side}01", "CCR")
        assert (row.qty, row.media, row.length_m, row.length_class) == (
            1,
            Media.SM,
            120,
            "external",
        )


def test_no_library_cable_for_media_is_a_warning(example: LoadedSubstation) -> None:
    result = suggest_cables(example, build(example))
    assert all(r.part_id is None for r in result.rows)
    assert "No library cable for MM 2 m: 16 cords are free text" in result.warnings
    assert find(list(result.rows), "PSA1-L2-ESW-A01", "PSA1-EXT-FW-A01").description == (
        "LC-LC duplex patch cord, MM"
    )


def test_a_library_cable_of_the_media_and_length_is_picked(example: LoadedSubstation) -> None:
    cord = DeviceType(
        part_id="LC-MM-2M",
        category=Category.CABLE,
        description_template="LC-LC patch cord MM 2 m",
        media=Media.MM,
        length_m=2,
    )
    library = example.library.model_copy(update={"devices": [*example.library.devices, cord]})
    result = suggest_cables(replace(example, library=library), build(example))
    in_cabinet = [r for r in result.rows if r.length_class == "in_cabinet"]
    assert {r.part_id for r in in_cabinet} == {"LC-MM-2M"}
    assert not [w for w in result.warnings if "MM 2 m" in w]


def test_a_cord_already_in_the_loose_material_is_not_suggested_again(
    example: LoadedSubstation,
) -> None:
    ref = CableRef(
        from_tag="PSA1-L2-ESW-A01", to_tag="PSA1-EXT-FW-A01", media=Media.MM, speed=PortSpeed.G1
    )
    material = example.substation.loose_material
    assert material is not None
    items = [*material.items, LooseExtra(description="cord", qty=2, cable=ref)]
    target = with_substation(example, loose_material=material.model_copy(update={"items": items}))
    found = rows(target)
    assert not [r for r in found if (r.from_tag, r.to_tag) == (ref.from_tag, ref.to_tag)]
    assert len(found) == len(rows(example)) - 1


def test_a_suggestion_becomes_a_loose_item_with_cable_data(example: LoadedSubstation) -> None:
    row = find(rows(example), "PSA1-L2-ESW-A01", "PSA1-EXT-FW-A01")
    item = LooseExtra.model_validate(loose_item(row))
    assert item.description == "LC-LC duplex patch cord, MM"
    assert item.qty == 2
    assert item.cable == CableRef(
        from_tag="PSA1-L2-ESW-A01",
        to_tag="PSA1-EXT-FW-A01",
        length_m=2,
        media=Media.MM,
        speed=PortSpeed.G1,
    )


def test_a_ring_has_its_neighbour_links_and_no_interlinks(example: LoadedSubstation) -> None:
    network = example.substation.network.model_copy(update={"topology": Topology.RING})
    found = rows(with_substation(example, network=network))
    l1 = "PSA1-L1-ESW-A11 to A16"
    ring = find(found, l1, l1)
    assert (ring.qty, ring.length_class, ring.rule) == (5, "in_cabinet", "L1 ring links")
    assert find(found, "PSA1-L2-ESW-A01", l1).qty == 2  # the ring's two ends
    assert not [r for r in found if r.rule.startswith("L1 A-B")]
