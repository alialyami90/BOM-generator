"""A new hand-written panel from the Add hand-written panel dialog (plan M32b).

The dialog asks for a name, a cabinet number, a kind and the first device (a panel
lists at least one). The rest starts from the substation: the generated panels'
enclosure and document when it has them (else the first panel's enclosure and the
workbook's document), and the next free sheet number.
"""

from __future__ import annotations

import re
from typing import Any

from bomgen.io.loader import LoadedSubstation


def _free(taken: set[str], base: str) -> str:
    return next(c for c in (base, *(f"{base}-{n}" for n in range(2, 1000))) if c not in taken)


def new_panel(loaded: LoadedSubstation, fields: dict[str, Any]) -> dict[str, Any]:
    """The panel file for ``fields`` (name, cabinet_number, kind, part_id)."""
    name = str(fields["name"]).strip()
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "panel"
    panel_id = _free({p.id for p in loaded.panels}, slug if slug[0].isalnum() else "panel")
    word = re.sub(r"[^A-Z0-9]", "", (name.split() or ["P"])[0].upper())
    prefix = word if word[:1].isalpha() else f"P{word}"
    sheets = {p.sheet_name for p in loaded.panels}
    sheet = next(str(n) for n in range(len(loaded.panels) + 1, 1000) if str(n) not in sheets)
    generated = loaded.substation.generated_panels
    first = loaded.panels[0] if loaded.panels else None
    enclosure = generated.enclosure if generated else first.enclosure if first else None
    return {
        "id": panel_id,
        "cabinet_number": str(fields["cabinet_number"]).strip(),
        "cabinet_name": name,
        "tag_prefix": prefix,
        "sheet_name": sheet,
        "kind": fields["kind"],
        "enclosure": enclosure.model_dump(mode="json", exclude_none=True) if enclosure else {},
        "devices": [{"part_id": fields["part_id"]}],
        "document": generated.document if generated else loaded.substation.document,
    }
