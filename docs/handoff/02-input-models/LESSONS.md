# LESSONS — role 2 (append-only)

## Decisions too small for an ADR
- **Writers compare problems by (file, location, message), not by line.** Lines move
  with an edit, so comparing lines would block sound edits. (ADR 0021 point 2.)
- **`Project.substations` stays required but may be empty** (M17d). A
  `default_factory` would have hidden a misspelt key, and the
  `test_*misspelt*` test caught it. The build refuses an empty substation ("has no
  panels yet").
- **A loose item's "Designation" is the existing `tag`.** No new key, so existing files
  load unchanged. (ADR 0022 point 1.)
- **Removing the last loose item leaves `items: []`.** `host_panel` and `title` are
  kept, and the engine prints no sheet without rows (#123).
- **`validate_*` functions are dry runs of the writer.** One code path, so the form's
  message is exactly what the save would report.

## ruamel.yaml round-trip (traps found while building `io/round_trip.py`)
- Settings that make `examples/` dump byte-identical: `indent(mapping=2, sequence=4,
  offset=2)`, width 4096, `_PaddedEmitter` for `{ a: 1 }`, and `null` written out.
- A comment after an entry is `ca.items[key][2]` (map) or `[0]` (seq). A flow
  collection's comment sits in its parent's slot. Blank lines before a key may sit in
  `ca.items[key][1]`.
- Failures, and what fixed them:
  - Deleting or emptying produced invalid YAML. Fixed by moving tails (`_take_tail` /
    `_put_tail`, `edit_document`) and writing empty containers in flow style.
  - Double blank lines came from `[1]` lead comments. Fixed by `_drop_blank_lead`.
  - The comment column shifted when a value grew. Fixed by `_shift_comment`.
- `mkstemp` makes files 0600. `write_atomic` keeps the old mode (new files get 0644)
  and creates the parent folder (A1 review on #106/#112).

## Testing
- Copy shared fixture dicts (`dict(ABB_MCB)`) before mutating them: one test leaked
  into the next.
- The suite is slow (2 min on main). Run the module under test first, then the whole
  suite, in the background, before you commit.

## B2, 2026-10-28
- **Gate commands:** `mypy` and `pytest` on PATH are isolated installs without pydantic,
  so they fail. Run `pip install -e ".[dev]"`, then use `python -m mypy` and
  `python -m pytest`.
- **One push branch per session.** A peer can't grant a second branch. After each squash
  merge, `git checkout -B <branch> origin/main`, cherry-pick the next commit, then
  `git merge -s ours origin/<branch>` so the push fast-forwards (force-push is blocked).
  Keep queued commits on local `b2-*` branches, with a patch backup in project files.
- **Editable install points at the main checkout.** To test another branch in a worktree,
  run with `PYTHONPATH=src`, or you test the wrong `src/`.
- **Suite speed:** the cost was YAML parsing, not pydantic. Profile one slow test with
  `python -m cProfile -s cumtime -m pytest <test>` before adding fixtures. The parse cache
  is keyed by text, so it can't go stale. Errors aren't cached, so each names its own file.
- **Rebasing a test module both sides appended to:** take main's file, then add your own
  appended tail from `git show <commit>` (old base vs new). That's simpler than resolving
  interleaved hunks.

## B2, 2026-10-29 (handover)
- **ruamel anchors:** ruamel writes `&id001`/`*id001` when the same object is dumped
  twice. A `date` reused for three register entries did this. `_Representer.ignore_aliases`
  in `io/round_trip.py` returns True for scalars only. Ignoring aliases for lists and
  mappings too broke the byte-identical round trip of `examples/library.yaml`: ruamel drops
  `id\d+` anchor names on load, so you can't tell the file's own anchors from generated ones.
- **Flow vs block style:** an empty collection is written in flow style (`[]`, `{}`) so
  the file stays valid YAML. When it gains its first entry, `set_entry` switches it to
  block style. Otherwise new nested mappings are written as `{ a: 1 }`.
- **`model_copy` skips validators.** Anything built with `model_copy(update=...)` (like
  `resolve_catalogues`) can hold values the model itself would refuse. Prefer computing
  in a property, or re-validate.
- **Seeded defaults with no source** get a `# ASSUMED` comment (`set_comment(node, key,
  "ASSUMED")`). The app highlights them through `fields.assumed_fields(file)`. Ask the
  lead before picking one. The lead may collect them into one question for Ali.
- **Single branch, queued work:** while one PR is open on the push branch, build the
  next one on a local branch from `origin/main`. After the merge, rebuild the push branch
  with `checkout -B ... origin/main`, `cherry-pick`, and `merge -s ours`.
- **Messaging threads:** check the thread id against `list_threads` before sending. A
  wrong id reaches a retired thread silently.
- **Ownership of `schemas/`:** it is not in the agents.md row, but it is generated from
  role 2's models, so role 2 regenerates it with every model change. No test checks that
  it is current.
