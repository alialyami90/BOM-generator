# M16 app side, PR (a): pending set and Device editor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A person edits a library device in the app, the edit waits in a pending set, and *Review and apply* writes it as a new local library version.

**Architecture:** The pending set is a list of `library_store.edit` operations kept per library in the app home (`library-pending/<name>.json`, with the base version). `src/bomgen/app/library_edit.py` loads, checks, describes and applies it with A5's `apply_edits`, `check_field`, `diff_libraries` and `save_edits`. The bridge exposes it, and `ui/screens-libedit.js` draws the pending bar, the Device editor (`#/library/device/<id>`) and Review (`#/library/review`).

**Tech Stack:** Python 3.12, pydantic, pywebview bridge (ADR 0015), plain JS UI.

**Spec:** `docs/ui/editing.md` "Library editing (v0.2)" ("The pending set", "Device editor"), ADR 0018; prototype `docs/ui/prototype/screens-libedit.js`.

## Global Constraints

- No business rule in the UI. Validation messages come from `check_field` / `apply_edits` (the model's own messages).
- Every `Bridge.call` uses a literal endpoint name (guard test `test_every_endpoint_the_screens_call_exists`).
- Edits never touch the installed version until *Apply and activate*. The previous version stays installed.
- The local version name is `save_edits`' (`<base>+local.<n>`); the UI shows the name the bridge returns, never computes it.
- Pending-bar copy: "n pending changes · not applied yet. Projects keep using <version> until you apply them." with *Discard all* and *Review and apply…*.
- Device editor is a form: save bar "Save device", Ctrl+S, leave dialog *Keep editing* · *Discard changes* · *Save and leave*.

## Scope of this PR

In: pending set (store, bar, discard with Undo, review, apply); Device editor tabs **Identity**, **Electrical**, **Ports and mounting** (height, cores; port groups read-only list); *Edit device* on the library detail pane.
Out, later PRs: port group, child, terminal and loose-item editing, Add device, Delete (PR a2); CSV (b); Alternatives tab (c); Catalogues editing.
Not possible yet: the **Datasheet** tab edits device records (`device-db/`), which `library_store.edit` does not reach. Ask role 5 for a record edit path before building it.

## Review Focus

1. The active version changes (import or *Make active*) while edits are pending → the pending set keeps its base, Review says "Started from 1.0.0; 1.1.0 is now active", and apply still works against the base.
2. The pending file is damaged or names an uninstalled base → the bar offers *Discard all*, and the library screens still open.
3. Two edits to the same field → one pending entry with the original *from* and the latest *to*; setting it back to the saved value drops the entry.
4. An emptied optional field (e.g. ordering code) → saved as a `remove` of the key, not as `""`.
5. A save that makes another device invalid (e.g. a voltage the power rules refuse) → refused with the model's message on that field, nothing added to the set.

---

### Task 1: Pending set store and its description

**Files:** Create `src/bomgen/app/library_edit.py`; Test `tests/unit/app/test_app_library_edit.py`

**Interfaces — Produces:**
- `class PendingEdits(folder: Path)` with `load(name) -> Pending | None`, `save(name, Pending)`, `clear(name)`. `Pending = {base: str, edits: list[dict]}` as JSON; a damaged file loads as `Pending(base=None, edits=[], problem=str)`.
- `describe(base_lib: Library, edited: Library) -> list[Entry]` with `Entry = {area: "Device", label, kind: added|changed|removed, field, from, to}` (one per changed top-level device field; `from`/`to` are display strings of the JSON values, `""` for missing).
- `merge(edits, new) -> list[dict]`: a `set` on a path already set replaces it; a `set` back to the base value drops both.

- [ ] Tests: `test_pending_edits_survive_a_new_api_instance`, `test_a_damaged_pending_file_reports_a_problem_and_loads_empty`, `test_describe_lists_one_entry_per_changed_field_with_from_and_to`, `test_setting_a_field_back_drops_its_entry`, `test_an_emptied_optional_field_is_a_remove` (Review Focus 3, 4).
- [ ] Implement; run `python -m pytest tests/unit/app/test_app_library_edit.py`; commit `feat(app): library pending set kept in the app home (M16)`.

### Task 2: Bridge endpoints

**Files:** Modify `src/bomgen/app/api.py`; Test `tests/unit/app/test_app_library_edit.py`

**Interfaces — Produces (all `@endpoint`):**
- `library_pending() -> {name, base, active, entries, count, next_version, problem}`; `next_version` from `library_store.local.next_local_version`.
- `library_device(part_id) -> {device, saved, pending_fields, used_by, choices}` (`choices`: the model's enum values for category, supply_type, load_type, purdue_level): `device` is the pending-applied device JSON, `saved` the base one, `used_by` `[]` until role 2's "rows that use a part" lands.
- `check_library_field(part_id, field, value) -> str | None` on the pending-applied library.
- `add_library_edits(edits: list[dict]) -> library_pending()`; refuses (`AppError("invalid_edit", …)` listing `location: message`) when `apply_edits` reports problems; nothing stored then.
- `discard_library_edits() -> {discarded: list[dict], page}`; Undo re-sends `discarded` through `add_library_edits`.
- `apply_library_edits(note: str) -> {version, previous, diff}` via `save_edits(store, name, edits, base=base, note=note)`, then clears the set.

- [ ] Tests: `test_an_edited_device_is_saved_as_a_new_local_version`, `test_check_field_reports_the_models_message`, `test_an_edit_that_breaks_the_library_is_refused_and_not_kept` (RF 5), `test_discard_returns_the_edits_for_undo`, `test_pending_keeps_its_base_when_another_version_is_activated` (RF 1), `test_a_pending_set_on_an_uninstalled_base_can_be_discarded` (RF 2).
- [ ] Implement; gate; commit `feat(app): library edit endpoints over library_store.edit and save_edits`.

### Task 3: Pending bar and Review and apply

**Files:** Create `src/bomgen/app/ui/screens-libedit.js` (add to `index.html`); Modify `screens-library.js` (call the bar, *Edit device* button); `styles.css` only if `.savebar--pending` is missing.

- [ ] Bar on every `#/library…` page while `count > 0`, copy per Global Constraints. *Discard all* asks, then toasts "Pending changes discarded" with Undo.
- [ ] `#/library/review`: Added / Changed / Removed groups (label, field, from → to), Now active, Will become (`next_version`), Kept, Note (default "Local edits"), *Apply and activate <next_version>*; empty state "Nothing to review". After apply: toast "<name> <version> is active", go to `#/library`, reload overview and versions.
- [ ] `node --check`; asset test that the bar copy contains "not applied yet"; commit.

### Task 4: Device editor (Identity, Electrical, Ports and mounting)

**Files:** `ui/screens-libedit.js`

- [ ] Fields map 1:1 to `DeviceType`: Identity — part_id (read-only), category, make, model, ordering_code, description_template (textarea), tag_type, purdue_level; Electrical — supply_type, voltage_v, power_supplies, unit_power_w, inrush_a, load_type, min_branch_mcb_a, hwio_points, di_inputs, alarm_on_branch_mcb, excluded_from_power; Ports and mounting — height_u, cores, and the port groups as a read-only table.
- [ ] Each field is checked on change with `check_library_field`; the message shows under the field (red border, error icon). Edited fields get `td.changed`/field highlight.
- [ ] Save bar "n unsaved changes · added to pending changes", *Discard*, *Save device* (Ctrl+S, blurs the focused field first). Save sends one `set` (or `remove` for an emptied optional field) per changed field to `add_library_edits`; a refusal shows a red banner and keeps the form.
- [ ] Leave dialog as Global Constraints. Unknown part: "Device not found" page with *Back to the library*.
- [ ] E2E in the scratchpad: edit unit_power_w and ordering_code, save, see 2 pending, review, apply → versions list shows `1.0.0+local.1` active; invalid voltage shows the model's message; no console errors. Screens to role 4.
- [ ] Gate; commit `feat(app): Device editor and Review and apply on the pending set (M16)`; open the PR for role 1.
