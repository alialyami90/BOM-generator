"""One line of an import review: what was checked and how it came out."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bomgen.bundle.errors import RefusalKind


class CheckStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Check:
    """A check the import review shows. `kind` is set on a failed check."""

    id: str
    label: str
    status: CheckStatus
    detail: str = ""
    kind: RefusalKind | None = None
