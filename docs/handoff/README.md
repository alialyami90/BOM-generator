# Handoff: resuming a role after a context reset

1. Find your role in [`ROSTER.md`](ROSTER.md): "Current name" is you (the outgoing agent set it at handover).
2. Read your folder in this order: `STATE.md`, `NEXT.md`, `LESSONS.md`, then the latest `checkpoints/` file.
3. Read [`CLAUDE.md`](../../CLAUDE.md) and [`docs/agents.md`](../agents.md) (roles keyed by number: B1 = A1's rights).
4. Before trusting STATE.md, rerun: `git fetch origin main`, `git status --short`, `git log --oneline -10`,
   then the gate `ruff check . && ruff format --check .`, `mypy`, `pytest`. Record any drift in LESSONS.md.
5. Do the first line of `NEXT.md`. Ask Ali only on a decision card, with a recommendation.

Each role edits only its own folder and its own ROSTER row. Stable knowledge stays where it lives
(CLAUDE.md, agents.md, plan.md, docs/spec/, ADRs); handoff files link to it rather than copy it.
Checkpoints go in a docs-only PR; role 1 (lead) reviews and merges them.
