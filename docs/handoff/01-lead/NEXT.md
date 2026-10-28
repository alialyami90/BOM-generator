# Role 1 (lead): next

**Next action:** run `list_pull_requests state=open` and review and merge each PR, using the procedure in LESSONS.md, in the order below.

1. **#157 (B10, power footnote rows).** Held for Ali's card on the print area (spec: A1:L97).
   "Print it": merge, then add a plan note that the print area now covers the footnote (a
   correction to the reference). "Keep it off the printout": B10 stops the print area at the
   NOTES first. Done when it is merged and the plan says which.
2. **A3's Q38 PR** (`data/library/build.py` → `psa-devices.yaml`, release.yml packs it,
   `test_shipped_library.py`, `ac_rated: false` on C60H-DC). B6 reviews the release.yml part.
   Expected: SEL branches go from 2 A to 6 A in the shipped library only; goldens unchanged.
   After the merge, add `data/library/` to role 3's row in agents.md and tell B9 its task 1
   (sizing against the shipped library) is unblocked.
3. **#155 and the rest of B11's queue** (Library editors b–d, then project and substation
   creation on `io/lifecycle`). Each needs a green "Build Windows installer" and B4's review.
   B11 raised two gaps directly with B5 (device-record edits) and B2 (a "rows that use a part" query).
4. **B7's docs pass** (README and CHANGELOG "Unreleased" entries for #130–#154, README:62
   "tag-driven").
5. **Checkpoint refreshes** from A3, B6 and B9: docs only, own folder and own ROSTER row.
   Tell the coordinator as each merges.
6. **Ali, when he has time:** one batch-accept card for the Proposed ADRs (list in STATE), and
   B10's header-fit Print Preview check.
7. **v0.2.0 release** once points 1, 4, 6, 7 and 10 of docs/backlog.md are done in the app. The
   release is a PR that bumps `__version__` and pyproject with a `## [0.2.0]` CHANGELOG section;
   merging it publishes (#153). B6 follows the run.

## Don't do

- Don't edit other roles' files. Send a fix request to the owner's thread instead (agents.md).
- Don't bump the version outside the release PR: on main it publishes at once (#153).
- Don't change golden values unless an ADR changes them (Q38 keeps them).
- Don't merge app or packaging PRs without a green "Build Windows installer".
- Don't mark ADRs Accepted. Only Ali does that, in review.
- Don't change what the spec describes without Ali's card (CLAUDE.md), as with #157.
