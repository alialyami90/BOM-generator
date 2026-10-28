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
| 0009 | [Installer layout and releases](0009-installer-layout-and-releases.md) | Proposed |
| 0010 | [Input schema details and validation behaviour](0010-input-schema.md) | Proposed |
| 0011 | [UI design language and bundled fonts](0011-ui-design-language.md) | Proposed |
| 0012 | [Projects hold substations; sharing by `.bomproj` export](0012-projects-substations-bomproj.md) | Accepted |
| 0013 | [Switches sized from the IED count; panels laid out automatically](0013-network-sizing-and-panel-layout.md) | Accepted |
| 0014 | [Engine output model and group A–H derivation choices](0014-engine-data-model.md) | Accepted |
| 0015 | [Desktop app: how the UI calls the engine](0015-desktop-app-bridge.md) | Proposed |
| 0016 | [Check report and revision comparison](0016-check-report-and-revision-comparison.md) | Proposed |
| 0017 | [Alternatives as library parts; catalogue brand sets](0017-alternatives-and-catalogue-brands.md) | Proposed |
| 0018 | [Library CSV exchange](0018-library-csv-exchange.md) | Proposed |
| 0019 | [Branch MCBs sized from device data](0019-branch-mcb-sizing.md) | Proposed |
| 0020 | [Loose material on its own sheet](0020-loose-material-sheet.md) | Accepted |
| 0021 | [Round-trip YAML writers, checked before they write](0021-round-trip-writers.md) | Proposed |
| 0022 | [Free-text loose items](0022-free-text-loose-items.md) | Proposed |
