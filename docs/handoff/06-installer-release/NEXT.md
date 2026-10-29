# NEXT — role 6, Windows installer and release

**Next action:** none open. After your readback (handoff README steps 1–5), wait for the lead or
Ali to call the next release, then do task 1. Nothing is half done.

## Tasks, in priority order

1. **Cut the next release when the lead or Ali call it** (v0.2.2, v0.3.0, ...). Done when Ali has
   the release link.
   1. Confirm `CHANGELOG.md` on main has `## [X.Y.Z]` (role 7 writes it and it merges first), and
      that `list_tags` has no `vX.Y.Z`.
   2. Branch from main. Change only `__version__` in `src/bomgen/__init__.py`, `version` in
      `pyproject.toml`, and the assert in `tests/test_package.py`. Run the gate
      (`ruff check . && ruff format --check .`, `python -m mypy`, `python -m pytest -q`; reinstall
      with `pip install -e ".[dev]"` first so the version metadata updates).
   3. Open the PR titled `chore(release): version X.Y.Z` (copy #211's body). Say in it that merging
      publishes, and tell the lead. Do not open it before the lead says go.
   4. After the lead merges it, find the push run of `release.yml` on main (`actions_list`,
      `list_workflow_runs`, `release.yml`, branch main, event push). `plan` must pass, and
      `installer` must run all its steps (check with `get_workflow_job`; a 90 s job is normal on a
      cache hit). Then `release` publishes.
   5. Run `get_release_by_tag vX.Y.Z`. Check that `bomgen-setup-X.Y.Z.exe` and `default.bomlib` are
      present and the tag is on the merge commit. Send Ali the link in the role 6 thread and tell
      the lead.
   - If `plan` fails (pyproject mismatch or missing changelog), nothing was created. Fix it with a
     follow-up PR and tell the lead.
   - If `installer` fails, read the job log (`get_job_logs`), fix it in a PR with the Windows job
     green on its head, and tell the lead. A merged fix on main does not re-release by itself unless
     it touches `__version__`, `pyproject.toml` or `CHANGELOG.md`; use "Re-run failed jobs" on the
     release run, or ask the lead.
   - If tag creation is refused (a tag ruleset), tell the lead and Ali. The fallback is Ali
     publishing a release in the GitHub UI on that commit with tag `vX.Y.Z`. The tag push re-runs
     the workflow, which attaches the assets and fills an empty body.
2. **When app work adds a dependency or a data file outside `src/bomgen/app/ui/`**, check the
   frozen build carries it (the lead may ask). UI files are covered since #186: a missing one fails
   `--self-test` on the Windows job. For anything else, check the PR's Windows job, or freeze on
   Windows with `pip install ".[app]" -r packaging/requirements.txt` and
   `pyinstaller packaging/bomgen.spec --noconfirm --clean`, then run `dist\bomgen\bomgen.exe build
   examples\project.yaml` and `"dist\bomgen\BOM Generator.exe" --self-test`. Precedent: ruamel.yaml
   (#106) needed no spec change, because its hook ships in pyinstaller-hooks-contrib.
3. **Review any PR that touches the files in STATE "Role and ownership"** when the lead asks, as
   with #161: check the pack step, the first-start regex, the test_packaging pins, ADR 0009, and a
   green Windows job on the PR head.

## Ideas not started (not asked for; ask the lead before doing any)

- Code signing (plan Q19): only if Ali supplies a certificate. It would be a `signtool` step after
  "Compile the installer", with the secret stored in repo settings.
- A smoke step that upgrades from the previous release's installer (install old, install new, store
  unchanged). Today only a same-version reinstall is tested.
- Bump `actions/checkout@v4`, `setup-python@v5`, `upload-artifact@v4` and `download-artifact@v4`
  when GitHub's Node 20 deprecation warning becomes an error. They are forced onto Node 24 today.

## Rules of the release workflow (do not break)

- Any change to `release.yml`, `bomgen.iss`, `bomgen.spec` or `launcher.py` needs "Build Windows
  installer" green on the PR head before the lead merges (standing rule since #55).
- Keep build, tag and release in one run, and keep release runs uncancelled (`cancel-in-progress`
  only for PRs).
- Keep the main-push path filter limited to the three version and changelog files, so ordinary
  merges never start a release run.
- The Release workflow is not part of `ci-status` (ADR 0006). Never make it a required check.
- Never change the Inno Setup `AppId`.
- The default library's name and version in the pack step must match `library:` in
  `examples/project.yaml`. `test_packaging` enforces this, and role 3 bumps them together.

## Don't do

- No tag pushes, force pushes, or moving or deleting a published tag or release.
- No edits to `src/bomgen/app/` except `launcher.py` (role 11 owns the rest), and none to
  `CHANGELOG.md` (role 7), models, examples or `data/` (role 3).
- Don't make the launcher bundle or import any library other than the one default package.
- No code signing work without a certificate from Ali.
