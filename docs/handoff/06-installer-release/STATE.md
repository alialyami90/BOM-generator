# STATE — role 6, Windows installer and release (M11)

- Outgoing: `A6 - Windows installer and release`. Successor: `B6 - Windows installer and release`.
- Date 2026-10-28. Branch `claude/project-thread-y4aekh` (docs-only checkpoint on `origin/main` aad6094, #133). The branch holds no unfinished work; restart it from main per LESSONS "Branch restarts".
- Contacts: Ali's thread is this role's project thread `cmsg_01CGuLumA5u5e7gSGbisWmMi9TL26SYzpQs1CWS9qSpPPv` (reply with post_message). A1's thread: `cmsg_01CGuLumA5u5e7gSGbisWmMi3nTuZbpZkUB1t4T5nt6GfE`. A5 (library packages): `cmsg_01CGuLumA5u5e7gSGbisWmMi4GsrhHJfEnM1ZoKq6Av5HP`.
- Role, ownership and rules: [docs/agents.md](../../agents.md) "Roles" and "A6 — Windows installer and release (M11)"; design in [ADR 0009](../../decisions/0009-installer-layout-and-releases.md), [docs/install.md](../../install.md), [packaging/README.md](../../../packaging/README.md), plan M11.

## Owned files (agents.md)
`packaging/` (spec, iss, entry points, requirements.txt, release-notes.md, README), `.github/workflows/release.yml`, `docs/install.md`, `src/bomgen/app/launcher.py` (the only file in `src/bomgen/app/` that is ours; A11 owns the rest), ADR 0009, the M11 section of `docs/plan.md`. Tests: `tests/unit/test_launcher.py`, `tests/unit/test_packaging.py`.

## Merged (all squash-merged by A1)
#2 installer pipeline, #15 real `.bomlib` import and `.bomproj` association, #24 test fixture fix, #38 launcher runs `run_window`, UI and pywebview bundled, #47 example `validate` smoke step, #55 example `build` smoke step, #57 PowerShell `$name:` parse fix, #70 UTF-8 console for the frozen CLI (touched A2's `cli.py`: `utf8_console` made public, A1 approved), #84 version 0.1.0, #86 default library bundled and installed on first start, version 0.1.1, release job attaches to an existing release.

## In review / in progress
- No open PR of mine. Nothing uncommitted besides this checkpoint.
- **Release v0.1.1 is on hold (Ali: "Dont release with a missing changlog", 20:44).** Tag `v0.1.1` is on 9313db1 (main at 20:42, includes M17 #106–#129), not 39fddc4 (A1's planned 0.1.1 changelog commit), so CHANGELOG 0.1.1 misses everything after #87. I cancelled run 40765665083 before its publish job: build and every smoke test passed, no Release exists (`get_release_by_tag v0.1.1` = 404). Proposed to A1 and Ali: A7 extends the 0.1.1 changelog, A1 names the commit, Ali deletes and re-pushes `v0.1.1` there (safe, nothing published). Then follow the new run and send Ali the Release link.
- The wrong capital-V tag `V0.1.1` is gone (list_tags 20:42 shows only `v0.1.1`, `v0.1.0`). Resolved.

## What works (evidence)
- Release v0.1.0 published with `bomgen-setup-0.1.0.exe` (run 40736513114, attempt 2; first attempt's publish step failed because Ali had already made an empty release in the UI).
- Windows job (release.yml) green on #86 head and on main builds: freeze, frozen smoke (version, `--help`, validate, build + `.checks.json` + "0 failed", self-test, real window title), compile, install, installed smoke (first start installs `psa-devices 1.0.0`, reinstall + second start leave the store unchanged, `.bomlib` double-click import, build, shortcut, associations), uninstall cleanup.
- Gate on 2026-10-28 (this checkpoint): see table.

## Verification
| command | result | date |
|---|---|---|
| `ruff check .` / `ruff format --check .` | pass (270 files) | 2026-10-28 |
| `mypy` | pass (210 files) | 2026-10-28 |
| `pytest -q` | 2414 passed | 2026-10-28 |
| `pytest -q tests/golden` | 94 passed | 2026-10-28 |
| Windows job on v0.1.0 tag run | success | 2026-10-28 |
| Windows job on v0.1.1 tag run (40765665083) | build + smoke passed; run cancelled by me before publish | 2026-10-28 |

Could not run here: the installer, the window and the PowerShell smoke steps (Windows only; CI is the proof), anything needing a tag push (sandbox returns HTTP 403 on tag pushes; Ali pushes tags).

## Scope check
No file outside the owned list is changed by this checkpoint. Past out-of-role edits, all approved by A1 and merged: `src/bomgen/cli.py` rename (#70), version strings in `pyproject.toml`, `src/bomgen/__init__.py`, `tests/test_package.py` (#84, #86).

## Known issues and caveats
- ADR 0009 status is still "Proposed"; it needs A1 to accept it (my file, A1 decides status).
- A broken bundled default library shows its message on every start while the store stays empty (accepted, A5 noted it).
- The first-start message includes the raw refusal kind (e.g. `invalid_package`), same as the double-click import message; A5 called it a nit, left as is.
- Superseded or cancelled CI runs report `ci-status` failure on the old head sha; check the newest run before reacting.
- Releases are unsigned (plan Q19); SmartScreen warns.

## Waiting on (since 2026-10-28)
- A1/A7: the extended 0.1.1 changelog and the commit to tag. Ali: re-pushing `v0.1.1` on that commit. Then I owe Ali the Release link.
- A1: word that A3's shipped library file (Q38) merged; acceptance of ADR 0009.
