# 0037. Record lifecycle and sources

- Status: Proposed
- Date: 2026-11-03
- Spec sections: Inputs the tool needs → 1. Device library; Validation and warnings

## Context

The engineering workflow review (`docs/superpowers/specs/2026-11-03-engineering-workflow-review.md`)
found that a library part says nothing about where its sizing numbers came from or whether anyone
checked them. The device database (`data/device-db/`) knows (`verified`, `sources`, a tier's
`power_basis`), but the library the generator builds from does not, so a part with an assumed or
zero wattage looks the same on Parts as one read from a datasheet. There is also no way to mark a
part as not yet checked, or as replaced by another. Milestones M67 to M69 and M53 (vendor list and
part states) need one agreed shape for both.

## Decision

1. **State.** `DeviceType.state` is one of `draft`, `reviewed`, `released`, `obsolete`, default
   `released`, so every existing library loads and means what it does today. A shipped library is
   all `released`. `successor` (a `part_id`) is allowed only on an `obsolete` part, must name
   another part of the same library, and is optional there.
2. **State never changes a BOM.** The generator builds from a part in any state. A picked `draft`
   or `obsolete` part is a warning in Checks (M53), the obsolete one naming its successor. Golden
   values do not move.
3. **Sources.** `DeviceType.sources` maps a sized field to its source. The sized fields are
   `unit_power_w`, `inrush_a`, `height_u`, `input_v_max` and `ports`. A source is
   `kind` (`datasheet`, `contractor`, `assumed`, `measured`), `ref` (a URL, document number or, for
   `assumed`, why) and an optional `date`. A source for a field the part leaves unset is refused.
   Sources are optional in the model, so old files load.
4. **Editing a sized value needs a source.** A pending set (device editor or CSV import) that changes
   a sized field's value and does not set that field's source in the same set is refused with a
   message naming the part and the field. The source may be `assumed`; it just has to be said.
5. **Who and when.** `changed_by` (the Windows user name), `changed_on` (date) and `note` (the
   pending set's note) are written by the local save on each record the set touched. They are
   record metadata, not inputs; the diff shows them but they never count as a change on their own.
6. **Shipped library migration.** `data/library/build.py` gives every shipped part a source for
   each sized field it sets, once: `datasheet` with the record's first source when its
   device-database record is `confirmed` or `partial` and the figure is not marked assumed;
   `contractor` for parts that came through `additions.yaml` from the contractor's delivery;
   `assumed` with the reason otherwise. A test keeps it that way.
7. **CSV (ADR 0018).** `devices.csv` gains `state`, `successor` and one `source_<field>` column per
   sized field written as `kind|ref|date`; an empty cell is no source.
8. **Package compatibility (ADR 0008).** The library schema version stays 1: every new field is
   optional and a version 1 file still loads. An older bomgen refuses a library that uses the new
   keys, so a package or local save that sets any of them carries a `min_app_version` of the
   release that reads them, and the older app says "needs bomgen X or later" instead of a
   validation error.

## Consequences

- Parts can show a "Assumed" chip and Checks can warn on assumed power or inrush (M67), which
  closes the gap the "watts 0" flag left.
- The Library gets a Review queue and a Health page from these fields alone (M68), and a project
  override can be proposed back to the library as a `draft` edit with a `measured` or `datasheet`
  source (M69).
- Editing gets one more required input per sized change. Picking `assumed` keeps it one click.
- Who may move a part to `released` is not enforced here; M68 decides whether the app needs an
  owner role or the state change is just a pending edit like any other.
- Watch: a library saved by this release cannot be opened by an older app; the message says which
  version to install.
