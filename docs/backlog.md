# Backlog: next version (v0.2)

Ali's feedback after testing v0.1.0 (2026-10-28), and the work planned for each
point. A1 keeps this file current: when a point's status, milestone or owner
changes, update its row here. The milestones' details are in
[`plan.md`](plan.md) → "M12–M18 (v0.2)". The terms MCB, catalogue and loose
material are as in the spec.

## Ali's points

| # | Point (Ali, 2026-10-28) | Milestone | Owner | Status |
| --- | --- | --- | --- | --- |
| 1 | The Library screen doesn't list the MCBs, terminal blocks, auxiliary contacts or other accessories. List them, so an engineer can change the MCB brand. | M13, M16 | A2, A5, A11 | In progress. Catalogue tabs read-only (#93); brand sets per project and substation (#97); the store side of editing is done (M16: #114, #116, #118, #120); the app's editors come next (A11). |
| 2 | A device's alternatives (e.g. for the SEL-2730M) are shown by tier, but they aren't library parts, so they can't be picked. Add them to the library. | M13, M14 | A2, A3 | In progress. Alternatives are library parts with `alt_group` and `tier` (#97); the comparison list is designed (#99) and built (#120); the researched data is in (#121), and A3's library entries for psa-devices 1.1.0 come next. |
| 3 | Size each MCB from the equipment's own data, worked out by the program, not from Ali's example. Fill in the data needed for every researched device. | M14, M15 | A3, A9 | Rule done: computed sizing with a 2 A floor, spikes under 10 ms ignored (#103), DC float-voltage warnings, iC60N kept (Q37, #109). Per-device data researched (#121); Q38: the shipped psa-devices 1.1.0 carries the datasheet data, the spec example keeps its values (A3, A6). Q39: DC MCB brand chosen apart from AC (ADR 0023, B2 then B9). |
| 4 | Create projects and substations in the app, with no YAML or project file. Files are only for import, export and backup. | M17 | A2, A11, A4 | In progress. Writers for substations, panels, fields and project lifecycle are in (#106, #112, #115, #119); the app's editors come next (A11). |
| 5 | Bundle the device library with the installer; it can still be updated separately. | M11 | A6 | Done in v0.1.1 (#86): the installer ships psa-devices 1.0.0 and a fresh install loads it on first start |
| 6 | Loose material belongs in its own sheet, not the substation settings; Preview doesn't show it; it must be customizable per project. | M18 | A2, A9, A10, A11 | In progress. Q36: its own sheet (#96) and its own Preview tab (#108); the editor page is designed (#102); free-text items and their writers are in (#122, ADR 0022), and the sheet is written only while it has rows (#123). The editor page comes with the app (A11). |
| 7 | Every setting, panel value and other field shown as a static example must be a real, editable value. | M17 | A2, A11, A4 | In progress. Writers for the generated-panel editor (#106), hand-written panels (#112) and every field (#115); the app's editors come next (A11). |
| 8 | Panels board: a cable manager is a passive plate, so it can sit directly against the next device. The one-blank-plate gap is only between two active devices. | M12 | A8 | Done (#90, #101). |
| 9 | Drag and drop on the Panels board doesn't work. | M17 | A11, A2 | In progress. Pins with a position (#100), the board shows pins (#110), the layout writers are in (#106), and the app's edit endpoints too (#117); A11's drag-and-drop PR is next. |
| 10 | Add and edit devices in the app, with every field editable. Export the library as a backup, and import one. Use CSV for both so engineers can work in Excel. Link alternatives in the CSV with a unique key, and show a list of all the alternatives for a device so they can be compared. | M16 | A5, A11, A4, A2 | In progress. Design (#99); local library versions (#105), edits (#114), CSV export and import (#116, #118) and the alternatives comparison (#120) are done; the app's editors come next (A11). |

## Order

1. Now, in parallel:
   - M12 layout fix (A8).
   - M13 library model (A2).
   - The v0.2 design pass for the editors (A4).
   - The read-only catalogue tabs on the Library screen (A11, the read side of point 1).
   - A3's research for M14, which can start before M13 lands and fills the new fields once it does.
2. After M13: M14 data (A3) and M16's store and CSV work (A5). Then M17's writers (A2).
3. Ali answered Q35 and Q36, so M15 (A9) and M18 (A10 leading, with A2 and A9) start now and build on M13 where they need it.
4. After A4's design and the back ends: the app editors (A11) for M16, M17 and M18.
5. v0.2.0 ships with the new default library (psa-devices 1.1.0) bundled (A6).
