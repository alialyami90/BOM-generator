"""One substation's build, shared by ``bomgen build`` and the desktop app.

Engine, revision compare, sheets, workbook and check report, in that order. The caller
lays out first (``engine.layout.with_layout``) so it can show the layout's lines whatever
happens next. Errors keep their types: ``EngineError`` from the engine, ``WriterError``
(or ``OSError``) from writing.
"""

import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from bomgen.checks import check_report
from bomgen.checks import render_json as render_checks_json
from bomgen.engine.errors import EngineError
from bomgen.engine.pipeline import build as build_bom
from bomgen.io.errors import InputError
from bomgen.io.fields import insert_item
from bomgen.io.loader import LoadedSubstation
from bomgen.models.bom import BuildResult
from bomgen.models.report import CheckReport, PreviousIssue, RevisionReport
from bomgen.models.substation import IssueRecord, OverrideNote
from bomgen.revision import compare_with_previous, file_sha256
from bomgen.sheets.workbook import build_workbook
from bomgen.writer import write_workbook


@dataclass(frozen=True)
class BuildOutcome:
    """What one substation's build produced."""

    path: Path
    result: BuildResult  # the engine's result, before revision marks
    revisions: RevisionReport | None = None
    checks: CheckReport | None = None
    sheets: tuple[str, ...] = ()  # the workbook's sheet names, in order

    @property
    def failed(self) -> bool:
        """A check failed."""
        return self.checks is not None and self.checks.failed


def workbook_name(substation: LoadedSubstation) -> str:
    """The workbook file name (spec: Output requirements, OUT-2)."""
    document = substation.documents[substation.substation.document]
    return substation.substation.output.file_name.format(doc_no=document.doc_no, rev=document.rev)


def build_substation(
    target: LoadedSubstation,
    out_path: Path,
    *,
    previous: PreviousIssue | None = None,
    checks: bool = True,
) -> BuildOutcome:
    """Build ``target`` (already laid out) into the workbook ``out_path``, and its
    ``.checks.json`` beside it."""
    if not target.panels:
        raise EngineError(
            f"substation '{target.substation.substation.id}' has no panels yet: "
            "list its equipment or add a panel"
        )
    result = build_bom(target)
    marked: BuildResult = result
    revisions: RevisionReport | None = None
    if previous is not None:
        loose_sheet = target.substation.output.sheet_names.loose_material
        marked, revisions = compare_with_previous(result, previous, loose_sheet=loose_sheet)
    workbook = build_workbook(target, marked, logo=target.logo)
    path = write_workbook(workbook, out_path)
    report = None
    if checks:
        report = check_report(target, result)
        path.with_suffix(".checks.json").write_text(render_checks_json(report), encoding="utf-8")
    return BuildOutcome(path, result, revisions, report, tuple(s.name for s in workbook.sheets))


def issue_refusal(target: LoadedSubstation) -> str | None:
    """Why ``target`` can't be built as issued: its main document's rev is recorded."""
    rev = target.documents[target.substation.document].rev
    if rev in {record.rev for record in target.substation.issues}:
        return f"Rev {rev} is already issued; change the document's rev in the register first."
    return None


def record_issue(
    project_file: Path,
    target: LoadedSubstation,
    path: Path,
    description: str,
    *,
    overrides: Sequence[OverrideNote] = (),
    today: date | None = None,
) -> IssueRecord:
    """Append the issue of the workbook at ``path`` to ``target``'s ``issues`` (ADR 0036):
    the main document's rev and names, the file's hash, the acceptances in force and the
    risky ``overrides`` with their reasons (ADR 0040)."""
    document = target.documents[target.substation.document]
    folder = target.file.parent
    resolved = path.resolve()
    inside = resolved.is_relative_to(project_file.parent.resolve())
    file = Path(os.path.relpath(resolved, folder.resolve())) if inside else resolved
    checks = target.substation.checks
    record = IssueRecord(
        rev=document.rev,
        date=today or date.today(),
        file=file,
        sha256=file_sha256(path),
        description=description,
        prepared=document.prepared,
        checked=document.checked,
        approved=document.approved,
        accepted_warnings=list(checks.accepted) if checks else [],
        overrides=list(overrides),
    )
    value = record.model_dump(mode="json", exclude_none=True, exclude_defaults=True)
    value |= {"rev": record.rev, "date": record.date.isoformat(), "file": file.as_posix()}
    result = insert_item(
        project_file, ("issues",), None, value, substation=target.substation.substation.id
    )
    if not result.written:
        raise InputError(list(result.issues))
    return record
