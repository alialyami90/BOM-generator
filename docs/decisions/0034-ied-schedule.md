# 0034. IED schedule

- Status: Proposed
- Date: 2026-11-03
- Spec sections: Automatic panel layout; Inputs, 2. Substation and its panels; Derivation rules →
  Network accessories (group C)

## Context

The L1 network is sized from one number, `network.ied_count` (ADR 0013): every IED is taken as
dual-attached with one 100 Mb MM port per side (`engine/sizing.py`). The engineering workflow review
(2026-11-03, section 2 and F2) found that copper IEDs, 1G IEDs, single-attached IEDs and bays can't
be described, so the L1 switch pick and the SFP mix can be wrong for a real IED list. Milestone M60
of the agent plan adds an IED schedule; M61 builds external links on it.

## Decision

1. **The schedule is an input; the count stays as a quick mode.** `network.ied_schedule` is a list
   of rows: bay, name (type or tag), quantity, ports per IED (count, speed, media), attachment
   (`dual`, `single_a`, `single_b`; default `dual`) and where it lands (`l1`, or `l2` directly;
   default `l1`). A substation sets either `ied_count` or a schedule, never both.
2. **Sizing per speed and media per side.** With a schedule, the engine sums the ports each side
   needs per speed and media and sizes the L1 switches against their port groups; a dual IED needs
   its ports on both sides, a single-attached IED on its side only, and a row landing on L2 adds to
   the L2 demand. When no candidate switch serves a speed and media, the sizing error names it
   ("1G RJ45").
3. **The SFP mix follows.** The L1 port plan's downlinks follow the schedule's mix, so M49's SFP
   "used" quantity follows it too.
4. **The quick count is the old rule.** `ied_count: n` sizes exactly as a schedule of n dual
   100M MM IEDs landing on L1 would, which is today's behaviour.
5. Rows are typed in the app; a CSV import from the protection design (`bay,name,qty,ports,
   attachment,lands_on`) fills the same rows through a dry-run review.
6. The spec gets one sentence under "Automatic panel layout" and one under "Inputs, 2": the L1
   demand comes from the IED schedule when there is one, and `ied_count` is then derived from it.

## Consequences

- The example keeps `ied_count` and builds unchanged; golden values don't move.
- A schedule can pick a different L1 switch or fail sizing where a count passed. The error names
  what doesn't fit.
- Port groups on library switches must carry correct speed and media, which M67's sources help
  check.
