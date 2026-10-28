# NEXT — role 6, Windows installer and release

**Next action:** wait for a release call from A1 or Ali, then run task 1. ADR 0009 acceptance (task 2) is on A1's batch card for Ali.

## Tasks, in priority order
1. **First release from main (v0.2.0 or the next version).** When A1 or Ali call a release, the version-bump PR is one PR (since #161, 159591f, the installer ships psa-devices 1.1.0 from `data/library/psa-devices.yaml`; name that in the changelog): `__version__`, `pyproject.toml`, `tests/test_package.py` (ask A1 before touching; not ours) and the `CHANGELOG.md` section (A7/A1 write it). After A1 merges it, follow the push run of `release.yml` on main: `plan` must say "Releasing v<version>", then installer, then "Publish GitHub Release". Then `get_release_by_tag`, confirm `bomgen-setup-<version>.exe`, send Ali the link and tell A1. If `plan` fails on the changelog or pyproject check, nothing was created: report to A1. If the tag creation is refused (a tag ruleset), report to A1 and Ali; the fallback is Ali publishing a release in the UI on that commit, which the workflow fills. Done when the link is sent.
2. **ADR 0009 acceptance** (status is "Proposed"). Only Ali accepts ADRs; A1 is putting it on a batch-accept card. Done when the status line changes.
3. **If M10 UI work adds new dependencies or data files**, check the frozen build bundles them (A1 may ask): freeze the PR head locally with `pip install ".[app]" -r packaging/requirements.txt` and `pyinstaller packaging/bomgen.spec`, run the frozen `--self-test` and `bomgen build examples/project.yaml`. Precedent: ruamel.yaml (#106) needed no spec change; its hook ships in pyinstaller-hooks-contrib.

## Rules of the release workflow (do not break)
- Any change to `release.yml`, `bomgen.iss`, `bomgen.spec` or `launcher.py` needs the "Build Windows installer" job green on the PR head before A1 merges (A1's standing rule since #55).
- Releases start from main (#153, ADR 0009): a merged PR that changes `__version__` releases when `v<version>` does not exist and CHANGELOG has `## [<version>]`. Keep build, tag and release in one run (a GITHUB_TOKEN tag starts no other workflow) and keep release runs uncancelled. Hand-pushed tags still work and must equal `__version__`; the workflow attaches to an existing release or creates one.
- The Release workflow is path-filtered and is not part of `ci-status` (ADR 0006); never make it a required check.

## Don't do
- No code signing work unless Ali supplies a certificate (Q19).
- No edits to `src/bomgen/app/` except `launcher.py` (A11), `CHANGELOG.md` (A7/A1), models or examples.
- No tag pushes, force pushes or moving a published tag.
- Don't make the launcher bundle or import libraries other than the one default package.
