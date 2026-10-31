"""Derived parts: a library part with one equipment entry's part number, overrides and SFP
choice, added to that substation's library only (ADR 0024)."""

from pydantic import ValidationError

from bomgen.io.errors import Loc
from bomgen.models.library import DeviceType, Library
from bomgen.models.panel import Panel
from bomgen.models.substation import Equipment, Substation

_VALUE_ERROR_PREFIX = "Value error, "


def needs_derived(entry: Equipment) -> bool:
    """Whether ``entry`` changes its library part."""
    return entry.ordering_code is not None or entry.overrides is not None or bool(entry.sfp)


def derived_id(entry: Equipment) -> str:
    return f"{entry.part_id}+{entry.id}"


def effective_part_id(entry: Equipment) -> str | None:
    """The part the layout places for ``entry``: its derived part when it has one."""
    return (
        derived_id(entry) if entry.part_id is not None and needs_derived(entry) else entry.part_id
    )


def derive_parts(library: Library, substation: Substation) -> tuple[Library, list[tuple[Loc, str]]]:
    """``library`` with a derived part per changed equipment entry, and the problems found.

    Returns ``library`` itself when no entry changes its part. An entry whose part is not in
    the library is left to the equipment check.
    """
    taken = set(library.part_ids())
    added: list[DeviceType] = []
    problems: list[tuple[Loc, str]] = []
    for index, entry in enumerate(substation.equipment):
        base = library.get(entry.part_id) if entry.part_id is not None else None
        if base is None or not needs_derived(entry):
            continue
        part_id = derived_id(entry)
        if part_id in taken:
            message = (
                f"the part id '{part_id}' for this entry's overrides is a library part "
                "already; rename the entry"
            )
            problems.append((("equipment", index, "id"), message))
            continue
        data = base.model_dump(exclude_unset=True)
        if entry.overrides is not None:
            data |= entry.overrides.values()
        if entry.ordering_code is not None:
            data["ordering_code"] = entry.ordering_code
        data |= {"part_id": part_id, "derived_from": base.part_id, "sfp_choice": entry.sfp}
        try:
            added.append(DeviceType.model_validate(data))
        except ValidationError as error:
            message = error.errors()[0]["msg"].removeprefix(_VALUE_ERROR_PREFIX)
            problems.append((("equipment", index, "overrides"), message))
    if not added:
        return library, problems
    # model_copy does not re-validate, so the library's refusal of derived parts is kept
    return library.model_copy(update={"devices": [*library.devices, *added]}), problems


def without_stale_derived(panel: Panel, library: Library) -> Panel:
    """A generated panel with each row naming a derived part that no longer exists (an
    override removed, an entry renamed) put back on its library part, so the substation
    still loads and the layout can rewrite the panel (ADR 0024). The file is not changed."""
    if not panel.generated:
        return panel
    known = set(library.part_ids())
    renamed: dict[str, str] = {}
    for device in panel.devices:
        base, plus, _entry = device.part_id.rpartition("+")
        if plus and device.part_id not in known and base in known:
            renamed[device.part_id] = base
    if not renamed:
        return panel
    devices = [
        d.model_copy(update={"part_id": renamed[d.part_id]}) if d.part_id in renamed else d
        for d in panel.devices
    ]
    port_plans = {renamed.get(key, key): plan for key, plan in panel.port_plans.items()}
    return panel.model_copy(update={"devices": devices, "port_plans": port_plans})
