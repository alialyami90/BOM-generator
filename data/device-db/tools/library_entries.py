"""Add the device database's alternative tiers to the shipped library as parts (M14).

Usage: ``python data/device-db/tools/library_entries.py``

Each distinct tier (one with no ``same_as``) of a ``data/device-db`` record whose part is an
original in ``examples/library.yaml`` becomes a part with the original's ``alt_group`` and a
``tier``. Parts already in the example or in ``data/library/additions.yaml`` are left alone,
so a second run adds nothing. New parts are appended to the additions' ``devices`` list
(plan Q38: the example stays the spec's example); run ``python data/library/build.py``
after. A powered tier with no ``unit_power_w`` is skipped and printed (finding 30).
"""

import re
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import yaml

COPY_FROM_ORIGINAL = ("tag_type", "purdue_level", "tag_pattern")
COPY_AFTER_POWER = ("alarm_on_branch_mcb", "hwio_points", "cores", "terminals")
MEDIA = {"MM", "SM", "RJ45"}
TIERS = ("low", "mid", "high")
POWERED = ("VDC", "VAC")

Part = dict[str, Any]


def slug(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", text.upper()).strip("-")


def alt_id(part_id: str, make: str, tier: str) -> str:
    return f"{part_id}.{slug(make)}-{tier.upper()}"


def _number(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _ports(groups: Iterable[Part]) -> list[Part]:
    out = []
    for group in groups:
        port: Part = {"count": group["count"], "speed": group["speed"]}
        if group["media"] in MEDIA:
            port["media"] = group["media"]
        elif group["kind"] == "fixed":
            raise ValueError(f"fixed port group without media: {group}")
        port["kind"] = group["kind"]
        port["usable_for"] = group["usable_for"]
        out.append(port)
    return out


def _tiers(record: Part) -> Iterator[tuple[str, str, Part]]:
    for alternative in record["alternatives"]:
        for tier in TIERS:
            part = alternative["tiers"][tier]
            if "same_as" not in part:
                yield alternative["make"], tier, part


def _kit(original: Part, make: str, tier: str, key: str, known: set[str]) -> list[Part]:
    """The same-brand, same-tier alternative of each kit part where there is one."""
    out = []
    for item in original.get(key) or []:
        child = dict(item)
        if alt_id(item["part_id"], make, tier) in known:
            child["part_id"] = alt_id(item["part_id"], make, tier)
        out.append(child)
    return out


def _part(original: Part, make: str, tier: str, data: Part, known: set[str]) -> Part:
    part: Part = {"part_id": alt_id(original["part_id"], make, tier)}
    part["category"] = original["category"]
    if data.get("mounting_kind") != "rack":
        part["height_u"] = 0
    elif data.get("height_u"):
        part["height_u"] = data["height_u"]  # unknown rack height stays out
    part["make"] = make
    part["model"] = str(data["model"])
    if data.get("ordering_code"):
        part["ordering_code"] = str(data["ordering_code"])
    part["description_template"] = original["description_template"]
    part.update({key: original[key] for key in COPY_FROM_ORIGINAL if key in original})
    if data.get("supply_type") in POWERED:
        part["supply_type"] = data["supply_type"]
        part["voltage_v"] = round(data["voltage_v"])
        part["unit_power_w"] = _number(data["unit_power_w"])
        part["load_type"] = original.get("load_type", "CONTINUOUS")
        if data["supply_type"] == "VDC":
            part["power_supplies"] = data.get("power_supplies", 1)
        if original.get("excluded_from_power") is True:
            part["excluded_from_power"] = True
        for key in ("inrush_a", "inrush_ms", "input_v_min", "input_v_max"):
            if key in data:
                part[key] = _number(data[key])
    part.update({key: original[key] for key in COPY_AFTER_POWER if key in original})
    if data.get("port_groups"):
        part["ports"] = _ports(data["port_groups"])
    for key in ("children", "loose_items"):
        if original.get(key):
            part[key] = _kit(original, make, tier, key, known)
    part["alt_group"] = original.get("alt_group", original["part_id"])
    part["tier"] = tier
    return part


def alternative_parts(
    originals: Iterable[Part], records: dict[str, Part], existing: set[str]
) -> tuple[list[Part], list[str]]:
    """The parts to add, and a line for each powered tier skipped for want of a figure."""
    pending: list[tuple[Part, str, str, Part]] = []
    skipped = []
    for original in originals:
        record = records.get(original["part_id"])
        if record is None:
            continue
        for make, tier, data in _tiers(record):
            if alt_id(original["part_id"], make, tier) in existing:
                continue
            if data.get("supply_type") in POWERED and "unit_power_w" not in data:
                name = f"{original['part_id']} {make} {tier} {data['model']}"
                skipped.append(f"{name}: no power figure")
                continue
            pending.append((original, make, tier, data))
    known = existing | {alt_id(o["part_id"], make, tier) for o, make, tier, _ in pending}
    return [_part(o, make, tier, data, known) for o, make, tier, data in pending], skipped


def inputs(root: Path) -> tuple[list[Part], dict[str, Part], set[str]]:
    """The example's originals, the database records and every part id already shipped."""
    example = yaml.safe_load((root / "examples" / "library.yaml").read_text(encoding="utf-8"))
    additions = yaml.safe_load(
        (root / "data" / "library" / "additions.yaml").read_text(encoding="utf-8")
    )
    records: dict[str, Part] = {}
    for path in sorted((root / "data" / "device-db").glob("*.yaml")):
        for record in yaml.safe_load(path.read_text(encoding="utf-8"))["records"]:
            records[record["part_id"]] = record
    originals = [d for d in example["devices"] if "tier" not in d]
    existing = {d["part_id"] for d in example["devices"] + additions["devices"]}
    return originals, records, existing


def append_to_additions(path: Path, parts: list[Part]) -> None:
    """Insert the parts at the end of the additions' ``devices`` list."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^(?!devices:)[a-z_]+:", text, flags=re.MULTILINE)
    end = match.start() if match else len(text)
    body = yaml.safe_dump(parts, sort_keys=False, allow_unicode=True, width=100)
    block = "".join("  " + line if line.strip() else line for line in body.splitlines(True))
    path.write_text(text[:end] + block + text[end:], encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    parts, skipped = alternative_parts(*inputs(root))
    if parts:
        append_to_additions(root / "data" / "library" / "additions.yaml", parts)
    print(f"{len(parts)} alternative parts added; skipped {len(skipped)}:")
    print("\n".join("  " + line for line in skipped))


if __name__ == "__main__":
    main()
