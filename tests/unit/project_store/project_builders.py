"""Helpers that build a small project folder on disk for the project-store tests."""

import os
from pathlib import Path

import pytest

PROJECT_YAML = """\
project:
  id: jfgp2
  name: JAFURAH JFGP2 PKG.3
library:
  name: psa-devices
  version: 1.2.0
substations:
  - substations/psa/substation.yaml
"""

FILES = {
    "substations/psa/substation.yaml": "name: PSA\n",
    "substations/psa/panels/p1.yaml": "id: p1\n",
}


def make_project(root: Path, project_yaml: str = PROJECT_YAML, **extra: str) -> Path:
    """Create `root` as a project folder and return the path of its `project.yaml`."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "project.yaml").write_text(project_yaml)
    for name, text in {**FILES, **extra}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root / "project.yaml"


def hold_project_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refuse to move a project folder away, as Windows does while a program uses it (a
    workbook open in Excel, a terminal inside the folder); every other rename works."""
    real_replace = os.replace

    def replace(src: str | Path, dst: str | Path) -> None:
        if Path(dst).name.startswith(".replaced-"):
            raise PermissionError(13, "Access is denied", str(src))
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", replace)
