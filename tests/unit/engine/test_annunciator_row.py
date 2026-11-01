"""A substation's annunciator row goes to loose material, not into a rack (plan M45, Q51).

Design §10 puts the annunciator in loose material by default, with its wall-mount kit; after a
layout it is fed from panel 001 (Ali, plan M1c).
"""

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from bomgen.engine.layout import layout_substation
from bomgen.engine.pipeline import build
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.bom import BuildResult

EXAMPLES = Path(__file__).parents[3] / "examples"
LOOSE_ANNUNCIATOR = """    - part_id: NAP-K55  # row 49
      tag: '55" LCD Alarm Annunciator'
      children: [LPA37-696]  # row 50: Wall Mount Kit
      fed_from: psa3  # PSA3-QCOD-1 "2A, 2P MCB For Annunciator" (plan Q13)
"""
L2_ROW = "  - { id: l2, part_id: RST2228-L2, role: l2_switch, redundant: true }\n"
KIT = "  - part_id: NAP-K55  # 'Aux' row 49: 55\" LCD Alarm Annunciator\n"


@pytest.fixture(scope="module")
def laid_out(tmp_path_factory: pytest.TempPathFactory) -> tuple[LoadedSubstation, BuildResult]:
    root = tmp_path_factory.mktemp("annunciator") / "examples"
    shutil.copytree(EXAMPLES, root)
    sub = root / "substations" / "gis01" / "substation.yaml"
    text = sub.read_text(encoding="utf-8")
    assert LOOSE_ANNUNCIATOR in text
    assert L2_ROW in text
    text = text.replace(LOOSE_ANNUNCIATOR, "")
    text = text.replace(L2_ROW, L2_ROW + "  - { id: ann, part_id: NAP-K55, role: annunciator }\n")
    sub.write_text(text, encoding="utf-8")
    lib = root / "library.yaml"
    lib_text = lib.read_text(encoding="utf-8")
    assert KIT in lib_text
    lib.write_text(
        lib_text.replace(KIT, KIT + "    loose_items: [{ part_id: LPA37-696 }]\n"), encoding="utf-8"
    )
    loaded = load_substation(sub)
    result = layout_substation(loaded)
    loaded = replace(loaded, panels=tuple(result.panels))
    return loaded, build(loaded)


def test_an_annunciator_row_is_not_placed_in_a_rack(
    laid_out: tuple[LoadedSubstation, BuildResult],
) -> None:
    loaded, _ = laid_out
    assert all(d.part_id != "NAP-K55" for p in loaded.panels for d in p.devices)


def test_an_annunciator_row_is_a_loose_item_with_its_wall_mount_kit(
    laid_out: tuple[LoadedSubstation, BuildResult],
) -> None:
    _, built = laid_out
    assert built.loose is not None
    parts = [line.part_id for line in built.loose.lines]
    at = parts.index("NAP-K55")
    assert parts[at + 1] == "LPA37-696"


def test_an_annunciator_row_is_fed_from_panel_001(
    laid_out: tuple[LoadedSubstation, BuildResult],
) -> None:
    _, built = laid_out
    psa1 = next(p for p in built.panels if p.panel_id == "psa1")
    assert any("For Annunciator" in line.description for line in psa1.lines)
