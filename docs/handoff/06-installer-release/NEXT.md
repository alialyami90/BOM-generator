# NEXT — role 6, Windows installer and release

**Next action:** when A3's Q38 PR is up, review its release.yml part (task 1).

## Tasks, in priority order
1. **Review A3's Q38 PR, release.yml part (A1's ask).** A3 repoints the "Build the default device library" pack step from `examples/library.yaml` 1.0.0 to the shipped library file at 1.1.0. Check:
   - the pack step and the first-start regex (`psa-devices\s+1\.0\.0 \(active\)`) both move to 1.1.0;
   - `tests/unit/test_packaging.py::test_release_workflow_packs_the_default_library_the_project_names_before_compiling` ties name and version to the shipped file, not `examples/project.yaml`;
   - ADR 0009 and the M11 section follow;
   - the PR's "Build Windows installer" job is green.
   Reply on the PR, and tell A1. Done when A1 has my review.
2. **First release from main (v0.2.0 or the next version).** When A1 or Ali call a release, the version-bump PR is one PR: `__version__`, `pyproject.toml`, `tests/test_package.py` (ask A1 before touching; not ours) and the `CHANGELOG.md` section (A7/A1 write it). After A1 merges it, follow the push run of `release.yml` on main: `plan` must say "Releasing v<version>", then installer, then "Publish GitHub Release". Then `get_release_by_tag`, confirm `bomgen-setup-<version>.exe`, send Ali the link and tell A1. If `plan` fails on the changelog or pyproject check, nothing was created: report to A1. If the tag creation is refused (a tag ruleset), report to A1 and Ali; the fallback is Ali publishing a release in the UI on that commit, which the workflow fills. Done when the link is sent.
3. **Ask A1 to accept ADR 0009** (status is "Proposed"). Done when the status line changes (my file; A1 decides).
4. **If M10 UI work adds new dependencies or data files**, check the frozen build bundles them (A1 may ask): freeze the PR head locally with `pip install ".[app]" -r packaging/requirements.txt` and `pyinstaller packaging/bomgen.spec`, run the frozen `--self-test` and `bomgen build examples/project.yaml`. Precedent: ruamel.yaml (#106) needed no spec change; its hook ships in pyinstaller-hooks-contrib.

## Rules of the release workflow (do not break)
- Any change to `release.yml`, `bomgen.iss`, `bomgen.spec` or `launcher.py` needs the "Build Windows installer" job green on the PR head before A1 merges (A1's standing rule since #55).
- Releases start from main (#153, ADR 0009): a merged PR that changes `__version__` releases when `v<version>` does not exist and CHANGELOG has `## [<version>]`. Keep build, tag and release in one run (a GITHUB_TOKEN tag starts no other workflow) and keep release runs uncancelled. Hand-pushed tags still work and must equal `__version__`; the workflow attaches to an existing release or creates one.
- The Release workflow is path-filtered and is not part of `ci-status` (ADR 0006); never make it a required check.

## Don't do
- No code signing work unless Ali supplies a certificate (Q19).
- No edits to `src/bomgen/app/` except `launcher.py` (A11), `CHANGELOG.md` (A7/A1), models or examples.
- No tag pushes, force pushes or moving a published tag.
- Don't make the launcher bundle or import libraries other than the one default package.
