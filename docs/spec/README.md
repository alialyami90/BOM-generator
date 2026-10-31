# Generator spec

`generator-spec-v2.md` is the **source of truth** for the BOM generator: workbook
structure, grouping and columns, tag naming, derivation rules, calculations,
formatting, output requirements, inputs and the data model. Code, tests and
`docs/plan.md` refer to it by section name (for example "Derivation rules → DC
distribution (group F)").

| File | Version | Source |
| --- | --- | --- |
| `generator-spec-v2.md` | v2 (28 Oct 2026) | Claude Doc "Substation SCADA BOM – Generator Spec v2", exported to Markdown |
| `generator-spec-v2.md` | v2.1 (30 Oct 2026) | Hand-edited from the v2 export with the passages of the Claude Doc "Spec v2.1 draft" (ADRs 0017, 0019, 0020, 0022, 0023); the master doc still reads v2 |
| `generator-spec-v2.md` | v2.1 + ADR 0024 (31 Oct 2026) | Hand-edited: equipment part number, overrides and SFP choice; derived parts in generation step 0 (design approved by Ali 2026-10-31) |
| `generator-spec-v2.md` | v2.1 + ADR 0027 (31 Oct 2026) | Hand-edited: the `ports` row of "Inputs the tool needs" lists the port speeds; 2.5G, 5G and 25G are never sized for SFPs (ADR 0027 proposed, waiting on Ali) |

The export replaces the doc's embedded "workbook data flow" diagram with a text
placeholder under "Relationships between sheets"; the surrounding text describes
the same chain.

## Updating the spec

1. Edit the master Claude Doc, then export it to Markdown and overwrite
   `generator-spec-v2.md`. For a new major version, add a new file
   (`generator-spec-v3.md`), keep the old one, and update the table above.
2. Do not hand-edit the Markdown except to fix export artefacts; say so in the
   commit message if you do.
3. Commit on its own branch with a `docs(spec): …` conventional commit and a
   one-paragraph summary of what changed and which sections moved.
4. In the same PR, list the rules and golden values affected, and open
   follow-up issues for the code. Spec changes are docs-only, so CI does not run
   on them; the code PRs that follow carry the tests.
5. If code and spec disagree, ask the owner before changing either (see
   `CLAUDE.md`).
