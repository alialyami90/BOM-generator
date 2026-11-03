# 0031. Design basis

- Status: Accepted (Ali, 2026-11-03)
- Date: 2026-11-03
- Spec sections: Inputs the tool needs → 2. Substation and its panels, 3. Project settings; Tag
  naming conventions; Validation and warnings

## Context

The engineering workflow review (`docs/superpowers/specs/2026-11-03-engineering-workflow-review.md`)
found that what an engineer states first on a real job (DC and AC voltage, LAN redundancy, Purdue
scope, time sync, tagging, the client's vendor list) has no single home. Today the voltages are
design constants inherited from the project, tag side letters and first numbers are constants in
`engine/tags.py`, and nothing records the scope or the vendor list, so Checks cannot compare the
substation with what the client asked for. Milestones M52 to M55 of the agent plan need one agreed
shape; M60 (IED schedule) and M64 (spares list) read from it.

## Decision

1. **One optional input per substation.** `substation.design_basis` holds `dc_voltage_v`,
   `ac_voltage_v`, `redundancy`, `purdue_scope`, `time_sync`, `tagging`, `spares_policy`,
   `vendor_list` and `notes`. Unset, or a key left out, means today's behaviour; the example sets
   none, so golden values do not move.
2. **It sets defaults, never a rule.** The design basis feeds a value only where the engineer has
   not written one closer to it. Order, highest first: the substation's own `constants`, the design
   basis, the project's `defaults`, the model's default. Each value the app shows says which of
   these it came from ("From the design basis"). No engine rule reads the design basis directly
   except through the values it feeds and the checks below.
3. **Mapping onto what exists today.**
   - `dc_voltage_v`, `ac_voltage_v` feed `constants.dc_voltage_v` and `ac_voltage_v`. DC is one of
     48, 110, 125, 220 or another positive number.
   - `tagging` holds the side letters (default `A`, `B`) and the first number per Purdue level
     (default L2 1, L1 11, L3 1); `engine/tags.py` reads them instead of its module constants. The
     cabinet number, cabinet name and tag prefix patterns stay in `generated_panels`, where M51's
     setup step writes them.
   - `redundancy` is `duplicated_lan` only (today's A/B LANs). PRP and HSR are refused with a
     message until a rule for them exists. M60 reads it.
   - `purdue_scope` (a set of `L1`, `L2`, `EXT`) and `time_sync` (`gps_clock`, `ptp_from_clock`,
     `none`) change no quantity; they are what M54's checks compare against.
   - `spares_policy` (percent per category, minimum per part, categories included) is stored here
     and used only by M64's spares list. Today's `spares` (port fraction, SFPs per L1, branch and
     rack spares) stay where they are and keep their meaning.
   - Brands stay in `catalogue_choice`. The design basis does not pick brands; it names a vendor
     list.
4. **Vendor lists live in the project.** `project.vendor_lists` holds named lists (allowed brand
   sets per catalogue, allowed makes, allowed and banned parts); `design_basis.vendor_list` names
   one by key. A part, brand set or make outside the list is a warning in Checks and is grouped
   after the allowed ones in the pickers, never hidden and never a build failure.
5. **Checks, warnings unless the build would be wrong** (M54): a DC-fed part whose input range
   excludes the design DC voltage fails; an AC part at another voltage, a Purdue level outside the
   scope, a GPS clock with `time_sync: none`, and EXT devices without a firewall warn.
6. **Templates carry it.** A substation template (M55) includes the design basis.

## Consequences

- A substation at 110 V DC needs one key instead of a constants override, and its Power
  Consumption sheet prints 110V.
- Two places can now set a voltage (the design basis and `constants`); the source line in the app
  and the order above say which wins.
- `engine/tags.py` gains inputs; its defaults equal today's numbers, so tags do not move.
- PRP and HSR stay out until a rule for them is written and accepted.
