# 0040. Overrides listed in Checks, reasons for risky ones

- Status: Proposed
- Date: 2026-11-04
- Spec sections: Derivation rules (DC distribution, AC distribution, terminals, grounding,
  housekeeping, heat dissipation); Inputs → 2. Panel definition; Revision History sheet (ADR 0036)

## Context

The workflow review's "automation contract" (points 4 to 6) asks that Checks list every override in
one place, that a default say where it came from, and that an override which weakens a check carry a
one-line reason printed in the revision history. M48 built the derived-value component (value, rule,
override, reset) and M49 to M69 applied it, so overrides now live in many inputs: the main MCB and
spare breaker ratings, terminal quantities and block types, housekeeping counts and breakers
(ADR 0032, 0033), SFP spare and extra counts, part overrides (ADR 0024), layout moves, spares-list
quantities (ADR 0035) and, with M72, switch counts. Nothing lists them together, no override records
why, and four derived values still show no rule: grounding busbars, switch counts, the cable
managers' count and the fan choice. Point 5 is done for the design basis (M52).

## Decision

1. **An Overrides group in the check report.** `engine/overrides.py` lists every override the build
   applied, from the inputs and the derived values the pipeline already carries: one `CheckItem` with
   `check="override"`, the panel, the subject (the derived value's key, e.g. `main_mcb`,
   `terminals.X3-AC`, `spares.<ordering code>`), the message "16 A instead of the automatic 10 A" and
   `values` holding `automatic`, `override` and `reason`. The CLI report and the app's Checks page
   show them as a group *Overrides* after the warnings, each with *Go to the field*. An override
   equal to the automatic value is still listed (it is stored, so it stops moving with the inputs).
2. **A reason for a risky override.** An override is risky when it weakens a check: a main MCB,
   spare breaker or housekeeping breaker below the engine's rating, a terminal quantity below its
   rule, a spare quantity below the policy, `ventilation: natural` where the heat check wants fans,
   and a switch count below the computed one if Q72 allows it. The reason is stored beside the
   override in the file that holds it: `PanelOptions.override_reasons: dict[str, str]` keyed by the
   subject above, and `reason` on a spares-list line. A risky override with no reason is a `warn`
   check ("16 A main MCB is below the automatic 10 A: give a reason") so the build still runs;
   the derived-value component asks for the reason when the typed value is weaker. The reasons are
   not inputs to any rule.
3. **Printed in the revision history.** Recording an issue (ADR 0036) copies the risky overrides
   with their reasons into the `IssueRecord` (`overrides: list[OverrideNote]`, subject, values and
   reason), and the Revision History sheet gains a seventh column, *Overrides*, listing them one per
   line for that issue. Older issues and the current unrecorded revision leave it blank. This amends
   ADR 0036's sheet by that column only.
4. **The remaining rule texts.** `engine/rules_text.py` gains `grounding_rule` ("2 busbars from the
   panel options: AC safety ground, instrument ground"), `switch_count_rule` ("3 L1 switches per
   side: 54 IED ports over 20 usable per switch"), `cable_manager_rule` ("9: one under each
   rack-mounted switch, firewall and patch panel") and `fan_rule` ("SK 3244.500: the smallest fan
   whose pair moves the 410 m³/h required"). They are shown where the value is: grounding and the
   fan on the panel editor's Options tab, cable managers on the Parts row, switch counts on the
   Result card (M72 shows them; M77 supplies the text, whichever merges first).

No golden value moves: the group only reports, the reasons are text, and the rule texts describe
what the engine already does.

## Consequences

- Easier: one place answers "what did the engineer change on this substation", and a client reading
  the Revision History sees why a protective value is lower than the rule.
- Harder: every new derived value must register with `engine/overrides.py` or it is missing from the
  list; the M48 contract gets a fifth line saying so, and a test asserts each `Derived` the pipeline
  returns has an entry.
- To watch: the risky set is a judgement. A value that is risky in one library and not another (a
  housekeeping breaker rated from the part's watts) is decided from the engine's own rating at build
  time, never from a fixed list of numbers.
