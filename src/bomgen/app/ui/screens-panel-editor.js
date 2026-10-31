/* Screen: the panel editor on bomgen.app.api (plan M32a; docs/ui/screens.md "Panel editor").
   panel_page gives one panel. A generated panel's enclosure, document, options and the port plans
   of its devices live in substation.yaml, so the form tabs draft and save there through the shared
   save bar (draftForm); adding or removing a port allocation writes at once. Devices and YAML are
   read-only: Parts and Device preview place the devices. Hand-written panels are edited in M32b. */
(function () {
  const { esc, S, ACTIONS, badge, banner, tabs, field, input, select, pageHead, toast } = App;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;
  const str = (v) => (v == null ? '' : String(v));

  /* ---------- data: one page per (project file, substation id, panel id) ---------- */
  const PE = { key: '', state: 'idle', page: null, error: null };
  function load(id) {
    const key = `${S.project.file}#${S.sub}#${id}`;
    if (PE.key !== key) Object.assign(PE, { key, state: 'idle', page: null, error: null });
    if (PE.state === 'idle') {
      PE.state = 'loading';
      const current = () => PE.key === key;
      Bridge.call('panel_page', S.project.file, S.sub, id)
        .then((p) => { if (current()) PE.page = p; }).catch((err) => { if (current()) PE.error = err; })
        .then(() => { if (current()) { PE.state = 'loaded'; App.render(); } });
    }
    return PE.state === 'loaded' ? PE : null;
  }
  const reload = () => { PE.state = 'idle'; };
  /* A write changes the board, Device preview and Parts too. */
  const changed = () => { reload(); App.network.reload(); App.devicePreview.reload(); App.sub.reload(); };

  /* ---------- the form: keys e.<enclosure field>, doc, o.<all|panel>.<option>, p.<row>.… ---------- */
  const ENC = { make: 'text', model: 'text', ordering_code: 'text', h_mm: 'int', d_mm: 'int', w_mm: 'int', cable_entry: 'choice', 'base_frame.h_mm': 'int', 'base_frame.d_mm': 'int', 'base_frame.w_mm': 'int' };
  const OPT = { dc_spare_branches_per_feed: 'int', ac_spare_branches: 'int', ventilation: 'choice', change_over_diodes: 'choice', main_mcb_override_a: 'int', aux_socket_a: 'int', inter_panel_terminals: 'int', smoke_detector: 'bool' };
  const PORT = { count: 'int', speed: 'choice', media: 'choice', spare: 'int' };
  function spec(key) {  // [path in substation.yaml, kind]
    const [k, a, ...r] = key.split('.');
    if (k === 'e') { const f = [a, ...r].join('.'); return ENC[f] ? [['generated_panels', 'enclosure', ...f.split('.')], ENC[f]] : null; }
    if (k === 'doc') return [['generated_panels', 'document'], 'choice'];
    if (k === 'o') return OPT[r[0]] ? [a === 'all' ? ['generated_panels', 'options', r[0]] : ['generated_panels', 'options_by_panel', Number(a), r[0]], OPT[r[0]]] : null;
    if (k === 'p' && r[0] === 'serial_ports') return [['equipment', Number(a), 'port_plan', 'serial_ports'], 'int'];
    if (k === 'p' && PORT[r[2]]) return [['equipment', Number(a), 'port_plan', r[0], Number(r[1]), r[2]], PORT[r[2]]];
    return null;
  }
  function saved(key) {
    const p = PE.page; if (!p || !p.panel) return '';
    const [k, a, ...r] = key.split('.');
    if (k === 'e') return str([a, ...r].reduce((o, x) => (o == null ? o : o[x]), p.enclosure));
    if (k === 'doc') return p.document;
    if (k === 'o') {
      const o = p.options.find((x) => x.key === r[0]); if (!o) return '';
      return a === 'all' ? str(o.shared) : o.own && Number(a) === p.panel.number ? str(o.value) : '';
    }
    if (k === 'p') {
      const row = p.ports.find((x) => x.equipment === Number(a)), own = row && row.own;
      if (!own) return '';
      if (r[0] === 'serial_ports') return str(own.serial_ports);
      const al = (own[r[0]] || [])[Number(r[1])];
      return al ? str(al[r[2]]) : '';
    }
    return '';
  }
  /* change_over_diodes is auto, true or false; the select gives text. */
  const typed = (path, value) => (path[path.length - 1] === 'change_over_diodes' && (value === 'true' || value === 'false') ? value === 'true' : value);
  const PD = App.draftForm({
    prefix: 'pe-', screen: 'panels', file: 'substation.yaml', label: 'Save the panel', spec, saved,
    check: (path, value) => Bridge.call('check_substation_field', S.project.file, S.sub, path, typed(path, value)),
    write: (path, value) => Bridge.call('set_substation_field', S.project.file, S.sub, path, typed(path, value)),
    done: changed
  });
  App.sub.resets.push(() => { PD.reset(); });
  const err = (key) => PD.err(key);
  const edit = (key, label, html, help) => PD.mark(key, field(label, html, help, err(key)));
  const text = (key, o = {}) => input('pe-' + key, str(PD.shown(key)), { invalid: !!PD.errors[key], ...o });
  const num = (key, unit, o = {}) => `<div class="input-affix">${text(key, { num: true, mono: true, ...o })}${unit ? `<span class="affix">${esc(unit)}</span>` : ''}</div>`;
  const choice = (key, opts) => select('pe-' + key, opts, str(PD.shown(key)), { invalid: !!PD.errors[key] });

  /* ---------- the page ---------- */
  const TABS = [['enclosure', 'Enclosure'], ['devices', 'Devices'], ['ports', 'Port plans'], ['options', 'Options'], ['document', 'Document'], ['yaml', 'YAML']];
  const KIND = { network: 'Network', control: 'Control', console: 'Console' };
  const TAB_OF = (key) => ({ e: 'enclosure', doc: 'document', o: 'options', p: 'ports' })[key.split('.')[0]];
  function tabMark(tab) {
    const bad = Object.keys(PD.errors).filter((k) => TAB_OF(k) === tab).length, n = Object.keys(PD.draft).filter((k) => TAB_OF(k) === tab).length;
    if (bad) return ` <span class="dot dot--bad" aria-hidden="true"></span><span class="sr-only">(${bad} to fix)</span>`;
    return n ? ` <span class="dot dot--warn" aria-hidden="true"></span><span class="sr-only">(${n} unsaved)</span>` : '';
  }
  App.panelEditor = (id) => {
    const crumbs = (name) => `<a href="#/panels">Panels</a>${icon('chevr')}<span>${esc(name)}</span>`;
    const l = load(id);
    if (!l) return `<div class="page">${pageHead(esc(id), 'Reading the panel…', '', crumbs(id))}</div>`;
    if (!l.page) return `<div class="page">${pageHead(esc(id), '', '', crumbs(id))}${banner('bad', `<b>This panel cannot be opened.</b> ${esc(l.error ? l.error.message : '')}`, '<a class="btn btn--secondary btn--sm" href="#/panels">Back to the panels</a>')}</div>`;
    const p = l.page;
    if (!p.panel) return `<div class="page">${pageHead(esc(id), '', '', crumbs(id))}${banner('bad', `<b>The panel cannot be read.</b> ${esc(p.reason)}.`, App.fixButtons(p.problems))}</div>`;
    const h = p.panel, gen = h.generated;
    const rc = App.route().c; if (TABS.some(([k]) => k === rc)) S.tab.panel = rc;
    const t = TABS.some(([k]) => k === S.tab.panel) ? S.tab.panel : 'enclosure';
    const meta = `<span class="mono" style="font-size:13px">${esc(h.cabinet_number)}</span> · ${KIND[h.kind] || esc(h.kind)}${gen ? ` · Side ${esc(h.side)}, pair ${h.pair} (panels ${2 * h.pair - 1} and ${2 * h.pair})` : ` · hand-written${h.manual ? ' (manual)' : ''}`}`;
    const intro = gen
      ? banner('info', '<b>Written by the layout.</b> Its devices come from Parts and where you place them on Device preview or the board. Enclosure, port plans, options and the document are yours to set.',
        '<a class="btn btn--secondary btn--sm" href="#/parts">Open Parts</a><a class="btn btn--secondary btn--sm" href="#/device-preview">Open Device preview</a>')
      : banner('info', '<b>Hand-written panel.</b> The layout does not touch it. Editing it here comes next; until then, change its file and reload.');
    const engine = p.engine_error ? `<div style="margin-bottom:var(--space-4)">${banner('warn', `<b>The engine stopped on this substation.</b> ${esc(p.engine_error)}`, '<a class="btn btn--secondary btn--sm" href="#/checks">Open checks</a>')}</div>` : '';
    const body = gen ? { enclosure, devices, ports, options, document: docTab, yaml }[t](p) : t === 'yaml' ? yaml(p) : t === 'devices' ? handDevices(p) : readOnly(p, t);
    return `<div class="page">${pageHead(esc(h.cabinet_name), meta, `<a class="btn btn--secondary" href="#/preview/${esc(h.id)}">${icon('preview')}Preview BOM</a>`, crumbs(h.cabinet_name))}
      <div style="margin-bottom:var(--space-4)">${intro}</div>${engine}
      ${tabs('panel', TABS.map(([k, x]) => [k, x, gen ? tabMark(k) : '']), t, 'Panel sections')}
      <div role="tabpanel" aria-labelledby="tab-panel-${t}" style="margin-top:var(--space-4)">${body}</div>${PD.bar()}</div>`;
  };

  /* ---------- Enclosure: shared by every generated panel ---------- */
  const enclosure = () => `<div style="margin-bottom:var(--space-4)">${banner('info', 'The enclosure is shared by every generated panel. A change here applies to each of them.')}</div>
    <div class="form form--3">
    ${edit('e.make', 'Make', text('e.make'))}${edit('e.model', 'Model', text('e.model'))}${edit('e.ordering_code', 'Ordering code', text('e.ordering_code', { mono: true, placeholder: 'Optional' }))}
    ${edit('e.h_mm', 'Height', num('e.h_mm', 'mm'))}${edit('e.d_mm', 'Depth', num('e.d_mm', 'mm'))}${edit('e.w_mm', 'Width', num('e.w_mm', 'mm'))}
    ${edit('e.base_frame.h_mm', 'Base frame height', num('e.base_frame.h_mm', 'mm'))}${edit('e.base_frame.d_mm', 'Base frame depth', num('e.base_frame.d_mm', 'mm'))}${edit('e.base_frame.w_mm', 'Base frame width', num('e.base_frame.w_mm', 'mm'))}
    ${edit('e.cable_entry', 'Cable entry', choice('e.cable_entry', [['top', 'Top'], ['side', 'Side']]))}</div>`;

  /* ---------- Devices: what the layout placed, read-only ---------- */
  const ROLES = { fopp: 'Fibre patch panel', l2_switch: 'L2 switch', l1_switch: 'L1 switch', ext_switch: 'External switch', firewall: 'Firewall' };
  const devName = (d) => ROLES[d.role] || d.label;
  function devices(p) {
    return `<div class="toolbar"><span class="muted small">Add or remove devices on Parts. Move or pin them on Device preview or the board.</span><span class="sp"></span><a class="btn btn--secondary btn--sm" href="#/parts">${icon('parts')}Open Parts</a></div>
      <div class="table-wrap"><table class="table"><thead><tr><th>Device</th><th>Part</th><th class="num" style="width:80px">Height</th><th style="width:90px">Side</th><th style="width:110px">Origin</th><th style="width:190px"><span class="sr-only">Action</span></th></tr></thead>
      <tbody>${p.devices.map((d, i) => `<tr><td>${esc(devName(d))}${d.label !== devName(d) ? `<span class="cell-sub">${esc(d.label)}</span>` : ''}</td><td class="mono">${esc(d.part_id)}</td><td class="num">${d.height_u ? d.height_u + ' U' : 'DIN rail'}</td><td>${d.side ? 'Side ' + esc(d.side) : 'Common'}</td>
        <td>${d.origin === 'pinned' ? badge('info', 'Pinned', 'pin') : '<span class="muted small">Layout</span>'}</td>
        <td><button class="btn btn--ghost btn--sm" data-action="pe-show" data-i="${i}">${icon('elevation')}Show on Device preview</button></td></tr>`).join('')}</tbody></table>
      <div class="table-foot"><span>${plural(p.devices.length, 'unit')} in this panel</span></div></div>`;
  }
  ACTIONS['pe-show'] = (el) => {
    const p = PE.page, d = p.devices[+el.dataset.i];
    const id = `${p.panel.number}:${d.device}#${d.n}:${(d.side || '').toLowerCase()}`;  // Device preview's uid
    App.devicePreview.select(id);
    App.fix({ file: '', location: '' }, { label: '', hash: '#/device-preview', focus: `.eu[data-uid="${id}"]` });
  };
  /* A hand-written panel's devices, as its file lists them (editing comes in M32b). */
  const handDevices = (p) => `<div class="table-wrap"><table class="table"><thead><tr><th>Part</th><th class="num" style="width:70px">Qty</th><th>Purpose</th><th>Tag</th></tr></thead>
    <tbody>${p.devices.map((d) => `<tr><td class="mono">${esc(d.part_id)}</td><td class="num">${d.qty}</td><td>${esc(d.purpose || '')}</td><td class="mono muted">${esc(d.tag || '')}</td></tr>`).join('')}</tbody></table></div>`;
  const readOnly = (p, t) => (t === 'document' ? `<dl class="kv"><dt>Register document</dt><dd class="mono">${esc(p.document)}</dd></dl>`
    : t === 'enclosure' ? `<dl class="kv">${Object.entries(p.enclosure).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(typeof v === 'object' ? JSON.stringify(v) : v)}</dd>`).join('')}</dl>`
    : t === 'options' ? `<dl class="kv">${p.options.map((o) => `<dt>${esc(o.key)}</dt><dd>${esc(JSON.stringify(o.value))}</dd>`).join('')}</dl>`
    : '<p class="muted">Port plans of a hand-written panel are in its file.</p>');

  /* ---------- Port plans: each device's own; the sized switches' are computed ---------- */
  const GROUPS = [['uplinks_l3', 'Uplink to L3'], ['uplinks', 'Uplink'], ['downlinks', 'Downlink']];
  const SPEEDS = ['10M', '100M', '1G', '2.5G', '5G', '10G', '25G'], MEDIA = ['MM', 'SM', 'RJ45'];
  const cellSel = (key, opts, label) => `<label class="sr-only" for="pe-${key}">${label}</label>${select('pe-' + key, opts, str(PD.shown(key)), { cls: 'ctl', invalid: !!PD.errors[key] })}`;
  const cellNum = (key, label) => `<label class="sr-only" for="pe-${key}">${label}</label>${text(key, { num: true, mono: true }).replace('class="input', 'class="ctl input')}`;
  const allocs = (plan) => GROUPS.flatMap(([g, use]) => ((plan && plan[g]) || []).map((a, i) => ({ g, use, i, a })));
  const result = (r) => `<div class="table-foot"><span>Engine result</span><span>${r.lines.length ? r.lines.map((x) => `<span class="mono" style="color:var(--color-text)">${esc(x.qty)} × ${esc(x.part_id || '')}</span> <span class="muted">${esc(x.description)}</span>`).join('<br>') : '<span class="muted">No SFPs or cables for this device</span>'}</span></div>`;
  const l2Line = (r) => `<p class="small" style="margin:var(--space-2) 0">${r.l2.ports ? `Linked to the L2 switch: ${r.l2.ports} × ${esc(r.l2.speed)} ${esc(r.l2.media)}.` : 'Not linked to the L2 switch.'} <a href="#/parts" data-action="pe-parts" data-i="${r.equipment}">Change on Parts</a></p>`;
  function portSection(r, p) {
    const d = p.devices.find((x) => x.device === r.device) || { role: r.role, label: r.device }, head = `<h3>${esc(devName(d))} <span class="muted mono" style="font-weight:400;font-size:13px">${esc(r.part_id)}</span></h3>`;
    if (!r.editable) {
      const rows = allocs(r.used);
      return `<section class="section" style="padding-top:var(--space-4)">${head}<p class="muted small" style="margin:var(--space-1) 0 var(--space-2)">Worked out by the switch sizing from Parts. Read-only.</p>
        <div class="table-wrap" style="max-width:820px"><table class="table"><thead><tr><th>Use</th><th class="num" style="width:90px">Ports</th><th style="width:100px">Speed</th><th style="width:100px">Media</th><th class="num" style="width:90px">Spare</th></tr></thead>
        <tbody>${rows.map(({ use, a }) => `<tr><td>${use}</td><td class="num">${a.count}</td><td class="mono">${esc(a.speed)}</td><td class="mono">${esc(a.media)}</td><td class="num">${a.spare}</td></tr>`).join('') || '<tr class="empty-row"><td colspan="5">No ports in use.</td></tr>'}</tbody></table>${result(r)}</div></section>`;
    }
    const rows = allocs(r.own), k = (x, f) => `p.${r.equipment}.${x.g}.${x.i}.${f}`;
    return `<section class="section" style="padding-top:var(--space-4)"><div class="row" style="justify-content:space-between">${head}
        <span class="row" style="gap:var(--space-2)"><label class="sr-only" for="pa-g-${r.equipment}">Use of the new allocation</label><select class="select" id="pa-g-${r.equipment}" style="width:auto">${GROUPS.map(([g, u]) => `<option value="${g}" ${g === 'downlinks' ? 'selected' : ''}>${u}</option>`).join('')}</select>
        <button class="btn btn--ghost btn--sm" data-action="pe-alloc-add" data-i="${r.equipment}" ${PD.dirty() ? 'disabled title="Save or discard the changes first"' : ''}>${icon('plus')}Add allocation</button></span></div>
      ${l2Line(r)}
      <div class="table-wrap" style="max-width:820px"><table class="table"><thead><tr><th>Use</th><th class="num" style="width:90px">Ports</th><th style="width:110px">Speed</th><th style="width:100px">Media</th><th class="num" style="width:90px">Spare</th><th style="width:44px"><span class="sr-only">Remove</span></th></tr></thead>
      <tbody>${rows.map((x) => { const bad = ['count', 'speed', 'media', 'spare'].map((f) => PD.errors[k(x, f)]).filter(Boolean); const chg = ['count', 'speed', 'media', 'spare'].some((f) => k(x, f) in PD.draft);
        return `<tr${chg ? ' class="is-changed"' : ''}><td>${x.use}${bad.length ? `<span class="err small">${icon('error')}<span>${esc(bad[0])}</span></span>` : ''}</td><td>${cellNum(k(x, 'count'), `${x.use} ports`)}</td><td>${cellSel(k(x, 'speed'), SPEEDS, `${x.use} speed`)}</td><td>${cellSel(k(x, 'media'), MEDIA, `${x.use} media`)}</td><td>${cellNum(k(x, 'spare'), `${x.use} spare ports`)}</td>
        <td><button class="btn btn--ghost btn--icon btn--sm" data-action="pe-alloc-remove" data-i="${r.equipment}" data-g="${x.g}" data-n="${x.i}" aria-label="Remove ${x.use.toLowerCase()} ${x.a.count} × ${esc(x.a.speed)}" ${PD.dirty() ? 'disabled title="Save or discard the changes first"' : ''}>${icon('trash')}</button></td></tr>`; }).join('')
        || '<tr class="empty-row"><td colspan="6">No ports beyond its L2 link. Add an allocation for the ports it uses.</td></tr>'}</tbody></table>${result(r)}</div>
      <div class="form form--3" style="margin-top:var(--space-3);max-width:820px">${edit(`p.${r.equipment}.serial_ports`, 'Serial ports', num(`p.${r.equipment}.serial_ports`, '', { placeholder: '0' }), 'Each one adds a serial cable to the BOM.')}</div></section>`;
  }
  const ports = (p) => `<p class="muted" style="max-width:68ch">A port plan belongs to the device on Parts, so a change here also applies to the other panels with that device, on both sides. The engine works out the SFPs and cables and shows them under each table.</p>
    ${p.ports.map((r) => portSection(r, p)).join('') || '<p class="muted">No devices in this panel.</p>'}`;
  /* Adding or removing an allocation writes the device's whole port plan at once. */
  function writePlan(row, plan) {
    const empty = GROUPS.every(([g]) => !(plan[g] || []).length) && !plan.serial_ports;
    Bridge.call('set_port_plan', S.project.file, S.sub, row.device, empty ? null : plan).then((r) => {
      if (!r.written) { toast(`Not changed. ${(r.issues[0] && r.issues[0].message) || 'The plan was refused.'}`, 'error'); return; }
      changed(); App.render();
    }).catch((e) => toast(e.message, 'error'));
  }
  const rowOf = (i) => PE.page.ports.find((x) => x.equipment === +i);
  const planOf = (row) => JSON.parse(JSON.stringify(row.own || { uplinks_l3: [], uplinks: [], downlinks: [], serial_ports: 0 }));
  ACTIONS['pe-alloc-add'] = (el) => {
    const row = rowOf(el.dataset.i), plan = planOf(row), g = document.getElementById('pa-g-' + el.dataset.i).value;
    plan[g] = [...(plan[g] || []), { count: 1, speed: row.l2.speed || '1G', media: row.l2.media || 'MM', spare: 0 }];
    writePlan(row, plan);
  };
  ACTIONS['pe-alloc-remove'] = (el) => {
    const row = rowOf(el.dataset.i), plan = planOf(row);
    plan[el.dataset.g] = plan[el.dataset.g].filter((_, i) => i !== +el.dataset.n);
    writePlan(row, plan);
  };
  ACTIONS['pe-parts'] = (el, e) => { e.preventDefault(); App.fix({ file: 'substation.yaml', location: `equipment[${el.dataset.i}]` }); };

  /* ---------- Options: for every generated panel, or this one only ---------- */
  const OPTIONS = [
    ['dc_spare_branches_per_feed', 'DC spare branches per feed', '', 'Spare MCBs on each of feed 1 and feed 2.'],
    ['ac_spare_branches', 'AC spare branches', ''],
    ['ventilation', 'Ventilation', [['auto', 'Automatic (from the heat calculation)'], ['forced', 'Fans'], ['natural', 'Filters']]],
    ['change_over_diodes', 'Change-over diodes', [['auto', 'Automatic'], ['true', 'Yes'], ['false', 'No']]],
    ['main_mcb_override_a', 'Main MCB override', 'A', 'Empty uses the sizing rule.'],
    ['aux_socket_a', 'Auxiliary socket', 'A', 'Empty means no socket.'],
    ['inter_panel_terminals', 'Inter-panel terminals', ''],
    ['smoke_detector', 'Smoke detector', [['true', 'Yes'], ['false', 'No']]]];
  const shownValue = (o, opts) => { const v = str(o); const hit = Array.isArray(opts) && opts.find(([x]) => x === v); return hit ? hit[1] : v || 'None'; };
  function options(p) {
    const own = S.optScope === 'own', n = p.panel.number, scope = own ? String(n) : 'all';
    const owned = p.options.filter((o) => o.own);
    const rows = OPTIONS.map(([k, label, kind, help]) => {
      const o = p.options.find((x) => x.key === k), key = `o.${scope}.${k}`;
      const opts = Array.isArray(kind) ? (own ? [['', `Shared: ${shownValue(o.shared, kind)}`], ...kind] : kind) : null;
      const ctl = opts ? choice(key, opts) : num(key, kind, own ? { placeholder: `Shared: ${str(o.shared) || 'none'}` } : {});
      const note = own && o.own ? `${badge('info', `Own value · shared ${shownValue(o.shared, kind)}`)} <button class="btn btn--ghost btn--sm" data-action="pe-use-shared" data-key="${key}">Use the shared value</button>`
        : !own && o.own ? `<span class="muted small">This panel has its own value, ${esc(shownValue(o.value, kind))}.</span>` : '';
      return edit(key, esc(label), ctl, [help || '', note].filter(Boolean).join(' '));
    }).join('');
    const extra = p.options.filter((o) => ['terminal_overrides', 'grounding_busbars'].includes(o.key));
    return `<div class="field" style="margin-bottom:var(--space-4)"><span class="label" id="pe-scope-l">Apply to</span><div class="segmented" role="radiogroup" aria-labelledby="pe-scope-l">
        <label><input type="radio" name="pe-scope" value="all" data-action="pe-scope" ${own ? '' : 'checked'}><span>All generated panels</span></label><label><input type="radio" name="pe-scope" value="own" data-action="pe-scope" ${own ? 'checked' : ''}><span>This panel only</span></label></div>
      <span class="help">${own ? `Values you set are kept for ${esc(p.panel.cabinet_name)} only and marked Own value.` : 'Values you set apply to every generated panel that has no value of its own.'}${owned.length ? ` This panel has ${plural(owned.length, 'own value')}.` : ''}</span></div>
      <div class="form form--2">${rows}</div>
      <div class="section" style="margin-top:var(--space-5)"><h3>Terminal overrides and grounding busbars</h3><p class="lede">Shown as written. Change them in substation.yaml for now.</p>
      <dl class="kv">${extra.map((o) => `<dt>${o.key === 'terminal_overrides' ? 'Terminal overrides' : 'Grounding busbars'}</dt><dd class="mono">${esc(Array.isArray(o.value) ? o.value.join(', ') : Object.entries(o.value).map(([a, b]) => `${a}: ${b}`).join(', ') || 'None')}</dd>`).join('')}</dl></div>`;
  }
  ACTIONS['pe-scope'] = (el) => { S.optScope = el.value; App.render(); };
  ACTIONS['pe-use-shared'] = (el) => { PD.set(el.dataset.key, ''); S.dirty = true; App.render(); };

  /* ---------- Document ---------- */
  function docTab(p) {
    const e = p.documents.find((x) => x.key === str(PD.shown('doc')));
    return `<div class="form form--3">${edit('doc', 'Register document', choice('doc', p.documents.map((x) => [x.key, x.key])), 'Shared by every generated panel. Chosen from the project\'s document register.')}
      ${field('Document number', input('pe-dn', e ? e.doc_no : '', { mono: true, readonly: true }), 'Printed in the page header and footer.')}${field('Revision', input('pe-dr', e ? e.rev : '', { mono: true, readonly: true }))}</div>
      <div class="row" style="margin-top:var(--space-3)"><a class="btn btn--secondary btn--sm" href="#/project/documents">Edit in the register</a></div>`;
  }

  /* ---------- YAML: read-only ---------- */
  const hl = (line) => esc(line).replace(/^(\s*)(- )?([A-Za-z_][\w]*)(:)/, '$1$2<span class="k">$3</span>$4').replace(/(#.*)$/, '<span class="c">$1</span>');
  function yaml(p) {
    const lines = p.yaml.replace(/\n$/, '').split('\n'), name = p.panel.file.split(/[\\/]/).slice(-2).join('/');
    return `<div class="toolbar"><span class="mono" style="font-size:12.5px">${esc(name)}</span>${p.panel.generated ? badge('info', 'Generated') : ''}<span class="sp"></span><span class="muted small">${icon('lock')} ${p.panel.generated ? 'Written by the layout. Read-only.' : 'Read-only in the app for now'}</span></div>
      <div class="code" role="textbox" aria-readonly="true" aria-multiline="true" aria-label="${esc(name)} source" tabindex="0">
        <div class="gut" aria-hidden="true">${lines.map((_, i) => `<div>${i + 1}</div>`).join('')}</div>
        <div class="src">${lines.map((x) => `<div>${hl(x) || ' '}</div>`).join('')}</div></div>`;
  }
})();
