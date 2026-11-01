"""The desktop app's UI files: complete, offline and in step with the M9 design (ADR 0011, 0015)."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from bomgen.app.api import Api
from bomgen.app.window import INDEX, UI_DIR

REPO = Path(__file__).parents[3]
DESIGN = REPO / "docs" / "ui"
UI_FILES = sorted(p for p in UI_DIR.rglob("*") if p.is_file())
TEXT_FILES = [p for p in UI_FILES if p.suffix in {".html", ".css", ".js"}]
# Fetches a resource from the network: an attribute, a CSS url() or @import, or fetch().
REMOTE = re.compile(
    r"""(?:src|href)\s*=\s*["']?(?:https?:)?//|url\(\s*["']?(?:https?:)?//|@import|fetch\(""",
    re.IGNORECASE,
)


def index_references() -> list[str]:
    html = INDEX.read_text(encoding="utf-8")
    return re.findall(r"""(?:src|href)="([^"#][^"]*)\"""", html)


def test_index_loads_only_files_that_exist_in_the_ui_folder() -> None:
    references = index_references()

    assert references
    for reference in references:
        assert (UI_DIR / reference).is_file(), reference


def test_every_script_in_the_ui_folder_is_loaded() -> None:
    scripts = {p.name for p in UI_DIR.glob("*.js")}

    assert scripts == {r for r in index_references() if r.endswith(".js")}


@pytest.mark.parametrize("path", TEXT_FILES, ids=lambda p: p.name)
def test_ui_never_loads_anything_from_the_network(path: Path) -> None:
    assert not REMOTE.findall(path.read_text(encoding="utf-8"))


def test_fonts_come_from_the_ui_folder() -> None:
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    fonts = re.findall(r"""url\("(fonts/[^"]+)"\)""", css)

    assert len(fonts) == 2
    for font in fonts:
        assert (UI_DIR / font).is_file()


def test_tokens_match_the_design() -> None:
    # Regenerate in docs/ui (node docs/ui/tools/build-tokens.mjs), then copy here.
    design = DESIGN / "prototype" / "tokens.css"
    assert (UI_DIR / "tokens.css").read_bytes() == design.read_bytes()


@pytest.mark.parametrize("font", sorted((DESIGN / "fonts").iterdir()), ids=lambda p: p.name)
def test_fonts_and_licences_match_the_design(font: Path) -> None:
    assert (UI_DIR / "fonts" / font.name).read_bytes() == font.read_bytes()


def test_prototype_state_controls_are_not_in_the_app() -> None:
    for path in TEXT_FILES:
        text = path.read_text(encoding="utf-8")
        assert "Prototype states" not in text, path.name
        assert "proto-panel" not in text, path.name


def test_content_security_policy_allows_nothing_from_outside_the_ui_folder() -> None:
    html = INDEX.read_text(encoding="utf-8")
    match = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html)

    assert match
    policy = dict((d.split()[0], d.split()[1:]) for d in match.group(1).split(";") if d.strip())
    assert policy["default-src"] == ["'none'"]
    for directive, sources in policy.items():
        assert all(s.startswith("'") or s == "data:" for s in sources), directive


def bridge_calls() -> list[str]:
    """The first argument of every ``Bridge.call(`` in the screens, as written."""
    calls = []
    for script in sorted(UI_DIR.glob("*.js")):
        if script.name == "bridge.js":
            continue
        for match in re.finditer(r"Bridge\.call\(([^,)]*)", script.read_text(encoding="utf-8")):
            calls.append(match.group(1))
    return calls


def test_every_endpoint_the_screens_call_exists() -> None:
    calls = bridge_calls()
    names = {name for call in calls for name in re.findall(r"'([^']*)'", call)}

    assert calls
    # a name held in a variable could not be checked here
    assert [
        c for c in calls if not re.fullmatch(r"\s*(?:\w+\s*\?\s*)?'\w+'(?:\s*:\s*'\w+')?\s*", c)
    ] == []
    missing = sorted(n for n in names if n.startswith("_") or not callable(getattr(Api, n, None)))
    assert missing == []


LOOSE = UI_DIR / "screens-loose.js"


def test_no_side_stripe_markers_in_the_styles() -> None:
    # A coloured inset or left border wider than a hairline is below the design's craft floor.
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    assert not re.search(r"inset\s+[2-9]px\s+0\s+0|border-left:\s*[2-9]px", css)


def test_loose_quantity_copy_promises_only_what_the_model_takes() -> None:
    js = LOOSE.read_text(encoding="utf-8")
    assert "with a unit" not in js
    assert js.count("A whole number, or 1 Lot.") >= 2  # both add dialogs
    assert "Quantity is a whole number, or 1 Lot." in js  # the table foot


def test_loose_leave_dialog_offers_keep_discard_and_save() -> None:
    js = LOOSE.read_text(encoding="utf-8")
    for label in (">Keep editing<", ">Discard changes<", "Save and leave<"):
        assert label in js
    assert "Discard and leave" not in js


def test_library_pending_bar_says_nothing_is_applied_yet() -> None:
    js = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert "not applied yet. Projects keep using" in js
    assert "Review and apply…" in js
    assert ">Keep editing<" in js


def test_a_local_library_version_reads_as_applied_local_edits() -> None:
    js = (UI_DIR / "screens-library.js").read_text(encoding="utf-8")
    assert "local edits of" in js
    assert "applied " in js
    assert "badge('info', 'Local')" in js


def test_the_device_editor_edits_every_list_the_model_has() -> None:
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    for key in ("ports:", "children:", "terminals:", "loose_items:"):
        assert key in edit
    assert "can't be edited here yet" not in edit


def test_in_use_rows_are_named_as_the_screens_show_them() -> None:
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert "the equipment row ${m(x.name)} (Parts)" in edit
    assert "on panel ${m(p)} (Panels)" in edit
    assert "Fixed once created: projects refer to it." in edit


def test_the_device_editor_has_a_datasheet_tab_on_the_record() -> None:
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert "datasheet: ['Datasheet'" in edit
    assert "Bridge.call('set_library_record_fields'" in edit
    assert "Bridge.call('check_library_record'" in edit


def test_csv_import_screen_loads_before_the_editor_so_the_pending_bar_wraps_it() -> None:
    html = (UI_DIR / "index.html").read_text(encoding="utf-8")
    assert html.index("screens-libcsv.js") < html.index("screens-libedit.js")
    js = (UI_DIR / "screens-libcsv.js").read_text(encoding="utf-8")
    assert "Bridge.call('preview_library_csv'" in js
    assert "Bridge.call('add_library_csv'" in js
    assert "goes to pending changes, not straight into the library" in js


def test_alternatives_compare_with_a_signed_delta_chip_not_colour_alone() -> None:
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert "alternatives: ['Alternatives'" in edit
    assert "Bridge.call('library_alternatives'" in edit
    assert "`${v > 0 ? '+' : '\u2212'}" in edit
    assert 'data-action="add-alternative"' in edit


def test_project_creation_is_live_and_deleting_a_project_asks_for_its_name() -> None:
    js = (UI_DIR / "screens-projects.js").read_text(encoding="utf-8")
    assert "later()" not in js
    for name in ("create_project", "create_substation", "rename_project", "rename_substation"):
        assert f"Bridge.call('{name}'" in js
    assert "Type the project name to confirm" in js


def test_project_overview_edits_client_logo_defaults_and_brands_in_the_app() -> None:
    js = (UI_DIR / "screens-projects.js").read_text(encoding="utf-8")
    assert "cannot be edited in the app yet" not in js
    for name in ("set_project_field", "check_project_field", "set_project_logo"):
        assert f"Bridge.call('{name}'" in js
    assert "Same as the AC branches" in js  # mcb_dc, ADR 0023


def test_parts_edits_the_network_inputs_with_a_setup_card_for_a_new_substation() -> None:
    js = (UI_DIR / "screens-parts.js").read_text(encoding="utf-8")
    for name in ("set_substation_field", "check_substation_field", "start_parts"):
        assert f"Bridge.call('{name}'" in js
    assert "function setupCard(p, rows)" in js
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    assert ".setup li.done svg" in css


def test_equipment_rows_are_edited_on_parts_and_removing_one_offers_undo() -> None:
    js = (UI_DIR / "screens-parts.js").read_text(encoding="utf-8")
    for name in ("add_equipment", "remove_equipment", "move_equipment"):
        assert f"Bridge.call('{name}'" in js
    assert "toast(`Removed ${label}`, 'trash', () =>" in js


def test_substation_settings_are_edited_through_the_shared_draft_form() -> None:
    ui = (UI_DIR / "ui.js").read_text(encoding="utf-8")
    assert "function draftForm(o)" in ui
    js = (UI_DIR / "screens-substation.js").read_text(encoding="utf-8")
    assert "App.draftForm({" in js
    assert "Editing substations in the app is not available yet" not in js
    assert "Reset all to defaults" in js


def test_the_document_register_is_edited_with_confirm_add_and_remove_with_undo() -> None:
    js = (UI_DIR / "screens-projects.js").read_text(encoding="utf-8")
    for name in ("confirm_project_field", "add_document", "remove_document", "restore_document"):
        assert f"Bridge.call('{name}'" in js
    assert "Pick another document there first." in js


def test_use_this_instead_hands_the_part_to_parts_as_an_unsaved_edit() -> None:
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert "ACTIONS['use-instead']" in edit
    assert "pins stay put" in edit
    assert "Review and save it on Parts." in edit
    assert "App.useButton(id, r.part_id)" in (UI_DIR / "screens-library.js").read_text("utf-8")
    assert "App.holdParts = " in (UI_DIR / "screens-parts.js").read_text(encoding="utf-8")


def test_overview_and_parts_use_the_shared_draft_form() -> None:
    for name in ("screens-projects.js", "screens-substation.js", "screens-parts.js"):
        js = (UI_DIR / name).read_text(encoding="utf-8")
        assert "function toModel(" not in js  # one reader of typed values, in ui.js
    assert "const PO = App.draftForm({" in (UI_DIR / "screens-projects.js").read_text("utf-8")
    assert "const PF = App.draftForm({" in (UI_DIR / "screens-parts.js").read_text("utf-8")


def test_deleting_a_device_not_applied_yet_drops_it_from_the_pending_changes() -> None:
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert "data-new=\"${isNew ? 1 : ''}\"" in edit
    assert "It is not in the library yet, so it goes at once" in edit
    assert "dropped from the pending changes" in edit


def test_the_parts_datalist_shows_make_and_model() -> None:
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert "label=\"${esc(names[p] || '')}\"" in edit


def test_loose_material_follows_the_design_review_notes() -> None:
    loose = (UI_DIR / "screens-loose.js").read_text(encoding="utf-8")
    assert "App.verified(p.data_quality)" in loose  # a data-quality badge in the picker
    assert "App.fixLine('lm-first-bad', bad)" in loose  # the count moves focus to the first one
    assert "Not fed: a free-text item has no library part" in loose
    assert "part_id: 'Part', fed_from: 'Fed from', children: 'Comes with'" in loose
    assert "toast(`Saved ${plural(n, 'change')}`" in loose
    assert "Saved substation.yaml" not in loose
    ui = (UI_DIR / "ui.js").read_text(encoding="utf-8")
    assert "fixLine(`${o.prefix}first-bad`, bad)" in ui


# -- v0.2 polish (docs/ui/polish-v02.md) -------------------------------------------------------


def _ui_scripts() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in UI_DIR.glob("*.js")}


def test_unsaved_edits_use_the_changed_marker_not_the_revision_yellow() -> None:
    """polish-v02 item 1; components.md "Changed marker"."""
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    ui = (UI_DIR / "ui.js").read_text(encoding="utf-8")
    assert '<span class="chg" aria-hidden="true"></span><span class="sr-only">changed</span>' in ui
    assert ".field.changed" not in css
    assert "td.is-changed" in css
    assert ".table td.changed { background: var(--color-highlight-yellow)" in css  # Preview only
    for name, js in _ui_scripts().items():
        if name == "screens-preview.js":
            continue
        assert 'class="changed"' not in js, name
        assert "field changed" not in js, name


def test_every_number_input_is_right_aligned() -> None:
    """polish-v02 item 5."""
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    assert ".input--num { font-variant-numeric: tabular-nums; text-align: right; }" in css


def test_the_save_bar_fix_sentence_is_one_control() -> None:
    """polish-v02 item 6; components.md "Save bar"."""
    ui = (UI_DIR / "ui.js").read_text(encoding="utf-8")
    assert "const fixLine = (action, bad) =>" in ui
    assert "fixing</b> before you can save.</span></button>" in ui
    for name in ("screens-loose.js", "screens-libedit.js"):
        js = (UI_DIR / name).read_text(encoding="utf-8")
        assert "fixLine(" in js, name
        assert "fixing</b></button> before you can save." not in js, name


def test_a_route_change_closes_an_open_dialog() -> None:
    """polish-v02 item 15."""
    ui = (UI_DIR / "ui.js").read_text(encoding="utf-8")
    assert "closeDialog(); render(); $('#main').scrollTop = 0;" in ui


def test_a_new_list_row_is_checked_once_it_is_filled_or_on_save() -> None:
    """polish-v02 item 2; editing.md "Validation"."""
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert "const unfinished = (r) => Object.values(r).some((v) => v === '');" in edit
    assert "rows.filter((r) => !unfinished(r))" in edit
    assert "function checkUnfinished()" in edit
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    assert ".section > .err" in css


def test_choices_show_labels_not_enum_values() -> None:
    """polish-v02 item 3."""
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert "const choiceName = (key, c) =>" in edit
    assert "serial_port: 'Serial port'" in edit or "catName(c.toLowerCase())" in edit
    assert "(choices[col] || []).map((c) => [c, choiceName(col, c)])" in edit
    assert "choices.map((c) => [c, choiceName(key, c)])" in edit


def test_the_datasheet_height_is_named_apart_and_power_input_is_a_textarea() -> None:
    """polish-v02 item 8."""
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert "['rec__datasheet__height_u', 'Height in the datasheet', 'int', " in edit
    assert "The layout uses Ports and mounting \u203a Height." in edit
    assert "['rec__datasheet__power__input', 'Power input', 'area', " in edit


def test_row_delete_buttons_share_one_style() -> None:
    """polish-v02 item 14: muted, danger on hover."""
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    assert ".btn--del { color: var(--color-text-muted); }" in css
    for name in (
        "screens-libedit.js",
        "screens-parts.js",
        "screens-loose.js",
        "screens-projects.js",
    ):
        js = (UI_DIR / name).read_text(encoding="utf-8")
        assert "btn--del" in js, name


def test_parts_rows_keep_to_their_column_and_a_part_change_says_what_was_cleared() -> None:
    """components.md "Parts and Device preview"; decision 1 of the M23 plan."""
    js = (UI_DIR / "screens-parts.js").read_text(encoding="utf-8")
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    assert ".net-grid > * { min-width: 0; }" in css
    assert "Bridge.call('set_equipment_part'" in js
    assert "was' : 'were'} cleared, so the BOM prints the library's code." in js


def test_settings_names_the_resolved_brand_and_the_register_key() -> None:
    """polish-v02 items 7, 9 and 13."""
    sub = (UI_DIR / "screens-substation.js").read_text(encoding="utf-8")
    assert "'Same as AC branches'" in sub
    assert '<div class="form form--2" style="margin-top:var(--space-3)">${KINDS.map(' in sub
    assert "`Same as the project (${from})`" in sub
    assert "const docOpts = (p) => p.documents.map((d) => [d.key, d.key]);" in sub
    assert "data-key=\"${key}\">Reset</button>` : ''}</td></tr>`" in sub  # no "Default" on each row


def test_the_register_rows_are_two_lines() -> None:
    """polish-v02 item 10."""
    proj = (UI_DIR / "screens-projects.js").read_text(encoding="utf-8")
    assert 'after: `<span class="cell-sub mono">${esc(d.key)}</span>`' not in proj
    assert "The issue date${assumed === 1 ? '' : 's'} of ${count(assumed, 'document')}" in proj
    assert ".replace(`${d.substation}: `, '')" in proj


def test_loose_material_wording_from_the_146_review() -> None:
    """polish-v02 item 12."""
    loose = (UI_DIR / "screens-loose.js").read_text(encoding="utf-8")
    assert "Quantity is a whole number, or 1 Lot." in loose
    assert "An item that needs power must be added to the library first." in loose
    assert "Add the part to the library to get them." not in loose


def test_the_project_path_stays_on_one_line() -> None:
    """polish-v02 item 16."""
    proj = (UI_DIR / "screens-projects.js").read_text(encoding="utf-8")
    assert '<span class="mono one-line" title="${esc(p.path)}">' in proj
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    assert ".page-head-main { min-width: 0; flex: 1 1 0; }" in css


def test_the_save_bar_meets_the_window_bottom() -> None:
    """Screen check of #206: no empty band under the bar at the end of a page."""
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    page_rule = ".page:has(> .savebar) { padding-bottom: 0; display: flex; flex-direction: column;"
    assert f"{page_rule} min-height: 100%; }}" in css
    assert ".page > .savebar { margin-top: auto; }" in css  # short pages too (#207)


def test_ids_in_a_sub_line_never_break_and_tab_panels_keep_their_offset() -> None:
    """#207 re-check nits: "ext-fw" broke at its hyphen; the device editor panel sat
    16px lower once the page became a flex column (margins no longer collapse)."""
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    assert ".table .cell-sub .mono { white-space: nowrap; }" in css
    libedit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert '<div role="tabpanel" aria-labelledby="tab-devEdit-${t}">' in libedit


def test_the_app_ships_none_of_the_prototypes_illustrative_data() -> None:
    """Audit 2026-10-30, finding 1: the installed app must never show the design prototype's
    example substation as if it were real. The data and the stub stay in docs/ui/prototype."""
    names = {p.name for p in UI_DIR.glob("*.js")}
    assert names.isdisjoint({"data.js", "engine-stub.js"})
    for path in TEXT_FILES:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\bDB\.", text), path.name
        assert not re.search(r"\bEngine\.", text), path.name
        assert "psa-devices 1.12.0" not in text, path.name


def test_without_its_bridge_the_app_says_so_instead_of_showing_example_pages() -> None:
    """The same finding: a missing bridge is reported as an error, never papered over."""
    ui = (UI_DIR / "ui.js").read_text(encoding="utf-8")
    assert "S.backend === 'no'" in ui
    assert "could not reach its engine" in ui
    app = (UI_DIR / "app.js").read_text(encoding="utf-8")
    assert "err.kind === 'no_backend'" in app


def test_the_deprecated_minimum_branch_mcb_is_shown_read_only_with_why() -> None:
    """Audit 2026-10-30, finding 3: ADR 0019 point 4 deprecates ``min_branch_mcb_a``; it no
    longer sets a rating, so the editor must not invite an engineer to type one."""
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    row = re.search(r"\['min_branch_mcb_a', '([^']*)', '(\w+)', '([^']*)'", edit)
    assert row
    assert row.group(2) == "fixed"
    assert "ADR 0019" in row.group(3)
    assert "no longer" in row.group(3)


def test_the_panels_board_drags_with_pointer_events_not_html5_drag_and_drop() -> None:
    """M19: HTML5 drag-and-drop does not reach the board in the installed app (WebView2), so the
    board drags with pointer events and pointer capture, and a cancel or lost capture ends it.
    M24 moved the pointer handling into drag.js, shared with Device preview."""
    js = (UI_DIR / "screens-panels.js").read_text(encoding="utf-8")
    js += (UI_DIR / "drag.js").read_text(encoding="utf-8")
    for html5 in ("draggable", "dragstart", "dragover", "dataTransfer"):
        assert html5 not in js, html5
    for event in ("pointerdown", "pointermove", "pointerup", "pointercancel", "lostpointercapture"):
        assert f"'{event}'" in js, event
    assert "setPointerCapture" in js
    assert "elementFromPoint" in js
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    assert re.search(r"\.dev\.is-movable \{[^}]*touch-action: none", css)
    assert re.search(r"body\.is-dragging-dev[^{]*\{[^}]*user-select: none", css)


def test_a_hand_written_board_offers_to_lay_out_panels_after_a_confirm_that_names_the_copies() -> (
    None
):
    """M19: the read-only board's banner has "Lay out panels from the equipment", which asks
    first and says where the hand-written files are copied; editing.md describes it."""
    js = (UI_DIR / "screens-panels.js").read_text(encoding="utf-8")
    assert "Lay out panels from the equipment" in js
    assert "Bridge.call('generate_panels'" in js
    assert "panels/hand-written-" in js
    assert 'data-action="pv-generate-go"' in js
    editing = (DESIGN / "editing.md").read_text(encoding="utf-8")
    assert "Lay out panels from the equipment" in editing


# -- Parts (plan M23; docs/ui/screens.md "Parts") ---------------------------------------------

PARTS = UI_DIR / "screens-parts.js"


def test_parts_replaces_network_and_network_redirects() -> None:
    ui = (UI_DIR / "ui.js").read_text(encoding="utf-8")
    assert "navItem('#/parts', 'parts', 'Parts'" in ui
    assert "'#/network'" not in ui
    assert "if (a === 'network') { location.replace('#/parts'); return; }" in ui
    assert "SCREENS.network" not in (UI_DIR / "screens-substation.js").read_text("utf-8")
    assert "SCREENS.parts = " in PARTS.read_text(encoding="utf-8")


def test_parts_offers_no_override_controls_on_a_sized_row_without_a_part() -> None:
    js = PARTS.read_text(encoding="utf-8")
    strip = js[js.index("function strip(r)") :]
    assert strip.index("if (!r.part_id) return") < strip.index('data-action="pp-edit"')
    assert "'Pick the switch to change its data.'" in strip


def test_generate_preview_is_disabled_while_parts_has_changes() -> None:
    js = PARTS.read_text(encoding="utf-8")
    assert (
        'PF.dirty() ? `<button class="btn btn--secondary" disabled title="Save your changes first."'
        in js
    )
    assert "href=\"#/device-preview\">${icon('elevation')}Generate preview</a>" in js


def test_an_empty_category_shows_a_line_not_an_empty_dropdown() -> None:
    """Decision 5 of the M23 plan: the library has no KVM or console parts yet."""
    js = PARTS.read_text(encoding="utf-8")
    assert "The library has no ${esc(label)} parts yet." in js
    assert "if (!opts.length && !r.part_id) return emptyLine(" in js
    assert "${n ? '' : `disabled title=\"The library has no ${esc(c.label)} parts yet.\"`}" in js


def test_time_accessories_on_parts_write_loose_material_items() -> None:
    """Decision 2 of the M23 plan."""
    js = PARTS.read_text(encoding="utf-8")
    for name in ("add_loose_item", "remove_loose_item", "set_loose_item"):
        assert f"Bridge.call('{name}'" in js
    assert "To add accessories, set the loose material's host panel first." in js


def test_network_rows_have_a_cable_manager_switch_written_through_its_endpoint() -> None:
    """Ali's change to the M22 design (2026-10-31); components.md "Part row"."""
    js = PARTS.read_text(encoding="utf-8")
    assert "Bridge.call('set_cable_manager'" in js
    assert '<label class="switch prow-cm"' in js
    assert "${r.cable_manager ? " in js  # network rows only


# -- Device preview (plan M24; docs/ui/screens.md "Device preview") ---------------------------


def test_board_and_preview_load_the_shared_drag_helper() -> None:
    index = (UI_DIR / "index.html").read_text(encoding="utf-8")
    assert index.index('src="drag.js"') < index.index('src="screens-panels.js"')
    drag = (UI_DIR / "drag.js").read_text(encoding="utf-8")
    for needle in ("setPointerCapture", "lostpointercapture", "pointercancel", "< 4)", "'Escape'"):
        assert needle in drag
    panels = (UI_DIR / "screens-panels.js").read_text(encoding="utf-8")
    assert "App.pointerDrag({ handle: '.dev.is-movable[data-uid]'" in panels
    assert "setPointerCapture" not in panels


DEVICE_PREVIEW = UI_DIR / "screens-device-preview.js"


def test_device_preview_draws_only_what_the_engine_gives() -> None:
    """No U, waist or MCB arithmetic in the screen beyond a unit's top U to pixels."""
    js = DEVICE_PREVIEW.read_text(encoding="utf-8")
    assert "Bridge.call('device_preview'" in js
    assert "44.45" not in js  # the waist U comes from the engine (waist_u)
    assert "d.waist_u" in js
    assert "rating_a" in js  # MCBs as the engine sized them
    assert "at_minimum" in js
    assert "Bridge.call('set_layout_overrides'" in js
    assert "Bridge.call('check_layout'" in js
    assert "App.pointerDrag({" in js


def test_device_preview_rail_item_follows_parts() -> None:
    ui = (UI_DIR / "ui.js").read_text(encoding="utf-8")
    parts = ui.index("navItem('#/parts'")
    preview = ui.index("navItem('#/device-preview', 'elevation', 'Device preview'")
    assert parts < preview < ui.index("navItem('#/panels'")
    assert "!ns || noParts()" in ui
    index = (UI_DIR / "index.html").read_text(encoding="utf-8")
    assert index.index('src="drag.js"') < index.index('src="screens-device-preview.js"')


def test_parts_rows_collapse_to_a_one_line_summary_at_20_or_more() -> None:
    """components.md "Part row", state Collapsed (20 or more rows)."""
    js = (UI_DIR / "screens-parts.js").read_text(encoding="utf-8")
    assert "rows.length >= 20" in js
    assert 'data-action="pp-expand"' in js
    assert "ACTIONS['pp-expand']" in js
    assert "override${n === 1 ? '' : 's'}" in js  # "1 U · 15 W · 125 VDC · 2 overrides"


def test_a_category_with_more_than_12_parts_opens_the_device_picker() -> None:
    """components.md "Device picker (combobox)" and "Part row"."""
    js = (UI_DIR / "screens-parts.js").read_text(encoding="utf-8")
    assert "opts.length > 12" in js
    assert 'role="combobox"' in js
    assert 'role="listbox"' in js
    assert ".slice(0, 8)" in js  # up to 8 matches
    assert "App.verified(o.data_quality)" in js
    assert "No device matches. Check the spelling, or install a library that has it." in js
    # the pick goes through the same change handlers as the select it replaces
    assert "dispatchEvent(new Event('change', { bubbles: true }))" in js


def test_device_preview_shows_the_ac_branch_mcb_like_any_other() -> None:
    """ADR 0025: AC units have their own branch MCB, so no AC-only dash."""
    js = (UI_DIR / "screens-device-preview.js").read_text(encoding="utf-8")
    assert "AC devices have no branch MCB" not in js


def test_preview_shows_the_nameplates_sheet_after_loose_material() -> None:
    """ADR 0026: the Nameplates sheet comes after Loose Material, before the calculations."""
    js = (UI_DIR / "screens-preview.js").read_text(encoding="utf-8")
    loose, plates, power = (js.index(s) for s in ("[LOOSE, ", "[PLATES, ", "['power', 'Power'"))
    assert loose < plates < power
    assert "function nameplatesView(n)" in js
    for head in ("<th>Panel</th>", "<th>Plate text</th>", "<th>Device</th>"):
        assert head in js


# -- M29: unsaved changes and app polish (audit 2026-10-31) --


def test_leaving_a_form_page_with_unsaved_changes_asks_first() -> None:
    """APP-6; editing.md "Leaving with unsaved changes": a link, another substation or project."""
    js = (UI_DIR / "ui.js").read_text(encoding="utf-8")
    form = js[js.index("function draftForm(o)") :]
    for label in (">Keep editing<", ">Discard changes<", "Save and leave<"):
        assert label in form
    assert "Save the changes first?" in form
    # Save and leave is disabled while a field is invalid, and says why
    assert "before you can save." in form
    # the shell holds the route and the substation switch until the dialog answers
    assert "history.replaceState(null, '', was)" in js
    assert "const leaving = (then) =>" in js
    assert "if (leaving(() => switchTo(value))) return;" in js
    # the draft is no longer dropped on a route change
    assert "if (route().a !== o.screen) D.reset()" not in js


def test_the_status_bar_says_unsaved_changes_while_a_save_bar_shows() -> None:
    """APP-6; editing.md "Save bar", components.md "Status bar"."""
    js = (UI_DIR / "ui.js").read_text(encoding="utf-8")
    assert "Unsaved changes</span>" in js
    assert ".status .warn" in (UI_DIR / "styles.css").read_text(encoding="utf-8")


def test_the_first_loose_save_does_not_clear_the_host_it_just_set() -> None:
    """APP-5: add_loose_item sets the host; a host never chosen is not written as null."""
    js = LOOSE.read_text(encoding="utf-8")
    assert "draft.host == null || draft.host === LM.data.host_panel" in js


def test_save_the_parts_also_saves_the_network_inputs() -> None:
    """APP-16: one press saves the picks and the IED count."""
    js = (UI_DIR / "screens-parts.js").read_text(encoding="utf-8")
    start = js[js.index("Bridge.call('start_parts'") :]
    assert "PF.save()" in start[: start.index("}).catch(fail);")]


def test_the_rail_counts_the_panels_from_the_last_layout() -> None:
    """APP-17: the Panels count follows a layout without a reload."""
    assert "App.panelCount = " in (UI_DIR / "screens-panels.js").read_text(encoding="utf-8")
    assert "App.panelCount()" in (UI_DIR / "ui.js").read_text(encoding="utf-8")


def test_every_engine_check_has_a_name_on_checks_and_build() -> None:
    """APP-13: no raw check ids such as branch_mcb or dc_float."""
    checks = (REPO / "src" / "bomgen" / "checks.py").read_text(encoding="utf-8")
    ids = set(re.findall(r'check="(\w+)"', checks))
    js = (UI_DIR / "screens-verify.js").read_text(encoding="utf-8")
    names = js[js.index("const CHECKS = {") : js.index("};", js.index("const CHECKS = {"))]
    assert ids
    assert [i for i in ids if f"{i}:" not in names] == []
    # Build's list names the device the way the Checks table does
    assert "i.subject ? ` · ${esc(i.subject)}` : ''" in js


def test_device_preview_with_no_panel_files_offers_to_lay_them_out() -> None:
    """APP-15: not called hand-written when there are none."""
    js = (UI_DIR / "screens-device-preview.js").read_text(encoding="utf-8")
    assert "d.panel_files" in js
    assert "No panels laid out yet." in js
    assert "Bridge.call('generate_panels'" in js


def test_add_a_device_and_the_result_card_read_as_english() -> None:
    """APP-18: "3 L1 switches", "Add an RTAC", "Add a KVM", "Add an I/O rack"."""
    panels = (UI_DIR / "screens-panels.js").read_text(encoding="utf-8")
    assert "plural(p.l1_per_side, 'L1 switch')" not in panels
    parts = (UI_DIR / "screens-parts.js").read_text(encoding="utf-8")
    assert "c.label.toLowerCase()" not in parts
    assert "const aName = (label) =>" in parts


def test_project_overview_edits_the_layout_heights_and_marks_them_assumed() -> None:
    """APP-19: waist height and rack start, with the register's Assumed badge and Confirm."""
    js = (UI_DIR / "screens-projects.js").read_text(encoding="utf-8")
    assert "['defaults', 'layout', 'waist_height_mm']" in js
    assert "['defaults', 'layout', 'rack_start_mm']" in js
    assert "p.layoutAssumed" in js
    assert 'data-action="po-confirm"' in js


def _where_to_fix(problems: list[dict[str, object]]) -> list[dict[str, object]]:
    """Runs ui.js's whereToFix on each problem in node, with generated panel n named psa<n>."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    js = (UI_DIR / "ui.js").read_text(encoding="utf-8")
    source = js[js.index("  const SETTINGS_TAB") : js.index("  /* A banner's buttons")]
    script = (
        "const App = { generatedPanelId: (n) => 'psa' + n };\n"
        f"{source}\nconsole.log(JSON.stringify({json.dumps(problems)}.map(whereToFix)));"
    )
    run = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(run.stdout)  # type: ignore[no-any-return]


def test_where_to_fix_leads_each_located_problem_to_its_page() -> None:
    """APP-7: one action per problem, labelled with where it goes (the M32 design brief)."""
    sub = "C:\\work\\gis01\\substation.yaml"
    cases: list[tuple[dict[str, object], str, str, str | None]] = [
        (
            {"file": sub, "location": "equipment[4].part_id"},
            "Go to the row",
            "#/parts",
            "p-e.4.part_id",
        ),
        (
            {"file": sub, "location": "network.ied_count"},
            "Go to the field",
            "#/parts",
            "p-n.ied_count",
        ),
        (
            {"file": sub, "location": "spares.port_fraction"},
            "Go to the field",
            "#/parts",
            "p-s.port_fraction",
        ),
        (
            {"file": sub, "location": "generated_panels.options_by_panel[2].aux_socket_a"},
            "Open the panel",
            "#/panels/psa2/options",
            "pe-o.2.aux_socket_a",
        ),
        (
            {"file": sub, "location": "generated_panels.enclosure.h_mm"},
            "Open the panel",
            "#/panels/psa1/enclosure",
            "pe-e.h_mm",
        ),
        (
            {"file": sub, "location": "generated_panels.document"},
            "Open the panel",
            "#/panels/psa1/document",
            "pe-doc",
        ),
        (
            {"file": "/w/gis01/panels/ws.yaml", "location": "devices[0].part_id"},
            "Open the panel",
            "#/panels/ws/devices",
            None,
        ),
        ({"file": sub, "location": "layout.overrides[0]"}, "Open the board", "#/panels", None),
        (
            {"file": sub, "location": "loose_material.items[0].fed_from"},
            "Open loose material",
            "#/loose",
            None,
        ),
        (
            {"file": sub, "location": "constants.t_max_c"},
            "Go to the field",
            "#/settings/constants",
            "st-c_t_max_c",
        ),
        (
            {"file": sub, "location": "output.file_name"},
            "Go to the field",
            "#/settings/output",
            "st-file_name",
        ),
        ({"file": sub, "location": "equipment"}, "Open Parts", "#/parts", None),
        (
            {"file": sub, "location": "something_else", "line": 9},
            "Show the line",
            "#/settings/yaml",
            None,
        ),
        ({"file": "/w/project.yaml", "location": "library"}, "Open the project", "#/project", None),
    ]
    got = _where_to_fix([case[0] for case in cases])
    for (problem, label, hash_, focus), fix in zip(cases, got, strict=True):
        assert (fix["label"], fix["hash"]) == (label, hash_), problem
        assert fix["focus"] == (f'[id="{focus}"]' if focus else None), problem


def test_checks_panels_and_device_preview_use_where_to_fix() -> None:
    """APP-7: Checks' action, and the banner when Panels or Device preview cannot show."""
    verify = (UI_DIR / "screens-verify.js").read_text(encoding="utf-8")
    assert "App.whereToFix(p).label" in verify
    assert "App.fix(cache.checks.data.problems[+el.dataset.i])" in verify
    for name in ("screens-panels.js", "screens-device-preview.js"):
        assert "App.fixButtons(d.problems)" in (UI_DIR / name).read_text(encoding="utf-8")


def test_panels_header_has_undo_and_reset_and_rows_open_the_editor() -> None:
    """APP-4 and APP-3: Undo and Reset to automatic stay in the header, disabled with
    nothing to do; list rows and board columns open the panel editor."""
    panels = (UI_DIR / "screens-panels.js").read_text(encoding="utf-8")
    head = panels[panels.index("function headActions(d)") : panels.index("function board(d)")]
    assert 'data-action="pv-undo"' in head
    assert "history.length && !busy ? '' : 'disabled'" in head
    assert 'data-action="pv-reset"' in head
    assert 'href="#/panels/${esc(p.id)}"' in panels
    assert "if (b) return App.panelEditor(b);" in panels
    assert "The panel editor comes with the substation writers." not in panels


def test_the_panel_editor_writes_generated_panels_through_the_save_bar() -> None:
    """APP-3: enclosure, document, options (all or one panel) and port plans are drafted and
    saved to substation.yaml; Devices and YAML stay read-only."""
    editor = (UI_DIR / "screens-panel-editor.js").read_text(encoding="utf-8")
    assert "App.draftForm({" in editor
    assert "['generated_panels', 'enclosure', ...f.split('.')]" in editor
    assert "['generated_panels', 'options_by_panel', Number(a), r[0]]" in editor
    assert "['equipment', Number(a), 'port_plan', r[0], Number(r[1]), r[2]]" in editor
    assert "Bridge.call('set_port_plan'" in editor
    assert "Bridge.call('panel_page'" in editor
    assert "Use the shared value" in editor
    assert "Show on Device preview" in editor
    index = (UI_DIR / "index.html").read_text(encoding="utf-8")
    assert index.index('src="screens-panels.js"') < index.index('src="screens-panel-editor.js"')


def test_hand_written_panels_are_added_edited_and_deleted_in_the_editor() -> None:
    """M32b: Add hand-written panel… asks for the first device; the editor writes the panel's
    own file field by field and the device list as a whole; Delete panel… lists what still
    names the panel and offers Undo."""
    panels = (UI_DIR / "screens-panels.js").read_text(encoding="utf-8")
    assert 'data-action="pv-add-panel"' in panels
    assert "Bridge.call('panel_parts'" in panels
    assert "Bridge.call('add_panel'" in panels
    editor = (UI_DIR / "screens-panel-editor.js").read_text(encoding="utf-8")
    assert "Bridge.call('set_panel_field', S.project.file, S.sub, hPanel" in editor
    assert "Bridge.call('check_panel_field'" in editor
    assert "['devices'], list)" in editor
    assert "Bridge.call('delete_panel'" in editor
    assert "Bridge.call('restore_panel'" in editor
    assert "is still in use" in editor
    assert "Delete the panel instead." in editor  # the last device is not removed


def test_parts_rows_edit_the_l2_link_and_the_rtac_com_ports() -> None:
    """M31: each non-switch row sets its link to the L2 switch; an RTAC row its COM ports."""
    js = PARTS.read_text(encoding="utf-8")
    assert "const LINK = { l2_ports: 'int', l2_speed: 'choice', l2_media: 'choice' };" in js
    assert "if (kind === 'l') return [['equipment', Number(a), b], LINK[b]];" in js
    assert "[['equipment', Number(a), 'port_plan', 'serial_ports'], 'int']" in js
    link = js[js.index("function linkRow(r)") :]
    assert link.index("if (!r.link || !r.part_id) return '';") < link.index("prow-link")
    assert "['10M', '100M', '1G', '10G']" in link
    assert "['MM', 'SM', 'RJ45']" in link
    assert "r.serial_ports == null ? ''" in link  # only an RTAC row has COM ports
    assert "${linkRow(r)}${sfpRows(r)}" in js
    assert "'eofcl'.includes(k[0])" in js  # the row shows its unsaved mark
