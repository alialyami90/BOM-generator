# STATE — role 6, Windows installer and release (M11)

- Outgoing: `A6 - Windows installer and release`. Successor: `B6 - Windows installer and release`.
- Date 2026-10-28 (B6 refresh). Branch `claude/project-thread-y4aekh` (docs-only checkpoint on `origin/main` ee5b451, #153). The branch holds no unfinished work; restart it from main per LESSONS "Branch restarts".
- Contacts: Ali's thread is this role's project thread `cmsg_01CGuLumA5u5e7gSGbisWmMi9TL26SYzpQs1CWS9qSpPPv` (reply with post_message). A1's thread: `cmsg_01CGuLumA5u5e7gSGbisWmMi3nTuZbpZkUB1t4T5nt6GfE`. A5 (library packages): `cmsg_01CGuLumA5u5e7gSGbisWmMi4GsrhHJfEnM1ZoKq6Av5HP`.
- Role, ownership and rules: [docs/agents.md](../../agents.md) "Roles" and "A6 — Windows installer and release (M11)"; design in [ADR 0009](../../decisions/0009-installer-layout-and-releases.md), [docs/install.md](../../install.md), [packaging/README.md](../../../packaging/README.md), plan M11.

## Owned files (agents.md)
`packaging/` (spec, iss, entry points, requirements.txt, release-notes.md, README), `.github/workflows/release.yml`, `docs/install.md`, `src/bomgen/app/launcher.py` (the only file in `src/bomgen/app/` that is ours; A11 owns the rest), ADR 0009, the M11 section of `docs/plan.md`. Tests: `tests/unit/test_launcher.py`, `tests/unit/test_packaging.py`.

## Merged (all squash-merged by A1)
#2 installer pipeline, #15 real `.bomlib` import and `.bomproj` association, #24 test fixture fix, #38 launcher runs `run_window`, UI and pywebview bundled, #47 example `validate` smoke step, #55 example `build` smoke step, #57 PowerShell `$name:` parse fix, #70 UTF-8 console for the frozen CLI (touched A2's `cli.py`: `utf8_console` made public, A1 approved), #84 version 0.1.0, #86 default library bundled and installed on first start, version 0.1.1, release job attaches to an existing release, #138 handoff checkpoint, #153 release from main (a merged version bump builds, tags and publishes; ADR 0009 amended).

## In review / in progress
- No open PR of mine. Nothing uncommitted besides this checkpoint.
- Release v0.1.1 is done: https://github.com/alialyami90/BOM-generator/releases/tag/v0.1.1 (tag on 135d7ee, CHANGELOG #143 covers it; run 40773272092). Ali made the release in the UI, so its title and notes are empty; Ali was told and may paste the changelog section. Since #153 the workflow fills an empty UI release itself.

## What works (evidence)
- Release v0.1.1 published with `bomgen-setup-0.1.1.exe` and `default.bomlib` (run 40773272092, both jobs green).
- Release from main (#153): Windows job green on the PR head (run 40774940276). The plan step was run locally for every trigger (tag match and mismatch, main with tag present, PR, manual, bump without pyproject, without changelog, full bump). Its first real main release has not happened yet.
- Release v0.1.0 published with `bomgen-setup-0.1.0.exe` (run 40736513114, attempt 2; first attempt's publish step failed because Ali had already made an empty release in the UI).
- Windows job (release.yml) green on #86 head and on main builds: freeze, frozen smoke (version, `--help`, validate, build + `.checks.json` + "0 failed", self-test, real window title), compile, install, installed smoke (first start installs `psa-devices 1.0.0`, reinstall + second start leave the store unchanged, `.bomlib` double-click import, build, shortcut, associations), uninstall cleanup.
- Gate on 2026-10-28 (this checkpoint): see table.

## Verification
| command | result | date |
|---|---|---|
| `ruff check .` / `ruff format --check .` | pass (319 files) | 2026-10-28 |
| `mypy` | pass (212 files) | 2026-10-28 |
| `pytest -q` | 2464 passed | 2026-10-28 |
| `pytest -q tests/golden` | 94 passed | 2026-10-28 |
| Windows job on v0.1.0 tag run | success | 2026-10-28 |
| Windows job on v0.1.1 tag run (40765665083, 9313db1) | build + smoke passed; cancelled by me before publish | 2026-10-28 |
| v0.1.1 tag run on 135d7ee (40773272092) | success, published | 2026-10-28 |
| #153 PR run (40774940276) | success | 2026-10-28 |

Could not run here: the installer, the window and the PowerShell smoke steps (Windows only; CI is the proof), anything needing a tag push (sandbox returns HTTP 403 on tag pushes). Since #153 no one needs to push tags.

## Scope check
No file outside the owned list is changed by this checkpoint. Past out-of-role edits, all approved by A1 and merged: the ADR 0009 row of `docs/decisions/README.md` (#153, own-ADR row), `src/bomgen/cli.py` rename (#70), version strings in `pyproject.toml`, `src/bomgen/__init__.py`, `tests/test_package.py` (#84, #86).

## Known issues and caveats
- ADR 0009 status is still "Proposed"; it needs A1 to accept it (my file, A1 decides status).
- A broken bundled default library shows its message on every start while the store stays empty (accepted, A5 noted it).
- The first-start message includes the raw refusal kind (e.g. `invalid_package`), same as the double-click import message; A5 called it a nit, left as is.
- Superseded or cancelled CI runs report `ci-status` failure on the old head sha; check the newest run before reacting.
- Releases are unsigned (plan Q19); SmartScreen warns.

## Waiting on (since 2026-10-28)
- A3: the Q38 PR that repoints the default library pack in release.yml to the shipped 1.1.0 file. A1 asked me to review that part.
- A1: acceptance of ADR 0009 (still "Proposed"); the two "tag-driven" lines in `README.md:62` and `docs/agents.md:81` (A1's files).
