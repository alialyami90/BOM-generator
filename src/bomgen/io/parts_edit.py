"""Writers for the Parts page (plan M23, ADR 0024).

The generic field writer (``io/fields.py``) writes any key; these add the rules it cannot
know: an override equal to the library value is no override, a changed part drops what
described the old one, and a new substation's rows are written together with its sized
L1 switch. Every writer is checked against the whole project before it writes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from bomgen.io.edit import EditError, EditResult, edit_substation, substation_file
from bomgen.io.errors import InputError
from bomgen.io.loader import load_project
from bomgen.io.round_trip import insert_entry, load_text, remove_entry, set_entry
from bomgen.models.library import DeviceType
from bomgen.models.substation import EquipmentRole, PartOverrides

if TYPE_CHECKING:
    from bomgen.library_store.store import LibraryStore

# the ids a new substation's rows get, by role (design §3 rows)
ROLE_IDS = {
    EquipmentRole.TIME_SERVER: "gps",
    EquipmentRole.L2_SWITCH: "l2",
    EquipmentRole.L1_SWITCH: "l1",
    EquipmentRole.OPERATOR_WS: "ows",
    EquipmentRole.ENGINEERING_WS: "ews",
    EquipmentRole.DA_SERVER: "da",
    EquipmentRole.KVM: "kvm",
    EquipmentRole.CONSOLE: "console",
    EquipmentRole.ANNUNCIATOR: "ann",
}
NO_L2 = "Pick the L2 switch first: the network is sized from it."
# what a part change clears: it described the old part (decision 1 of the M23 plan)
OLD_PART_KEYS = ("overrides", "sfp", "ordering_code")


def _entry(data: CommentedMap, index: int) -> CommentedMap:
    rows = data.get("equipment")
    if not isinstance(rows, CommentedSeq) or not 0 <= index < len(rows):
        raise EditError(f"no equipment row {index + 1}")
    row = rows[index]
    if not isinstance(row, CommentedMap):
        raise EditError(f"equipment row {index + 1} is not a mapping")
    return row


def _base_part(
    project_file: Path, part_id: object, store: LibraryStore | None
) -> DeviceType | None:
    """The project library's part ``part_id``, or None when the project does not load."""
    if not isinstance(part_id, str):
        return None
    try:
        return load_project(project_file, store=store).library.get(part_id)
    except InputError:
        return None


def _typed(field: str, value: object) -> object | None:
    """``value`` as the YAML file holds a valid ``field`` override, or None if invalid."""
    try:
        checked = PartOverrides.model_validate({field: value})
    except ValidationError:
        return None
    found: object = checked.model_dump(mode="json")[field]
    return found


def _row_of(project_file: Path, substation_id: str, index: int) -> CommentedMap:
    file = substation_file(project_file, substation_id)
    return _entry(load_text(file.read_text(encoding="utf-8-sig")), index)


def set_override(
    project_file: Path,
    substation_id: str,
    index: int,
    field: str,
    value: object,
    *,
    store: LibraryStore | None = None,
) -> EditResult:
    """Override ``field`` of equipment row ``index``. ``None``, or the library part's own
    value, removes the override; the last one removed takes ``overrides`` with it."""
    if field not in PartOverrides.model_fields:
        raise EditError(f"'{field}' is not a value a part can override")
    base = _base_part(
        project_file, _row_of(project_file, substation_id, index).get("part_id"), store
    )
    typed = _typed(field, value) if value is not None else None
    same = (
        base is not None
        and typed is not None
        and PartOverrides.model_validate({field: typed}).values()[field] == getattr(base, field)
    )

    def change(data: CommentedMap) -> None:
        row = _entry(data, index)
        overrides = row.get("overrides")
        if value is None or same:
            if isinstance(overrides, CommentedMap) and field in overrides:
                remove_entry(overrides, field)
                if not overrides:
                    remove_entry(row, "overrides")
            return
        if not isinstance(overrides, CommentedMap):
            set_entry(row, "overrides", {})
            overrides = row["overrides"]
        set_entry(overrides, field, typed if typed is not None else value)

    return edit_substation(project_file, substation_id, change, store=store)


def set_sfp_choice(
    project_file: Path,
    substation_id: str,
    index: int,
    speed: str,
    media: str,
    part_id: str | None,
    *,
    store: LibraryStore | None = None,
) -> EditResult:
    """Choose the SFP for ``speed`` and ``media`` on equipment row ``index``; ``None``
    goes back to the automatic pick, and the last choice removed takes ``sfp`` with it."""

    def change(data: CommentedMap) -> None:
        row = _entry(data, index)
        choices = row.get("sfp")
        if not isinstance(choices, CommentedSeq):
            if part_id is None:
                return
            set_entry(row, "sfp", [])
            choices = row["sfp"]
        at = next(
            (
                i
                for i, c in enumerate(choices)
                if str(c.get("speed")) == speed and str(c.get("media")) == media
            ),
            None,
        )
        if part_id is None:
            if at is not None:
                remove_entry(choices, at)
            if not choices:
                remove_entry(row, "sfp")
            return
        choice = {"speed": speed, "media": media, "part_id": part_id}
        if at is None:
            insert_entry(choices, len(choices), choice)
        else:
            set_entry(choices[at], "part_id", part_id)

    return edit_substation(project_file, substation_id, change, store=store)


def set_equipment_part(
    project_file: Path,
    substation_id: str,
    index: int,
    part_id: str,
    *,
    store: LibraryStore | None = None,
) -> tuple[EditResult, tuple[str, ...]]:
    """Give equipment row ``index`` another part. Its overrides, SFP choices and part
    number described the old part, so they go; returns the result and what was cleared."""
    row = _row_of(project_file, substation_id, index)
    if row.get("part_id") == part_id:
        return EditResult(False, ()), ()
    cleared = tuple(k for k in OLD_PART_KEYS if k in row)

    def change(data: CommentedMap) -> None:
        target = _entry(data, index)
        set_entry(target, "part_id", part_id)
        for key in cleared:
            remove_entry(target, key)

    return edit_substation(project_file, substation_id, change, store=store), cleared


def start_parts(
    project_file: Path,
    substation_id: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    store: LibraryStore | None = None,
) -> EditResult:
    """A new substation's first equipment: the rows with a part, in order, and the sized
    L1 switch, written together because the model takes no equipment without the L1 and
    L2 switches (ADR 0013)."""
    picked: list[dict[str, Any]] = []
    for row in rows:
        role = EquipmentRole(row["role"])
        if row.get("part_id") or role is EquipmentRole.L1_SWITCH:
            picked.append(dict(row))
    if not any(r["role"] == EquipmentRole.L2_SWITCH and r.get("part_id") for r in picked):
        raise EditError(NO_L2)
    if not any(r["role"] == EquipmentRole.L1_SWITCH for r in picked):
        picked.append({"role": EquipmentRole.L1_SWITCH.value, "redundant": True})
    taken: set[str] = set()
    for r in picked:
        if not r.get("id"):
            base = ROLE_IDS.get(EquipmentRole(r["role"]), "device")
            r["id"], n = base, 2
            while r["id"] in taken:
                r["id"], n = f"{base}-{n}", n + 1
        taken.add(r["id"])

    def change(data: CommentedMap) -> None:
        if data.get("equipment"):
            raise EditError("This substation already has equipment.")
        set_entry(
            data, "equipment", [{k: v for k, v in r.items() if v not in (None, "")} for r in picked]
        )

    return edit_substation(project_file, substation_id, change, store=store)
