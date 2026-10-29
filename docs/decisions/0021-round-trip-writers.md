# 0021. Round-trip YAML writers, checked before they write

- Status: Accepted (Ali, 2026-10-28)
- Date: 2026-10-28
- Spec sections: Inputs the tool needs (2. Panel definition, 3. Project settings)

## Context

In M17 (backlog points 4, 7 and 9), the app edits projects, substations and panels, so
YAML becomes an import, export and backup format. The input files are hand-written, and
their comments carry provenance ("# ASSUMED", "'Panel 1' row 8"). The example
substation file alone has 43 comment lines. If a writer regenerated the files from the
models, it would drop those comments, reorder keys and expand every default. The
editor table (`docs/ui/editing.md`, "Back-end needs for the generated-panel editor")
lists the first writers, and each one returns the new layout preview and its problems.

## Decision

1. **Round-trip editing with ruamel.yaml** (`io/round_trip.py`). A writer parses the
   file, changes only the nodes it owns, and dumps the file again. The dumper is set up
   to match the files' style:
   - two-space mappings, with sequences indented under their key
   - flow mappings padded as `{ a: 1 }`
   - `null` written out
   - long lines never folded

   With these settings, every file in `examples/` dumps byte-identical when nothing
   changes, and a test keeps it that way. `merge_value` puts a new value onto the old
   node. Unchanged keys and items keep their comments, and a quoted string stays
   quoted.

   Writers change entries through `set_entry` and `remove_entry`, and wrap each file's
   change in `edit_document`. This keeps the layout of the file intact:
   - The blank line and comments that end an entry stay at its end when items are
     appended or removed.
   - A list or mapping that becomes empty is written inline as `[]` or `{}`, with its
     key's comment after it.
   - An end-of-line comment keeps its distance from a value that grows or shrinks.
   - A rewritten file keeps its permissions.

   *M17b:* `io/panel_edit.py` writes, creates and deletes hand-written panel files:
   - `write_panel` replaces a panel's contents.
   - `create_panel` writes `panels/<id>.yaml` and lists it last in `manual_panels`.
   - `delete_panel` removes the file and its list entry. The usual check refuses it
     while something still names the panel.
   - Generated panels are refused.

   `pending_texts` takes `None` for a file the edit deletes.

   *M17c:* `io/fields.py` gives the forms field-level access. A field is a path in the
   project file, a substation file or a hand-written panel file:
   - `set_field` and `remove_field`. A mapping that a removal leaves empty is removed
     too.
   - `insert_item`, `remove_item` and `move_item`, for equipment rows, panel devices,
     register rows and other lists.
   - `validate_field(path, value)`: a dry run of `set_field` that returns the engine's
     message for that field, or nothing. A rule that spans several keys (for example
     `t_max_c > t_int_c`) counts as the field's message.
   - `document_users(key)`: what uses a register document.
   - `assumed_fields` and `confirm_field`: values whose comment says `ASSUMED`, and
     dropping that mark when the person confirms one. The rest of the comment stays.
   - `file_fingerprint`: a hash, so the app can tell when a file changed on disk.

   *M17d:* `io/lifecycle.py` creates and deletes projects and substations:
   - `create_project` writes `<workspace>/<id>/project.yaml`. The id comes from the
     name, gets `-2`, `-3` and so on when that folder is taken, and the project starts
     with no substations.
   - `create_substation` adds a blank substation or copies another:
     - A blank one has no panels and three register documents (BOM, power, heat), whose
       number and date are marked `ASSUMED`.
     - A copy takes the other substation's files with their comments. Its register
       documents and every `document:` key are renamed to the new id.
   - `delete_substation` checks the delete, saves a `.bomproj` backup (ADR 0012), then
     removes the folder, the project's entry for it and its register documents.
   - `delete_project` saves `<Deleted>/<id>.bomproj`, then removes the folder.
   - Names are edited with `set_field`. Ids name folders and register keys, so they stay
     read-only, as the design has them.
   - Two model rules are loosened so that a new project or substation can load:
     `substations` may be an empty list (the key is still required), and a substation
     may list no panel files. `build_substation` raises `EngineError` ("has no panels
     yet") for such a substation.
2. **Check before writing** (`io/edit.py`). The writer loads the whole project with the
   edited text in place of the file (`yaml_source.pending_texts`), so the edit passes
   through the same loader checks as a build would.
   - If the edit causes a problem the project did not have before, nothing is written,
     and the writer returns those located problems. Problems are compared by file,
     location and message, because lines move with an edit.
   - Problems that were already there never block an edit, so a broken project can
     still be fixed from the app.
   - A sound edit is written atomically: a temporary file in the same folder, then
     `os.replace`.
3. **Result.** `EditResult(written, issues, preview)`: the problems the edit caused when
   nothing was written, or the project's remaining problems when it was, plus the new
   `layout_preview` when the substation has equipment. `EditError` means the request
   names something that does not exist (a substation, an equipment row, an option key),
   and the file stays unchanged.
4. **Writers in M17a.**
   - **Generated panels:**
     - `set_enclosure` and `set_generated_document`.
     - `set_option` and `remove_option`, for every panel or for one panel. Removing a
       panel's last own option removes its entry, and the empty `options_by_panel` goes
       with it.
     - The reader `panel_options`, which gives each option's value, its shared value and
       whether the panel has its own.
   - **Equipment:** `set_port_plan`, per row.
   - **Panels board:** `set_layout_overrides` and `set_layout_removed`, which write one
     move per line as flow mappings.

   Hand-written panel files (M17b), and project and substation settings with per-field
   validation (M17c), follow the same pattern.

## Consequences

- A new runtime dependency, `ruamel.yaml` (MIT, pure Python; the C extension is
  optional). The frozen app must bundle it.
- Each write loads the project twice: once as it is and once with the edit. That is
  fast enough for one edit at a time.
- New YAML a writer adds (a new key or item) is written in block style, apart from the
  board's moves.
- `bomgen layout` still writes generated panel files with PyYAML. Those files carry a
  generated header and no hand comments.
