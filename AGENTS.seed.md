# AGENTS.seed.md

Lessons from a past project, written to start a new one. Copy it to `AGENTS.md` (or `CLAUDE.md`),
fill in the last section, and delete rules that don't fit.

## 1. Project Setup

- Put the authoritative spec in the repo before any code. When code and spec disagree, ask the
  owner before changing either, and record the answer. A gap that a reference file seems to answer
  is still a question.
- Get the owner's real reference output (spreadsheet, report, screenshot) early. Pin its numbers
  as golden tests that cite the spec section they come from. Golden values move only with a
  recorded decision.
- Create a handoff folder on day one: `STATE` (rewritten each stop), `NEXT` (first line is the
  single next action), `LESSONS` (append-only: decisions too small for an ADR, rejected
  alternatives, failed approaches) and a dated `CHECKPOINT` log. Agents lose context; the repo
  must not. Link to stable docs instead of copying them.
- Keep numbered ADRs and a numbered open-questions list. State in the agent file how to find the
  next free number, because parallel agents otherwise reuse one.
- Set up CI with a path filter so docs-only changes skip the slow jobs, plus one always-run
  aggregate status job that is the only required check. A skipped workflow reports no status and
  blocks merges. Every new job must join the aggregate job's needs.
- Decide the release path before the first release: merging a PR that bumps the version and adds
  a changelog section should build, tag and publish in one workflow run. Agent sessions often
  can't push tags, and a tag pushed by the CI token doesn't trigger other workflows.

## 2. Working Style

- Ask the owner every question as a multiple-choice card with one option marked recommended and
  a one-line reason. Ask one at a time. Keep working on the recommended option while waiting,
  unless the step can't be undone. If the owner answers in plain text, close the open cards.
- Record each answer where the next agent will find it (open-questions list or ADR), in the same
  turn.
- For a large request, run: clarifying questions, a written design the owner approves, a plan
  split into milestones, then one PR per milestone. Don't mix milestones in one PR.
- Merge your own PRs once CI is green and the branch is conflict-free, if the owner allows it.
  Asking the owner to merge each PR stalls a multi-agent project.
- Split parallel work by file ownership: each role owns named paths. A minimal guard in another
  area is fine; anything larger goes to its owner.
- Before claiming a state, verify it in this session. Status docs drift: earlier agents recorded
  merged PRs as open and stale commit hashes. Check `git log origin/main` against what the docs
  say before trusting them.
- Keep handoff docs current in batches. Check for unlisted merges each time; docs once fell dozens
  of PRs behind.
- Test a handoff by giving only the handoff folder to a fresh agent with no history and asking
  what it would do next and how it would verify it. Fix the gaps it finds.

## 3. Architecture and Code

- Keep business rules in the engine, never in the UI. The UI calls one bridge; validation runs
  through the same code path as the save, so the form shows the exact message the save would.
- Never ship illustrative or prototype data in the product. When a backend is missing, fail
  visibly. An audit found the app silently showing fake data.
- Show model errors in plain words through one mapping layer; never show raw validator text,
  enum names or pattern errors to users.
- A control that can't act must be absent or disabled with a reason. A drag handle that did
  nothing was reported as "drag doesn't work".
- Write files atomically: temp file in the same folder, then replace. On failure, delete only the
  temp file, never the target.
- When editing a human-written config file, round-trip it so comments and formatting survive.
  Test that loading and dumping the examples is byte-identical.
- In UI code that awaits, check the route is unchanged after the await before opening a dialog,
  and mark the trigger busy.
- [Python] A model copy with updates may skip validation. Re-validate or use a computed property.
- [Python] Don't give a required field a default factory just to allow "empty"; it hides misspelt
  keys. Allow an empty value instead.

## 4. Testing and Verification

- Write the failing test first, named after the rule it checks (`test_<rule_in_words>`).
- Run the full gate (lint, format check, type check, tests) before every commit, and run any
  check again just before you report its result.
- Writer tests reopen the produced file and assert its contents, formulas, styles and print
  settings, not just that it was written.
- When a test reads cached results (e.g. spreadsheet formulas), force a recalculation; otherwise
  the test compares the cache with itself.
- Check UI changes in the real app before merging: drive it headlessly, take screenshots at the
  minimum window size and a common size, and measure (overflow, wrapping, clipped text) rather
  than eyeballing.
- Before a release, run a fresh-project check: create a new project from nothing and go to the
  final output. It found bugs that example-based tests missed.
- Never loosen a test to get green. Assert the new behaviour and list changed tests in the PR.
- Don't hard-code a version or other value that changes on every release in a test; read it
  from the source of truth.

## 5. Common Pitfalls

- Don't merge a PR while its branch is still being pushed, because main gets half a change. Check
  the head commit is final, and merge with the expected head SHA.
- Don't rebase a branch after its PR was squash-merged, because it replays the whole history and
  conflicts. Recreate the branch from main instead.
- Don't let parallel PRs each edit the changelog's unreleased section and merge at once, because
  they conflict. Merge one at a time and keep the release PR last.
- Don't release with a proposed decision the owner rejected, because it ships. Revert it on main
  before the release PR merges.
- Don't trust "passed" from a grep on test output, because lint prints it too. Match the test
  runner's summary line.
- Don't commit after resolving conflicts without searching for conflict markers, because a
  partial merge once committed them into the changelog.
- Don't create a release by hand in the hosting UI when a workflow also creates it, because the
  workflow then fails.
- Don't trust a fast CI job as proof it ran. Check every step ran and the log ends as expected.
- Don't call a generated file correct from a converted copy (e.g. PDF), because converters drop
  or clip parts of it. Ask the owner to check in the real tool when only it can tell.
- Don't research the web in one large pass, because rate limits cut it off. Plan smaller passes,
  and mark data verified only when the exact code was read on a primary source; never invent a
  value.

## 6. Tools and Workflow

- Run long test suites in the background and wait on the summary line; foreground calls time out.
- In a fresh container, install the project in editable mode first, and rerun the install after
  pulling new dependencies. Run tools as `python -m <tool>` so they use the project's interpreter.
- In a git worktree, check which source tree the editable install imports; it may point at the
  main checkout and test the wrong code.
- Review a PR by fetching its head, checking a clean merge with `git merge-tree --write-tree`,
  reading the diff stat for scope, and checking CI on the newest run (a new push cancels the old
  one, which then shows as failed).
- Subscribe to PR events instead of polling.
- Use the project's skills for process (brainstorm, plan, TDD, verify before completion) and a
  design skill to produce tokens, component specs and a clickable prototype before building UI.
- Put decision-record edits in their own PR, apart from other docs changes.

## 7. Customize for This Project

- Spec: `[spec path]`; reference outputs: `[reference files]`; golden values: `[golden test path]`
- Gate: `[lint command]`, `[format check]`, `[type check]`, `[test command]`
- Install: `[install command]`; run the app: `[run command]`
- Build/release: `[build command]`; release by `[version-bump PR steps]`
- CI: required check `[aggregate job name]`; docs-only paths `[paths]`
- Docs: handoff `[handoff folder]`, ADRs `[decisions folder]`, open questions `[file and section]`,
  next free numbers `[how to find them]`
- Roles and owned paths: `[role → paths]`
- Never commit: `[generated outputs]`
- Owner's standing rules: `[merge policy, question format, release policy]`
- Stack-specific traps: `[lint rules that reject characters, platform-only steps, minimum window]`
