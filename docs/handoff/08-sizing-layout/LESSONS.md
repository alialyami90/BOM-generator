# LESSONS: role 8 (append-only)

Decisions too small for an ADR, and approaches that failed. The rules themselves are in
ADR 0013 and `docs/superpowers/specs/2026-10-28-substations-and-auto-layout-design.md` (R1-R10).

## Decisions
- **L1 model is ranked, then picked** (Ali): fewest per side, then fewest ports, then part_id.
  The `l1_switch` entry's `part_id` pins the model.
- **Each IED takes one A port and one B port** (Ali): `ied_count` ports per side.
  The port spare default stays 20 % (Ali).
- **Cable managers count** (Ali, Q32): 1U under each rack switch, firewall or patch panel.
- **Golden = what the rules give** (Ali): 3 L1 per side, demand 8, psa1 23U, psa2 19U after M12.
- **Annunciator after a layout is fed from panel 001** (Ali). `examples/` keeps psa3 for the
  hand-written goldens; the layout golden's fixture rewrites `fed_from: psa3` to `psa1`.
- **`with_layout` takes over `panels:` only once a listed file is `generated: true`.** Until then
  the build uses hand-written panels, which keeps the spec goldens (A1 agreed).
- **Size from kept units** (A1 review of #19): removed units leave the L2 demand and SFPs; when
  the kept switches fall short, report `port-capacity`. Rejected: removal as layout-only.
- **`l2_ports` count once per entry**, as R2's text says (sum of `equipment.l2_ports`), not per unit.
- **`bomgen layout` rewrites the `panels:` list as text** to keep comments; it deletes stale
  generated files and only names hand-written ones. Rejected: a YAML round-trip, which drops comments.
- **Overrides apply after the fill (R7), in order; a later move of a unit replaces it.** Pins-first
  was rejected (A1, 2026-10-28): it re-flows other devices, which the board contract forbids.
- **A pin to the automatic place stays a pin**: every move records `PanelFill.pins`.
- **Position** = 1-based place among rack devices; DIN-rail parts don't count; a position past
  the bottom means last; ties go by group order.
- **A `PairMove` on an entry without A/B units** is `stale-override`, not a silent no-op.
- **Blank plates (M12, Ali)**: one under each rack block that ends in its active device, never under
  a cable manager. The BOM is unchanged, because plates have no row (Q25).

## Failed approaches and pitfalls
- A CLI test that grows the layout to psa4 failed on a sheet-name clash with the manual `ws`
  panel (sheet "4"). The test renames ws's sheet first.
- The first `_side_ports` multiplied `l2_ports` by the unit count, which contradicted R2. Reverted to per entry.
- ruff RUF001-003 reject en dash, × and − in code and comments. Write ASCII.
- After rebasing a pushed branch, use `git push --force-with-lease=<branch>:<old sha>`.
- Install with `pip install -e ".[dev]"` (pycel), and run `python3 -m mypy` / `python3 -m pytest`.
- The full pytest run takes 2 to 7 minutes; run it with a longer timeout or in the background.

## 2026-10-29 (B8)
- **Resume drift was harmless**: B8 found origin/main moved from `aad6094` to `ded5fe4` with only
  other roles' checkpoint docs, and the gate green (2414 passed). Always diff role-8 paths
  (`git log <old>..origin/main -- src/bomgen/engine/sizing.py src/bomgen/engine/layout.py tests/golden/layout`)
  to tell docs-only drift from code drift.
- **STATE's branch name goes stale**: each session is assigned its own branch; use the session's,
  not the one STATE names.
- **Releases freeze merges**: during a release (v0.1.1) the lead held code and docs merges until the tag;
  commit locally and wait for the lead's go rather than opening a PR that has to wait.
- **The lead changes**: A1 retired and B1 took over in a new thread. Message the lead's current thread
  (ask the coordinator if unsure); a message to a retired thread is lost.
- **Requesting Ali's review fails** on a PR the session opened as Ali ("Review cannot be requested from
  pull request author"). Assigning him works; skip the review request.
- **Docs-only PRs skip lint/mypy/pytest in CI**: only `ci-status` and "Detect code changes" run. Still
  run `ruff` locally.
