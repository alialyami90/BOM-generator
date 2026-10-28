# NEXT — role 6, Windows installer and release

**Next action:** check whether A7's 0.1.1 changelog merged and Ali re-pushed `v0.1.1`; then follow that tag's Release run and send Ali the link (task 1).

## Tasks, in priority order
1. **Finish release v0.1.1 (M11, no PR).** Goal: Ali has a Release page whose changelog covers what the tag contains. Never publish while the CHANGELOG misses the tagged work (Ali's rule). Steps: `list_tags` (the tag sha must be the commit A1 names after A7's changelog); find the push run of `release.yml` for the tag; when "Publish GitHub Release" succeeds, `get_release_by_tag v0.1.1`, confirm asset `bomgen-setup-0.1.1.exe`, post `https://github.com/alialyami90/BOM-generator/releases/tag/v0.1.1` to Ali, tell A1. If a job fails: read `get_job_logs`, report to A1 and Ali first, and re-run only failed jobs once they agree. If the tag still points at 9313db1 with no new changelog, cancel the run before publish (as done for 40765665083) and remind A1. Done when the link is sent.
2. **Q38 / v0.2.0: default library from A3's shipped file (M11).** Trigger: A1 says A3's PR with the library file (likely `data/library/psa-devices.yaml`) is merged. Change `.github/workflows/release.yml` ("Build the default device library" pack step and the first-start check regex) from 1.0.0 to 1.1.0 using that file instead of `examples/library.yaml`; update `tests/unit/test_packaging.py::test_release_workflow_packs_the_default_library_the_project_names_before_compiling` (it currently ties name/version to `examples/project.yaml`'s `library:`; A1 says the shipped file, not the example, is the source) and the `psa-devices` regex test; update ADR 0009 and the M11 section of `docs/plan.md`. The file path and version 1.1.0 are A1's word, unverified until A3's PR merges: read it first. Ask A5 (thread in STATE) if the pack flags change. A v0.2.0 tag also needs the version bump in `pyproject.toml`, `src/bomgen/__init__.py`, `tests/test_package.py` (not ours: ask A1 before touching, as for #84/#86). Failing tests first. Done when the gate passes, a PR is open, and the Windows job is green (A1 merges only after that).
3. **Ask A1 to accept ADR 0009** (status is "Proposed"). Done when the status line changes (my file; A1 decides).
4. **After each release PR merges, ask A7 for the CHANGELOG entry** (A7/A1 own CHANGELOG.md; never edit it).
5. **If M10 UI work adds new dependencies or data files**, check the frozen build bundles them (A1 may ask): freeze the PR head locally with `pip install ".[app]" -r packaging/requirements.txt` and `pyinstaller packaging/bomgen.spec`, run the frozen `--self-test` and `bomgen build examples/project.yaml`. Precedent: ruamel.yaml (#106) needed no spec change; its hook ships in pyinstaller-hooks-contrib.

## Rules of the release workflow (do not break)
- Any change to `release.yml`, `bomgen.iss`, `bomgen.spec` or `launcher.py` needs the "Build Windows installer" job green on the PR head before A1 merges (A1's standing rule since #55).
- Tags are lowercase `v<version>` and must equal `bomgen.__version__`; Ali pushes them (the sandbox cannot). The workflow attaches to an existing release or creates one.
- The Release workflow is path-filtered and is not part of `ci-status` (ADR 0006); never make it a required check.

## Don't do
- No code signing work unless Ali supplies a certificate (Q19).
- No edits to `src/bomgen/app/` except `launcher.py` (A11), `CHANGELOG.md` (A7/A1), models or examples.
- No tag pushes, force pushes or moving a published tag.
- Don't make the launcher bundle or import libraries other than the one default package.
