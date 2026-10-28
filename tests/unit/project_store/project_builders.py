"""Helpers that build a small project folder on disk for the project-store tests."""

from pathlib import Path

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
