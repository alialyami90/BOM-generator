# Backlog

Ali's feedback after each release, point by point, and the work done for each point. Keep this file
current: when a point's status or milestone changes, update its row here.

## v0.3: Ali's feedback on v0.2.1

Nothing yet. When the feedback arrives, number the points below (1, 2, …), propose a milestone for
each in [`plan.md`](plan.md) (from M19), and record decisions as ADRs (from 0024) or plan questions
(from Q42).

| # | Point (Ali) | Milestone | Status |
| --- | --- | --- | --- |

## v0.2 (shipped in v0.2.0)

Ali's feedback after testing v0.1.0 (2026-10-28), and the work done for each
point; all ten shipped in [v0.2.0](https://github.com/alialyami90/BOM-generator/releases/tag/v0.2.0) (2026-10-29). The milestones' details are in
[`plan.md`](plan.md) → "M12–M18 (v0.2)". The terms MCB, catalogue and loose
material are as in the spec.

### Ali's points

| # | Point (Ali, 2026-10-28) | Milestone | Status |
| --- | --- | --- | --- |
| 1 | The Library screen doesn't list the MCBs, terminal blocks, auxiliary contacts or other accessories. List them, so an engineer can change the MCB brand. | M13, M16 | Done in v0.2.0. Catalogue tabs (#93), brand sets per project and substation (#97), the store side (#114, #116, #118, #120) and the app's library editor (#155, #166, #175, #178, #180); DC MCBs can take their own brand set (ADR 0023, #130). |
| 2 | A device's alternatives (e.g. for the SEL-2730M) are shown by tier, but they aren't library parts, so they can't be picked. Add them to the library. | M13, M14 | Done in v0.2.0. Alternatives are library parts with `alt_group` and `tier` (#97, #121), compared on the Alternatives tab (#180), and "Use this instead" puts one on an equipment row (#194, after the release). |
| 3 | Size each MCB from the equipment's own data, worked out by the program, not from Ali's example. Fill in the data needed for every researched device. | M14, M15 | Done in v0.2.0. Computed sizing with a 2 A floor (#103), float-voltage warnings (Q37, #109), the shipped psa-devices 1.1.0 with datasheet data (Q38), sizing pinned against it (#171); DC MCB brand apart from AC (Q39, ADR 0023). |
| 4 | Create projects and substations in the app, with no YAML or project file. Files are only for import, export and backup. | M17 | Done in v0.2.0. Create, rename and delete projects and substations in the app (#181, #182); a blank substation is seeded so it can take equipment (#189, #192). |
| 5 | Bundle the device library with the installer; it can still be updated separately. | M11 | Done in v0.1.1 (#86): the installer ships psa-devices 1.0.0 and a fresh install loads it on first start |
| 6 | Loose material belongs in its own sheet, not the substation settings; Preview doesn't show it; it must be customizable per project. | M18 | Done in v0.2.0. Its own sheet (#96) and Preview tab (#108), free-text items (#122, ADR 0022), and the Loose material page (#146). |
| 7 | Every setting, panel value and other field shown as a static example must be a real, editable value. | M17 | Done in v0.2.0. Project and substation fields and Settings (#185, #190), equipment rows (#188), and the documents register (#192) are all editable. |
| 8 | Panels board: a cable manager is a passive plate, so it can sit directly against the next device. The one-blank-plate gap is only between two active devices. | M12 | Done (#90, #101). |
| 9 | Drag and drop on the Panels board doesn't work. | M17 | Done in v0.2.0. Drag and drop with pins, deletes and undo (#126), and keyboard moves (#129). |
| 10 | Add and edit devices in the app, with every field editable. Export the library as a backup, and import one. Use CSV for both so engineers can work in Excel. Link alternatives in the CSV with a unique key, and show a list of all the alternatives for a device so they can be compared. | M16 | Done in v0.2.0. The library editor, CSV export and import, `.bomlib` backup and the alternatives comparison (#155, #166, #175, #178, #179, #180). |

### Order

All of it shipped in v0.2.0; v0.2.1 added the UI polish pass (`docs/ui/polish-v02.md`).
