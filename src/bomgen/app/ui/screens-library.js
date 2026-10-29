/* Screens: Library (browse, detail) and import / installed versions, on bomgen.app.api (plan M10b). */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, select, pageHead, illus, dialog, closeDialog, toast, go, verified, $ } = App;
  /* "SEL SEL-2730M" reads as a stutter: when the model starts with the make, the model alone says both. */
  const makeModel = (d) => (d.model && d.make && d.model.toLowerCase().startsWith(d.make.toLowerCase()) ? esc(d.model) : `${esc(d.make)} <span class="muted">${esc(d.model)}</span>`);
  const ACRONYMS = { io: 'IO', gps: 'GPS', rtac: 'RTAC', sfp: 'SFP' };
  const catName = (c) => c.split('_').map((w) => ACRONYMS[w] || w).join(' ').replace(/^./, (m) => m.toUpperCase());
  const F = { q: '', cat: '', ver: '', alt: false };

  /* ---------- data from Python; the illustrative DB only when opened outside the app ---------- */
  const LIB = { state: 'idle', overview: null, versions: null, projects: [], errors: {}, offline: false };
  function loadLibrary() {
    LIB.state = 'loading';
    // Loaded independently: a damaged active version must not hide the versions that can repair it.
    const load = (call, key) => call.then((data) => { LIB[key] = data; LIB.errors[key] = null; })
      .catch((err) => { LIB[key] = null; LIB.errors[key] = err; });
    const projects = Bridge.call('list_projects').then((list) => { LIB.projects = list; }).catch(() => { LIB.projects = []; });  // only for the Projects column
    return Promise.all([load(Bridge.call('library_overview'), 'overview'), load(Bridge.call('library_versions'), 'versions'), projects]).then(() => {
      LIB.state = 'loaded';
      LIB.offline = Object.values(LIB.errors).some((e) => e && e.kind === 'no_backend');
      App.render();
    });
  }
  const loadError = (key, what) => {
    const err = !LIB.offline && LIB.errors[key];
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
  const lib = () => LIB.offline
    ? { name: DB.library.name, version: DB.library.version, date: DB.library.installed, notes: DB.library.notes }
    : LIB.overview && LIB.overview.library ? { name: LIB.overview.library.name, version: LIB.overview.library.version, date: day(LIB.overview.library.created), notes: LIB.overview.library.notes } : null;
  const devices = () => (LIB.offline ? DB.devices : LIB.overview ? LIB.overview.devices.map((d) => row(d, LIB.overview.records)) : []);
  const versions = () => (LIB.offline
    ? DB.library.versions.map((v) => ({ version: v.v, released: v.date, notes: v.notes, active: v.active, problem: null, projects: v.projects }))
    : LIB.versions ? LIB.versions.versions.map((v) => ({ ...v, projects: builtWith(LIB.versions.name, v.version) })) : []);
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
    const lede = L ? `${esc(L.name)} ${esc(L.version)}${released(L)}. Device edits wait as pending changes; the library changes when you apply them or import an update package. Spreadsheet imports go to pending changes too.` : LIB.errors.overview && !LIB.offline ? 'Make an installed version active, or import the package again.' : 'No library is active.';
    return `<div class="page">${pageHead('Device library', lede,
      `${L && !LIB.offline ? `<button class="btn btn--secondary" data-action="lib-export">${icon('download')}Export…</button><button class="btn btn--secondary" data-action="lib-import">${icon('upload')}Import…</button><button class="btn btn--primary" data-action="add-device">${icon('plus')}Add device…</button>` : `<button class="btn btn--secondary" data-action="goto" data-to="#/library/import">${icon('upload')}Import update…</button>`}`)}
      ${loadError('overview', 'The active library could not be read.')}
      ${LIB.overview && LIB.overview.library && LIB.overview.library.problem ? `<div style="margin-bottom:var(--space-4)">${banner('warn', `<b>Part of the active library is damaged.</b> ${esc(LIB.overview.library.problem)}`)}</div>` : ''}
      ${LIB.overview && LIB.overview.records_problem ? `<div style="margin-bottom:var(--space-4)">${banner('warn', `<b>Datasheets and alternatives could not be read.</b> ${esc(LIB.overview.records_problem)}`)}</div>` : ''}
      ${L ? contents() : LIB.errors.overview && !LIB.offline ? '' : versions().length
        ? banner('warn', '<b>No library version is active.</b> Make an installed version active, or import a package.', '<button class="btn btn--primary btn--sm" data-action="show-versions">Installed versions…</button>')
        : banner('warn', '<b>No library is installed.</b> Import a <span class="mono">.bomlib</span> file to see devices here.', '<a class="btn btn--primary btn--sm" href="#/library/import">Import…</a>')}</div>`;
  }

  /* Devices, and the commodity catalogues the engine picks MCBs, terminal blocks and busbars from. */
  function contents() {
    const cat = !LIB.offline && LIB.overview && LIB.overview.catalogues;
    if (!cat) return devicesView();
    const t = S.tab.libview === 'catalogues' ? 'catalogues' : 'devices';
    return `${tabs('libview', [['devices', 'Devices', badge('plain', devices().length)], ['catalogues', 'Catalogues']], t, 'Library contents')}
      <div role="tabpanel" aria-labelledby="tab-libview-${t}">${t === 'catalogues' ? cataloguesView(cat) : devicesView()}</div>`;
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
        </tbody></table><div class="table-foot"><span>Select a row to see its details</span>${LIB.offline ? `<span>${illus()}</span>` : ''}</div></div></div>
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
  function detail(d, o) {  // o: a catalogue entry's heading and Overview, in place of a device's
    const t = S.tab.libdetail;
    const tabsList = [['overview', 'Overview'], ['datasheet', 'Datasheet'], ['alternatives', 'Alternatives']];
    let body = '';
    if (t === 'overview') body = o ? o.kv : `<dl class="kv"><dt>Part ID</dt><dd class="mono">${esc(d.id)}</dd><dt>Make</dt><dd>${esc(d.make)}</dd><dt>Model</dt><dd>${esc(d.model)}</dd><dt>Ordering code</dt><dd class="mono">${esc(d.code || '—')}</dd><dt>Category</dt><dd>${esc(catName(d.cat))}</dd><dt>Tag</dt><dd class="mono">${d.tagType ? esc(d.tagType) + (d.level ? ' · ' + esc(d.level) : '') : '—'}</dd><dt>Supply</dt><dd>${esc(d.supply)}</dd><dt>Power</dt><dd>${esc(d.power || '—')}</dd><dt>Rated power</dt><dd class="num" style="text-align:left">${d.w != null ? d.w + ' W' : '—'}</dd><dt>Branch MCB</dt><dd>${esc(d.mcb || '—')}</dd></dl>`;
    else if (t === 'datasheet') body = d.ds ? `${d.ds.summary ? `<p style="margin-bottom:var(--space-3)">${esc(d.ds.summary)}</p>` : ''}<dl class="kv"><dt>Supply range</dt><dd>${esc(d.ds.supply)}</dd><dt>Typical power</dt><dd>${esc(d.ds.typical)}</dd><dt>Maximum power</dt><dd>${esc(d.ds.max)}</dd><dt>Ports</dt><dd>${esc(d.ds.ports)}</dd><dt>Dimensions</dt><dd>${esc(d.ds.dims)}</dd><dt>Weight</dt><dd>${esc(d.ds.weight)}</dd><dt>Operating temperature</dt><dd>${esc(d.ds.temp)}</dd><dt>Certifications</dt><dd>${esc(d.ds.certs)}</dd>${d.ds.url ? `<dt>Datasheet</dt><dd class="row" style="gap:4px;flex-wrap:nowrap"><span class="mono small" style="overflow-wrap:anywhere">${esc(d.ds.url)}</span><button class="btn btn--ghost btn--icon btn--sm" data-action="copy" data-v="${esc(d.ds.url)}" aria-label="Copy the datasheet link">${icon('copy')}</button></dd>` : ''}</dl>
      ${(d.src || []).length ? `<div class="section" style="margin-top:var(--space-4);padding-bottom:0"><h3>Sources</h3><ul style="margin:var(--space-2) 0 0;padding-left:18px">${d.src.map((x) => `<li style="overflow-wrap:anywhere">${esc(x)}</li>`).join('')}</ul></div>` : ''}` : `<p class="muted">No datasheet recorded for this device.</p>`;
    else body = `${o || LIB.offline ? '' : altCompact(d.id)}${d.alt ? `<details class="section" style="margin-top:var(--space-4)"><summary>Researched brands <span class="muted small">(device database)</span></summary>
      ${d.alt.map((a) => `<h3 style="margin-top:var(--space-4)">${esc(a.brand)}</h3><div class="table-wrap" style="margin-top:6px"><table class="table"><thead><tr><th style="width:56px">Tier</th><th>Model</th><th>Data</th><th style="width:40px"><span class="sr-only">Copy</span></th></tr></thead><tbody>${a.rows.map((r) => `<tr><td>${esc(r.tier)}</td><td><span class="mono nowrap">${esc(r.model)}</span><span class="cell-sub">${r.same_as ? `Same as ${esc(r.same_as)}` : esc(r.sub || '')}</span></td><td>${verified(r.verified)}</td><td style="width:40px"><button class="btn btn--ghost btn--icon btn--sm" data-action="copy" data-v="${esc(r.model)}" aria-label="Copy ${esc(r.model)}">${icon('copy')}</button></td></tr>`).join('')}</tbody></table></div>`).join('')}</details>` : ''}`;
    const what = o ? 'Catalogue entry detail' : 'Device detail';
    return `<aside class="detail" aria-label="${what}"><h2 class="mono" style="font-size:18px;font-family:var(--font-mono)">${o ? o.title : esc(d.id)}</h2><p class="muted" style="margin-bottom:var(--space-3)">${o ? o.sub : makeModel(d)}</p>${o || LIB.offline ? '' : `<a class="btn btn--secondary btn--sm" style="margin-bottom:var(--space-3)" href="#/library/device/${encodeURIComponent(d.id)}">${icon('edit')}Edit device</a>`}
      ${tabs('libdetail', tabsList, t, what)}<div role="tabpanel" aria-labelledby="tab-libdetail-${t}">${body}</div></aside>`;
  }

  /* ---------- Catalogues (read-only; editing them is M16) ---------- */
  const firstLine = (text) => String(text || '').split('\n')[0];
  const ROLES = {
    lamp: 'Cabinet lamp', door_switch: 'Door switch', fan: 'Fan', vent_filter: 'Vent filter', thermostat: 'Thermostat', ipr_kit: 'IPR kit',
    change_over_diode_negative: 'Change-over diode, negative', change_over_diode_positive: 'Change-over diode, positive', socket: 'Socket'
  };
  const withRecord = (e) => {
    const r = (e.record && LIB.overview.records[e.record]) || null;
    return { ...e, make: e.make || (r && r.make) || '', verified: r ? r.verified : null, ds: r ? datasheet(r) : null, alt: r && r.alternatives.length ? alternatives(r) : null, src: r ? r.sources : null };
  };
  const catalogueEntries = (c) => [
    ...c.mcb.ratings.map((m) => ({ key: `mcb.${m.rating_a}`, section: 'MCB', title: m.code, name: `${m.rating_a} A`, make: c.mcb.make, model: `${c.mcb.family}, ${c.mcb.poles}-pole, ${m.rating_a} A`, code: m.code, record: m.record })),
    { key: 'aux_contact', section: 'Auxiliary contact', title: c.aux_contact.ordering_code, name: c.aux_contact.model, make: c.aux_contact.make, model: c.aux_contact.model, code: c.aux_contact.ordering_code, record: c.aux_contact.record },
    ...c.terminal_blocks.map((b) => ({ key: `terminal_blocks.${b.type}`, section: 'Terminal block', title: b.ordering_code, name: b.type, make: b.make, model: b.type, code: b.ordering_code, record: b.record })),
    ...c.busbars.map((b) => ({ key: `busbars.${b.key}`, section: 'Busbar', title: b.tag || b.key, name: b.tag || b.key, make: '', model: firstLine(b.description), code: '', description: b.description, record: b.record }))
  ].map(withRecord);
  const catKv = (e) => `<dl class="kv"><dt>Catalogue</dt><dd>${esc(e.section)}</dd>${e.make ? `<dt>Make</dt><dd>${esc(e.make)}</dd>` : ''}<dt>${e.description ? 'Description' : 'Model'}</dt><dd style="white-space:pre-line">${esc(e.description || e.model)}</dd>${e.code ? `<dt>Ordering code</dt><dd class="mono">${esc(e.code)}</dd>` : ''}<dt>Datasheet record</dt><dd class="mono">${esc(e.record || '—')}</dd></dl>`;
  function cataloguesView(c) {
    const all = catalogueEntries(c), quality = hasDeviceDb() || all.some((e) => e.verified);
    const sel = all.find((e) => e.key === S.selectedCatalogue) || all[0];
    const data = (e) => (quality ? `<td style="white-space:nowrap">${e.verified ? verified(e.verified) : '<span class="muted">No record</span>'}</td>` : '');
    const tr = (e, cells) => `<tr class="clickable" tabindex="0" data-action="lib-select-cat" data-id="${esc(e.key)}" aria-selected="${sel.key === e.key}">${cells}${data(e)}</tr>`;
    const table = (title, lede, head, rows) => `<section style="margin-bottom:var(--space-5)"><h3>${title}</h3>${lede ? `<p class="muted small" style="margin:2px 0 0">${lede}</p>` : ''}
      <div class="table-wrap" style="margin-top:var(--space-2)"><table class="table"><thead><tr>${head.map((h) => `<th>${h}</th>`).join('')}${quality ? '<th>Data</th>' : ''}</tr></thead><tbody>${rows}</tbody></table></div></section>`;
    const of = (prefix) => all.filter((e) => e.key.startsWith(prefix));
    const kit = c.housekeeping;
    return `<div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(340px,400px);gap:var(--space-5);align-items:start;margin-top:var(--space-4)"><div>
      ${table('Miniature circuit breakers', `${esc(c.mcb.make)} ${esc(c.mcb.family)}, ${c.mcb.poles}-pole. The engine sizes each MCB and takes the code for its rating from here.`, ['Rating', 'Ordering code'],
        of('mcb.').map((e) => tr(e, `<td class="nowrap">${esc(e.name)}</td><td class="mono">${esc(e.code)}</td>`)).join(''))}
      ${table('Auxiliary alarm contact', '', ['Make and model', 'Ordering code'], of('aux_contact').map((e) => tr(e, `<td>${esc(e.make)} <span class="muted">${esc(e.model)}</span></td><td class="mono">${esc(e.code)}</td>`)).join(''))}
      ${table('Terminal blocks', '', ['Type', 'Make', 'Ordering code'], of('terminal_blocks.').map((e) => tr(e, `<td class="mono nowrap">${esc(e.name)}</td><td>${esc(e.make)}</td><td class="mono">${esc(e.code)}</td>`)).join(''))}
      ${table('Busbars', '', ['Tag', 'Description'], of('busbars.').map((e) => tr(e, `<td class="mono nowrap">${esc(e.name)}</td><td>${esc(e.model)}</td>`)).join(''))}
      ${table('Housekeeping kit', 'Each role is a part in the device list. Select one to open it there.', ['Role', 'Part ID', ''],
        kit.map((h) => `<tr ${h.in_library ? `class="clickable" tabindex="0" data-action="lib-goto-device" data-id="${esc(h.part_id)}"` : ''}><td>${esc(ROLES[h.role] || h.role)}</td><td class="mono">${esc(h.part_id)}</td><td class="muted">${esc(h.detail || '')}</td>${quality ? `<td style="white-space:nowrap">${LIB.overview.records[h.part_id] ? verified(LIB.overview.records[h.part_id].verified) : '<span class="muted">No record</span>'}</td>` : ''}</tr>`).join(''))}
      <p class="muted small">Standard enclosure: ${c.enclosure_u} U.</p></div>
      ${detail(sel, { title: esc(sel.title), sub: `${esc(sel.section)}${sel.make ? ` · ${esc(sel.make)}` : ''}`, kv: catKv(sel) })}</div>`;
  }
  ACTIONS['lib-select-cat'] = (el) => { S.selectedCatalogue = el.dataset.id; S.tab.libdetail = 'overview'; App.render(); };
  ACTIONS['lib-goto-device'] = (el) => { S.tab.libview = 'devices'; S.selectedDevice = el.dataset.id; S.tab.libdetail = 'overview'; App.render(); };

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
      <p class="muted small" style="margin-top:var(--space-3)">You can also double-click a .bomlib file in Windows to import it. ${L ? `Currently installed: ${esc(L.name)} ${esc(L.version)}.` : LIB.errors.overview && !LIB.offline ? 'The active library could not be read; see Installed versions.' : 'No library is installed yet.'}</p>`;
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
    if (LIB.errors.versions && !LIB.offline) return loadError('versions', 'The installed versions could not be read.');
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
