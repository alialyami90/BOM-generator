"""The desktop app's UI files: complete, offline and in step with the M9 design (ADR 0011, 0015)."""

import re
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
    assert js.count("A whole number, or 1 Lot.") >= 3  # the table foot and both add dialogs


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
    assert "the equipment row ${m(x.name)} (Network)" in edit
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


def test_network_inputs_are_edited_with_a_setup_card_for_a_new_substation() -> None:
    js = (UI_DIR / "screens-substation.js").read_text(encoding="utf-8")
    for name in ("set_substation_field", "check_substation_field"):
        assert f"Bridge.call('{name}'" in js
    assert "function setupCard(p)" in js
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    assert ".setup li.done svg" in css


def test_equipment_rows_are_edited_on_network_and_removing_one_offers_undo() -> None:
    js = (UI_DIR / "screens-substation.js").read_text(encoding="utf-8")
    for name in ("add_equipment", "remove_equipment"):
        assert f"Bridge.call('{name}'" in js
    assert "toast(`Removed ${id}`, 'trash', () =>" in js


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
    network = (UI_DIR / "screens-substation.js").read_text(encoding="utf-8")
    assert "Bridge.call('start_equipment'" in network


def test_use_this_instead_hands_the_part_to_network_as_an_unsaved_edit() -> None:
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert "ACTIONS['use-instead']" in edit
    assert "pins stay put" in edit
    assert "App.useButton(id, r.part_id)" in (UI_DIR / "screens-library.js").read_text("utf-8")
    assert "App.holdParts = " in (UI_DIR / "screens-substation.js").read_text(encoding="utf-8")


def test_overview_and_network_use_the_shared_draft_form() -> None:
    for name in ("screens-projects.js", "screens-substation.js"):
        js = (UI_DIR / name).read_text(encoding="utf-8")
        assert "function toModel(" not in js  # one reader of typed values, in ui.js
    assert "const PO = App.draftForm({" in (UI_DIR / "screens-projects.js").read_text("utf-8")
    assert "const NET = App.draftForm({" in (UI_DIR / "screens-substation.js").read_text("utf-8")


def test_deleting_a_device_not_applied_yet_drops_it_from_the_pending_changes() -> None:
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert "data-new=\"${isNew ? 1 : ''}\"" in edit
    assert "It is not in the library yet, so it goes at once" in edit
    assert "dropped from the pending changes" in edit


def test_an_equipment_row_changes_its_part_with_its_alternatives_first() -> None:
    sub = (UI_DIR / "screens-substation.js").read_text(encoding="utf-8")
    assert 'data-action="eq-part-change"' in sub
    assert "Bridge.call('library_alternatives', was)" in sub
    assert 'label="Alternatives to ${esc(was)}"' in sub
    assert "Other parts in the library" in sub
    assert "ACTIONS['eq-part-change-do']" in sub


def test_the_parts_datalist_shows_make_and_model() -> None:
    edit = (UI_DIR / "screens-libedit.js").read_text(encoding="utf-8")
    assert "label=\"${esc(names[p] || '')}\"" in edit
