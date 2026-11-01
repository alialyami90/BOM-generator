"""The Library's Catalogues tab: brand sets as rows, and the edits that change them (M36).

docs/ui/editing.md "Catalogues tab". The default brand is ``catalogues.<kind>``; the others
are ``catalogue_brands.<kind>`` (ADR 0017). The page edits a brand as rows; this module turns
rows back into the model's shape and into one whole-value edit per catalogue, so the pending
set keeps one entry per catalogue and a value set back to the saved one leaves it.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from bomgen.models.library import DEFAULT_BRAND, Library

KINDS = ("mcb", "aux_contact", "terminal_blocks", "busbars", "housekeeping")
_ROWS = {"terminal_blocks": "types", "busbars": "entries"}  # a brand's mapping of rows
# Housekeeping roles as rows: a role is a key, or a key and a sub-key of a mapping.
ROLES = (
    ("lamp", ("lamp", "part_id")),
    ("door_switch", ("door_switch", "part_id")),
    ("fan", ("fan", "part_id")),
    ("vent_filter", ("vent_filter", "part_id")),
    ("thermostat", ("thermostat", "part_id")),
    ("ipr_kit", ("ipr_kit", "part_id")),
    ("change_over_diode_negative", ("change_over_diodes", "negative")),
    ("change_over_diode_positive", ("change_over_diodes", "positive")),
    ("socket", ("socket", "part_id")),
    ("nameplate", ("nameplate", "part_id")),
)


class CatalogueEditError(ValueError):
    """A catalogue change the page asked for that does not fit (the message says why)."""


def _sets(library: Library, kind: str) -> list[tuple[str, dict[str, Any]]]:
    """(brand id, model value) of each brand of `kind`, the default first."""
    data = library.model_dump(mode="json", exclude_none=True)
    default = data["catalogues"][kind]
    if kind in _ROWS:
        default = {"id": DEFAULT_BRAND, _ROWS[kind]: default}
    brands = data.get("catalogue_brands", {}).get(kind, [])
    return [(DEFAULT_BRAND, default), *((b["id"], b) for b in brands)]


def _label(kind: str, value: dict[str, Any]) -> str:
    if value.get("name"):
        return str(value["name"])
    if kind == "mcb":
        return f"{value['make']} {value['family']}"
    if kind == "aux_contact":
        return f"{value['make']} {value['model']}"
    if kind == "housekeeping":
        return "Standard kit" if value.get("id", DEFAULT_BRAND) == DEFAULT_BRAND else value["id"]
    rows = value.get(_ROWS.get(kind, ""), {})
    makes = sorted({r["make"] for r in rows.values() if r.get("make")})
    return ", ".join(makes) or str(value.get("id", ""))


def _code(mcb: dict[str, Any], rating: int) -> str:
    codes = mcb.get("codes")
    if codes is not None:
        return str(codes[str(rating)] if str(rating) in codes else codes[rating])
    return str(mcb["code_pattern"].format(rating=rating))


def to_rows(kind: str, value: dict[str, Any]) -> dict[str, Any]:
    """A brand's model value as the page edits it."""
    named = {"name": value.get("name")} if value.get("id", DEFAULT_BRAND) != DEFAULT_BRAND else {}
    if kind == "mcb":
        rows = [{"rating_a": a, "code": _code(value, a)} for a in value["ratings_a"]]
        return {**named, "make": value["make"], "family": value["family"], "rows": rows}
    if kind == "aux_contact":
        return {**named, **{k: value[k] for k in ("make", "model", "ordering_code")}}
    if kind == "housekeeping":
        rows = []
        for role, (key, sub) in ROLES:
            rows.append({"role": role, "part_id": (value.get(key) or {}).get(sub)})
        return {**named, "rows": rows}
    rows = [{"key": key, **row} for key, row in value[_ROWS[kind]].items()]
    return {**named, "rows": rows}


def from_rows(
    kind: str, old: dict[str, Any], page: dict[str, Any], pattern: str | None = None
) -> dict[str, Any]:
    """The model value of a brand edited as rows; fields the page does not show are kept.
    An MCB set keeps (or gets back) `pattern`, its saved code pattern, while the codes fit it."""
    new = copy.deepcopy(old)
    if "name" in page and new.get("id", DEFAULT_BRAND) != DEFAULT_BRAND:
        if page["name"]:
            new["name"] = page["name"]
        else:
            new.pop("name", None)
    if kind == "mcb":
        rows = page["rows"]
        new.update(make=page["make"], family=page["family"])
        new["ratings_a"] = [r["rating_a"] for r in rows]
        pattern = new.get("code_pattern") or pattern
        try:
            fits = pattern is not None and all(
                pattern.format(rating=r["rating_a"]) == r["code"] for r in rows
            )
        except (ValueError, TypeError):  # a rating that is not a number; the model says so
            fits = False
        if fits:
            new.pop("codes", None)
            new["code_pattern"] = pattern
        else:
            new.pop("code_pattern", None)
            new["codes"] = {str(r["rating_a"]): r["code"] for r in rows}  # as JSON keeps them
        return new
    if kind == "aux_contact":
        new.update({k: page[k] for k in ("make", "model", "ordering_code")})
        return new
    if kind == "housekeeping":
        for row in page["rows"]:
            key, sub = dict(ROLES)[row["role"]]
            if row["part_id"]:
                new.setdefault(key, {})[sub] = row["part_id"]
            elif key in new:
                del new[key]  # only the optional roles may be left empty; the model says so
        return new
    new[_ROWS[kind]] = {r["key"]: {k: v for k, v in r.items() if k != "key"} for r in page["rows"]}
    return new


def page(library: Library, saved: Library) -> dict[str, Any]:
    """Every catalogue's brands as rows, marked when they differ from the saved version."""
    kinds: dict[str, list[dict[str, Any]]] = {}
    for kind in KINDS:
        before = dict(_sets(saved, kind))
        kinds[kind] = [
            {
                "id": brand_id,
                "label": _label(kind, value),
                "default": brand_id == DEFAULT_BRAND,
                "changed": before.get(brand_id) != value,
                "ac_rated": value.get("ac_rated", True) if kind == "mcb" else None,
                "value": to_rows(kind, value),
            }
            for brand_id, value in _sets(library, kind)
        ]
    return {"kinds": kinds, "parts": sorted(library.part_ids())}


def _whole(library: Library, kind: str, sets: list[tuple[str, dict[str, Any]]]) -> list[Any]:
    """The edits that write `sets` (default first) as the library's brands of `kind`."""
    default = sets[0][1]
    if kind in _ROWS:
        default = default[_ROWS[kind]]
    now = _sets(library, kind)
    edits: list[dict[str, Any]] = []
    if sets[0] != now[0]:
        edits.append({"op": "set", "path": ["catalogues", kind], "value": default})
    if sets[1:] != now[1:]:
        brands = [v for _, v in sets[1:]]
        edits.append({"op": "set", "path": ["catalogue_brands", kind], "value": brands})
    return edits


def set_brand(
    library: Library, kind: str, brand_id: str, rows: dict[str, Any], saved: Library
) -> list[Any]:
    """The edits that give brand `brand_id` of `kind` the page's `rows`."""
    sets = _sets(library, kind)
    at = next((i for i, (b, _) in enumerate(sets) if b == brand_id), None)
    if at is None:
        raise CatalogueEditError(f"there is no {kind} brand '{brand_id}'")
    pattern = dict(_sets(saved, kind)).get(brand_id, {}).get("code_pattern")
    sets[at] = (brand_id, from_rows(kind, sets[at][1], rows, pattern))
    return _whole(library, kind, sets)


def add_brand(library: Library, kind: str, brand_id: str, name: str, copy_of: str) -> list[Any]:
    """The edits that add brand `brand_id`, a copy of brand `copy_of`'s rows."""
    sets = _sets(library, kind)
    if brand_id in (b for b, _ in sets):
        raise CatalogueEditError(f"{kind} already has a brand '{brand_id}'")
    source = next((v for b, v in sets if b == copy_of), None)
    if source is None:
        raise CatalogueEditError(f"there is no {kind} brand '{copy_of}'")
    new = {**copy.deepcopy(source), "id": brand_id}
    new.pop("name", None)
    if name:
        new["name"] = name
    return _whole(library, kind, [*sets, (brand_id, new)])


def _free_id(value: dict[str, Any], taken: set[str]) -> str:
    words = [value.get("make") or "", value.get("family") or value.get("model") or ""]
    for text in (words[0], " ".join(words), "previous-default"):
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        if slug and slug not in taken:
            return slug
    n = 2
    while f"previous-default-{n}" in taken:
        n += 1
    return f"previous-default-{n}"


def make_default(library: Library, kind: str, brand_id: str) -> list[Any]:
    """The edits that make brand `brand_id` the default; the old default becomes a brand."""
    sets = _sets(library, kind)
    found = next((v for b, v in sets if b == brand_id and b != DEFAULT_BRAND), None)
    if found is None:
        raise CatalogueEditError(f"there is no {kind} brand '{brand_id}'")
    if kind == "mcb" and found.get("ac_rated") is False:
        raise CatalogueEditError(
            f"{_label(kind, found)} is DC only, so it cannot be the default MCB set"
        )
    old = {**sets[0][1], "id": _free_id(sets[0][1], {b for b, _ in sets})}
    if kind in _ROWS:
        old = {"id": old["id"], _ROWS[kind]: old[_ROWS[kind]]}
    promoted = {k: v for k, v in found.items() if k not in ("id", "name", "ac_rated")}
    rest = [(b, v) for b, v in sets[1:] if b != brand_id]
    return _whole(library, kind, [(DEFAULT_BRAND, promoted), (old["id"], old), *rest])
