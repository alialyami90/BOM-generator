# Handoff: moving the SCADA BOM project to Claude Code CLI

Written 2026-11-10. Source of truth for code and the detailed state is the repo
github.com/alialyami90/BOM-generator (`docs/handoff/STATE.md`, `NEXT.md`,
`CHECKPOINT.md`, `docs/plan.md`, `CHANGELOG.md`). This file summarises where the
project-thread work stopped so it can carry on from the CLI.

## Project state
- Latest release: **v0.5.0** (2026-11-04), installer `bomgen-setup-0.5.0.exe` and
  `default.bomlib` from psa-devices 1.17.0. Ships milestones M70 to M81.
- Phase G of the implementation plan is done; every review point in plan.md's
  coverage table names its milestone and PR. ADRs 0038 to 0040 Accepted; Q72, Q73 answered.
- Last handoff docs PR in the repo: #393.

## Open pull requests
None. All 22 project PRs (#317 to #393) are merged with green CI.

## Open work
1. **W2 Issue outputs and revisions (blocked on Ali):** run Export PDF with
   *Use Excel* once on a Windows PC with Excel installed (CI cannot run Excel).
   Report pass or fail to the `issue-outputs` agent; a failure becomes a fix PR.
2. **Panels board drag-and-drop hand test (ALI-8):** waiting on Ali.
3. Open ends listed in STATE.md, not yet scheduled:
   - psa-devices has no RedBox or media-converter part (blocks ADR 0038 roles in practice).
   - Library detail pane does not show tags.
   - Socket pick list.
   - Built-in PDF renderer leaves out the header logo.

## Agents (`.claude/agents/`)
| Agent | Former thread | State |
|---|---|---|
| `lead` | Lead: Deliver the engineering workflow plan | Done; owns releases and relays |
| `issue-outputs` | W2 Issue outputs and revisions | Blocked on Use Excel test |
| `library-parts` | W1 Library parts, review and function tags | Done |
| `panel-notes` | W3 Panel notes, misc rows and labels | Done (ALI-8 hand test pending) |
| `parts-network` | W4 Parts and network | Done |
| `setup-design-basis` | W5 Setup and design basis | Done |
| `bom-workflow-reviewer` | Review BOM workflow for missing user inputs | Done |

## Working rules
- Use the Superpowers skills (brainstorming, writing-plans, test-driven-development,
  verification-before-completion).
- Squash-merge PRs once CI is green and there are no conflicts, per CLAUDE.md
  "Review and merge". Don't ask Ali to merge.
- Releases: changelog PR, then version-bump PR; release.yml publishes. Never push tags.
- Agent-to-agent messages go through the lead.
- Ask Ali questions as multiple choice with the recommendation marked.

## Memory
No saved project memory files were found for this project in the Claude Code memory
folder; everything durable is in the repo's handoff docs and in this file.
