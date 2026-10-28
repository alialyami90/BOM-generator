"""The step 15 check report and the OUT-8 revision comparison (spec: Data model and
generation order, step 15; Output requirements, OUT-8; plan M7, Q10)."""

from enum import StrEnum

from pydantic import Field

from bomgen.models.bom import Column
from bomgen.models.output import OutputModel


class CheckStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class CheckItem(OutputModel):
    """One check on one panel or device; ``values`` carries the compared numbers."""

    check: str
    status: CheckStatus
    panel_id: str | None = None
    subject: str | None = None
    message: str
    values: dict[str, int | float | str] = Field(default_factory=dict)


class CheckReport(OutputModel):
    items: tuple[CheckItem, ...]

    @property
    def failed(self) -> bool:
        """Any failed check; ``bomgen build`` exits non-zero on it."""
        return any(item.status is CheckStatus.FAIL for item in self.items)

    def count(self, status: CheckStatus) -> int:
        return sum(1 for item in self.items if item.status is status)

    def with_items(self, *items: CheckItem) -> "CheckReport":
        return CheckReport(items=(*self.items, *items))


class PreviousTable(OutputModel):
    """One BOM table of a previous issue: each row's B-H cells as text."""

    rows: tuple[dict[Column, str], ...]


class PreviousIssue(OutputModel):
    """The BOM tables of a previously issued workbook, by sheet name in sheet order."""

    source: str
    sheets: dict[str, tuple[PreviousTable, ...]]


class RevisionKind(StrEnum):
    CHANGED = "changed"
    ADDED = "added"
    REMOVED = "removed"


class RevisionChange(OutputModel):
    """A row added, changed or removed since the previous issue (OUT-8, plan Q10)."""

    sheet: str
    kind: RevisionKind
    tag: str | None
    description: str
    columns: frozenset[Column] = frozenset()


class RevisionReport(OutputModel):
    previous: str
    changes: tuple[RevisionChange, ...]
