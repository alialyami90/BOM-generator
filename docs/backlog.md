# Backlog: next version (v0.2)

Ali's feedback after testing v0.1.0 (2026-10-28), and the work planned for each
point. A1 keeps this file current: when a point's status, milestone or owner
changes, update its row here. The milestones' details are in
[`plan.md`](plan.md) → "M12–M18 (v0.2)". The terms MCB, catalogue and loose
material are as in the spec.

## Ali's points

| # | Point (Ali, 2026-10-28) | Milestone | Owner | Status |
| --- | --- | --- | --- | --- |
| 1 | The Library screen doesn't list the MCBs, terminal blocks, auxiliary contacts or other accessories. List them, so an engineer can change the MCB brand. | M13, M16 | A2, A5, A11 | Planned |
| 2 | A device's alternatives (e.g. for the SEL-2730M) are shown by tier, but they aren't library parts, so they can't be picked. Add them to the library. | M13, M14 | A2, A3 | Planned |
| 3 | Size each MCB from the equipment's own data, worked out by the program, not from Ali's example. Fill in the data needed for every researched device. | M14, M15 | A3, A9 | Planned; rule asked on a card (Q35) |
| 4 | Create projects and substations in the app, with no YAML or project file. Files are only for import, export and backup. | M17 | A2, A11, A4 | Planned |
| 5 | Bundle the device library with the installer; it can still be updated separately. | M11 | A6 | Done in v0.1.1 (#86): the installer ships psa-devices 1.0.0 and a fresh install loads it on first start |
| 6 | Loose material belongs in its own sheet, not the substation settings; Preview doesn't show it; it must be customizable per project. | M18 | A2, A9, A10, A11 | Planned; placement asked on a card (Q36) |
| 7 | Every setting, panel value and other field shown as a static example must be a real, editable value. | M17 | A2, A11, A4 | Planned |
| 8 | Panels board: a cable manager is a passive plate, so it can sit directly against the next device. The one-blank-plate gap is only between two active devices. | M12 | A8 | In progress |
| 9 | Drag and drop on the Panels board doesn't work. | M17 | A11, A2 | Planned. Moves were waiting on the substation writers, so the board showed the drag affordance without acting on it. |
| 10 | Add and edit devices in the app, with every field editable. Export the library as a backup, and import one. Use CSV for both so engineers can work in Excel. Link alternatives in the CSV with a unique key, and show a list of all the alternatives for a device so they can be compared. | M16 | A5, A11, A4, A2 | Planned |

## Order

1. Now, in parallel:
   - M12 layout fix (A8).
   - M13 library model (A2).
   - The v0.2 design pass for the editors (A4).
   - The read-only catalogue tabs on the Library screen (A11, the read side of point 1).
   - A3's research for M14, which can start before M13 lands and fills the new fields once it does.
2. After M13: M14 data (A3) and M16's store and CSV work (A5). Then M17's writers (A2).
3. After Ali's cards: M15 (A9) and M18 (A2, A9, A10).
4. After A4's design and the back ends: the app editors (A11) for M16, M17 and M18.
5. v0.2.0 ships with the new default library (psa-devices 1.1.0) bundled (A6).
