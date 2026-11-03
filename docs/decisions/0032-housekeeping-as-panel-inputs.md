# 0032. Housekeeping as panel inputs

- Status: Accepted (Ali, 2026-11-03)
- Date: 2026-11-03
- Spec sections: Derivation rules → Housekeeping kit (group D); Derivation rules → AC distribution
  (group E); Derivation rules → Terminal block quantities (group G), THF and XSD rows; Inputs,
  2. Substation and its panels (Options)

## Context

"Housekeeping kit (group D)" fixes every cabinet's kit (two fans and three thermostats, or filters
and one thermostat), and "AC distribution (group E)" fixes the branch ratings (C1 lamp 1A, C2 and C3
fan + thermostat 2A, C4 thermostat 1A, one 2A spare). The engine holds these as module constants in
`engine/housekeeping.py` and `engine/ac_dist.py`. The engineering workflow review (2026-11-03,
section "Panel design") found that an engineer can't change a count, add a heater or hygrostat, or
say that the smoke detector is supplied by others, and that a housekeeping part with real watts is
never sized from them. Milestone M56 of the agent plan makes them inputs.

## Decision

1. **Counts are panel options with the spec's defaults.** `PanelOptions.housekeeping` holds
   `fans`, `thermostats_forced`, `thermostats_natural`, `filters` and `lamps`. Unset means the
   spec's count, so every existing panel builds as today. The ventilation choice from Heat
   Calculations still picks forced or natural; the counts only say how many of each.
2. **Heater and hygrostat** are new housekeeping roles in the library (`Housekeeping.heater`,
   `hygrostat`, also in each housekeeping brand set and as `housekeeping.csv` roles). A panel
   option `heater: true` or `hygrostat: true` adds the group D row, its own AC branch after the
   thermostat branches, its terminals and its power line. Both default to off.
3. **Smoke detector** becomes `none`, `terminals` (today: the XSD strip only, the detector by
   others) or `supplied` (the strip plus a group D row from the new `smoke_detector` role). The
   loader reads today's `true` as `terminals` and `false` as `none`, so existing files keep their
   meaning.
4. **Branch ratings.** A housekeeping branch takes, in order: the panel's `branch_ratings` entry
   for its load (`lamp`, `fan`, `thermostat`, `heater`); else, when the part has `unit_power_w` and
   `supply_type: VAC`, the smallest AC catalogue rating that meets ADR 0019's running condition for
   the branch's loads, never below the spec's fixed rating; else the spec's fixed rating. The
   `min_branch_mcb_a` floor (2 A) does not apply to housekeeping branches, so the lamp stays 1A.
   The spare stays the largest housekeeping branch, and CINC follows its existing rule.
5. **Terminals follow the kit.** THF is computed from the actual fans and thermostats (12 forced
   and 5 natural at the defaults); a heater or hygrostat adds its own strip rows as ADR 0033 sets.
6. Every count and rating is returned with its rule text (M48), and the panel editor shows them as
   derived values with an override and a reset.
7. The spec gets one sentence in "Housekeeping kit (group D)" and one in "AC distribution
   (group E)": the counts and ratings are panel inputs whose defaults are the values stated.

## Consequences

- With no new option set, groups D, E and G, the power and heat totals and the golden values are
  unchanged: the shipped and example housekeeping parts draw well under their fixed ratings.
- A heater adds AC power and heat; the heat check counts it, so a heater can change the
  ventilation result. The rule text says so.
- Libraries need the three new roles filled per brand before an engineer can pick them; M68's
  health view lists unfilled roles.
