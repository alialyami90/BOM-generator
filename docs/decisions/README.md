# Architecture decision records

One ADR per significant design choice. Copy `0000-template.md` to the next free
number, keep it short, and link it from `docs/plan.md` when it changes the plan.
An ADR stays "Proposed" until Ali accepts it in review.

| # | Decision | Status |
| --- | --- | --- |
| 0001 | [Record decisions as ADRs](0001-record-decisions.md) | Accepted |
| 0002 | [Tech stack: Python 3.12, pydantic, YAML, typer](0002-tech-stack.md) | Accepted |
| 0003 | [Write .xlsx with XlsxWriter, read back with openpyxl](0003-xlsx-writer-library.md) | Accepted |
| 0004 | [One BOM sheet per cabinet with hidden HWIO column](0004-single-bom-sheet-per-cabinet.md) | Proposed |
| 0005 | [Pipeline: rule engine → sheet models → thin writer](0005-pipeline-architecture.md) | Proposed |
| 0006 | [CI gated by paths-filter with an always-on ci-status job](0006-ci-docs-only-gating.md) | Accepted |
| 0007 | [Windows desktop app: pywebview + PyInstaller + Inno Setup](0007-windows-desktop-app-stack.md) | Proposed |
| 0008 | [Device library updates as `.bomlib` packages](0008-library-update-packages.md) | Proposed |
| 0009 | [Installer layout and tag-driven releases](0009-installer-layout-and-releases.md) | Proposed |
