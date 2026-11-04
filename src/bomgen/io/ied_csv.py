"""The IED schedule as text: a row's ports ("2x100M MM + 1x1G RJ45") and the CSV a protection
design gives (``bay,name,qty,ports,attachment,lands_on[,notes]``; plan M60, ADR 0034 item 5)."""

import csv
import io
import re
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from bomgen.models.library import Media, PortSpeed
from bomgen.models.substation import IedRow

COLUMNS = ("bay", "name", "qty", "ports", "attachment", "lands_on", "notes")
_PORT = re.compile(r"^(?:(\d+)\s*[x\u00d7]\s*)?(\S+)\s+(\S+)$", re.IGNORECASE)


def parse_ports(text: str) -> list[dict[str, Any]]:
    """``"2x100M MM + 1G RJ45"`` as port needs; the count defaults to 1."""
    ports = []
    for part in text.split("+"):
        found = _PORT.match(part.strip())
        speeds = {s.value.upper(): s.value for s in PortSpeed}
        media = {m.value.upper(): m.value for m in Media}
        if not found or found[2].upper() not in speeds or found[3].upper() not in media:
            raise ValueError(
                f"'{part.strip()}' is not a port: write count x speed media, e.g. 2x100M MM"
            )
        count = int(found[1]) if found[1] else 1
        ports.append(
            {"count": count, "speed": speeds[found[2].upper()], "media": media[found[3].upper()]}
        )
    return ports


def ports_text(ports: Sequence[Mapping[str, Any]]) -> str:
    return " + ".join(f"{p['count']}x{p['speed']} {p['media']}" for p in ports)


def read_schedule(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The CSV's rows as schedule rows, and the problems of the rows that are not; a row is
    numbered as the spreadsheet shows it (the header is row 1)."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    header = [c.strip().lower() for c in reader.fieldnames or []]
    if not {"bay", "name"} <= set(header):
        message = f"The file needs the columns bay, name (and may have {', '.join(COLUMNS[2:])})."
        return [], [{"row": 1, "column": None, "message": message}]
    rows, problems = [], []
    for number, raw in enumerate(reader, start=2):
        cells = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}
        row: dict[str, Any] = {k: v for k, v in cells.items() if k in COLUMNS and v}
        try:
            if "ports" in row:
                row["ports"] = parse_ports(row["ports"])
            if "qty" in row:
                row["qty"] = int(row["qty"]) if row["qty"].isdigit() else row["qty"]
            IedRow.model_validate(row)
        except ValueError as exc:
            problems.append(_problem(number, exc))
            continue
        rows.append(row)
    return rows, problems


MESSAGES = {
    "bay": "Fill in the bay.",
    "name": "Fill in the IED type or tag.",
    "qty": "Enter a whole number, 1 or more.",
    "attachment": "Write dual, single_a or single_b.",
    "lands_on": "Write l1 or l2.",
}


def _problem(number: int, exc: ValueError) -> dict[str, Any]:
    if isinstance(exc, ValidationError):
        error = exc.errors()[0]
        column = str(error["loc"][0]) if error["loc"] else None
        message = MESSAGES.get(column or "", error["msg"])
        return {"row": number, "column": column, "message": message}
    return {"row": number, "column": "ports", "message": str(exc)}


def shown(row: Mapping[str, Any] | IedRow) -> dict[str, Any]:
    """A schedule row with its defaults filled in and its ports as text, for the app."""
    model = row if isinstance(row, IedRow) else IedRow.model_validate(row)
    data = model.model_dump(mode="json")
    return data | {"ports_text": ports_text(data["ports"])}
