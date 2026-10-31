# Back to the contractor: delivery of 2026-10-31

What the library still needs from the contractor after the delivery in
`contractor-2026-10-31/` has been reviewed and its usable parts taken in (psa-devices 1.2.0
to 1.6.0). One row per part and ask is in
[`contractor-return-2026-10-31.csv`](contractor-return-2026-10-31.csv) (`part_id`, `ask`,
`detail`). The rules of the original brief still apply: every value cites its page, and a
value the document does not state gets a `not_given` row.

| Ask | Parts | What we need |
| --- | ---: | --- |
| `not_delivered` | 127 | Worklist parts with no row in `devices.csv` (`worklist_coverage.csv` says `false`). |
| `missing_fields` | 72 | Worklist parts whose row still leaves fields out, as `worklist-updated.csv` lists them: mostly the inrush peak and duration, then input range, ordering code and height. FG-600F and FG-601F have no `voltage_v` or `load_type`, so they cannot be taken in yet. |
| `ordering_code` | 62 | Parts whose ordering code needs a configuration (`device_review.csv`: configuration required or unselected). We need the configured code a substation panel orders, with the 125 V DC supply where the part offers one. |
| `port_speed` | 3 | SEL-2731, SEL-2740S and SEL-2741: the RJ45 management port has no speed. We keep the port and need its speed from the datasheet. |
| `power` | 4 | SEL-3555-2, SEL-3355-2, SEL-3560E and SEL-3560S: the delivery gives the supply's peak burden, computed or assumed. We need typical or measured consumption, or a statement that none is published (plan Q54). |
| `dc_rating` | 2 | Hager MCN and NCN 2P C: a DC rating with the two poles in series, if Hager publishes one. Until then they ship as AC-only sets. |

## Also open, not the contractor's

- Alternatives at low, mid and high tier: the delivery gives none for its new parts (one
  `mid` row in 991). The brief made alternatives optional, so this is a request, not a gap.
  Which parts need them first follows from the projects that use them.
- Five categories have no library category yet (plan Q55): security sensors, fibre channel
  switches, storage, data diodes and servers, 25 parts. They wait until a project needs one.
- The 35 Cisco spare ids ending in `=` keep the `=` in the ordering code and drop it from
  `part_id`. They come in when a switch needs them; nothing is asked of the contractor.
