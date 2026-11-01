/* Screens: library export and CSV import (plan M16 b, docs/ui/editing.md "Export and import", ADR 0018).
   Export writes the active version as CSV tables or a .bomlib backup. A CSV import is checked first (a dry
   run), and its valid rows go to the pending set, never straight into the library. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, pageHead, dialog, closeDialog, toast, go, $ } = App;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;
  const fail = (e) => toast(e.kind === 'no_backend' ? 'This works in the app, not in a browser.' : e.message, 'error');

  /* ---------- Export ---------- */
  ACTIONS['lib-export'] = () => dialog({ title: 'Export the library', body: `<div class="stack">
    <div class="stack" style="gap:8px"><label class="check"><input type="radio" name="ex-fmt" value="csv" checked> <span><b>Spreadsheet (CSV)</b><span class="small muted" style="display:block">For editing in Excel. One file per table, saved so Excel shows accents and symbols.</span></span></label>
      <label class="check"><input type="radio" name="ex-fmt" value="bomlib"> <span><b>Backup package (.bomlib)</b><span class="small muted" style="display:block">The whole active version, to keep or hand on as an update.</span></span></label></div>
    <div id="ex-csv"><span class="label" style="display:block;margin-bottom:4px">Include</span><div class="stack" style="gap:6px">
      <label class="check"><input type="checkbox" name="ex-inc" value="devices" checked> Devices <span class="muted">(with their ports, parts, terminals and alternative groups)</span></label>
      <label class="check"><input type="checkbox" name="ex-inc" value="catalogues" checked> Catalogues <span class="muted">(MCBs for AC and DC, aux contacts, terminal blocks, busbars, housekeeping)</span></label></div>
      <p class="muted small" style="margin-top:var(--space-2)">Keep <span class="mono">part_id</span> and <span class="mono">alt_group</span> as they are: they link the rows. The files go in a new folder inside the one you choose.</p></div>
    <div id="ex-err"></div></div>`,
    actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="lib-export-do">Export…</button>' });
  document.addEventListener('change', (e) => { if (e.target.name === 'ex-fmt') { const b = $('#ex-csv'); if (b) b.hidden = e.target.value !== 'csv'; } });
  ACTIONS['lib-export-do'] = () => {
    const fmt = $('input[name="ex-fmt"]:checked').value;
    const include = [...document.querySelectorAll('input[name="ex-inc"]:checked')].map((x) => x.value);
    if (fmt === 'csv' && !include.length) { $('#ex-err').innerHTML = banner('bad', 'Choose at least one kind of table.'); return; }
    const call = fmt === 'csv' ? Bridge.call('export_library_csv', include) : Bridge.call('export_library_package');
    call.then((r) => {
      if (!r) return;  // the person cancelled the file dialog
      closeDialog();
      toast(fmt === 'csv' ? `Exported ${plural(r.files.length, 'CSV file')} to ${r.folder}` : `Exported ${r.file}`, 'check');
    }).catch((e) => { $('#ex-err').innerHTML = banner('bad', esc(e.message)); });
  };

  /* ---------- Import: a package (the existing flow) or a spreadsheet ---------- */
  ACTIONS['lib-import'] = () => dialog({ title: 'Import into the library', body: `<div class="stack" style="gap:8px">
    <button class="btn btn--secondary" style="justify-content:flex-start;height:auto;padding:10px 12px;text-align:left" data-action="lib-import-go" data-to="#/library/import">${icon('pkg')}<span><b>Update package (.bomlib)</b><span class="small muted" style="display:block">A new library version from your team. It replaces the active one when you confirm.</span></span></button>
    <button class="btn btn--secondary" style="justify-content:flex-start;height:auto;padding:10px 12px;text-align:left" data-action="lib-import-go" data-to="#/library/csv">${icon('file')}<span><b>Spreadsheet (CSV)</b><span class="small muted" style="display:block">Tables you exported and edited. Accepted rows go to pending changes.</span></span></button></div>`,
    actions: '<button class="btn btn--secondary" data-action="close">Cancel</button>' });
  ACTIONS['lib-import-go'] = (el) => { closeDialog(); CSV.step = 'choose'; go(el.dataset.to); };

  /* ---------- CSV import with a review step ---------- */
  const CSV = { step: 'choose', path: '', preview: null, added: null };
  const name = (p) => p.split(/[\\/]/).pop();
  const kb = (b) => (b == null ? 'a folder' : b < 1024 ? `${b} bytes` : `${Math.round(b / 1024)} KB`);
  const grp = (title, items, kind, open) => (items.length ? `<details ${open ? 'open' : ''}><summary>${icon('chevr', 'chev')}${title} ${badge(kind, items.length)}</summary><div class="items">${items.map(([a, b]) => `<div><span class="mono">${esc(a)}</span><span class="muted">${esc(b)}</span></div>`).join('')}</div></details>` : '');
  function csvScreen() {
    const crumbs = `<a href="#/library">Library</a>${icon('chevr')}<span>Import spreadsheet</span>`;
    const head = pageHead('Import a spreadsheet', 'Edit the exported CSV files in Excel, then bring them back. The files are checked before anything is added, and what you accept goes to pending changes, not straight into the library.', '', crumbs);
    if (CSV.step === 'choose') return `<div class="page">${head}<div class="drop" data-action="csv-pick" tabindex="0" role="button" aria-label="Choose a CSV file">${icon('file', 'i--lg')}<h3 style="margin:8px 0 2px">Choose one of the exported files</h3><p>The other tables in its folder are read with it. A .zip of the tables works too.</p><button class="btn btn--primary" data-action="csv-pick">${icon('folder')}Choose file…</button></div></div>`;
    if (CSV.step === 'checking') return `<div class="page">${head}<div class="stack" style="max-width:520px"><h3>Checking ${esc(name(CSV.path))}</h3><div class="progress" role="progressbar" aria-label="Checking"><i style="width:40%"></i></div><p class="muted">Reading the tables and comparing them with the library. Nothing is added yet.</p></div></div>`;
    if (CSV.step === 'done') {
      const n = CSV.added;
      return `<div class="page">${head}${banner('ok', n ? `<b>${plural(n, 'change')} ${n === 1 ? 'is' : 'are'} now pending.</b> Nothing is in the library yet. Review ${n === 1 ? 'it' : 'them'}, then apply.` : '<b>Nothing to add.</b> The files match the library.', `${n ? '<a class="btn btn--primary btn--sm" href="#/library/review">Review and apply…</a>' : ''}<button class="btn btn--secondary btn--sm" data-action="csv-cancel">Import another…</button>`)}</div>`;
    }
    const p = CSV.preview, failed = p.checks.find((c) => c.status === 'failed');
    const valid = p.added.length + p.changed.length + p.removed.length + p.catalogues.length;
    const byKey = {};
    p.changes.forEach((c) => { (byKey[c.key] = byKey[c.key] || []).push(c.field ? `${c.field}: ${c.from || 'empty'} → ${c.to || 'empty'}` : `${c.from || 'empty'} → ${c.to || 'empty'}`); });
    const rows = Object.entries(p.rows).filter(([, n]) => n);
    return `<div class="page">${head}<div class="stack" style="max-width:920px">
      ${failed ? banner('bad', `<b>These files cannot be imported.</b> ${esc(failed.label)}${failed.detail ? `: ${esc(failed.detail)}` : '.'}`) : ''}
      <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:var(--space-6)">
        <section><h3>Files</h3><dl class="kv" style="margin-top:var(--space-2);grid-template-columns:190px 1fr"><dt>Chosen</dt><dd class="mono">${esc(p.file)}</dd><dt>Size</dt><dd>${kb(p.size)}</dd><dt>Compared with</dt><dd>${esc(p.base || '')}</dd>
          ${rows.map(([t, n]) => `<dt class="mono">${esc(t)}</dt><dd>${plural(n, 'row')}</dd>`).join('')}</dl></section>
        <section><h3>Checks</h3><ul class="checklist" style="margin-top:var(--space-2)">${App.checkList(p.checks)}</ul></section></div>
      ${p.problems.length ? `<section><h3>Rows with a problem</h3><div class="table-wrap" style="margin-top:var(--space-2)"><table class="table"><thead><tr><th>Table</th><th class="num" style="width:70px">Row</th><th style="width:160px">Column</th><th>What is wrong</th></tr></thead><tbody>${p.problems.map((r) => `<tr><td class="mono">${esc(r.table)}</td><td class="num">${r.row || ''}</td><td class="mono">${esc(r.column || '')}</td><td>${icon('error')} ${esc(r.message)}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section><h3>What changes</h3>${valid ? `<div class="row" style="margin:var(--space-2) 0 var(--space-3)">${badge('ok', `${p.added.length} added`)}${badge('info', `${p.changed.length} changed`)}${badge('bad', `${p.removed.length} removed`)}${p.catalogues.length ? badge('plain', `${p.catalogues.length} catalogues changed`) : ''}</div>
        <div class="diff-list table-wrap" style="padding:0 var(--space-4)">${grp('Added devices', p.added.map((x) => [x, '']), 'ok', true)}${grp('Changed devices', p.changed.map((x) => [x, (byKey[x] || []).join('; ')]), 'info', true)}${grp('Removed devices', p.removed.map((x) => [x, 'not in the file']), 'bad', true)}${grp('Changed catalogues', p.catalogues.map((x) => [x, (byKey[x] || []).slice(0, 3).join('; ')]), 'plain')}</div>` : '<p class="muted" style="margin-top:6px">No changes: the files match the library.</p>'}</section>
      <div class="actionbar"><button class="btn btn--primary" data-action="csv-add" ${p.can_import && valid ? '' : 'disabled'}>${icon('check')}Add ${plural(valid, 'change')} to pending changes</button><button class="btn btn--secondary" data-action="csv-cancel">Choose different files</button>
        ${p.problems.length ? `<span class="muted small">${plural(p.problems.length, 'row')} with a problem ${p.problems.length === 1 ? 'is' : 'are'} skipped. Fix ${p.problems.length === 1 ? 'it' : 'them'} in the file and import again to include ${p.problems.length === 1 ? 'it' : 'them'}.</span>` : ''}</div></div></div>`;
  }
  ACTIONS['csv-pick'] = () => Bridge.call('choose_file', 'csv').then((path) => {
    if (!path) return;
    CSV.path = path; CSV.step = 'checking'; App.render();
    return Bridge.call('preview_library_csv', path).then((p) => { CSV.preview = p; CSV.step = 'review'; })
      .catch((e) => { CSV.step = 'choose'; fail(e); }).then(() => App.render());
  }).catch(fail);
  ACTIONS['csv-cancel'] = () => { CSV.step = 'choose'; CSV.preview = null; App.render(); };
  ACTIONS['csv-add'] = (el) => {
    el.disabled = true;
    const p = CSV.preview;
    Bridge.call('add_library_csv', CSV.path).then((page) => {
      App.setPending(page); App.cataloguesStale();
      CSV.added = p.added.length + p.changed.length + p.removed.length + p.catalogues.length; CSV.step = 'done'; App.render();
    }).catch((e) => { el.disabled = false; fail(e); });
  };

  /* #/library/csv; loaded before screens-libedit.js so the pending bar wraps this page too. */
  const base = SCREENS.library;
  SCREENS.library = () => (App.route().b === 'csv' && S.backend === 'yes' ? csvScreen() : base());
})();
