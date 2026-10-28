/* v0.2 Library editing: catalogues with brands, the device editor, alternatives as a comparison list,
   add device, CSV export and import, and the review of pending changes. Edits collect in a pending set;
   nothing reaches a project until the set is applied as a new local library version. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, select, pageHead, dialog, closeDialog, toast, go, verified, $, $$ } = App;
  const L = DB.library;
  const CAT = () => DB.catalogues;
  const catKeys = [['mcb', 'MCBs'], ['aux', 'Aux contacts'], ['tb', 'Terminal blocks'], ['bus', 'Busbars'], ['hk', 'Housekeeping']];
  const ctl = (html) => html.replace('class="input', 'class="ctl input');
  const nextLocal = () => `${L.versions.filter((v) => v.local).length ? L.version.split('+')[0] : L.version}+local.${L.versions.filter((v) => v.local).length + 1}`;

  /* ---------- Pending changes ---------- */
  const pend = (e) => {
    const i = DB.pending.findIndex((x) => x.label === e.label && x.area === e.area);
    if (i >= 0) { e.from = DB.pending[i].from; if (e.kind === 'changed' && e.from === e.to) DB.pending.splice(i, 1); else DB.pending[i] = e; } else DB.pending.push(e);
  };
  function pendingBar() {
    const n = DB.pending.length; if (!n) return '';
    return `<div class="savebar savebar--pending" role="region" aria-label="Pending library changes"><span class="savebar-msg"><span class="dot dot--warn" aria-hidden="true"></span><b>${n} pending ${n === 1 ? 'change' : 'changes'}</b> · not applied yet. Projects keep using ${esc(L.version)} until you apply them.</span><span class="sp"></span>
      <button class="btn btn--secondary" data-action="pending-discard">Discard all</button><a class="btn btn--primary" href="#/library/review">Review and apply…</a></div>`;
  }
  const refreshPending = () => { $$('.savebar--pending').forEach((x) => x.remove()); const m = $('#main'); if (m && /^#\/library\/?$/.test(location.hash)) m.insertAdjacentHTML('beforeend', pendingBar()); };
  App.pendingBar = pendingBar;
  ACTIONS['pending-discard'] = () => dialog({ title: 'Discard all pending changes?', body: `<p>${DB.pending.length} pending changes are removed. The library stays at ${esc(L.version)}.</p>`, actions: '<button class="btn btn--secondary" data-action="close">Keep them</button><button class="btn btn--danger" data-action="pending-discard-do">Discard all</button>' });
  ACTIONS['pending-discard-do'] = () => { const was = DB.pending.slice(); DB.pending = []; closeDialog(); App.render(); toast('Pending changes discarded', 'trash', () => { DB.pending = was; App.render(); }); };

  /* ---------- Route ---------- */
  const base = SCREENS.library;
  SCREENS.library = () => {
    const { b, c } = App.route();
    if (b === 'device') return deviceEditor(c);
    if (b === 'review') return reviewScreen();
    if (b === 'csv') return csvScreen();
    return base();
  };

  /* ---------- Catalogues ---------- */
  App.catalogues = () => {
    const key = S.tab.cat || 'mcb'; const c = CAT()[key];
    const sw = `<div class="segmented" role="radiogroup" aria-label="Catalogue">${catKeys.map(([k, t]) => `<label><input type="radio" name="cat" value="${k}" data-action="cat-pick" ${k === key ? 'checked' : ''}><span>${t}</span></label>`).join('')}</div>`;
    const head = `<div class="row" style="justify-content:space-between;margin-bottom:var(--space-3);flex-wrap:wrap">${sw}</div>
      <h3>${esc(c.title)}</h3><p class="muted small" style="margin:var(--space-1) 0 var(--space-4);max-width:72ch">${esc(c.blurb)}</p>`;
    return head + (key === 'hk' ? housekeeping(c) : brandView(key, c));
  };
  ACTIONS['cat-pick'] = (el) => { S.tab.cat = el.value; S.tab.brand = null; App.render(); const n = $('[name="cat"]:checked'); n && n.focus(); };

  function brandView(key, c) {
    const cur = c.brands.find((b) => b.id === S.tab.brand) || c.brands.find((b) => b.id === c.active) || c.brands[0];
    const isDef = cur.id === c.active;
    const brandTabs = tabs('brand', c.brands.map((b) => [b.id, b.name, b.id === c.active ? '<span class="badge badge--info" style="margin-left:8px">Default</span>' : '']), cur.id, 'Brands');
    return `${brandTabs}
      <div class="row" style="margin:var(--space-3) 0;gap:var(--space-4);flex-wrap:wrap"><span class="muted small">${esc(cur.detail)}</span><span class="sp" style="flex:1"></span>
        ${isDef ? '<span class="muted small">New projects start with this brand. A project can choose another on its overview page.</span>' : `<button class="btn btn--secondary btn--sm" data-action="brand-default" data-cat="${key}" data-id="${cur.id}">Make ${esc(cur.name)} the default brand</button>`}
        <button class="btn btn--ghost btn--sm" data-action="brand-add" data-cat="${key}">${icon('plus')}Add brand…</button></div>
      <div role="tabpanel" aria-labelledby="tab-brand-${cur.id}"><div class="table-wrap" style="max-width:760px"><table class="table"><thead><tr>${c.cols.map(([k, t, u]) => `<th ${k === 'rating' ? 'style="width:130px"' : ''}>${t}${u ? ` (${u})` : ''}</th>`).join('')}<th style="width:40px"><span class="sr-only">Actions</span></th></tr></thead>
        <tbody>${cur.rows.map((r, i) => `<tr>${r.map((v, j) => `<td>${ctl(`<input class="input ${c.cols[j][0] === 'code' || j === 1 ? 'input--mono' : ''}" id="cat-${key}-${cur.id}-${i}-${j}" aria-label="${esc(c.cols[j][1])}, row ${i + 1}" value="${esc(v)}" data-old="${esc(v)}" data-lib-edit="${esc(`${c.title} · ${cur.name} · ${r[0] || 'new row'} · ${c.cols[j][1].toLowerCase()}`)}">`)}</td>`).join('')}
          <td><button class="btn btn--ghost btn--icon btn--sm" data-action="cat-row-remove" data-cat="${key}" data-brand="${cur.id}" data-i="${i}" aria-label="Remove row ${i + 1}">${icon('trash')}</button></td></tr>`).join('')}</tbody></table>
        <div class="table-foot"><span>${cur.rows.length} ${cur.rows.length === 1 ? 'entry' : 'entries'}</span><button class="btn btn--ghost btn--sm" data-action="cat-row-add" data-cat="${key}" data-brand="${cur.id}">${icon('plus')}Add ${key === 'mcb' ? 'rating' : 'row'}</button></div></div></div>`;
  }
  document.addEventListener('change', (e) => {
    const t = e.target; if (!t.dataset || !t.dataset.libEdit) return;
    pend({ area: 'Catalogue', label: t.dataset.libEdit, kind: 'changed', from: t.dataset.old, to: t.value }); t.dataset.old = t.dataset.old; refreshPending();
  });
  ACTIONS['brand-default'] = (el) => { const c = CAT()[el.dataset.cat]; const from = c.brands.find((b) => b.id === c.active).name; c.active = el.dataset.id; const to = c.brands.find((b) => b.id === c.active).name; pend({ area: 'Catalogue', label: `${c.title} · default brand`, kind: 'changed', from, to }); App.render(); toast(`${to} is the default for ${c.title}`); };
  ACTIONS['brand-add'] = (el) => dialog({ title: `Add a brand to ${CAT()[el.dataset.cat].title}`, body: `<div class="stack">${field('Brand name', input('nb-name', '', { placeholder: 'e.g. Eaton' }))}${field('Detail', input('nb-detail', '', { placeholder: 'e.g. 2-pole, C curve' }), 'Shown under the brand name.')}
    <label class="check"><input type="checkbox" id="nb-copy" checked> Start with a copy of the current brand's rows, so you only change the ordering codes</label></div>`, actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="brand-add-do" data-cat="${el.dataset.cat}">Add brand</button>` });
  ACTIONS['brand-add-do'] = (el) => {
    const name = $('#nb-name').value.trim(); if (!name) { $('#nb-name').setAttribute('aria-invalid', 'true'); $('#nb-name').focus(); return; }
    const c = CAT()[el.dataset.cat]; const cur = c.brands.find((b) => b.id === (S.tab.brand || c.active)) || c.brands[0];
    c.brands.push({ id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-'), name, detail: $('#nb-detail').value.trim(), rows: $('#nb-copy').checked ? cur.rows.map((r) => r.map((v, j) => (j === 1 ? '' : v))) : [] });
    pend({ area: 'Catalogue', label: `${c.title} · brand ${name}`, kind: 'added', from: '', to: `${c.brands[c.brands.length - 1].rows.length} rows` }); S.tab.brand = c.brands[c.brands.length - 1].id; closeDialog(); App.render(); toast(`Added ${name}. Fill in its ordering codes.`);
  };
  ACTIONS['cat-row-add'] = (el) => { const c = CAT()[el.dataset.cat]; const b = c.brands.find((x) => x.id === el.dataset.brand); b.rows.push(c.cols.map(() => '')); pend({ area: 'Catalogue', label: `${c.title} · ${b.name} · new row ${b.rows.length}`, kind: 'added', from: '', to: 'empty row' }); App.render(); const n = $(`#cat-${el.dataset.cat}-${b.id}-${b.rows.length - 1}-0`); n && n.focus(); };
  ACTIONS['cat-row-remove'] = (el) => { const c = CAT()[el.dataset.cat]; const b = c.brands.find((x) => x.id === el.dataset.brand); const [r] = b.rows.splice(+el.dataset.i, 1); pend({ area: 'Catalogue', label: `${c.title} · ${b.name} · ${r[0] || 'row'}`, kind: 'removed', from: r.join(' · '), to: '' }); App.render(); toast(`Removed ${r[0] || 'a row'}`, 'trash', () => { b.rows.splice(+el.dataset.i, 0, r); DB.pending.pop(); App.render(); }); };

  function housekeeping(c) {
    return `<div class="table-wrap" style="max-width:760px"><table class="table"><thead><tr><th style="width:200px">Role</th><th>Part</th><th style="width:110px"><span class="sr-only">Actions</span></th></tr></thead><tbody>
      ${c.roles.map(([role, part], i) => { const d = DB.devices.find((x) => x.id === part); return `<tr><td>${esc(role)}</td><td><span class="mono">${esc(part)}</span><span class="cell-sub">${d ? esc(d.make + ' ' + d.model) : '<span style="color:var(--color-warning)">Not in this library</span>'}</span></td><td style="text-align:right"><button class="btn btn--secondary btn--sm" data-action="hk-change" data-i="${i}">Change…</button></td></tr>`; }).join('')}</tbody></table>
      <div class="table-foot"><span>${c.roles.length} roles</span><span>Each role names a library part; edit the part itself under Devices.</span></div></div>`;
  }
  ACTIONS['hk-change'] = (el) => {
    const c = CAT().hk; const [role, part] = c.roles[+el.dataset.i]; const opts = DB.devices.filter((d) => ['fan', 'lamp', 'thermostat', 'vent_filter', 'relay', 'component', 'diode', 'socket'].includes(d.cat) || d.id === part).slice(0, 14);
    dialog({ title: `Change the ${role.toLowerCase()}`, body: `<div class="stack">${field('Part', select('hk-part', opts.map((d) => [d.id, `${d.id} · ${d.make} ${d.model}`]), part), 'Parts are picked from the active library.')}</div>`, actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="hk-do" data-i="${el.dataset.i}">Change</button>` });
  };
  ACTIONS['hk-do'] = (el) => { const c = CAT().hk; const r = c.roles[+el.dataset.i]; const to = $('#hk-part').value; pend({ area: 'Catalogue', label: `Housekeeping · ${r[0]}`, kind: 'changed', from: r[1], to }); r[1] = to; closeDialog(); App.render(); };

  /* ---------- Alternatives: one list per device, for comparing ---------- */
  const delta = (v, base, unit) => { if (base == null || v === base) return ''; const d = v - base; return `<span class="delta ${d > 0 ? 'up' : 'down'}" title="${d > 0 ? 'More' : 'Less'} than ${esc(base)}${unit}">${d > 0 ? '+' : '−'}${Math.abs(d)}</span>`; };
  App.altTable = (d, compact) => {
    const rows = DB.altList(d); const b = rows[0];
    const head = compact
      ? '<th>Part</th><th class="num">Power</th><th class="num">Inrush</th><th style="width:64px"><span class="sr-only">Actions</span></th>'
      : '<th style="width:48px">Tier</th><th>Part</th><th>Make</th><th class="num">Power (W)</th><th class="num">Inrush (A)</th><th>Ports</th><th class="num">Height</th><th>Data</th><th style="width:90px"><span class="sr-only">Actions</span></th>';
    const use = (r) => (r.self ? '' : `<button class="btn btn--secondary btn--sm" data-action="use-instead" data-from="${esc(d.id)}" data-to="${esc(r.id)}" aria-label="Use ${esc(r.id)} instead of ${esc(d.id)}">Use…</button>`);
    const body = rows.map((r) => compact
      ? `<tr ${r.self ? 'class="is-self"' : ''}><td><span class="mono">${esc(r.id)}</span><span class="cell-sub">${r.self ? 'This device' : esc(`${r.tier} · ${r.make}`)}</span></td><td class="num">${r.w} W${r.self ? '' : `<span class="cell-sub">${delta(r.w, b.w, ' W')}</span>`}</td><td class="num">${r.inrush} A${r.self ? '' : `<span class="cell-sub">${delta(r.inrush, b.inrush, ' A')}</span>`}</td><td style="text-align:right">${use(r)}</td></tr>`
      : `<tr ${r.self ? 'class="is-self"' : ''}><td>${r.self ? '' : esc(r.tier)}</td><td><span class="mono">${esc(r.id)}</span><span class="cell-sub">${r.self ? 'This device' : esc(r.model)}</span></td><td>${esc(r.make)}</td><td class="num">${r.w} ${r.self ? '' : delta(r.w, b.w, ' W')}</td><td class="num">${r.inrush} ${r.self ? '' : delta(r.inrush, b.inrush, ' A')}</td><td>${esc(r.ports)}</td><td class="num">${r.h} U ${r.self ? '' : delta(r.h, b.h, ' U')}</td><td>${verified(r.verified)}</td><td style="text-align:right">${use(r)}</td></tr>`).join('');
    return `${compact ? '' : `<p class="muted small" style="max-width:68ch;margin-bottom:var(--space-3)">Every row is a library part. The differences from <span class="mono">${esc(d.id)}</span> are marked, so you can compare before you swap one in.</p>`}
      <div class="table-wrap alt-table"><table class="table"><caption class="sr-only">${esc(d.id)} and its alternatives</caption><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>
      <div class="table-foot"><span>${rows.length - 1} alternatives${compact ? '' : ` · group <span class="mono">${esc(DB.altGroup(d))}</span>`}</span>${compact ? `<a href="#/library/device/${esc(d.id)}">Compare in full</a>` : ''}</div></div>`;
  };
  ACTIONS['use-instead'] = (el) => {
    const from = el.dataset.from, to = el.dataset.to; const rows = DB.equipment.filter((e) => e.part === from);
    const sub = App.curSub();
    dialog({ title: `Use ${esc(to)} instead of ${esc(from)}`, body: `<div class="stack">${!sub ? banner('warn', 'Open a substation first. An alternative is used inside a substation, on its equipment rows.')
      : rows.length ? `<p>Rows in <b>${esc(sub.name)}</b> that use <span class="mono">${esc(from)}</span>:</p>${rows.map((r, i) => `<label class="check"><input type="checkbox" name="ui-row" value="${esc(r.id)}" checked> ${esc(r.label)} <span class="muted">· ${r.count > 1 ? r.count + ' per side' : r.redundant ? 'A + B' : '1'}</span></label>`).join('')}
        ${banner('info', 'Only the part changes. The layout, MCB sizes and BOM are worked out again from the new part\'s data, and pins stay where they are.')}`
      : `<p>No equipment in <b>${esc(sub.name)}</b> uses <span class="mono">${esc(from)}</span>, so there is nothing to change. Add <span class="mono">${esc(to)}</span> from Network › Add device.</p>`}</div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="use-instead-do" data-to="${esc(to)}" ${sub && rows.length ? '' : 'disabled'}>Use ${esc(to)}</button>` });
  };
  ACTIONS['use-instead-do'] = (el) => { const n = $$('input[name="ui-row"]:checked').length; const to = el.dataset.to; closeDialog(); go('#/network'); setTimeout(() => { S.dirty = true; S.changed.add('eq-part'); App.render(); toast(`${to} set on ${n} ${n === 1 ? 'row' : 'rows'}. Save to keep it.`, 'check'); }, 0); };

  /* ---------- Add device ---------- */
  ACTIONS['add-device'] = () => dialog({ title: 'Add a device', body: `<div class="stack">
    ${field('Start from', select('ad-from', [['', 'A blank device'], ...DB.devices.slice(0, 12).map((d) => [d.id, `A copy of ${d.id} (${d.make} ${d.model})`])], ''), 'A copy keeps the electrical data, ports and parts, so you only change what differs.')}
    <div class="form form--2">${field('Part ID', input('ad-id', '', { mono: true, placeholder: 'e.g. SEL-2730M-EXT-B' }), 'Unique in the library. It cannot change once projects use it.')}${field('Category', select('ad-cat', [...new Set(DB.devices.map((d) => d.cat))].map((c) => [c, App.libParts.catName(c)]), 'network_switch'))}
    ${field('Make', input('ad-make', ''))}${field('Model', input('ad-model', ''))}</div></div>`,
    actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="add-device-do">Create and edit</button>' });
  ACTIONS['add-device-do'] = () => {
    const id = $('#ad-id').value.trim();
    if (!id) { $('#ad-id').setAttribute('aria-invalid', 'true'); $('#ad-id').focus(); return; }
    if (DB.devices.some((d) => d.id.toLowerCase() === id.toLowerCase())) { toast(`${id} is already in the library. Choose another part ID.`, 'error'); $('#ad-id').setAttribute('aria-invalid', 'true'); $('#ad-id').focus(); return; }
    const src = DB.devices.find((d) => d.id === $('#ad-from').value) || {};
    S.newDev = Object.assign({}, src, { id, make: $('#ad-make').value || src.make || '', model: $('#ad-model').value || src.model || '', cat: $('#ad-cat').value, verified: 'unverified', alt: null, isNew: true });
    closeDialog(); S.tab.devEdit = 'identity'; S.changed.add('new'); S.dirty = true; go('#/library/device/' + encodeURIComponent(id));
  };

  /* ---------- Device editor ---------- */
  const edTabs = [['identity', 'Identity'], ['electrical', 'Electrical'], ['ports', 'Ports and mounting'], ['parts', 'Parts it brings'], ['datasheet', 'Datasheet'], ['alternatives', 'Alternatives']];
  const unitInput = (id, v, u, o) => `<div class="input-affix">${input(id, v, Object.assign({ num: true, mono: true }, o))}<span class="affix">${u}</span></div>`;
  function deviceEditor(idRaw) {
    const id = decodeURIComponent(idRaw || ''); const d = (S.newDev && S.newDev.id === id) ? S.newDev : DB.devices.find((x) => x.id === id);
    if (!d) return `<div class="page">${pageHead('Device not found', `There is no part <span class="mono">${esc(id)}</span> in ${esc(L.name)} ${esc(L.version)}.`, '<a class="btn btn--secondary" href="#/library">Back to the library</a>')}</div>`;
    const t = S.tab.devEdit && edTabs.some(([k]) => k === S.tab.devEdit) ? S.tab.devEdit : 'identity'; const ds = d.ds || {};
    const cats = [...new Set(DB.devices.map((x) => x.cat))].map((c) => [c, App.libParts.catName(c)]);
    const body = {
      identity: () => `<div class="form form--2">${field('Part ID', input('de-id', d.id, { mono: true, readonly: !d.isNew }), d.isNew ? 'Unique in the library. It cannot change once projects use it.' : 'Fixed: projects refer to it. To rename, add a copy and retire this one.')}
        ${field('Category', select('de-cat', cats, d.cat))}${field('Make', input('de-make', d.make))}${field('Model', input('de-model', d.model))}
        <div class="span-2">${field('Ordering code', input('de-code', d.code || '', { mono: true }), 'Printed in the BOM. Leave empty if the manufacturer gives none.')}</div>
        <div class="span-2">${field('Description in the BOM', `<textarea class="input input--mono" id="de-desc" rows="3" data-dirty="1" placeholder="e.g. LAN-{side} Industrial Ethernet switch ({level})" style="height:auto;padding:8px 10px">${esc(d.desc || '')}</textarea>`, 'Placeholders in braces, such as <span class="mono">{side}</span> and <span class="mono">{level}</span>, are filled in by the engine.')}</div>
        ${field('Tag type', input('de-tag', d.tagType || '', { mono: true }), 'First part of the generated tag, e.g. ESW.')}${field('Purdue level', select('de-level', [['', 'Not set'], ['L1', 'L1'], ['L2', 'L2'], ['EXT', 'External']], d.level || ''))}</div>`,
      electrical: () => `<div class="form form--3">${field('Supply type', select('de-sup', [['dc', 'DC'], ['ac', 'AC'], ['both', 'AC or DC']], /VAC/.test(d.supply || '') ? 'ac' : 'dc'))}${field('Voltage', unitInput('de-v', (d.supply || '125').replace(/\D+.*$/, '') || '125', 'V'))}${field('Power supplies', select('de-ps', [['0', 'None'], ['1', 'Single feed'], ['2', 'Dual feed (2 supplies)']], '2'))}
        ${field('Rated power', unitInput('de-w', d.w || '', 'W'), 'What the power sheet uses.')}${field('Inrush current', unitInput('de-inrush', d.inrush || Math.round((d.w || 0) * 0.35) || '', 'A'), 'The branch MCB is sized to clear it.')}${field('Load type', select('de-load', [['', 'Not set'], ['constant', 'Constant'], ['peak', 'Peak']], ''))}
        ${field('Minimum branch MCB', unitInput('de-mcb', '2', 'A'))}${field('HWIO points', input('de-hwio', d.hwio || '0', { num: true, mono: true }), 'Hardwired points one unit gives.')}${field('Digital inputs', input('de-di', '0', { num: true, mono: true }))}
        <div class="field"><span class="label">Options</span><label class="switch"><input type="checkbox" data-dirty="1" ${/alarm/.test(d.mcb || '') ? 'checked' : ''}>Alarm on the branch MCB</label><label class="switch" style="margin-top:8px"><input type="checkbox" data-dirty="1">Leave out of the power total</label></div></div>`,
      ports: () => `<div class="form form--3" style="margin-bottom:var(--space-4)">${field('Height', unitInput('de-h', d.h == null ? '1' : d.h, 'U'), '0 for a DIN-rail part; empty if not known yet.')}${field('Fibre cores', input('de-cores', '', { num: true, mono: true }), 'For patch panels.')}</div>
        <h3>Port groups</h3><div class="table-wrap" style="max-width:760px;margin-top:var(--space-2)"><table class="table"><thead><tr><th class="num" style="width:80px">Count</th><th style="width:100px">Speed</th><th style="width:100px">Media</th><th style="width:130px">Kind</th><th>Used for</th><th style="width:40px"><span class="sr-only">Actions</span></th></tr></thead><tbody>
        ${[[24, '100M', 'MM', 'fixed', 'any'], [4, '1G', '', 'sfp_slot', 'uplink']].map(([n, sp, m, k, u], i) => `<tr><td>${ctl(input('pg-n' + i, n, { num: true, mono: true }))}</td><td>${select('pg-s' + i, ['100M', '1G', '10G'], sp, { cls: 'ctl' })}</td><td>${select('pg-m' + i, [['', '—'], 'MM', 'SM', 'RJ45'], m, { cls: 'ctl' })}</td><td>${select('pg-k' + i, [['fixed', 'Fixed'], ['sfp_slot', 'SFP slot']], k, { cls: 'ctl' })}</td><td>${select('pg-u' + i, [['any', 'Anything'], ['uplink', 'Uplinks only'], ['field', 'Field devices']], u, { cls: 'ctl' })}</td><td><button class="btn btn--ghost btn--icon btn--sm" data-action="toast" data-m="Removed port group" aria-label="Remove port group ${i + 1}">${icon('trash')}</button></td></tr>`).join('')}</tbody></table>
        <div class="table-foot"><span>28 ports in total</span><button class="btn btn--ghost btn--sm" data-action="toast" data-m="Added a port group">${icon('plus')}Add port group</button></div></div>`,
      parts: () => `<p class="muted small" style="max-width:68ch;margin-bottom:var(--space-3)">Parts that come with each unit of this device. They appear as extra rows in the BOM.</p>
        ${['Child parts', 'Terminals', 'Loose items'].map((h, k) => `<section class="section" style="padding-top:var(--space-3)"><div class="row" style="justify-content:space-between"><h3>${h}</h3><button class="btn btn--ghost btn--sm" data-action="toast" data-m="Row added">${icon('plus')}Add</button></div>
          <div class="table-wrap" style="max-width:760px;margin-top:6px"><table class="table"><thead><tr>${[['Part', 'Qty'], ['Strip', 'Block', 'Count', 'Per'], ['Part', 'Qty', 'Tag']][k].map((c) => `<th>${c}</th>`).join('')}<th style="width:40px"><span class="sr-only">Actions</span></th></tr></thead><tbody>
          ${k === 1 && d.cat === 'gateway' ? `<tr><td>${ctl(input('t-s', 'X1', { mono: true }))}</td><td>${ctl(input('t-b', 'UT-2.5-MT', { mono: true }))}</td><td>${ctl(input('t-c', '2', { num: true, mono: true }))}</td><td>${select('t-p', [['unit', 'unit'], ['serial_port', 'serial port']], 'unit', { cls: 'ctl' })}</td><td><button class="btn btn--ghost btn--icon btn--sm" aria-label="Remove row">${icon('trash')}</button></td></tr>` : `<tr class="empty-row"><td colspan="${[2, 4, 3][k] + 1}">None. Add one if each unit brings it.</td></tr>`}</tbody></table></div></section>`).join('')}`,
      datasheet: () => `<div class="form form--2">${field('Supply range', input('ds-sup', ds.supply || ''))}${field('Operating temperature', input('ds-temp', ds.temp || ''))}${field('Typical power', unitInput('ds-typ', (ds.typical || '').replace(/\D+$/, ''), 'W'))}${field('Maximum power', unitInput('ds-max', (ds.max || '').replace(/\D+$/, ''), 'W'))}
        <div class="span-2">${field('Ports', input('ds-ports', ds.ports || ''))}</div>${field('Dimensions', input('ds-dim', ds.dims || ''))}${field('Weight', input('ds-wt', ds.weight || ''))}${field('Certifications', input('ds-cert', ds.certs || ''))}${field('Datasheet link', input('ds-url', ds.url || '', { mono: true }))}
        ${field('Data quality', select('ds-q', [['confirmed', 'Confirmed'], ['partial', 'Partial'], ['unverified', 'Unverified']], d.verified), 'Confirmed means a person checked every value against the manufacturer\'s datasheet.')}<div class="span-2">${field('Sources', `<textarea class="input" id="ds-src" rows="3" data-dirty="1" style="height:auto;padding:8px 10px">${esc((d.src || []).join('\n'))}</textarea>`, 'One source per line.')}</div></div>`,
      alternatives: () => `<div class="form" style="margin-bottom:var(--space-4);max-width:520px">${field('Alternative group', input('de-grp', DB.altGroup(d) || '', { mono: true, placeholder: 'Not in a group' }), 'Devices with the same group key are alternatives of each other. The key is what links them in CSV files too.')}</div>
        ${d.alt ? App.altTable(d, false) : '<div class="empty"><b>No alternatives yet.</b><div class="muted small">Add a copy of this device under another make, then edit what differs.</div></div>'}
        <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary" data-action="add-alt" data-id="${esc(d.id)}">${icon('plus')}Add alternative…</button></div>`
    }[t]();
    const used = !d.isNew && DB.equipment.some((e) => e.part === d.id);
    return `<div class="page">${pageHead(esc(d.id), [`${d.make} ${d.model}`.trim(), d.isNew ? 'new device' : ''].filter(Boolean).map(esc).join(' · '),
      `<button class="btn btn--secondary" data-action="add-alt" data-id="${esc(d.id)}">${icon('copy')}Copy as alternative…</button>${d.isNew ? '' : `<button class="btn btn--danger" data-action="delete-device" data-id="${esc(d.id)}">${icon('trash')}Delete…</button>`}`,
      `<a href="#/library">Library</a>${icon('chevr')}<span>${esc(d.id)}</span>`)}
      ${used ? `<div style="margin-bottom:var(--space-4)">${banner('info', `<b>This device is in use.</b> GIS Substation 01 has ${DB.equipment.filter((e) => e.part === d.id).length} equipment row using it. Projects keep the library version they record, so an edit reaches a project only when it records the version you apply.`)}</div>` : ''}
      ${tabs('devEdit', edTabs, t, 'Device sections')}<div role="tabpanel" aria-labelledby="tab-devEdit-${t}" style="margin-top:var(--space-4)">${body}</div></div>`;
  }
  ACTIONS['add-alt'] = (el) => dialog({ title: `Copy ${esc(el.dataset.id)} as an alternative`, body: `<div class="stack"><p class="muted small">The copy joins this device's alternative group. Edit what differs afterwards.</p><div class="form form--2">${field('Part ID', input('aa-id', '', { mono: true, placeholder: el.dataset.id + '-ALT' }))}${field('Tier', select('aa-tier', ['Low', 'Mid', 'High'], 'Mid'))}${field('Make', input('aa-make', ''))}${field('Model', input('aa-model', ''))}</div></div>`, actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="add-alt-do" data-id="${esc(el.dataset.id)}">Create and edit</button>` });
  ACTIONS['add-alt-do'] = (el) => { const id = $('#aa-id').value.trim(); if (!id) { $('#aa-id').setAttribute('aria-invalid', 'true'); $('#aa-id').focus(); return; } const src = DB.devices.find((d) => d.id === el.dataset.id); S.newDev = Object.assign({}, src, { id, make: $('#aa-make').value || src.make, model: $('#aa-model').value || src.model, verified: 'unverified', isNew: true }); closeDialog(); S.tab.devEdit = 'identity'; S.changed.add('new'); S.dirty = true; go('#/library/device/' + encodeURIComponent(id)); };
  ACTIONS['delete-device'] = (el) => {
    const used = DB.equipment.filter((e) => e.part === el.dataset.id).length;
    dialog({ title: `Delete ${esc(el.dataset.id)}?`, body: `<div class="stack">${used ? banner('bad', `<b>GIS Substation 01 uses it in ${used} equipment row.</b> After you apply this change the substation will report an error until you pick another part.`) : '<p>No equipment in the open project uses it.</p>'}<p>The device and its alternatives link are removed from the library when you apply the pending change. You can still cancel it before then.</p></div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--danger" data-action="delete-device-do" data-id="${esc(el.dataset.id)}">${icon('trash')}Delete device</button>` });
  };
  ACTIONS['delete-device-do'] = (el) => { pend({ area: 'Device', label: el.dataset.id, kind: 'removed', from: el.dataset.id, to: '' }); closeDialog(); App.clearEdits(); go('#/library'); toast(`${el.dataset.id} will be removed when you apply the changes`, 'trash'); };

  /* Saving a device puts one pending entry per edited field. */
  const baseSave = ACTIONS['save-all'];
  ACTIONS['save-all'] = () => {
    if (!/^#\/library\/device\//.test(location.hash)) return baseSave();
    if (S.invalid.size) return;
    const id = decodeURIComponent(location.hash.split('/')[3] || ''); const labels = [...S.changed].map((k) => { const l = document.querySelector(`label[for="${k}"]`); return l ? l.textContent.trim() : null; }).filter(Boolean);
    if (S.newDev && S.newDev.id === id) { pend({ area: 'Device', label: id, kind: 'added', from: '', to: `${S.newDev.make} ${S.newDev.model}` }); DB.devices.push(S.newDev); S.newDev = null; }
    else (labels.length ? labels : ['fields']).forEach((l) => pend({ area: 'Device', label: `${id} · ${l.toLowerCase()}`, kind: 'changed', from: 'saved value', to: 'edited value' }));
    App.clearEdits(); toast(`${id} saved to pending changes`); go('#/library');
  };

  /* ---------- Review and apply ---------- */
  function reviewScreen() {
    const P = DB.pending; const g = (k) => P.filter((x) => x.kind === k); const ver = nextLocal();
    const grp = (title, items, kind) => items.length ? `<details open><summary>${icon('chevr', 'chev')}${esc(title)} ${badge(kind, items.length)}</summary><div class="items">${items.map((x) => `<div><span class="mono">${esc(x.label)}</span><span class="muted">${x.kind === 'changed' ? `${esc(x.from)} → ${esc(x.to)}` : esc(x.to || x.from)}</span></div>`).join('')}</div></details>` : '';
    return `<div class="page">${pageHead('Review library changes', `These edits become a new local version of ${esc(L.name)}. Nothing changes in any project until you apply them and a project records the new version.`, '', `<a href="#/library">Library</a>${icon('chevr')}<span>Review changes</span>`)}
      ${P.length ? `<div class="stack" style="max-width:920px"><section><h3>What changes</h3><div class="row" style="margin:var(--space-2) 0 var(--space-3)">${badge('ok', `${g('added').length} added`)}${badge('info', `${g('changed').length} changed`)}${badge('bad', `${g('removed').length} removed`)}</div>
        <div class="diff-list table-wrap" style="padding:0 var(--space-4)">${grp('Added', g('added'), 'ok')}${grp('Changed', g('changed'), 'info')}${grp('Removed', g('removed'), 'bad')}</div></section>
        <section><h3>New version</h3><dl class="kv" style="margin-top:var(--space-2);grid-template-columns:150px 1fr"><dt>Now active</dt><dd class="mono">${esc(L.name)} ${esc(L.version)}</dd><dt>Will become</dt><dd class="mono">${esc(L.name)} ${esc(ver)}</dd><dt>Kept</dt><dd>${esc(L.version)} stays installed under Installed versions, so you can go back.</dd></dl>
        <div class="form" style="margin-top:var(--space-3);max-width:520px">${field('Note', input('rv-note', 'Local edits'), 'Shown next to the version.')}</div></section>
        <div class="actionbar"><button class="btn btn--primary" data-action="apply-pending">${icon('check')}Apply and activate ${esc(ver)}</button><a class="btn btn--secondary" href="#/library">Back to the library</a></div></div>`
      : `<div class="empty" style="max-width:640px"><h3>Nothing to review</h3><p>Edits you save appear here before they are applied.</p><a class="btn btn--secondary" href="#/library">Back to the library</a></div>`}</div>`;
  }
  ACTIONS['apply-pending'] = () => {
    const note = ($('#rv-note') && $('#rv-note').value) || 'Local edits'; const v = nextLocal(); const n = DB.pending.length;
    L.versions.forEach((x) => { x.active = false; }); L.versions.unshift({ v, date: '2026-10-28', active: true, local: true, notes: `${note} (${n} changes)`, projects: 0 }); L.version = v; DB.pending = []; S.applied = v;
    App.render(); go('#/library'); toast(`${L.name} ${v} is active`, 'check');
  };
  ACTIONS.goto = (el) => { App.closeMenu(); go(el.dataset.to); };
  ACTIONS['lib-import-menu'] = (el) => App.openMenu(el, [{ icon: 'pkg', label: 'Update package (.bomlib)…', action: 'goto', data: { to: '#/library/import' } }, { icon: 'file', label: 'Spreadsheet (CSV)…', action: 'goto', data: { to: '#/library/csv' } }]);

  /* ---------- Export ---------- */
  ACTIONS['lib-export'] = () => dialog({ title: 'Export the library', body: `<div class="stack">
    <div class="stack" style="gap:8px"><label class="check"><input type="radio" name="ex-fmt" value="csv" checked> <span><b>Spreadsheet (CSV)</b><span class="small muted" style="display:block">For editing in Excel. One file per table, opens with the right accents and symbols.</span></span></label>
      <label class="check"><input type="radio" name="ex-fmt" value="bomlib"> <span><b>Backup package (.bomlib)</b><span class="small muted" style="display:block">A complete copy of this version, to keep or to give a colleague as an update.</span></span></label></div>
    <div id="ex-csv"><span class="label" style="display:block;margin-bottom:4px">Include</span><div class="stack" style="gap:6px"><label class="check"><input type="checkbox" checked> Devices <span class="muted">(${DB.devices.length} rows)</span></label><label class="check"><input type="checkbox" checked> Alternatives <span class="muted">(linked by the alt_group column)</span></label><label class="check"><input type="checkbox" checked> Catalogues <span class="muted">(MCBs, aux contacts, terminal blocks, busbars, housekeeping)</span></label></div>
      <p class="muted small" style="margin-top:var(--space-2)">Keep the <span class="mono">alt_group</span> and <span class="mono">part_id</span> columns as they are when you edit: they link the rows.</p></div>
    ${field('Save to', '<div class="row" style="flex-wrap:nowrap">' + input('ex-dir', 'D:\\Exports\\psa-devices-' + L.version, { mono: true }) + '<button class="btn btn--secondary">Browse…</button></div>')}</div>`,
    actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="lib-export-do">Export</button>' });
  document.addEventListener('change', (e) => { if (e.target.name === 'ex-fmt') { const b = $('#ex-csv'); if (b) b.hidden = e.target.value !== 'csv'; } });
  ACTIONS['lib-export-do'] = () => { const f = $('input[name="ex-fmt"]:checked').value; closeDialog(); toast(f === 'csv' ? 'Exported 3 CSV files to D:\\Exports' : `Exported psa-devices-${L.version}.bomlib`); };

  /* ---------- CSV import with a review step ---------- */
  function csvScreen() {
    const sc = DB.csvScenario; const st = S.csvStep || 'choose';
    const crumbs = `<a href="#/library">Library</a>${icon('chevr')}<span>Import CSV</span>`;
    const head = pageHead('Import a spreadsheet', 'Edit the exported CSV files in Excel, then bring them back. The file is checked before anything is added, and what you accept goes to pending changes, not straight into the library.', '', crumbs);
    if (st === 'choose') return `<div class="page">${head}<div class="drop" data-action="csv-pick" tabindex="0" role="button" aria-label="Choose a CSV file">${icon('file', 'i--lg')}<h3 style="margin:8px 0 2px">Drop a .csv file here</h3><p>Or choose the devices file you exported. Alternatives and catalogues files are matched by their column names.</p><button class="btn btn--primary" data-action="csv-pick">${icon('folder')}Choose file…</button></div>
      <p class="muted small" style="margin-top:var(--space-3);max-width:68ch">Part IDs must stay unique. Devices with the same <span class="mono">alt_group</span> are alternatives of each other. Leave a cell empty to leave that value unset.</p></div>`;
    if (st === 'done') return `<div class="page">${head}${banner('ok', `<b>${sc.added.length + sc.changed.length} rows were added to pending changes.</b> Nothing is in the library yet. Review them, then apply.`, '<a class="btn btn--primary btn--sm" href="#/library/review">Review and apply…</a>')}</div>`;
    const grp = (t, items, kind) => items.length ? `<details ${kind === 'info' ? 'open' : ''}><summary>${icon('chevr', 'chev')}${t} ${badge(kind, items.length)}</summary><div class="items">${items.map(([a, b]) => `<div><span class="mono">${esc(a)}</span><span class="muted">${esc(b)}</span></div>`).join('')}</div></details>` : '';
    return `<div class="page">${head}<div class="stack" style="max-width:920px">
      <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:var(--space-6)"><section><h3>File</h3><dl class="kv" style="margin-top:var(--space-2);grid-template-columns:110px 1fr"><dt>Name</dt><dd class="mono">${esc(sc.file)}</dd><dt>Size</dt><dd>${esc(sc.size)}</dd>${sc.tables.map(([k, n, note]) => `<dt>${esc(k)}</dt><dd>${n} rows <span class="muted">· ${esc(note)}</span></dd>`).join('')}</dl></section>
        <section><h3>Checks</h3><ul class="checklist" style="margin-top:var(--space-2)">${sc.checks.map(([k, t]) => `<li class="${k}">${icon({ ok: 'check', bad: 'error' }[k])}<span style="color:var(--color-text)">${esc(t)}</span></li>`).join('')}</ul></section></div>
      <section><h3>Rows with a problem</h3><div class="table-wrap" style="margin-top:var(--space-2)"><table class="table"><thead><tr><th>Table</th><th class="num" style="width:70px">Row</th><th style="width:140px">Column</th><th>What is wrong</th></tr></thead><tbody>${sc.errors.map(([t, r, c, m]) => `<tr><td>${esc(t)}</td><td class="num">${r}</td><td class="mono">${esc(c)}</td><td>${icon('error')} ${esc(m)}</td></tr>`).join('')}</tbody></table></div></section>
      <section><h3>What changes</h3><div class="row" style="margin:var(--space-2) 0 var(--space-3)">${badge('ok', `${sc.added.length} added`)}${badge('info', `${sc.changed.length} changed`)}${badge('bad', `${sc.removed.length} removed`)}</div><div class="diff-list table-wrap" style="padding:0 var(--space-4)">${grp('Added devices', sc.added, 'ok')}${grp('Changed devices', sc.changed, 'info')}</div></section>
      <div class="actionbar"><button class="btn btn--primary" data-action="csv-add">${icon('check')}Add ${sc.added.length + sc.changed.length} valid rows to pending changes</button><button class="btn btn--secondary" data-action="csv-cancel">Choose a different file</button><span class="muted small">${sc.errors.length} rows with problems are skipped. Fix them in the file and import again to include them.</span></div></div></div>`;
  }
  ACTIONS['csv-pick'] = () => { S.csvStep = 'review'; App.render(); };
  ACTIONS['csv-cancel'] = () => { S.csvStep = 'choose'; App.render(); };
  ACTIONS['csv-add'] = () => { const sc = DB.csvScenario; sc.added.forEach(([id, t]) => pend({ area: 'Device', label: id, kind: 'added', from: '', to: t })); sc.changed.forEach(([id, t]) => pend({ area: 'Device', label: id, kind: 'changed', from: t.split(' → ')[0], to: t.split(' → ')[1] || t })); S.csvStep = 'done'; App.render(); };
})();
