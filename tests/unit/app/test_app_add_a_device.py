"""*Add a device* offers every role a default row has (plan M91).

A new substation starts with the default rows; one removed past Undo comes back through
*Add a device*, as the row the set-up card writes. The roles where the role matters (the
tag's OWS, EWS or SRV, the annunciator in loose material) are offered by role, the rest by
category. The model takes any number of each, except the sized switches, which it takes
exactly once; the page takes one time server, whose accessories it lists under it.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.app.parts import DEFAULT_ROWS, SIZED, offers_ab
from bomgen.engine.layout import with_layout
from bomgen.engine.pipeline import build
from bomgen.io import lifecycle
from bomgen.io.loader import load_substation
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.store import LibraryStore
from bomgen.models.substation import EquipmentRole

EXAMPLES = Path(__file__).parents[3] / "examples"

# the set-up card's picks for a new substation: every default row the example library has
# parts for (it has no KVM or console)
SET_UP: list[dict[str, Any]] = [
    {"role": "time_server", "part_id": "SEL-2488"},
    {"role": "l2_switch", "part_id": "RST2228-L2", "redundant": True},
    {"role": "operator_ws", "part_id": "SEL-3355", "redundant": True},
    {"role": "engineering_ws", "part_id": "SEL-3355"},
    {"role": "da_server", "part_id": "SEL-3355"},
    {"role": "annunciator", "part_id": "NAP-K55"},
]


@pytest.fixture
def app(tmp_path: Path) -> api.Api:
    return api.Api(
        env={
            "BOMGEN_LIBRARY_HOME": str(tmp_path / "libraries"),
            "BOMGEN_WORKSPACE": str(tmp_path / "workspace"),
            "BOMGEN_APP_HOME": str(tmp_path / "app"),
        }
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3")
    return tmp_path / "workspace" / "jfgp2-pkg3" / "project.yaml"


@pytest.fixture
def new(app: api.Api, project: Path, tmp_path: Path) -> Path:
    """A new substation "b", set up with the default rows."""
    lifecycle.create_substation(project, "b", "b", store=LibraryStore(tmp_path / "libraries"))
    ok(app.start_parts(str(project), "b", SET_UP))
    return project


def ok(envelope: dict[str, object]) -> Any:
    assert envelope["ok"] is True, envelope
    json.dumps(envelope)
    return envelope["data"]


def page(app: api.Api, project: Path, sid: str = "b") -> Any:
    return ok(app.parts_page(str(project), sid))["parts"]


def written(project: Path) -> list[dict[str, Any]]:
    rows = read_yaml(project.parent / "substations" / "b" / "substation.yaml").data["equipment"]
    plain: list[dict[str, Any]] = json.loads(json.dumps(rows))  # as plain dicts, in key order
    return plain


def offered(app: api.Api, project: Path, sid: str = "b") -> dict[str, Any]:
    """Add a device's entries that make a row of a role other than "other", by role."""
    entries = page(app, project, sid)["add_categories"]
    return {e["role"]: e for e in entries if e["role"] != "other"}


def remove(app: api.Api, project: Path, role: str) -> dict[str, Any]:
    index = next(r["index"] for r in page(app, project)["rows"] if r["role"] == role)
    removed: dict[str, Any] = ok(app.remove_equipment(str(project), "b", index))["row"]
    return removed


def add(app: api.Api, project: Path, entry: dict[str, Any], part_id: str, ab: bool) -> None:
    """What the Add dialog writes: the entry's role, its id (the set-up card's for a role,
    numbered when taken) and the part; A and B only when ticked."""
    taken = {r["id"] for r in written(project)}
    base = entry["id"] or part_id.lower()
    row_id, n = base, 2
    while row_id in taken:
        row_id, n = f"{base}-{n}", n + 1
    row: dict[str, Any] = {"id": row_id, "part_id": part_id, "role": entry["role"]}
    if ab:
        row["redundant"] = True
    ok(app.add_equipment(str(project), "b", row, None, True))


def tags(project: Path) -> list[str]:
    file = project.parent / "substations" / "b" / "substation.yaml"
    result = build(with_layout(load_substation(file))[0])
    return [line.tag for panel in result.panels for line in panel.lines if line.tag]


def test_add_a_device_offers_the_time_server_when_the_row_is_gone(app: api.Api, new: Path) -> None:
    assert "time_server" not in offered(app, new)  # the substation has one

    remove(app, new, "time_server")

    entry = offered(app, new)["time_server"]
    assert entry["label"] == "Time server clock"
    assert entry["category"] == "gps_clock"
    assert entry["id"] == "gps"
    assert "SEL-2488" in [c["part_id"] for c in entry["choices"]]


def test_add_a_device_offers_the_annunciator_when_the_row_is_gone(app: api.Api, new: Path) -> None:
    remove(app, new, "annunciator")

    entry = offered(app, new)["annunciator"]
    assert entry["label"] == "Annunciator"
    assert entry["id"] == "ann"
    assert "NAP-K55" in [c["part_id"] for c in entry["choices"]]


def test_add_a_device_offers_every_role_a_default_row_has(app: api.Api, new: Path) -> None:
    """By role first, in the default rows' order, then the categories; never the sized
    switches, which the model takes exactly once."""
    remove(app, new, "time_server")

    entries = page(app, new)["add_categories"]

    roles = [e["role"] for e in entries[:7]]
    assert roles == [r.value for r in DEFAULT_ROWS if r not in SIZED]
    assert not {"l1_switch", "l2_switch"} & {e["role"] for e in entries}
    labels = [e["label"] for e in entries[7:]]
    assert labels == [
        "Fibre patch panel",
        "Firewall",
        "Switch",
        "Gateway",
        "RedBox",
        "Media converter",
        "RTAC",
        "I/O rack",
        "Workstation",
        "Monitor",
        "Keyboard and mouse",
    ]
    assert all(e["id"] is None for e in entries[7:])  # named by their part, as before


def test_add_does_not_offer_a_role_the_substation_already_has(
    app: api.Api, new: Path, project: Path
) -> None:
    """One time server: its accessories are listed under its row. A row of another role
    whose part is a clock (the example's gps row, role other) is that time server."""
    assert "time_server" not in offered(app, new)
    assert "time_server" not in offered(app, project, "gis01")


def test_add_offers_a_second_workstation_and_annunciator(app: api.Api, new: Path) -> None:
    """The model takes any number of these rows; a second operator workstation is usual."""
    roles = offered(app, new)

    for role in ("operator_ws", "engineering_ws", "da_server", "annunciator"):
        assert roles[role]["choices"]


@pytest.mark.parametrize(
    ("role", "code"),
    [("operator_ws", "OWS"), ("engineering_ws", "EWS"), ("da_server", "SRV")],
)
def test_an_added_operator_workstation_is_tagged_ows(
    app: api.Api, new: Path, role: str, code: str
) -> None:
    """ADR 0030: the workstation roles share one part, so the role gives the type code."""
    remove(app, new, role)
    assert not [t for t in tags(new) if f"-{code}-" in t]

    add(app, new, offered(app, new)[role], "SEL-3355", ab=False)

    (tag,) = [t for t in tags(new) if f"-L2-{code}-" in t]
    assert tag.endswith("01")
    assert not [t for t in tags(new) if "SRV/OAS/EAS" in t]


def test_a_workstation_added_as_other_takes_the_librarys_type_code(app: api.Api, new: Path) -> None:
    """A fourth computer, with no role, is tagged with its part's own type code."""
    entries = page(app, new)["add_categories"]
    other = next(e for e in entries if e["category"] == "workstation" and e["role"] == "other")

    add(app, new, other, "SEL-3355", ab=False)

    (tag,) = [t for t in tags(new) if "SRV/OAS/EAS" in t]
    assert tag.endswith(("-L2-SRV/OAS/EAS-A01", "-L2-SRV/OAS/EAS-B01"))


@pytest.mark.parametrize("role", ["time_server", "operator_ws", "da_server", "annunciator"])
def test_an_added_row_is_the_row_the_set_up_card_writes(app: api.Api, new: Path, role: str) -> None:
    """Same id, role, part, A and B and L2 link (M89) in the file: the time server's link
    is 100M, a workstation's RJ45, the annunciator has none."""
    removed = remove(app, new, role)

    add(app, new, offered(app, new)[role], removed["part_id"], ab=bool(removed.get("redundant")))

    back = written(new)[-1]
    assert back == removed
    assert list(back) == list(removed)


def test_the_add_dialog_offers_a_and_b_only_where_the_row_does(app: api.Api, new: Path) -> None:
    remove(app, new, "time_server")

    for entry in page(app, new)["add_categories"]:
        assert entry["ab"] is offers_ab(EquipmentRole(entry["role"])), entry["label"]
    assert offered(app, new)["annunciator"]["ab"] is False
    assert offered(app, new)["operator_ws"]["ab"] is True


def test_kvm_and_console_stay_offered_with_no_parts(app: api.Api, new: Path) -> None:
    """Backlog v0.3, point 7: the shipped library has none, and the rows stay empty."""
    roles = offered(app, new)

    assert (roles["kvm"]["label"], roles["kvm"]["choices"]) == ("KVM", [])
    assert (roles["console"]["label"], roles["console"]["choices"]) == ("Console", [])
