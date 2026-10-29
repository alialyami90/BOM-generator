# NEXT — role 6, Windows installer and release

**Next action:** none open. Wait for the lead (B1) or Ali to call the next release, then run task 1.

## Tasks, in priority order
1. **Next release from main (after v0.2.0).** When the lead or Ali call a release, the version-bump PR is one PR: `__version__`, `pyproject.toml`, `tests/test_package.py` (the lead's go covers them; not ours) and the `CHANGELOG.md` section (role 7 writes it, merged first). Keep a ready patch: v0.2.0 used `/mnt/project-files/b6/bump-0.2.0.patch`. After the lead merges it, follow the push run of `release.yml` on main: `plan` must say "Releasing v<version>", then installer, then "Publish GitHub Release". Then `get_release_by_tag`, confirm `bomgen-setup-<version>.exe`, send Ali the link and tell the lead. If `plan` fails on the changelog or pyproject check, nothing was created: report to the lead. If the tag creation is refused (a tag ruleset), report to the lead and Ali; the fallback is Ali publishing a release in the UI on that commit, which the workflow fills. Done when the link is sent.
2. **If app work adds new dependencies or data files**, check the frozen build bundles them (the lead may ask; since #186 a missing UI file fails the frozen `--self-test`): freeze the PR head locally with `pip install ".[app]" -r packaging/requirements.txt` and `pyinstaller packaging/bomgen.spec`, run the frozen `--self-test` and `bomgen build examples/project.yaml`. Precedent: ruamel.yaml (#106) needed no spec change; its hook ships in pyinstaller-hooks-contrib.

## Rules of the release workflow (do not break)
- Any change to `release.yml`, `bomgen.iss`, `bomgen.spec` or `launcher.py` needs the "Build Windows installer" job green on the PR head before the lead merges (standing rule since #55).
- Releases start from main (#153, ADR 0009): a merged PR that changes `__version__` releases when `v<version>` does not exist and CHANGELOG has `## [<version>]`. Keep build, tag and release in one run (a GITHUB_TOKEN tag starts no other workflow) and keep release runs uncancelled. Hand-pushed tags still work and must equal `__version__`; the workflow attaches to an existing release or creates one.
- The Release workflow is path-filtered and is not part of `ci-status` (ADR 0006); never make it a required check.

## Don't do
- No code signing work unless Ali supplies a certificate (Q19).
- No edits to `src/bomgen/app/` except `launcher.py` (A11), `CHANGELOG.md` (A7/A1), models or examples.
- No tag pushes, force pushes or moving a published tag.
- Don't make the launcher bundle or import libraries other than the one default package.
