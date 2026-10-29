# STATE — role 6, Windows installer and release (M11)

Final handoff from `B6 - Windows installer and release` to `C6 - Windows installer and release`, 2026-10-29. Ali retired every agent. The
successor starts with no history, so this file is meant to stand on its own. Read it, then
[NEXT.md](NEXT.md), [LESSONS.md](LESSONS.md) and the newest file in [checkpoints/](checkpoints/).

## Where things stand (2026-10-29)

- **Latest release: v0.2.1**, https://github.com/alialyami90/BOM-generator/releases/tag/v0.2.1.
  The tag is on 1678343 (#211). It was published 2026-10-29 03:17 by the push run of `release.yml`
  on main, with `bomgen-setup-0.2.1.exe` (29.7 MB) and `default.bomlib` (psa-devices 1.1.0).
- **Before that: v0.2.0** (tag f65a5fe, #195, run 40797286698), the first release from main.
  **v0.1.1** (tag 135d7ee, run 40773272092) and **v0.1.0** (tag 2064227, run 40736513114) were
  released from hand-pushed or UI-made tags, before #153.
- `bomgen.__version__` on main is `0.2.1`. The next release is whatever the lead and Ali call. No
  version is reserved.
- **No open PR, no unfinished branch, no uncommitted work.** The role's branch is
  `claude/project-thread-s79idd`, and it only holds history already squash-merged (#169, #186, #195,
  #196, #211). A6's old branch `claude/project-thread-y4aekh` is also fully merged. Restart a branch
  from main before new work (LESSONS "Branch restarts").
- Nothing is waiting on anyone. ADR 0009 is **Accepted** (Ali, 2026-10-28, #184).
- Gate on main 1678343 (the 0.2.1 bump head): ruff and format pass, mypy passes (224 files), and
  pytest has 2672 passed.

## Role and ownership

The roles table is in [docs/agents.md](../../agents.md), under "Roles" and "A6 — Windows installer
and release (M11)". The design is in [ADR 0009](../../decisions/0009-installer-layout-and-releases.md).
User-facing steps are in [docs/install.md](../../install.md), and build steps in
[packaging/README.md](../../../packaging/README.md). The plan section is M11 in `docs/plan.md`.

Role 6 owns:

| file | what it is |
| --- | --- |
| `packaging/bomgen.spec` | PyInstaller spec: one folder `dist/bomgen/`, two exes (`BOM Generator.exe` windowed, `bomgen.exe` console). It bundles all of `src/bomgen/app/ui/` and writes `bomgen_modules.txt` (every bomgen module) for `--self-test`. |
| `packaging/bomgen.iss` | Inno Setup script. Per-user install (`PrivilegesRequired=lowest`) to `%LOCALAPPDATA%\Programs\BOM Generator`. It sets up the Start-menu shortcut and the `.bomlib`/`.bomproj` associations (HKCU), installs `default.bomlib` to `{app}\library`, and runs the WebView2 bootstrapper check (warn only). **AppId `{9B1E5C2A-4F37-4E8B-9D61-2C7A0F3B8E15}` must never change**, or upgrades stop replacing the old install. |
| `packaging/entry_app.py`, `entry_cli.py` | PyInstaller entry scripts. They call `launcher.app_main` and `launcher.cli_main`. |
| `packaging/requirements.txt` | Build-only dependencies (`pyinstaller==6.22.3`), kept out of pyproject on purpose. |
| `packaging/release-notes.md` | Header of every GitHub Release body (install steps, SmartScreen note). GitHub's generated notes are appended under it. |
| `packaging/README.md` | How to build locally on Windows. |
| `.github/workflows/release.yml` | Jobs `plan` (ubuntu) → `installer` (windows) → `release` (ubuntu). See "How a release works". |
| `docs/install.md` | End-user install, upgrade, library packages, uninstall. |
| `src/bomgen/app/launcher.py` | The only file in `src/bomgen/app/` that is ours; role 11 owns the rest. `parse_args`, `app_main` (window, `.bomlib` import, `.bomproj` open, `--self-test`, first-start default library), `cli_main` (typer app with the UTF-8 console), `self_test`, `ui_files`/`ui_files_missing`, `install_bundled_library`. |
| ADR 0009, the M11 section of `docs/plan.md` | Design record. |
| `tests/unit/test_launcher.py` (43 tests), `tests/unit/test_packaging.py` (22 tests) | Unit tests for the above. `test_packaging` reads release.yml, the spec and the iss as text and pins their key lines. |

Edits outside this list, each approved by the lead at the time: the version strings in
`pyproject.toml`, `src/bomgen/__init__.py` and `tests/test_package.py` (every bump, the lead's go
covers them); `src/bomgen/cli.py` (#70, `utf8_console` made public); the ADR 0009 row of
`docs/decisions/README.md` (#153).

## How a release works (since #153)

1. Role 7 (lead assistant) merges a `CHANGELOG.md` section `## [X.Y.Z] - date`. Ali's rule: never
   release without a changelog section.
2. Role 6 opens one PR that changes only the three version lines: `__version__` in
   `src/bomgen/__init__.py`, `version` in `pyproject.toml`, and the assert in
   `tests/test_package.py`. Examples are #195 and #211. Don't open it before the lead says so,
   because merging it publishes.
3. The lead squash-merges it once CI and "Build Windows installer" are green.
4. The push to main starts `release.yml`. Main pushes are path-filtered to `src/bomgen/__init__.py`,
   `pyproject.toml` and `CHANGELOG.md`. Steps:
   - `plan` reads `__version__`. If tag `vX.Y.Z` already exists it builds nothing. Otherwise it
     checks that pyproject agrees and that the CHANGELOG section exists, and either fails (nothing
     created) or prints `Releasing vX.Y.Z from <sha>`.
   - `installer` freezes, smoke-tests the frozen app, packs `default.bomlib` from
     `data/library/psa-devices.yaml` plus `data/device-db`, compiles with Inno Setup, then installs,
     smoke-tests and uninstalls.
   - `release` runs `gh release create vX.Y.Z --target <sha>` with both assets. That command also
     creates the tag. If a release already exists for the tag (made in the UI), it uploads with
     `--clobber` instead, and fills an empty body.
5. Role 6 checks with `get_release_by_tag`, then sends Ali the link and tells the lead.

Also supported: a hand-pushed `v*` tag that equals `__version__` releases that commit (how v0.1.x
went), and `workflow_dispatch` builds without publishing. PRs that touch `packaging/**`,
`src/bomgen/app/**`, `data/library/**`, `data/device-db/**`, `pyproject.toml` or `release.yml` run
the same build without publishing. Release runs never cancel each other; PR runs do.

## What the Windows job proves (each run)

- **Frozen app:** `--version`, `--help`, `validate` and `build` on `examples/project.yaml`. For
  `build` it checks that `.checks.json` exists and the report says "0 failed". It also runs
  `--self-test` (every module in the build-time manifest imports, and since #186 every script,
  stylesheet and font `index.html` loads is in the bundle). Finally it starts the real window and
  waits for the title "BOM Generator".
- **Installed app:** a fresh `BOMGEN_LIBRARY_HOME`. The first start must list
  `psa-devices\s+<version> (active)`, with the version pinned by `test_packaging` to
  `examples/project.yaml` `library:`. A reinstall plus second start must leave the store snapshot
  unchanged. It also checks the `.bomlib` double-click import, a `build` with the installed
  `bomgen.exe`, the Start-menu shortcut, and the two file associations.
- **Uninstall:** the exe, ProgIDs, extension keys and shortcut are all gone.

## Decisions and why (details in ADR 0009 and LESSONS)

- **Release from main, not tags (#153):** agents can't push tags (the sandbox returns HTTP 403), so
  tag releases stalled on Ali. Build, tag and release run in one workflow run, because a tag made
  with `GITHUB_TOKEN` does not trigger other workflows.
- **The first-start default library comes from a launcher hook, not an installer `[Run]` step:** the
  smoke test can use a temporary store and prove a reinstall changes nothing. The hook imports only
  when `LibraryStore.list()` is empty, never forces, and never blocks the window.
- **The self-test reads a build-time module manifest:** walking the frozen app only sees what
  PyInstaller kept, so a dropped module would pass.
- **The default library is the shipped `data/library/psa-devices.yaml` (Q38, #161), not
  `examples/library.yaml`.** The example library stays golden-test data.
- **Unsigned builds (plan Q19):** no certificate yet, so SmartScreen warns. Don't start signing work
  unless Ali supplies a certificate.
- **The Release workflow is not a required check and not part of `ci-status` (ADR 0006):** it is
  path-filtered, so a required check would block unrelated PRs.

## Known issues and caveats

- An existing install keeps its library store on upgrade by design. To move it to a newer default
  library, the user double-clicks the release's `default.bomlib`. Ali was told this at v0.2.0.
- A broken bundled default library shows its message on every start while the store stays empty.
  Role 5 accepted this.
- The first-start and import messages show the raw refusal kind (e.g. `invalid_package`). Role 5
  called it a nit; left as is.
- A superseded or cancelled run shows `ci-status` failure on the old sha. Check the newest run
  before reacting.
- `pip install -e ".[app]"` fails on Linux (pywebview's `proxy_tools` wheel), so use `.[dev]` for
  the gate here. Anything Windows-only (freeze, installer, window, PowerShell) is proven only by the
  Windows job.
- A "Build Windows installer" job can finish in about 90 s on a pip cache hit. Confirm every step
  ran before trusting it.

## Contacts (threads in the "Scada BOM" project; all agents were retired 2026-10-29)

- Role 6 thread (Ali reads it): `cmsg_01CGuLumA5u5e7gSGbisWmMiHdmiF2zR4D9rPGYUSRQDkT`. A6's
  earlier thread was `cmsg_01CGuLumA5u5e7gSGbisWmMi9TL26SYzpQs1CWS9qSpPPv`.
- Lead (B1) thread: `cmsg_01CGuLumA5u5e7gSGbisWmMiJaADCWuiNCb42qQHM1dpuv`. A1's thread is retired.
  The lead reviews and squash-merges every PR; never ask Ali to merge. Ask Ali questions only as
  decision cards with a recommendation.
- Role 3 (device db, owns `data/library/`): `cmsg_01CGuLumA5u5e7gSGbisWmMiMn4Ay5kTA4wLV22n9mEuru`.
  Role 5 (library packages): `cmsg_01CGuLumA5u5e7gSGbisWmMi4GsrhHJfEnM1ZoKq6Av5HP`.
- These ids belong to retired sessions. Check ROSTER.md and the project's thread list for the
  current ones.

## Verification log

| check | result | date |
| --- | --- | --- |
| ruff, format, mypy on main 1678343 | pass (224 files) | 2026-10-29 |
| `pytest -q` on the 0.2.1 bump head | 2672 passed | 2026-10-29 |
| v0.2.1 push run on main | success, published 03:17 | 2026-10-29 |
| v0.2.0 push run on main (40797286698) | success, published 00:59 | 2026-10-29 |
| #186 Windows job | success (B1 merged as 445baa6) | 2026-10-29 |
| #161 Windows job on 64a8e65 (40778617300) | success | 2026-10-28 |
| #153 PR run (40774940276) | success | 2026-10-28 |
| v0.1.1 tag run on 135d7ee (40773272092) | success, published | 2026-10-28 |
| v0.1.0 tag run (40736513114, attempt 2) | success, published | 2026-10-28 |

## Merged history (all squash-merged by the lead)

#2 installer pipeline · #15 `.bomlib` import and `.bomproj` association · #24 test fixture fix ·
#38 launcher runs `run_window`, with the UI and pywebview bundled · #47 frozen `validate` smoke ·
#55 frozen `build` smoke · #57 PowerShell `$name:` fix · #70 UTF-8 console for the frozen CLI ·
#84 v0.1.0 · #86 default library bundled and installed on first start, v0.1.1, attach to an existing
release · #138, #162, #169, #196 handoff checkpoints · #153 release from main · #186 self-test checks
every UI file · #195 v0.2.0 · #211 v0.2.1. Reviewed: #161 (Q38 shipped library, release.yml part).
