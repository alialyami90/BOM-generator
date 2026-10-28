# Role 1 (lead): next

**Next action:** in `alialyami90/BOM-generator`, run `list_pull_requests state=open`; merge whatever is ready (#171, #166 when green), using the procedure in LESSONS.md. Items 1 and 2 wait on Ali's cards; work the rest in order.

1. **#157 (B10, power footnote rows).** Held for Ali's card on the print area (spec: A1:L97;
   card `cmsg_01CGuLumA5u5e7gSGbisWmMiMH42ayNRhuWcnbjHvKGNWm`; close it with `close_decision`).
   "Print it": merge, then add a plan note that the print area now covers the footnote (a
   correction to the reference). "Keep it off the printout": B10 stops the print area at the
   NOTES first. Done when it is merged and the plan says which.
2. **FGR-60F `dc_float` warning** (B9, #171): its datasheet input stops at 125 V DC, below the
   140 V float. Ask Ali on a card whether it stays (warning accepted, as for the iC60N under
   Q37) or the firewall needs a DC-rated alternative; recommend keeping it with the warning.
3. **#171 (B9, shipped-library sizing tests)** and **#166 (B11, Library list editing)**: merge
   when CI is green; #166 also needs "Build Windows installer". Then B11's Datasheet tab (on
   #164), CSV (b), alternatives (c), then project and substation creation on `io/lifecycle`.
4. **B7's next docs pass:** CHANGELOG "Unreleased" lines for #155, #161, #163, #164, #165 and
   the installer now shipping `data/library/` psa-devices 1.1.0.
5. **Checkpoints:** review each docs-only checkpoint PR (own folder and own ROSTER row only;
   ADR changes go in their own PR). Tell the coordinator as each merges.
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
