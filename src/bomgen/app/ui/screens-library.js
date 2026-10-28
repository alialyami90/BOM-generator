/* Screens: Library (browse, detail) and import / installed versions. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, select, pageHead, illus, dialog, closeDialog, toast, go, verified, $ } = App;
  const L = DB.library;
  const catName = (c) => c.replace(/_/g, ' ').replace(/^./, (m) => m.toUpperCase()).replace(/^Io\b/, 'IO');
  const F = { q: '', cat: '', ver: '', alt: false };

  SCREENS.library = () => {
    const { b } = App.route();
    if (b === 'import') return importScreen();
    return browse();
  };

  function browse() {
    const t = S.tab.libtab || 'devices';
    return `<div class="page">${pageHead('Device library', `${esc(L.name)} ${esc(L.version)}, installed ${esc(L.installed)}. This list is read-only. It changes only when you import an update package.`,
      `<button class="btn btn--secondary" data-action="goto" data-to="#/library/import">${icon('upload')}Import update…</button>`)}
      ${S.firstRun ? banner('warn', '<b>No library is installed.</b> Import a <span class="mono">.bomlib</span> file to see devices here.', '<a class="btn btn--primary btn--sm" href="#/library/import">Import…</a>') : devicesView()}</div>`;
  }

  function filtered() {
    return DB.devices.filter((d) => (!F.q || (d.id + d.make + d.model).toLowerCase().includes(F.q.toLowerCase()))
      && (!F.cat || F.cat === d.cat) && (!F.ver || F.ver === d.verified) && (!F.alt || d.alt));
  }
  function devicesView() {
    const list = filtered(); const cats = [...new Set(DB.devices.map((d) => d.cat))];
    const sel = DB.devices.find((d) => d.id === S.selectedDevice) || list[0];
    return `<div class="toolbar" role="search">
        <div class="input-wrap" style="width:280px"><label class="sr-only" for="lib-q">Search library</label>${icon('search')}<input class="input" id="lib-q" type="search" placeholder="Search part, make, model" value="${esc(F.q)}"></div>
        <label class="sr-only" for="lib-cat">Category</label>${select('lib-cat', [['', 'All categories'], ...cats.map((c) => [c, catName(c)])], F.cat, { cls: 'ctl' }).replace('data-dirty="1"', 'data-action="lib-cat"').replace('class="select ctl"', 'class="select" style="width:190px"')}
        <label class="sr-only" for="lib-ver">Data quality</label>${select('lib-ver', [['', 'Any data quality'], ['confirmed', 'Confirmed'], ['partial', 'Partial'], ['unverified', 'Unverified']], F.ver, {}).replace('data-dirty="1"', 'data-action="lib-ver"').replace('class="select "', 'class="select" style="width:190px"')}
        <label class="check"><input type="checkbox" data-action="lib-alt" ${F.alt ? 'checked' : ''}> Has alternatives</label>
        <span class="sp"></span><span class="muted small">${list.length} of ${DB.devices.length} devices</span></div>
      <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(340px,400px);gap:var(--space-5);align-items:start">
        <div><div class="table-wrap"><table class="table"><thead><tr><th>Part ID</th><th>Make and model</th><th>Supply</th><th>Data</th></tr></thead><tbody>
          ${list.map((d) => `<tr class="clickable" tabindex="0" data-action="lib-select" data-id="${d.id}" aria-selected="${sel && sel.id === d.id}"><td><span class="mono">${esc(d.id)}</span><span class="cell-sub">${esc(catName(d.cat))}</span></td><td>${esc(d.make)} <span class="muted">${esc(d.model)}</span></td><td>${esc(d.supply)}${d.w ? `<span class="cell-sub">${d.w} W</span>` : ''}</td><td style="white-space:nowrap">${verified(d.verified)}</td></tr>`).join('') || '<tr class="empty-row"><td colspan="4">No device matches these filters. Clear a filter or search for a different part.</td></tr>'}
        </tbody></table><div class="table-foot"><span>Select a row to see its datasheet and alternatives</span><span>${illus()}</span></div></div></div>
        ${sel ? detail(sel) : ''}
      </div>`;
  }
  function detail(d) {
    const t = S.tab.libdetail;
    const tabsList = [['overview', 'Overview'], ['datasheet', 'Datasheet'], ['alternatives', 'Alternatives']];
    let body = '';
    if (t === 'overview') body = `<dl class="kv"><dt>Part ID</dt><dd class="mono">${esc(d.id)}</dd><dt>Make</dt><dd>${esc(d.make)}</dd><dt>Model</dt><dd>${esc(d.model)}</dd><dt>Ordering code</dt><dd class="mono">${esc(d.code || '—')}</dd><dt>Category</dt><dd>${esc(catName(d.cat))}</dd><dt>Tag</dt><dd class="mono">${d.tagType ? esc(d.tagType) + (d.level ? ' · ' + esc(d.level) : '') : '—'}</dd><dt>Supply</dt><dd>${esc(d.supply)}</dd><dt>Power</dt><dd>${esc(d.power || '—')}</dd><dt>Rated power</dt><dd class="num" style="text-align:left">${d.w ? d.w + ' W' : '—'}</dd><dt>Branch MCB</dt><dd>${esc(d.mcb || '—')}</dd></dl>`;
    else if (t === 'datasheet') body = d.ds ? `<dl class="kv"><dt>Supply range</dt><dd>${esc(d.ds.supply)}</dd><dt>Typical power</dt><dd>${esc(d.ds.typical)}</dd><dt>Maximum power</dt><dd>${esc(d.ds.max)}</dd><dt>Ports</dt><dd>${esc(d.ds.ports)}</dd><dt>Dimensions</dt><dd>${esc(d.ds.dims)}</dd><dt>Weight</dt><dd>${esc(d.ds.weight)}</dd><dt>Operating temperature</dt><dd>${esc(d.ds.temp)}</dd><dt>Certifications</dt><dd>${esc(d.ds.certs)}</dd><dt>Datasheet</dt><dd><a href="#" data-action="noop">${icon('ext')} ${esc(d.ds.url)}</a></dd></dl>
      <div class="section" style="margin-top:var(--space-4);padding-bottom:0"><h3>Sources</h3><ul style="margin:var(--space-2) 0 0;padding-left:18px">${(d.src || []).map((s) => `<li>${esc(s)}</li>`).join('')}</ul></div>` : `<p class="muted">No datasheet details are recorded for this device yet.</p>`;
    else body = d.alt ? `${banner('info', 'Alternatives are for reference. Swapping a device inside a panel is not available yet.')}
      ${d.alt.map((a) => `<h3 style="margin-top:var(--space-4)">${esc(a.brand)}</h3><div class="table-wrap" style="margin-top:6px"><table class="table"><thead><tr><th style="width:56px">Tier</th><th>Model</th><th>Data</th><th style="width:40px"><span class="sr-only">Copy</span></th></tr></thead><tbody>${a.rows.map((r) => `<tr><td>${esc(r.tier)}</td><td class="mono">${esc(r.model)}${r.same_as ? `<span class="cell-sub" style="font-family:var(--font-sans)">Same as ${esc(r.same_as)}</span>` : ''}</td><td>${verified(r.verified)}</td><td><button class="btn btn--ghost btn--icon btn--sm" data-action="copy" data-v="${esc(r.model)}" aria-label="Copy ${esc(r.model)}">${icon('copy')}</button></td></tr>`).join('')}</tbody></table></div>`).join('')}`
      : `<p class="muted">No alternatives are recorded for this device yet.</p>`;
    return `<aside class="detail" aria-label="Device detail"><h2 class="mono" style="font-size:18px;font-family:var(--font-mono)">${esc(d.id)}</h2><p class="muted" style="margin-bottom:var(--space-3)">${esc(d.make)} ${esc(d.model)}</p>
      ${tabs('libdetail', tabsList, t, 'Device detail')}<div role="tabpanel" aria-labelledby="tab-libdetail-${t}">${body}</div></aside>`;
  }
  ACTIONS['lib-select'] = (el) => { S.selectedDevice = el.dataset.id; S.tab.libdetail = 'overview'; App.render(); };
  document.addEventListener('keydown', (e) => { const r = e.target.closest && e.target.closest('tr.clickable[data-action="lib-select"]'); if (r && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); r.click(); } });
  document.addEventListener('change', (e) => { if (e.target.id === 'lib-cat') { F.cat = e.target.value; App.render(); } if (e.target.id === 'lib-ver') { F.ver = e.target.value; App.render(); } });
  ACTIONS['lib-cat'] = () => {}; ACTIONS['lib-ver'] = () => {};
  ACTIONS['lib-alt'] = () => { F.alt = !F.alt; App.render(); };
  ACTIONS.copy = (el) => { toast(`Copied ${el.dataset.v}`); };
  ACTIONS.noop = (el, e) => e.preventDefault();
  document.addEventListener('input', (e) => { if (e.target.id === 'lib-q') { F.q = e.target.value; const pos = e.target.selectionStart; App.render(); const n = $('#lib-q'); n.focus(); n.setSelectionRange(pos, pos); } });

  /* ---------- Import and versions ---------- */
  function importScreen() {
    const t = S.libTab;
    return `<div class="page">${pageHead('Import library update', 'Check what a package changes before it replaces anything. Nothing is installed until you confirm.', '',
      `<a href="#/library">Library</a>${icon('chevr')}<span>Import update</span>`)}
      ${tabs('libtab', [['import', 'Import package'], ['versions', 'Installed versions']], t === 'import' ? 'import' : 'versions', 'Library tasks').replace(/data-group="libtab"/g, 'data-group="libtab2"')}
      ${t === 'import' ? importFlow() : versionsView()}</div>`;
  }
  ACTIONS.tab2 = null;
  const origTab = ACTIONS.tab;
  ACTIONS.tab = (el) => { if (el.dataset.group === 'libtab2') { S.libTab = el.dataset.value; App.render(); const n = document.getElementById(el.id); n && n.focus(); } else origTab(el); };

  function importFlow() {
    const sc = DB.importScenarios[S.importScenario];
    if (S.importStep === 'choose') return `<div class="drop" data-action="pick-file" id="drop" tabindex="0" role="button" aria-label="Choose a library package">${icon('pkg', 'i--lg')}<h3 style="margin:8px 0 2px">Drop a .bomlib file here</h3><p>or choose one from your PC</p><button class="btn btn--primary" data-action="pick-file">${icon('folder')}Choose package…</button></div>
      <p class="muted small" style="margin-top:var(--space-3)">You can also double-click a .bomlib file in Windows to open it here. Currently installed: ${esc(L.name)} ${esc(L.version)}.</p>`;
    if (S.importStep === 'importing') return `<div class="stack" style="max-width:520px"><h3>Installing ${esc(sc.name)} ${esc(sc.version)}</h3><div class="progress" role="progressbar" aria-label="Installing" aria-valuemin="0" aria-valuemax="100" aria-valuenow="60"><i style="width:60%"></i></div><p class="muted">Copying files and keeping the previous version for rollback…</p></div>`;
    if (S.importStep === 'done') return `${banner('ok', `<b>${esc(sc.name)} ${esc(sc.version)} is now active.</b> Version ${esc(sc.active)} is kept, so you can go back under Installed versions.`, '<button class="btn btn--secondary btn--sm" data-action="goto" data-to="#/library">View library</button>')}
      ${sc.impact ? `<div style="margin-top:var(--space-3)">${banner('info', esc(sc.impact), '<button class="btn btn--secondary btn--sm" data-action="goto" data-to="#/checks">Open checks</button>')}</div>` : ''}`;
    const d = sc.diff; const refused = sc.refused;
    const n = d ? { a: d.added.length, c: d.changed.length, r: d.removed.length } : { a: 0, c: 0, r: 0 };
    const canImport = !refused;
    return `<div class="stack" style="max-width:920px">
      ${refused ? banner('bad', `<b>${esc(refused.title)}</b><div>${esc(refused.body)}</div>${refused.force ? `<label class="check" style="margin-top:8px"><input type="checkbox" data-action="force-toggle" ${S.force ? 'checked' : ''}> ${esc(refused.force)}</label>` : ''}`) : ''}
      <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:var(--space-6)">
        <section><h3>Package</h3><dl class="kv" style="margin-top:var(--space-2);grid-template-columns:130px 1fr"><dt>File</dt><dd class="mono">${esc(sc.file)}</dd><dt>Size</dt><dd>${esc(sc.size)}</dd><dt>Library</dt><dd>${esc(sc.name)}</dd><dt>Version</dt><dd><b>${esc(sc.version)}</b> <span class="muted">(active ${esc(sc.active)})</span></dd><dt>Library schema</dt><dd>${esc(sc.schema)}</dd><dt>Needs app</dt><dd>${esc(sc.minApp)} or later</dd><dt>Built</dt><dd>${esc(sc.created)}</dd></dl>
        ${sc.notes ? `<h3 style="margin-top:var(--space-4)">Release notes</h3><p style="margin-top:6px">${esc(sc.notes)}</p>` : ''}</section>
        <section><h3>Verification</h3><ul class="checklist" style="margin-top:var(--space-2)">${sc.checks.map(([k, tx]) => `<li class="${k}">${icon({ ok: 'check', bad: 'error', info: 'info' }[k])}<span style="color:var(--color-text)">${esc(tx)}</span></li>`).join('')}</ul></section></div>
      ${d ? `<section><h3>What changes</h3>
        ${n.a + n.c + n.r + d.catalogues.length + d.files.added.length + d.files.changed.length === 0 ? '<p class="muted" style="margin-top:6px">No changes.</p>' : `
        <div class="row" style="margin:var(--space-2) 0 var(--space-3)">${badge('ok', `${n.a} added`)}${badge('info', `${n.c} changed`)}${badge('bad', `${n.r} removed`)}${d.catalogues.length ? badge('plain', `${d.catalogues.length} catalogue changed`) : ''}${d.files.added.length + d.files.changed.length + d.files.removed.length ? badge('plain', `${d.files.added.length + d.files.changed.length + d.files.removed.length} data files`) : ''}</div>
        <div class="diff-list table-wrap" style="padding:0 var(--space-4)">
          ${group('Added parts', d.added, 'ok')}${group('Changed parts', d.changed, 'info', true)}${group('Removed parts', d.removed, 'bad')}
          ${d.catalogues.length ? group('Changed catalogues', d.catalogues.map((c) => [c, '']), 'plain') : ''}
          ${group('Device-database files', [...d.files.added.map((f) => [f, 'added']), ...d.files.changed.map((f) => [f, 'changed']), ...d.files.removed.map((f) => [f, 'removed'])], 'plain')}
        </div>`}</section>` : ''}
      <div class="actionbar">
        <button class="btn btn--primary" data-action="do-import" ${canImport || (refused && refused.force && S.force) ? '' : 'disabled'}>${icon('check')}Import and activate ${esc(sc.version)}</button>
        <button class="btn btn--secondary" data-action="import-cancel">Choose a different package</button></div></div>`;
  }
  const group = (title, items, kind, fields) => items.length ? `<details ${kind === 'info' || kind === 'bad' ? 'open' : ''}><summary>${icon('chevr', 'chev')}${esc(title)} ${badge(kind, items.length)}</summary><div class="items">${items.map(([a, b]) => `<div><span class="mono">${esc(a)}</span><span class="muted">${fields && b ? 'fields: ' + esc(b) : esc(b)}</span></div>`).join('')}</div></details>` : '';
  ACTIONS['pick-file'] = () => { S.importStep = 'review'; S.force = false; App.render(); };
  ACTIONS['import-cancel'] = () => { S.importStep = 'choose'; App.render(); };
  ACTIONS['force-toggle'] = (el) => { S.force = el.checked; App.render(); };
  ACTIONS['do-import'] = () => { S.importStep = 'importing'; App.render(); setTimeout(() => { S.importStep = 'done'; App.render(); toast('Library updated'); }, 900); };

  function versionsView() {
    return `<div class="table-wrap" style="max-width:980px"><table class="table table--comfort"><thead><tr><th>Version</th><th>Released</th><th>Notes</th><th class="num">Projects built with it</th><th>State</th><th style="width:130px"><span class="sr-only">Actions</span></th></tr></thead><tbody>
      ${L.versions.map((v) => `<tr><td class="mono">${esc(v.v)}</td><td class="nowrap">${esc(v.date)}</td><td class="wrap">${esc(v.notes)}</td><td class="num">${v.projects}</td><td>${v.active ? badge('ok', 'Active', 'check') : badge('plain', 'Installed')}</td><td>${v.active ? '' : `<button class="btn btn--secondary btn--sm" data-action="rollback" data-v="${v.v}">Make active</button>`}</td></tr>`).join('')}</tbody></table></div>
      <p class="muted small" style="margin-top:var(--space-3);max-width:68ch">Making an older version active does not change any project file. Projects keep the version they record, and the check report tells you when it differs from the active one.</p>`;
  }
  ACTIONS.rollback = (el) => dialog({ title: `Make ${el.dataset.v} active?`, body: `<p>The library switches back to ${esc(el.dataset.v)} for every project on this PC. Version ${esc(L.version)} stays installed.</p>`, actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="close-toast" data-v="${el.dataset.v}">Make ${esc(el.dataset.v)} active</button>` });
  ACTIONS['close-toast'] = (el) => { closeDialog(); toast(`Library ${el.dataset.v} is now active`); };
})();
