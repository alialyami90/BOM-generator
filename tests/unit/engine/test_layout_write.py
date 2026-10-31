"""``write_generated_panels``: the panel files ``bomgen layout`` and the app's "Lay out
panels" button write (M19)."""

import shutil
from pathlib import Path

import pytest
import yaml

from bomgen.engine.layout import GENERATED_HEADER, write_generated_panels

EXAMPLES = Path(__file__).parents[3] / "examples"


@pytest.fixture
def substation(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "examples")
    path = tmp_path / "examples" / "substations" / "gis01" / "substation.yaml"
    # feed the annunciator from psa1, which the layout writes (as in test_layout_cli.py)
    path.write_text(path.read_text().replace("fed_from: psa3", "fed_from: psa1"))
    return path


def test_generate_panels_copies_hand_written_files_before_replacing_them(
    substation: Path,
) -> None:
    panels = substation.parent / "panels"
    before = {p.name: p.read_bytes() for p in panels.glob("*.yaml")}

    written = write_generated_panels(substation, replace_hand_written=True, backup=True)

    assert written.backup_dir is not None
    assert written.backup_dir.parent == panels
    assert written.backup_dir.name.startswith("hand-written-")
    assert sorted(p.name for p in written.written) == ["psa1.yaml", "psa2.yaml"]
    for path in written.written:
        assert path.read_text(encoding="utf-8").startswith(GENERATED_HEADER)
        assert (written.backup_dir / path.name).read_bytes() == before[path.name]
    assert sorted(p.name for p in written.backup_dir.iterdir()) == ["psa1.yaml", "psa2.yaml"]
    assert written.refused == []
    listed = yaml.safe_load(substation.read_text())["panels"]
    assert listed == ["panels/psa1.yaml", "panels/psa2.yaml"]


def test_generate_panels_refuses_hand_written_files_without_replace(substation: Path) -> None:
    panels = substation.parent / "panels"
    before = {p.name: p.read_bytes() for p in panels.glob("*.yaml")}
    listed = substation.read_bytes()

    written = write_generated_panels(substation, replace_hand_written=False, backup=False)

    assert sorted(p.name for p in written.refused) == ["psa1.yaml", "psa2.yaml"]
    assert written.written == []
    assert written.backup_dir is None
    assert {p.name: p.read_bytes() for p in panels.glob("*.yaml")} == before
    assert substation.read_bytes() == listed


def test_generate_panels_makes_no_backup_when_every_file_is_generated(substation: Path) -> None:
    write_generated_panels(substation, replace_hand_written=True, backup=False)

    again = write_generated_panels(substation, replace_hand_written=False, backup=True)

    assert again.backup_dir is None
    assert sorted(p.name for p in again.written) == ["psa1.yaml", "psa2.yaml"]
    assert not list((substation.parent / "panels").glob("hand-written-*"))
