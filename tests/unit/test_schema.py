"""JSON Schema export for the four input files."""

import json
from pathlib import Path
from typing import Any

import yaml

from bomgen.io.schema import json_schemas, write_json_schemas

NAMES = [
    "library.schema.json",
    "panel.schema.json",
    "project.schema.json",
    "substation.schema.json",
]


def test_json_schemas_cover_the_four_input_files() -> None:
    schemas = json_schemas()
    assert sorted(schemas) == NAMES
    assert schemas["project.schema.json"]["title"] == "Project"
    assert schemas["library.schema.json"]["title"] == "Library"
    assert schemas["panel.schema.json"]["title"] == "Panel"
    assert schemas["substation.schema.json"]["title"] == "Substation"
    assert "mirror_of" in json.dumps(schemas["panel.schema.json"])
    for schema in schemas.values():
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_write_json_schemas_writes_sorted_files(tmp_path: Path) -> None:
    out_dir = tmp_path / "nested" / "schemas"
    written = write_json_schemas(out_dir)
    assert [path.name for path in written] == NAMES
    assert all(path.parent == out_dir for path in written)
    expected = json_schemas()
    for path in written:
        text = path.read_text(encoding="utf-8")
        assert text.endswith("}\n")
        assert json.loads(text) == expected[path.name]
        assert text == json.dumps(expected[path.name], indent=2, sort_keys=True) + "\n"


def test_committed_schemas_are_current() -> None:
    schema_dir = Path(__file__).resolve().parents[2] / "schemas"
    for name, schema in json_schemas().items():
        committed = schema_dir / name
        assert committed.is_file(), f"{committed} is missing; run `bomgen schema`"
        assert json.loads(committed.read_text(encoding="utf-8")) == schema, (
            f"{committed} is out of date; run `bomgen schema` and commit the result"
        )


def test_excluded_from_power_is_not_required_in_schema() -> None:
    device = json_schemas()["library.schema.json"]["$defs"]["DeviceType"]
    assert "excluded_from_power" not in device["required"]
    assert device["properties"]["excluded_from_power"]["default"] is False


def test_example_files_carry_every_key_the_schemas_require() -> None:
    # Required-keys subset check; a full validator is not a dependency.
    examples = Path(__file__).resolve().parents[2] / "examples"
    schemas = json_schemas()

    def load(path: Path) -> dict[str, Any]:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        return data

    def missing(required: list[str], record: dict[str, Any]) -> list[str]:
        return [key for key in required if key not in record]

    project = load(examples / "project.yaml")
    assert missing(schemas["project.schema.json"]["required"], project) == []
    substation_dir = examples / "substations" / "gis01"
    substation = load(substation_dir / "substation.yaml")
    assert missing(schemas["substation.schema.json"]["required"], substation) == []

    library = load(examples / "library.yaml")
    library_schema = schemas["library.schema.json"]
    assert missing(library_schema["required"], library) == []
    device_required = library_schema["$defs"]["DeviceType"]["required"]
    for device in library["devices"]:
        assert missing(device_required, device) == [], device["part_id"]

    panel_defs = schemas["panel.schema.json"]["$defs"]
    for panel_file in sorted((substation_dir / "panels").glob("*.yaml")):
        panel = load(panel_file)
        kind = "PanelMirror" if "mirror_of" in panel else "Panel"
        assert missing(panel_defs[kind]["required"], panel) == [], panel_file.name
