# 0029. Larger fans for hot cabinets

- Status: Proposed
- Date: 2026-10-31
- Spec sections: Heat Dissipation and Heat Calculations sheets ("Rule for the tool"); Derivation
  rules → Housekeeping kit (group D); Inputs, 1. Device library (commodity catalogues)

## Context

"Rule for the tool" asks for fans whose throughput is at least the required airflow. The engine
always fitted two of the one catalogue fan (`housekeeping.fan`), so a hotter cabinet only failed
the airflow check (audit 2026-10-31, ENG-6). The spec doesn't say how to get more airflow. Ali
was offered three options on a card (A1, 2026-10-31): a bigger fan with the pair kept, more fan
pairs, or no change. Option 1, a bigger fan, was recommended and is built here. It can be
reverted if Ali picks another option.

## Decision

1. The housekeeping catalogue, and each housekeeping brand set, may list `larger_fans`, each with
   its part and its m³/h per fan, like `fan`. In CSV, each one is a `housekeeping.csv` row with
   the role `larger_fan`.
2. A forced cabinet keeps **two** fans and three thermostats. It gets the catalogue fan, or else
   the fan with the least airflow among `larger_fans` whose pair moves the required airflow.
   The required airflow counts the fans' and the thermostats' own heat, which Heat Dissipation
   includes. When no fan is enough, the largest is fitted and the airflow check fails, as it
   did before.
3. The forced check, the line-up check and Heat Calculations compare against the pair the
   cabinet got.

## Consequences

- Groups E and G don't change: C2 fan-1+TH-1 and C3 fan-2+TH-2 stay 2 A, and the THF strip
  stays the same. A fan drawing more than 2 A with its thermostat would need a rule; the shipped
  fans draw well under 1 A at 230 V.
- A library without `larger_fans` (the example and psa-devices 1.9.0) builds exactly as before.
- The library owner has to list the larger fans and their airflow; none are listed yet.
