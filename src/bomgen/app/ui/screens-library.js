/* Screens: Library (browse, detail) and import / installed versions, on bomgen.app.api (plan M10b). */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, select, pageHead, dialog, closeDialog, toast, go, verified, $ } = App;
  /* "SEL SEL-2730M" reads as a stutter: when the model starts with the make, the model alone says both. */
  const makeModel = (d) => (d.model && d.make && d.model.toLowerCase().startsWith(d.make.toLowerCase()) ? esc(d.model) : `${esc(d.make)} <span class="muted">${esc(d.model)}</span>`);
  const ACRONYMS = { io: 'IO', gps: 'GPS', rtac: 'RTAC', sfp: 'SFP' };
  const catName = (c) => c.split('_').map((w) => ACRONYMS[w] || w).join(' ').replace(/^./, (m) => m.toUpperCase());
  const F = { q: '', cat: '', ver: '', alt: false };

  /* ---------- data from Python ---------- */
  const LIB = { state: 'idle', overview: null, versions: null, projects: [], errors: {} };
  function loadLibrary() {
    LIB.state = 'loading';
    // Loaded independently: a damaged active version must not hide the versions that can repair it.
    const load = (call, key) => call.then((data) => { LIB[key] = data; LIB.errors[key] = null; })
      .catch((err) => { LIB[key] = null; LIB.errors[key] = err; });
    const projects = Bridge.call('list_projects').then((list) => { LIB.projects = list; }).catch(() => { LIB.projects = []; });  // only for the Projects column
    return Promise.all([load(Bridge.call('library_overview'), 'overview'), load(Bridge.call('library_versions'), 'versions'), projects]).then(() => {
      LIB.state = 'loaded';
      App.render();
    });
  }
  const loadError = (key, what) => {
    const err = LIB.errors[key];
    return err ? `<div style="margin-bottom:var(--space-4)">${banner('bad', `<b>${what}</b> ${esc(err.message)}`, key === 'overview' && LIB.versions && LIB.versions.versions.length ? '<button class="btn btn--primary btn--sm" data-action="show-versions">Installed versions…</button>' : '')}</div>` : '';
  };
  const reloadLibrary = () => { LIB.state = 'idle'; return Bridge.call('app_info').then(App.setAppInfo).catch(() => {}).then(loadLibrary); };
  App.reloadLibrary = reloadLibrary;  // after a library edit is applied (screens-libedit.js)
  App.libraryDevices = () => devices();  // the Add device dialog's Start from list
  const day = (iso) => (iso ? String(iso).slice(0, 10) : '—');
  /* A +local.N version was made here from the version before the "+" (ADR 0018), so it was applied, not released. */
  const localOf = (v) => (/\+local\.\d+$/.test(v || '') ? v.split('+')[0] : null);
  const released = (L) => (localOf(L.version) ? ` ${badge('info', 'Local')}, local edits of ${esc(localOf(L.version))}${L.date !== '—' ? `, applied ${esc(L.date)}` : ''}` : L.date !== '—' ? `, released ${esc(L.date)}` : '');
  const feeds = { 1: 'Single feed', 2: 'Dual feed (2 supplies)' };
  const num = (v, unit) => (v == null ? '' : `${v} ${unit}`);
  const datasheet = (r) => {
    const ds = r.datasheet, p = ds.power || {}, dim = ds.dimensions_mm, t = ds.operating_temp_c;
    return {
      summary: ds.summary, supply: p.input || '—', typical: num(p.typical_w, 'W') || '—', max: num(p.max_w, 'W') || '—',
      ports: (ds.ports || []).map(String).join('; ') || '—',
      dims: dim ? `${[dim.h, dim.w, dim.d].map((x) => (x == null ? '?' : x)).join(' × ')} mm (H × W × D)${ds.rack_units ? `, ${ds.rack_units} U` : ''}` : '—',
      weight: num(ds.weight_kg, 'kg') || '—', temp: t ? `${t.min ?? '?'} to ${t.max ?? '?'} °C` : '—',
      certs: (ds.certifications || []).join(', ') || '—', url: ds.datasheet_url || ds.product_url || ''
    };
  };
  const TIERS = [['low', 'Low'], ['mid', 'Mid'], ['high', 'High']];
  const alternatives = (r) => r.alternatives.map((a) => ({
    brand: a.make,
    rows: TIERS.map(([k, label]) => ({ tier: label, model: a.tiers[k].model, sub: a.tiers[k].description, verified: a.tiers[k].verified ? 'confirmed' : 'unverified', same_as: a.tiers[k].same_as ? TIERS.find(([x]) => x === a.tiers[k].same_as)[1] : '' }))
  }));
  const row = (d, records) => {
    const r = records[d.part_id];
    return {
      id: d.part_id, make: d.make || (r && r.make) || '', model: d.model || '', cat: d.category,
      supply: d.supply_type ? `${d.voltage_v ? d.voltage_v + ' ' : ''}${d.supply_type}` : '—', w: d.unit_power_w,
      code: d.ordering_code, tagType: d.tag_type, level: d.purdue_level, power: feeds[d.power_supplies] || '',
      mcb: d.min_branch_mcb_a ? `${d.min_branch_mcb_a} A branch` : '',
      verified: r ? r.verified : null, ds: r ? datasheet(r) : null, alt: r && r.alternatives.length ? alternatives(r) : null, src: r ? r.sources : null
    };
  };
  const lib = () => (LIB.overview && LIB.overview.library ? { name: LIB.overview.library.name, version: LIB.overview.library.version, date: day(LIB.overview.library.created), notes: LIB.overview.library.notes } : null);
  const devices = () => (LIB.overview ? LIB.overview.devices.map((d) => row(d, LIB.overview.records)) : []);
  const versions = () => (LIB.versions ? LIB.versions.versions.map((v) => ({ ...v, projects: builtWith(LIB.versions.name, v.version) })) : []);
  const builtWith = (name, version) => LIB.projects.filter((p) => p.library && !p.library.local_file && p.library.name === name && p.library.version === version).length;
  /* Data quality, datasheets and alternatives come from the device database a package may carry. */
  const hasDeviceDb = () => devices().some((d) => d.verified);

  SCREENS.library = () => {
    const { b } = App.route();
    if (LIB.state === 'idle') { loadLibrary(); return `<div class="page">${pageHead('Device library', 'Reading the installed library…')}</div>`; }
    if (b === 'import') return importScreen();
    return browse();
  };

  function browse() {
    const L = lib();
    const lede = L ? `${esc(L.name)} ${esc(L.version)}${released(L)}. Device edits wait as pending changes; the library changes when you apply them or import an update package. Spreadsheet imports go to pending changes too.` : LIB.errors.overview ? 'Make an installed version active, or import the package again.' : 'No library is active.';
    return `<div class="page">${pageHead('Device library', lede,
      `${L ? `<button class="btn btn--secondary" data-action="lib-export">${icon('download')}Export…</button><button class="btn btn--secondary" data-action="lib-import">${icon('upload')}Import…</button><button class="btn btn--primary" data-action="add-device">${icon('plus')}Add device…</button>` : `<button class="btn btn--secondary" data-action="goto" data-to="#/library/import">${icon('upload')}Import update…</button>`}`)}
      ${loadError('overview', 'The active library could not be read.')}
      ${LIB.overview && LIB.overview.library && LIB.overview.library.problem ? `<div style="margin-bottom:var(--space-4)">${banner('warn', `<b>Part of the active library is damaged.</b> ${esc(LIB.overview.library.problem)}`)}</div>` : ''}
      ${LIB.overview && LIB.overview.records_problem ? `<div style="margin-bottom:var(--space-4)">${banner('warn', `<b>Datasheets and alternatives could not be read.</b> ${esc(LIB.overview.records_problem)}`)}</div>` : ''}
      ${L ? contents() : LIB.errors.overview ? '' : versions().length
        ? banner('warn', '<b>No library version is active.</b> Make an installed version active, or import a package.', '<button class="btn btn--primary btn--sm" data-action="show-versions">Installed versions…</button>')
        : banner('warn', '<b>No library is installed.</b> Import a <span class="mono">.bomlib</span> file to see devices here.', '<a class="btn btn--primary btn--sm" href="#/library/import">Import…</a>')}</div>`;
  }

  /* Devices, and the commodity catalogues the engine picks MCBs, terminal blocks and busbars from. */
  function contents() {
    if (!(LIB.overview && LIB.overview.catalogues)) return devicesView();
    const t = S.tab.libview === 'catalogues' ? 'catalogues' : 'devices';
    return `${tabs('libview', [['devices', 'Devices', badge('plain', devices().length)], ['catalogues', 'Catalogues']], t, 'Library contents')}
      <div role="tabpanel" aria-labelledby="tab-libview-${t}">${t === 'catalogues' ? cataloguesView() : devicesView()}</div>`;
  }

  function filtered() {
    return devices().filter((d) => (!F.q || (d.id + d.make + d.model).toLowerCase().includes(F.q.toLowerCase()))
      && (!F.cat || F.cat === d.cat) && (!F.ver || F.ver === d.verified) && (!F.alt || d.alt));
  }
  function devicesView() {
    const all = devices(), list = filtered(), cats = [...new Set(all.map((d) => d.cat))], quality = hasDeviceDb();
    const sel = all.find((d) => d.id === S.selectedDevice) || list[0];
    return `<div class="toolbar" role="search">
        <div class="input-wrap" style="width:280px"><label class="sr-only" for="lib-q">Search library</label>${icon('search')}<input class="input" id="lib-q" type="search" placeholder="Search part, make, model" value="${esc(F.q)}"></div>
        <label class="sr-only" for="lib-cat">Category</label>${select('lib-cat', [['', 'All categories'], ...cats.map((c) => [c, catName(c)])], F.cat, { cls: 'ctl' }).replace('data-dirty="1"', 'data-action="lib-cat"').replace('class="select ctl"', 'class="select" style="width:190px"')}
        ${quality ? `<label class="sr-only" for="lib-ver">Data quality</label>${select('lib-ver', [['', 'Any data quality'], ['confirmed', 'Confirmed'], ['partial', 'Partial'], ['unverified', 'Unverified']], F.ver, {}).replace('data-dirty="1"', 'data-action="lib-ver"').replace('class="select "', 'class="select" style="width:190px"')}
        <label class="check"><input type="checkbox" data-action="lib-alt" ${F.alt ? 'checked' : ''}> Has alternatives</label>` : ''}
        <span class="sp"></span><span class="muted small">${list.length} of ${all.length} devices</span></div>
      <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(340px,400px);gap:var(--space-5);align-items:start">
        <div><div class="table-wrap"><table class="table"><thead><tr><th>Part ID</th><th>Make and model</th><th>Supply</th>${quality ? '<th>Data</th>' : ''}</tr></thead><tbody>
          ${list.map((d) => `<tr class="clickable" tabindex="0" data-action="lib-select" data-id="${esc(d.id)}" aria-selected="${sel && sel.id === d.id}"><td><span class="mono">${esc(d.id)}</span><span class="cell-sub">${esc(catName(d.cat))}</span></td><td>${makeModel(d)}</td><td class="nowrap">${esc(d.supply)}${d.w ? `<span class="cell-sub">${d.w} W</span>` : ''}</td>${quality ? `<td style="white-space:nowrap">${d.verified ? verified(d.verified) : ''}</td>` : ''}</tr>`).join('') || `<tr class="empty-row"><td colspan="${quality ? 4 : 3}">No device matches these filters. Clear a filter or search for a different part.</td></tr>`}
        </tbody></table><div class="table-foot"><span>Select a row to see its details</span></div></div></div>
        ${sel ? detail(sel) : ''}
      </div>`;
  }
  /* The library's own alternatives (same alt_group), compact: part, power and inrush against this device. */
  const ALT = { id: '', reply: null };
  window.addEventListener('hashchange', () => { ALT.id = ''; });  // pending edits may have changed them
  function altCompact(id) {
    if (ALT.id !== id) {
      ALT.id = id; ALT.reply = null;
      Bridge.call('library_alternatives', id).then((a) => { if (ALT.id === id) { ALT.reply = a; App.render(); } }).catch(() => { if (ALT.id === id) { ALT.reply = { group: null, rows: [] }; App.render(); } });
    }
    const a = ALT.reply, chip = App.altChip || (() => '');
    if (!a) return '<p class="muted">Reading the alternatives…</p>';
    if (!a.group || a.rows.length < 2) return '<p class="muted">No alternatives in the library for this device.</p>';
    const num = (v, u) => (v == null ? '—' : `${v} ${u}`);
    return `<div class="table-wrap"><table class="table"><thead><tr><th>Part</th><th class="num">Power</th><th class="num">Inrush</th><th><span class="sr-only">Use</span></th></tr></thead><tbody>${a.rows.filter((r) => !r.is_self).map((r) => `<tr><td><span class="mono">${esc(r.part_id)}</span><span class="cell-sub">${esc([r.tier ? r.tier[0].toUpperCase() + r.tier.slice(1) : '', r.make, r.model].filter(Boolean).join(' · '))}</span></td><td class="num nowrap">${num(r.unit_power_w, 'W')}${chip(r.power_delta_w, 'W')}</td><td class="num nowrap">${num(r.inrush_a, 'A')}${chip(r.inrush_delta_a, 'A')}</td><td>${App.useButton ? App.useButton(id, r.part_id) : ''}</td></tr>`).join('')}</tbody></table>
      <div class="table-foot"><span>${a.rows.length - 1} in group <span class="mono">${esc(a.group)}</span></span><a href="#/library/device/${encodeURIComponent(id)}" data-action="compare-full">Compare in full</a></div></div>`;
  }
  ACTIONS['compare-full'] = () => { S.tab.devEdit = 'alternatives'; return true; };
  function detail(d) {
    const t = S.tab.libdetail;
    const tabsList = [['overview', 'Overview'], ['datasheet', 'Datasheet'], ['alternatives', 'Alternatives']];
    let body = '';
    if (t === 'overview') body = `<dl class="kv"><dt>Part ID</dt><dd class="mono">${esc(d.id)}</dd><dt>Make</dt><dd>${esc(d.make)}</dd><dt>Model</dt><dd>${esc(d.model)}</dd><dt>Ordering code</dt><dd class="mono">${esc(d.code || '—')}</dd><dt>Category</dt><dd>${esc(catName(d.cat))}</dd><dt>Tag</dt><dd class="mono">${d.tagType ? esc(d.tagType) + (d.level ? ' · ' + esc(d.level) : '') : '—'}</dd><dt>Supply</dt><dd>${esc(d.supply)}</dd><dt>Power</dt><dd>${esc(d.power || '—')}</dd><dt>Rated power</dt><dd class="num" style="text-align:left">${d.w != null ? d.w + ' W' : '—'}</dd><dt>Branch MCB</dt><dd>Sized by the engine${d.mcb ? ` <span class="muted">(the library's ${esc(d.mcb)} is deprecated, ADR 0019)</span>` : ''}</dd></dl>`;
    else if (t === 'datasheet') body = d.ds ? `${d.ds.summary ? `<p style="margin-bottom:var(--space-3)">${esc(d.ds.summary)}</p>` : ''}<dl class="kv"><dt>Supply range</dt><dd>${esc(d.ds.supply)}</dd><dt>Typical power</dt><dd>${esc(d.ds.typical)}</dd><dt>Maximum power</dt><dd>${esc(d.ds.max)}</dd><dt>Ports</dt><dd>${esc(d.ds.ports)}</dd><dt>Dimensions</dt><dd>${esc(d.ds.dims)}</dd><dt>Weight</dt><dd>${esc(d.ds.weight)}</dd><dt>Operating temperature</dt><dd>${esc(d.ds.temp)}</dd><dt>Certifications</dt><dd>${esc(d.ds.certs)}</dd>${d.ds.url ? `<dt>Datasheet</dt><dd class="row" style="gap:4px;flex-wrap:nowrap"><span class="mono small" style="overflow-wrap:anywhere">${esc(d.ds.url)}</span><button class="btn btn--ghost btn--icon btn--sm" data-action="copy" data-v="${esc(d.ds.url)}" aria-label="Copy the datasheet link">${icon('copy')}</button></dd>` : ''}</dl>
      ${(d.src || []).length ? `<div class="section" style="margin-top:var(--space-4);padding-bottom:0"><h3>Sources</h3><ul style="margin:var(--space-2) 0 0;padding-left:18px">${d.src.map((x) => `<li style="overflow-wrap:anywhere">${esc(x)}</li>`).join('')}</ul></div>` : ''}` : `<p class="muted">No datasheet recorded for this device.</p>`;
    else body = `${altCompact(d.id)}${d.alt ? `<details class="section" style="margin-top:var(--space-4)"><summary>Researched brands <span class="muted small">(device database)</span></summary>
      ${d.alt.map((a) => `<h3 style="margin-top:var(--space-4)">${esc(a.brand)}</h3><div class="table-wrap" style="margin-top:6px"><table class="table"><thead><tr><th style="width:56px">Tier</th><th>Model</th><th>Data</th><th style="width:40px"><span class="sr-only">Copy</span></th></tr></thead><tbody>${a.rows.map((r) => `<tr><td>${esc(r.tier)}</td><td><span class="mono nowrap">${esc(r.model)}</span><span class="cell-sub">${r.same_as ? `Same as ${esc(r.same_as)}` : esc(r.sub || '')}</span></td><td>${verified(r.verified)}</td><td style="width:40px"><button class="btn btn--ghost btn--icon btn--sm" data-action="copy" data-v="${esc(r.model)}" aria-label="Copy ${esc(r.model)}">${icon('copy')}</button></td></tr>`).join('')}</tbody></table></div>`).join('')}</details>` : ''}`;
    const what = 'Device detail';
    return `<aside class="detail" aria-label="${what}"><h2 class="mono" style="font-size:18px;font-family:var(--font-mono)">${esc(d.id)}</h2><p class="muted" style="margin-bottom:var(--space-3)">${makeModel(d)}</p><a class="btn btn--secondary btn--sm" style="margin-bottom:var(--space-3)" href="#/library/device/${encodeURIComponent(d.id)}">${icon('edit')}Edit device</a>
      ${tabs('libdetail', tabsList, t, what)}<div role="tabpanel" aria-labelledby="tab-libdetail-${t}">${body}</div></aside>`;
  }

  /* ---------- Catalogues (M36; docs/ui/editing.md "Catalogues tab") ----------
     Each catalogue has brand tabs, the default first. A cell edit becomes a pending change as soon
     as it leaves the cell; a change the library refuses stays in the table with the reason. */
  const ROLES = {
    lamp: 'Cabinet lamp', door_switch: 'Door switch', fan: 'Fan', vent_filter: 'Vent filter', thermostat: 'Thermostat', ipr_kit: 'IPR kit',
    change_over_diode_negative: 'Change-over diode, negative', change_over_diode_positive: 'Change-over diode, positive', socket: 'Socket', nameplate: 'Device nameplate'
  };
  const OPTIONAL = ['door_switch', 'nameplate'];
  const KINDS = [['mcb', 'MCBs'], ['aux_contact', 'Aux contacts'], ['terminal_blocks', 'Terminal blocks'], ['busbars', 'Busbars'], ['housekeeping', 'Housekeeping']];
  const COLS = {  // [field, heading, mono, wide]
    mcb: [['rating_a', 'Rating (A)', true], ['code', 'Ordering code', true]],
    terminal_blocks: [['key', 'Type', true], ['make', 'Make'], ['ordering_code', 'Ordering code', true]],
    busbars: [['key', 'Key', true], ['tag', 'Tag', true], ['description', 'Description', false, true]]
  };
  const BLANK = { mcb: { rating_a: '', code: '' }, terminal_blocks: { key: '', make: '', ordering_code: '' }, busbars: { key: '', tag: '', description: '' } };
  const CAT = { state: 'idle', data: null, draft: {}, error: {} };
  App.cataloguesStale = () => { CAT.state = 'idle'; CAT.draft = {}; CAT.error = {}; };
  const catKind = () => (KINDS.some(([k]) => k === S.tab.catkind) ? S.tab.catkind : 'mcb');
  const brandsOf = (kind) => CAT.data.kinds[kind];
  const catBrand = (kind) => brandsOf(kind).find((b) => b.id === S.tab[`cb_${kind}`]) || brandsOf(kind)[0];
  const draftKey = (kind, b) => `${kind}/${b.id}`;
  const valueOf = (kind, b) => CAT.draft[draftKey(kind, b)] || b.value;
  /* The datasheet record of a default-brand row, from the overview (backlog v0.2 point 1). */
  function recordOf(kind, row) {
    const c = LIB.overview && LIB.overview.catalogues; if (!c) return null;
    const id = kind === 'mcb' ? (c.mcb.ratings.find((m) => m.rating_a === row.rating_a) || {}).record
      : kind === 'aux_contact' ? c.aux_contact.record
      : kind === 'terminal_blocks' ? (c.terminal_blocks.find((t) => t.type === row.key) || {}).record
      : kind === 'busbars' ? (c.busbars.find((t) => t.key === row.key) || {}).record : row.part_id;
    return (id && LIB.overview.records[id]) || null;
  }
  function cataloguesView() {
    if (CAT.state === 'idle') {
      CAT.state = 'loading';
      Bridge.call('library_catalogues').then((d) => { CAT.data = d; CAT.state = 'loaded'; App.render(); })
        .catch((e) => { CAT.state = 'failed'; CAT.failed = e.message; App.render(); });
    }
    if (CAT.state === 'failed') return `<div style="margin-top:var(--space-4)">${banner('bad', `<b>The catalogues could not be read.</b> ${esc(CAT.failed)}`)}</div>`;
    if (!CAT.data) return '<p class="muted" style="margin-top:var(--space-4)">Reading the catalogues…</p>';
    const kind = catKind(), b = catBrand(kind), key = draftKey(kind, b), v = valueOf(kind, b);
    const quality = b.default && !b.changed && hasDeviceDb();  // the records describe the installed default
    const switcher = `<div class="segmented" role="group" aria-label="Catalogue">${KINDS.map(([k, t]) => `<button data-action="cat-kind" data-kind="${k}" aria-pressed="${k === kind}">${t}${brandsOf(k).some((x) => x.changed) ? ' <span class="chg" aria-hidden="true"></span>' : ''}</button>`).join('')}</div>`;
    const brandTabs = tabs(`cb_${kind}`, brandsOf(kind).map((x) => [x.id, x.label.length > 34 ? x.label.slice(0, 32) + '…' : x.label, `${x.default ? ` ${badge('info', 'Default')}` : ''}${x.changed ? '<span class="chg" aria-hidden="true"></span><span class="sr-only">, pending</span>' : ''}`, x.label]), b.id, 'Brands');
    const actions = `<div class="row cat-actions">${b.default ? '<span class="muted small">Projects use the default unless they pick another brand.</span>' : `<button class="btn btn--secondary btn--sm" data-action="cat-default" ${CAT.draft[key] ? 'disabled title="Finish or undo the row first"' : ''}>Make ${esc(b.label)} the default</button>`}<span class="sp"></span><button class="btn btn--secondary btn--sm" data-action="cat-add-brand">${icon('plus')}Add brand…</button></div>`;
    const name = b.default ? '' : `<div class="cat-name">${field('Brand name', input('cat-name', v.name || '', { placeholder: b.label }).replace('<input ', '<input data-cat="name" '), 'Shown on the brand tab and in the project\'s brand selects.')}</div>`;
    const err = CAT.error[key] ? `<div class="cat-err" role="alert">${banner('bad', `<b>Not added to the pending changes.</b> ${esc(CAT.error[key])}`, `<button class="btn btn--secondary btn--sm" data-action="cat-revert">Undo my edit</button>`)}</div>` : '';
    return `<div class="cat" style="margin-top:var(--space-4)">${switcher}${brandTabs}<div role="tabpanel" aria-labelledby="tab-cb_${kind}-${b.id}">${actions}${err}${name}${catTable(kind, b, v, quality)}</div>
      ${kind === 'mcb' ? `<p class="muted small">${esc(b.label)}${b.ac_rated === false ? ', DC only: a substation can pick it for the DC branches' : ''}. The engine sizes each MCB and takes the code for its rating from here. Standard enclosure: ${CAT.data.enclosure_u || (LIB.overview.catalogues || {}).enclosure_u || 42} U.</p>` : ''}</div>`;
  }
  const cell = (kind, i, f, val, o = {}) => {
    const id = `cat-${i}-${f}`, label = `${(COLS[kind] || []).concat([['make', 'Make'], ['model', 'Model'], ['ordering_code', 'Ordering code']]).find(([x]) => x === f)[1]}, row ${i + 1}`;
    return o.wide ? `<textarea class="input cat-cell" id="${id}" rows="${String(val).split('\n').length}" data-cat="${i}.${f}" aria-label="${esc(label)}">${esc(val)}</textarea>`
      : `<input class="input cat-cell${o.mono ? ' input--mono' : ''}${o.num ? ' input--num' : ''}" id="${id}" value="${esc(val)}" data-cat="${i}.${f}" aria-label="${esc(label)}">`;
  };
  const dataCell = (quality, kind, row) => (quality ? `<td class="nowrap">${(() => { const r = recordOf(kind, row); return r ? verified(r.verified) : '<span class="muted">No record</span>'; })()}</td>` : '');
  function catTable(kind, b, v, quality) {
    const head = (cols, del) => `<thead><tr>${cols.map((h) => `<th>${h}</th>`).join('')}${quality ? '<th>Data</th>' : ''}${del ? '<th><span class="sr-only">Remove</span></th>' : ''}</tr></thead>`;
    if (kind === 'aux_contact') {
      return `<div class="table-wrap"><table class="table cat-table">${head(['Make', 'Model', 'Ordering code'])}<tbody><tr>${['make', 'model', 'ordering_code'].map((f) => `<td>${cell(kind, 0, f, v[f], { mono: f === 'ordering_code' })}</td>`).join('')}${dataCell(quality, kind, v)}</tr></tbody></table></div>`;
    }
    if (kind === 'housekeeping') {
      const parts = CAT.data.parts;
      return `<div class="table-wrap"><table class="table cat-table">${head(['Role', 'Part'])}<tbody>${v.rows.map((r, i) => `<tr><td>${esc(ROLES[r.role] || r.role)}</td><td><select class="select" id="cat-${i}-part_id" data-cat="${i}.part_id" aria-label="Part for ${esc(ROLES[r.role] || r.role)}">${OPTIONAL.includes(r.role) ? `<option value="" ${!r.part_id ? 'selected' : ''}>None</option>` : ''}${parts.map((p) => `<option value="${esc(p)}" ${p === r.part_id ? 'selected' : ''}>${esc(p)}</option>`).join('')}</select></td>${dataCell(quality, kind, r)}</tr>`).join('')}</tbody></table>
        <div class="table-foot"><span>Each role is a part in the device list.</span></div></div>`;
    }
    const cols = COLS[kind];
    const rows = v.rows.map((r, i) => `<tr>${cols.map(([f, , mono, wide]) => `<td${wide ? ' class="cat-wide"' : f === 'rating_a' ? ' class="cat-num"' : ''}>${cell(kind, i, f, r[f], { mono, wide, num: f === 'rating_a' })}</td>`).join('')}${dataCell(quality, kind, r)}<td class="cat-del"><button class="btn btn--ghost btn--icon btn--sm btn--del" data-action="cat-remove" data-i="${i}" aria-label="Remove ${esc(String(r[cols[0][0]] || 'the new row'))}" ${v.rows.length < 2 ? 'disabled title="A catalogue keeps at least one row"' : ''}>${icon('trash')}</button></td></tr>`).join('');
    const fill = v.rows.some((r) => cols.some(([f]) => r[f] === '')) ? '<span class="muted small">Fill in the new row to add it to the pending changes.</span>' : '';
    return `<div class="table-wrap"><table class="table cat-table">${head(cols.map(([, h]) => h), true)}<tbody>${rows}</tbody></table>
      <div class="table-foot"><button class="btn btn--ghost btn--sm" data-action="cat-add-row">${icon('plus')}${kind === 'mcb' ? 'Add rating' : 'Add row'}</button>${fill}</div></div>`;
  }
  /* Send the brand's rows; the reply is the catalogues and the pending set. */
  function sendCatalogue(kind, b, value) {
    const key = draftKey(kind, b), cols = COLS[kind];
    CAT.draft[key] = value; delete CAT.error[key];
    if (cols && value.rows.some((r) => cols.some(([f]) => r[f] === ''))) return;  // a new row is still blank: kept as typed
    const render = () => { const at = document.activeElement && document.activeElement.id; App.render(); const n = at && document.getElementById(at); n && n.focus(); };
    const sent = kind === 'mcb' ? { ...value, rows: value.rows.map((r) => ({ ...r, rating_a: /^\d+$/.test(String(r.rating_a).trim()) ? Number(r.rating_a) : r.rating_a })) } : value;
    Bridge.call('set_library_catalogue', kind, b.id, sent).then((r) => {
      delete CAT.draft[key]; CAT.data = r.catalogues; App.setPending(r.pending); render();
    }).catch((e) => { CAT.error[key] = e.message.replace(/^The library cannot take this change: /, ''); render(); });
  }
  document.addEventListener('change', (e) => {
    const f = e.target.dataset && e.target.dataset.cat; if (f == null || !CAT.data) return;
    const kind = catKind(), b = catBrand(kind), value = JSON.parse(JSON.stringify(valueOf(kind, b)));
    if (f === 'name') value.name = e.target.value.trim() || null;
    else { const [i, field] = f.split('.'); if (value.rows) value.rows[+i][field] = e.target.value; else value[field] = e.target.value; }
    sendCatalogue(kind, b, value);
  });
  ACTIONS['cat-kind'] = (el) => { S.tab.catkind = el.dataset.kind; App.render(); };
  ACTIONS['cat-add-row'] = () => { const kind = catKind(), b = catBrand(kind), value = JSON.parse(JSON.stringify(valueOf(kind, b))); value.rows.push({ ...BLANK[kind] }); CAT.draft[draftKey(kind, b)] = value; App.render(); const n = document.getElementById(`cat-${value.rows.length - 1}-${COLS[kind][0][0]}`); n && n.focus(); };
  ACTIONS['cat-remove'] = (el) => { const kind = catKind(), b = catBrand(kind), value = JSON.parse(JSON.stringify(valueOf(kind, b))); value.rows.splice(+el.dataset.i, 1); sendCatalogue(kind, b, value); };
  ACTIONS['cat-revert'] = () => { const kind = catKind(), key = draftKey(kind, catBrand(kind)); delete CAT.draft[key]; delete CAT.error[key]; App.render(); };
  const catReply = (r, text) => { closeDialog(); CAT.data = r.catalogues; App.setPending(r.pending); App.render(); toast(text, 'check'); };
  const KIND_NAME = { mcb: 'MCB', aux_contact: 'aux contact', terminal_blocks: 'terminal block', busbars: 'busbar', housekeeping: 'housekeeping' };
  ACTIONS['cat-default'] = () => {
    const kind = catKind(), b = catBrand(kind), now = brandsOf(kind)[0];
    dialog({ title: `Make ${esc(b.label)} the default?`, body: `<p>Projects that use the default ${KIND_NAME[kind]} set get ${esc(b.label)} once the change is applied. ${esc(now.label)} stays in the library as a brand of its own.</p><p class="muted">A project or substation that picked ${esc(b.label)} by name picks Default instead after this.</p>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="cat-default-do">Make default</button>` });
  };
  ACTIONS['cat-default-do'] = () => {
    const kind = catKind(), b = catBrand(kind);
    Bridge.call('make_default_brand', kind, b.id).then((r) => { S.tab[`cb_${kind}`] = 'default'; catReply(r, `${b.label} is the default, pending`); }).catch((e) => { closeDialog(); toast(e.message, 'error'); });
  };
  ACTIONS['cat-add-brand'] = () => {
    const kind = catKind(), b = catBrand(kind);
    dialog({ title: `Add a ${KIND_NAME[kind]} brand`, body: `<div class="form">${field('Brand id', input('cat-new-id', '', { mono: true, placeholder: 'for example abb-s200' }), 'Lowercase letters, digits and dashes. Projects pick the brand by it.')}
      ${field('Name', input('cat-new-name', '', { placeholder: 'for example ABB S200' }), 'Optional. The tab shows it.')}
      ${field('Start from', select('cat-new-from', brandsOf(kind).map((x) => [x.id, `${x.label}${x.default ? ' (default)' : ''}`]), b.id), 'Its rows are copied, so only the codes need typing.')}<p class="err small" id="cat-new-err" hidden></p></div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="cat-add-brand-do">Add brand</button>` });
  };
  ACTIONS['cat-add-brand-do'] = () => {
    const kind = catKind(), id = $('#cat-new-id').value.trim(), name = $('#cat-new-name').value.trim(), from = $('#cat-new-from').value, bad = $('#cat-new-err');
    const say = (t) => { bad.textContent = t; bad.hidden = false; $('#cat-new-id').setAttribute('aria-invalid', 'true'); $('#cat-new-id').focus(); };
    if (!/^[a-z0-9][a-z0-9-]*$/.test(id)) { say('Use lowercase letters, digits and dashes, starting with a letter or digit.'); return; }
    Bridge.call('add_catalogue_brand', kind, id, name, from).then((r) => { S.tab[`cb_${kind}`] = id; catReply(r, `Brand ${name || id} added, pending`); }).catch((e) => say(e.message.replace(/^The library cannot take this change: /, '')));
  };

  ACTIONS['lib-select'] = (el) => { S.selectedDevice = el.dataset.id; S.tab.libdetail = 'overview'; App.render(); };
  document.addEventListener('keydown', (e) => { const r = e.target.closest && e.target.closest('tr.clickable[data-action^="lib-"]'); if (r && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); r.click(); } });
  document.addEventListener('change', (e) => { if (e.target.id === 'lib-cat') { F.cat = e.target.value; App.render(); } if (e.target.id === 'lib-ver') { F.ver = e.target.value; App.render(); } });
  ACTIONS['lib-cat'] = () => {}; ACTIONS['lib-ver'] = () => {};
  ACTIONS['lib-alt'] = () => { F.alt = !F.alt; App.render(); };
  ACTIONS.copy = (el) => {
    const text = el.dataset.v;
    const fallback = () => { const t = document.createElement('textarea'); t.value = text; document.body.appendChild(t); t.select(); document.execCommand('copy'); t.remove(); };
    (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).catch(fallback).then(() => toast(`Copied ${text}`));
  };
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

  /* Refusals: what the first failed check means for the person importing (docs/ui/screens.md, Refusals). */
  const REFUSALS = {
    downgrade: { title: 'This package is older than the installed library', body: 'To go back to a version you already have, use Installed versions → Make active.', force: 'Install anyway (downgrade)' },
    already_installed: { title: 'This version is already installed', body: 'There is nothing new to import.', force: 'Reinstall and make active' },
    incompatible: { title: 'This package needs a newer version of the app', body: 'Install the newer app, then import this package again. Your current library is unchanged.' },
    invalid_package: { title: 'The package is damaged or is not a library package', body: 'Nothing was installed. Ask the sender for a new copy, or download it again.' },
    validation_failed: { title: 'The library in this package has errors', body: 'Nothing was installed. Send the details below to whoever maintains the library.' },
    store_damaged: { title: 'The installed libraries need attention', body: 'Make a version active under Installed versions, or import a package again.' }
  };
  const IMP = { step: 'choose', path: '', preview: null, force: false, result: null };

  function importFlow() {
    const L = lib();
    if (IMP.step === 'choose') return `<div class="drop" data-action="pick-file" id="drop" tabindex="0" role="button" aria-label="Choose a library package">${icon('pkg', 'i--lg')}<h3 style="margin:8px 0 2px">Choose a .bomlib file</h3><p>The package is checked before anything is installed.</p><button class="btn btn--primary" data-action="pick-file">${icon('folder')}Choose package…</button></div>
      <p class="muted small" style="margin-top:var(--space-3)">You can also double-click a .bomlib file in Windows to import it. ${L ? `Currently installed: ${esc(L.name)} ${esc(L.version)}.` : LIB.errors.overview ? 'The active library could not be read; see Installed versions.' : 'No library is installed yet.'}</p>`;
    if (IMP.step === 'checking') return `<div class="stack" style="max-width:520px"><h3>Checking ${esc(IMP.path.split(/[\\/]/).pop())}</h3><div class="progress" role="progressbar" aria-label="Checking"><i style="width:40%"></i></div><p class="muted">Verifying checksums, the library and its version. Nothing is installed.</p></div>`;
    const p = IMP.preview, m = p.manifest;
    if (IMP.step === 'importing') return `<div class="stack" style="max-width:520px"><h3>Installing ${esc(m.name)} ${esc(m.version)}</h3><div class="progress" role="progressbar" aria-label="Installing"><i style="width:60%"></i></div><p class="muted">Copying files and keeping the previous version for rollback…</p></div>`;
    if (IMP.step === 'done') {
      const r = IMP.result;
      return `${banner('ok', `<b>${esc(r.manifest.name)} ${esc(r.manifest.version)} is now active.</b> ${r.previous ? `Version ${esc(r.previous)} is kept, so you can go back under Installed versions.` : ''}`, '<button class="btn btn--secondary btn--sm" data-action="import-cancel">Import another…</button><button class="btn btn--secondary btn--sm" data-action="goto" data-to="#/library">View library</button>')}
      ${r.previous ? `<div style="margin-top:var(--space-3)">${banner('info', `Projects built with ${esc(r.previous)} show a warning in Checks until they are built again with ${esc(r.manifest.version)}.`)}</div>` : ''}`;
    }
    const failed = p.checks.find((c) => c.status === 'failed');
    const active = p.previous || (m && S.library && S.library.name === m.name ? S.library.version : '');
    const refusal = failed ? REFUSALS[failed.kind] || { title: 'This package cannot be imported', body: '' } : null;
    const forced = IMP.force && !failed;
    const d = p.diff;
    const n = d ? { a: d.added.length, c: Object.keys(d.changed).length, r: d.removed.length, f: d.files_added.length + d.files_changed.length + d.files_removed.length } : null;
    const kb = (b) => (b == null ? '—' : b < 1024 ? `${b} bytes` : `${Math.round(b / 1024)} KB`);
    return `<div class="stack" style="max-width:920px">
      ${refusal ? banner('bad', `<b>${esc(refusal.title)}</b><div>${esc(failed.detail)}</div>${refusal.body ? `<div>${esc(refusal.body)}</div>` : ''}${refusal.force ? `<label class="check" style="margin-top:8px"><input type="checkbox" data-action="force-toggle"> ${esc(refusal.force)}</label>` : ''}`) : ''}
      ${forced ? banner('warn', `<b>Forced.</b> ${esc((p.checks.find((c) => c.status === 'warning') || {}).detail || '')}`, '<button class="btn btn--secondary btn--sm" data-action="force-off">Undo</button>') : ''}
      <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:var(--space-6)">
        <section><h3>Package</h3><dl class="kv" style="margin-top:var(--space-2);grid-template-columns:130px 1fr"><dt>File</dt><dd class="mono">${esc(p.file_name)}</dd><dt>Size</dt><dd>${kb(p.package_size)}</dd>
          ${m ? `<dt>Library</dt><dd>${esc(m.name)}</dd><dt>Version</dt><dd><b>${esc(m.version)}</b> <span class="muted">(${active ? `active ${esc(active)}` : 'first install'})</span></dd><dt>Library schema</dt><dd>${esc(m.schema_version)}</dd><dt>Needs app</dt><dd>${esc(m.min_app_version)} or later</dd><dt>Built</dt><dd>${esc(String(m.created).replace('T', ' ').slice(0, 16))}</dd>` : ''}</dl>
        ${m && m.release_notes ? `<h3 style="margin-top:var(--space-4)">Release notes</h3><p style="margin-top:6px">${esc(m.release_notes)}</p>` : ''}</section>
        <section><h3>Verification</h3><ul class="checklist" style="margin-top:var(--space-2)">${App.checkList(p.checks)}</ul></section></div>
      ${d ? `<section><h3>What changes</h3>
        ${n.a + n.c + n.r + d.catalogues_changed.length + n.f === 0 ? '<p class="muted" style="margin-top:6px">No changes.</p>' : `
        <div class="row" style="margin:var(--space-2) 0 var(--space-3)">${badge('ok', `${n.a} added`)}${badge('info', `${n.c} changed`)}${badge('bad', `${n.r} removed`)}${d.catalogues_changed.length ? badge('plain', `${d.catalogues_changed.length} catalogues changed`) : ''}${n.f ? badge('plain', `${n.f} data files`) : ''}</div>
        <div class="diff-list table-wrap" style="padding:0 var(--space-4)">
          ${group('Added parts', d.added.map((x) => [x, '']), 'ok')}${group('Changed parts', Object.entries(d.changed).map(([k, v]) => [k, v.join(', ')]), 'info', true)}${group('Removed parts', d.removed.map((x) => [x, '']), 'bad')}
          ${group('Changed catalogues', d.catalogues_changed.map((c) => [c, '']), 'plain')}
          ${group('Device-database files', [...d.files_added.map((f) => [f, 'added']), ...d.files_changed.map((f) => [f, 'changed']), ...d.files_removed.map((f) => [f, 'removed'])], 'plain')}
        </div>`}</section>` : ''}
      <div class="actionbar">
        <button class="btn btn--primary" data-action="do-import" ${p.can_import && m ? '' : 'disabled'}>${icon('check')}Import and activate ${m ? esc(m.version) : ''}</button>
        <button class="btn btn--secondary" data-action="import-cancel">Choose a different package</button></div></div>`;
  }
  const group = (title, items, kind, fields) => items.length ? `<details ${kind === 'info' || kind === 'bad' ? 'open' : ''}><summary>${icon('chevr', 'chev')}${esc(title)} ${badge(kind, items.length)}</summary><div class="items">${items.map(([a, b]) => `<div><span class="mono">${esc(a)}</span><span class="muted">${fields && b ? 'fields: ' + esc(b) : esc(b)}</span></div>`).join('')}</div></details>` : '';
  const fail = (err) => { toast(err.kind === 'no_backend' ? 'Importing works in the app, not in a browser.' : err.message, 'error'); };
  function review(force) {
    IMP.force = force; IMP.step = 'checking'; App.render();
    return Bridge.call('preview_library_import', IMP.path, force)
      .then((preview) => { IMP.preview = preview; IMP.step = 'review'; })
      .catch((err) => { IMP.step = 'choose'; fail(err); })
      .then(() => {
        App.render();
        const next = $(force ? '[data-action="force-off"]' : '[data-action="force-toggle"]') || $('[data-action="do-import"]:not([disabled])') || $('[data-action="import-cancel"]');
        if (next) next.focus();  // keep the keyboard where the person is working
      });
  }
  ACTIONS['pick-file'] = () => {
    Bridge.call('choose_file', 'bomlib').then((path) => { if (path) { IMP.path = path; review(false); } }).catch(fail);
  };
  ACTIONS['show-versions'] = () => { S.libTab = 'versions'; go('#/library/import'); };
  ACTIONS['import-cancel'] = () => { IMP.step = 'choose'; IMP.preview = null; App.render(); };
  ACTIONS['force-toggle'] = () => review(true);
  ACTIONS['force-off'] = () => review(false);
  ACTIONS['do-import'] = () => {
    IMP.step = 'importing'; App.render();
    Bridge.call('import_library', IMP.path, IMP.force)
      .then((result) => { IMP.result = result; IMP.step = 'done'; toast(`Library ${result.manifest.version} is active`); return reloadLibrary(); })
      .catch((err) => { IMP.step = 'review'; fail(err); App.render(); });
  };
  window.addEventListener('hashchange', () => { if (IMP.step === 'done') ACTIONS['import-cancel'](); });  // the next visit starts fresh
  /* A file dropped on the window must not replace the app page. */
  const isFile = (e) => e.dataTransfer && [...e.dataTransfer.types].includes('Files');
  ['dragover', 'drop'].forEach((t) => window.addEventListener(t, (e) => { if (!isFile(e)) return; e.preventDefault(); if (t === 'drop') toast('Use "Choose package…" to pick the file.', 'info'); }));

  function versionsView() {
    const L = lib(), list = versions();
    if (LIB.errors.versions) return loadError('versions', 'The installed versions could not be read.');
    if (!L && !list.length) return `<p class="muted">No library is installed yet.</p>`;
    return `<div class="table-wrap" style="max-width:980px"><table class="table table--comfort"><thead><tr><th>Version</th><th>Released</th><th>Notes</th><th class="num">Projects</th><th>State</th><th style="width:130px"><span class="sr-only">Actions</span></th></tr></thead><tbody>
      ${list.map((v) => `<tr><td class="mono">${esc(v.version)}${localOf(v.version) ? ` ${badge('info', 'Local')}` : ''}</td><td class="nowrap">${localOf(v.version) ? `Applied ${esc(day(v.released))}` : esc(day(v.released))}</td><td class="wrap">${esc(v.notes || '')}</td><td class="num">${v.projects}</td><td>${v.active ? badge('ok', 'Active', 'check') : ''} ${v.problem ? `${badge('bad', 'Problem', 'error')}<span class="cell-sub">${esc(v.problem)}</span>` : v.active ? '' : badge('plain', 'Installed')}</td><td>${v.active ? '' : `<button class="btn btn--secondary btn--sm" data-action="rollback" data-v="${esc(v.version)}" ${v.problem ? 'disabled' : ''}>Make active</button>`}</td></tr>`).join('')}</tbody></table></div>
      <p class="muted small" style="margin-top:var(--space-3);max-width:68ch">Making an older version active does not change any project file. Projects keep the version they record, and the check report tells you when it differs from the active one.</p>`;
  }
  ACTIONS.rollback = (el) => { const L = lib(); dialog({ title: `Make ${esc(el.dataset.v)} active?`, body: `<p>The library switches to ${esc(el.dataset.v)} for every project on this PC. ${L ? `Version ${esc(L.version)} stays installed.` : ''}</p>`, actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="activate-version" data-v="${esc(el.dataset.v)}">Make ${esc(el.dataset.v)} active</button>` }); };
  ACTIONS['activate-version'] = (el) => {
    closeDialog();
    const name = LIB.versions && LIB.versions.name;
    Bridge.call('activate_library_version', name, el.dataset.v)
      .then((v) => { toast(`Library ${v} is now active`); return reloadLibrary(); })
      .catch(fail);
  };
})();
