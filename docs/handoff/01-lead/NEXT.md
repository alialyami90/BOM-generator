# Role 1 (lead): next

**Next action:** check the open PRs (`list_pull_requests state=open`) and review and merge them in the order below, using the procedure in LESSONS.md.

1. **v0.1.1 re-tag (release; A6, A7).** A7's CHANGELOG PR extends 0.1.1 to cover #88–#129.
   Merge it, then give Ali that merge commit on a card or in a message, so he can delete v0.1.1
   and re-push it there. B6 follows the release run. Hold code merges (#130, #131) until the tag
   is pushed, so the changelog matches the tag. Done when the GitHub Release v0.1.1 exists.
2. **Remaining checkpoints.** #139 (role 5) and #140 (role 7) after their ROSTER rebase, then
   roles 3 and 9 when they arrive. Check each touches only `docs/handoff/<its folder>/` and its
   own ROSTER row. Tell the coordinator as each merges, so it can start the B thread.
3. **#130 (A3, M14 library entries).** Reviewed locally on 87eee46: clean merge, gate passes
   (2414, goldens 94), CI and Windows build green. A2 reviewed it on GitHub: fine, with two notes.
   (i) The example's check report now WARNs `dc_float` because iC60N `dc_rating_v` 125 is below
   140. That is expected under Q37, so the PR isn't blocked. (ii) The full pytest run went from
   about 2 to 9 minutes, because the library is about 4,600 lines. Ask role 2 for a
   session-scoped parsed-library fixture or a load cache as a follow-up. Still waiting on A5/B5's
   sign-off on its tests. The release.yml 1.1.0 bump is an interim; the Q38 follow-up repoints it.
4. **#131 (A11/B11, M18 Loose material page on `io/loose_edit`).** Not reviewed yet. It touches
   the app, so it needs "Build Windows installer" green.
5. **A3's Q38 follow-up** (stacked on #130): `data/library/build.py` generates
   `data/library/psa-devices.yaml`, release.yml packs it, test_packaging is updated, and
   `tests/unit/test_shipped_library.py` is added. Needs A6/B6's review. Expected: the SEL
   branches go from 2 A to 6 A in the shipped library only, while the goldens stay unchanged.
6. **B2: `McbBrand.ac_rated` guard** (option (a), told to A2 on 2026-10-28). The loader refuses an
   `ac_rated: false` brand as `catalogue_choice.mcb`, and A3 sets the flag on C60H-DC.
7. **Ali's card "choose the DC MCB brand separately from the AC one?"** (posted 2026-10-28,
   recommended: separate choices). If he says yes, assign Q39 and an ADR number (next 0023) to
   role 2 for the model, then role 9 for the engine.
8. **B11 queue after #131:** the Library editors (edit, local version, CSV, comparison), then
   project and substation creation on `io/lifecycle`. Each needs the Windows build.
9. **v0.2.0 release** once points 1, 4, 6, 7 and 10 of docs/backlog.md are done in the app.
   psa-devices 1.1.0 is bundled (B6).

## Don't do

- Don't edit other roles' files. Send a fix request to the owner's thread instead (agents.md).
- Don't push tags (403); Ali pushes them.
- Don't change golden values unless an ADR changes them (Q38 keeps them).
- Don't merge app or packaging PRs without a green "Build Windows installer".
- Don't mark ADRs Accepted. Only Ali does that, in review.
