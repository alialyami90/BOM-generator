"""One substation's build, shared by ``bomgen build`` and the desktop app.

Layout, engine, revision compare, sheets, workbook and check report, in that order.
Errors keep their types: ``EngineError`` from the layout or the engine, ``WriterError``
(or ``OSError``) from writing. A layout with errors is not raised: the outcome carries
its report and no workbook, so the caller can show every line.
"""

from dataclasses import dataclass
from pathlib import Path

from bomgen.checks import check_report
from bomgen.checks import render_json as render_checks_json
from bomgen.engine.layout import LayoutReport, with_layout
from bomgen.engine.pipeline import build as build_bom
from bomgen.io.loader import LoadedSubstation
from bomgen.models.bom import BuildResult
from bomgen.models.report import CheckReport, PreviousIssue, RevisionReport
from bomgen.revision import compare_with_previous
from bomgen.sheets.workbook import build_workbook
from bomgen.writer import write_workbook


@dataclass(frozen=True)
class BuildOutcome:
    """What one substation's build produced; ``path`` is None when the layout stopped it."""

    substation: LoadedSubstation  # as built, after the layout
    path: Path | None = None
    result: BuildResult | None = None  # the engine's result, before revision marks
    revisions: RevisionReport | None = None
    layout: LayoutReport | None = None
    checks: CheckReport | None = None

    @property
    def failed(self) -> bool:
        """The layout stopped the build or a check failed."""
        stopped = self.layout is not None and self.layout.has_errors
        return stopped or (self.checks is not None and self.checks.failed)


def workbook_name(substation: LoadedSubstation) -> str:
    """The workbook file name (spec: Output requirements, OUT-2)."""
    document = substation.documents[substation.substation.document]
    return substation.substation.output.file_name.format(doc_no=document.doc_no, rev=document.rev)


def build_substation(
    target: LoadedSubstation,
    out_path: Path,
    *,
    previous: PreviousIssue | None = None,
    layout: bool = True,
    checks: bool = True,
) -> BuildOutcome:
    """Build ``target`` into the workbook ``out_path``, and its ``.checks.json`` beside it."""
    layout_report = None
    if layout:
        target, layout_report = with_layout(target)
        if layout_report is not None and layout_report.has_errors:
            return BuildOutcome(substation=target, layout=layout_report)
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
    return BuildOutcome(target, path, result, revisions, layout_report, report)
