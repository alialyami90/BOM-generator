"""One substation's build, shared by ``bomgen build`` and the desktop app.

Engine, revision compare, sheets, workbook and check report, in that order. The caller
lays out first (``engine.layout.with_layout``) so it can show the layout's lines whatever
happens next. Errors keep their types: ``EngineError`` from the engine, ``WriterError``
(or ``OSError``) from writing.
"""

from dataclasses import dataclass
from pathlib import Path

from bomgen.checks import check_report
from bomgen.checks import render_json as render_checks_json
from bomgen.engine.pipeline import build as build_bom
from bomgen.io.loader import LoadedSubstation
from bomgen.models.bom import BuildResult
from bomgen.models.report import CheckReport, PreviousIssue, RevisionReport
from bomgen.revision import compare_with_previous
from bomgen.sheets.workbook import build_workbook
from bomgen.writer import write_workbook


@dataclass(frozen=True)
class BuildOutcome:
    """What one substation's build produced."""

    path: Path
    result: BuildResult  # the engine's result, before revision marks
    revisions: RevisionReport | None = None
    checks: CheckReport | None = None

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
    result = build_bom(target)
    marked: BuildResult = result
    revisions: RevisionReport | None = None
    if previous is not None:
        marked, revisions = compare_with_previous(result, previous)
    path = write_workbook(build_workbook(target, marked, logo=target.logo), out_path)
    report = None
    if checks:
        report = check_report(target, result)
        path.with_suffix(".checks.json").write_text(render_checks_json(report), encoding="utf-8")
    return BuildOutcome(path, result, revisions, report)
