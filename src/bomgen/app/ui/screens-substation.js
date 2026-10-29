/* Screens: substation Settings and the Network inputs on bomgen.app.api (plan M10c).
   Settings and the Network inputs are edited here (M17c). The L1 ranking and the Result card come from screens-panels.js.
   Opened in a plain browser, the prototype's screens in screens-project.js and screens-layout.js are used instead. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, select, pageHead, toast } = App;
  const example = { settings: SCREENS.settings, network: SCREENS.network };
  const ro = (html) => html.replace('data-dirty="1"', 'readonly').replace('class="input', 'class="ctl input');
  const fixed = (v, unit) => `<div class="input-affix">${ro(input('x', v, { num: true, mono: true }))}${unit ? `<span class="affix">${esc(unit)}</span>` : ''}</div>`;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;

  /* ---------- data: one substation page per (project file, substation id) ---------- */
  const SUB = { key: '', state: 'idle', page: null, error: null };
  const real = () => S.backend === 'yes' && S.project && S.project.real && S.sub;
  function page() {
    const key = `${S.project.file}#${S.sub}`;
    if (SUB.key !== key) { Object.assign(SUB, { key, state: 'idle', page: null, error: null }); NET.reset(); ST.reset(); }
    if (SUB.state === 'idle') {
      SUB.state = 'loading';
      const current = () => SUB.key === key;  // the user may have moved on while it loaded
      Bridge.call('open_substation', S.project.file, S.sub)
        .then((p) => { if (current()) SUB.page = p; }).catch((err) => { if (current()) { SUB.error = err; toast(err.message, 'error'); } })
        .then(() => { if (current()) { SUB.state = 'loaded'; App.render(); } });
    }
    return SUB.state === 'loaded' ? SUB.page : null;
  }
  const waiting = (title) => `<div class="page">${pageHead(title, SUB.error ? esc(SUB.error.message) : 'Reading substation.yaml…')}</div>`;
  const problems = (p) => (p.problems.length ? `<div style="margin-bottom:var(--space-4)">${banner('bad', `<b>${plural(p.problems.length, 'problem')} in this substation's files.</b> <ul style="margin:6px 0 0;padding-left:18px">${p.problems.slice(0, 8).map((x) => `<li><span class="mono small">${esc(x.file.split(/[\\/]/).slice(-2).join('/'))}${x.line ? ':' + x.line : ''}</span>${x.location ? ` <span class="mono small">${esc(x.location)}</span>` : ''}: ${esc(x.message)}</li>`).join('')}</ul>`, jump(p))}</div>` : '');
  /* On the YAML tab the button scrolls to the first marked line; elsewhere it opens the tab. */
  const jump = (p) => {
    const first = p.problems.find((x) => x.line && x.file === p.file);
    return App.route().a === 'settings' && S.tab.settings === 'yaml' && first
      ? `<button class="btn btn--secondary btn--sm" data-action="yaml-goto" data-line="${first.line}">Go to line ${first.line}</button>`
      : '<button class="btn btn--secondary btn--sm" data-action="goto" data-to="#/settings/yaml">Show the YAML</button>';
  };
  ACTIONS['yaml-goto'] = (el) => {
    const row = document.querySelector(`.code .src > div:nth-child(${Number(el.dataset.line)})`);
    if (row) { row.scrollIntoView({ block: 'center' }); document.querySelector('.code').focus({ preventScroll: true }); }
  };
  const changed = (row, fmt = (v) => v) => (row.changed ? badge('info', `Changed from ${fmt(row.default)}`) : '<span class="muted small">Default</span>');

  /* ---------- Settings ---------- */
  const SHEETS = { power_consumption: 'Power Consumption', heat_dissipation: 'Heat Dissipation', heat_calculations: 'Heat Calculations' };
  const CONSTANTS = {
    dc_voltage_v: ['DC supply voltage', 'V'], ac_voltage_v: ['AC supply voltage', 'V'], power_margin: ['Power margin', '×'], current_factor: ['Current factor', '×'],
    btu_per_w: ['Heat conversion', 'BTU/h per W'], t_max_c: ['Maximum ambient', '°C'], t_int_c: ['Internal limit', '°C'],
    air_constant_m3k_per_wh: ['Air constant', 'm³·K/Wh'], steel_coefficient_w_per_m2c: ['Sheet-steel heat transfer', 'W/m²·°C'], min_main_mcb_a: ['Minimum main MCB', 'A'],
    min_branch_mcb_a: ['Smallest branch MCB', 'A'], inrush_min_ms: ['Shortest inrush that sizes an MCB', 'ms'], dc_float_v: ['Battery float voltage', 'V']
  };
  const tabsSettings = [['general', 'General'], ['documents', 'Documents'], ['output', 'Output'], ['constants', 'Design constants'], ['yaml', 'YAML']];
  SCREENS.settings = () => {
    if (!real()) return example.settings();
    const p = page(); if (!p) return waiting('Settings');
    const rb = App.route().b; if (tabsSettings.some(([k]) => k === rb)) S.tab.settings = rb;
    const t = p.calculations || S.tab.settings === 'yaml' ? S.tab.settings : 'yaml';
    const body = { general, documents, output, constants, yaml }[t](p);
    return `<div class="page">${pageHead('Settings', `Settings of ${esc(p.name)} only. Project-wide values are on the project page.`)}
      ${problems(p)}${tabs('settings', tabsSettings.map(([k, l]) => [k, l, tabMark(k)]), t, 'Substation settings')}
      <div role="tabpanel" aria-labelledby="tab-settings-${t}">${body}</div>${ST.bar()}</div>`;
  };
  /* Settings fields are drafted and saved together; an emptied field is removed so the default applies. */
  const KINDS = [['mcb', 'MCBs, AC branches'], ['mcb_dc', 'MCBs, DC branches'], ['aux_contact', 'Aux contacts'], ['terminal_blocks', 'Terminal blocks'], ['busbars', 'Busbars'], ['housekeeping', 'Housekeeping']];
  const PCT = new Set(['power_margin']);
  function stSpec(key) {
    const [, kind, rest] = /^(\w+?)_(.*)$/.exec(key) || [, key, ''];
    if (key === 'name') return [['substation', 'name'], 'text'];
    if (key === 'document') return [['document'], 'choice'];
    if (key === 'file_name') return [['output', 'file_name'], 'text'];
    if (kind === 'brand') return [['catalogue_choice', rest], 'choice'];
    if (kind === 'calc') return [['calculations', rest, 'document'], 'choice'];
    if (kind === 'sheet') return [['output', 'sheet_names', rest], 'text'];
    if (kind === 'c') return [['constants', rest], PCT.has(rest) ? 'pct' : rest.endsWith('_a') ? 'int' : 'num'];
    return null;
  }
  function stSaved(key) {
    const p = SUB.page, [, kind, rest] = /^(\w+?)_(.*)$/.exec(key) || [, key, ''];
    if (!p || !p.calculations) return '';
    if (key === 'name') return p.name;
    if (key === 'document') return p.output.document;
    if (key === 'file_name') return p.output.file_name;
    if (kind === 'brand') return p.catalogue_choice[rest] || '';
    if (kind === 'calc') return (p.calculations.find((c) => c.key === rest) || {}).document || '';
    if (kind === 'sheet') return p.output.sheet_names[rest];
    if (kind === 'c') { const c = p.constants.find((x) => x.key === rest); return c ? (PCT.has(rest) ? Math.round(c.value * 1000) / 10 : c.value) : ''; }
    return '';
  }
  const ST = App.draftForm({
    prefix: 'st-', screen: 'settings', file: 'substation.yaml', label: 'Save settings', spec: stSpec, saved: stSaved,
    check: (path, value) => Bridge.call('check_substation_field', S.project.file, S.sub, path, value),
    write: (path, value) => Bridge.call('set_substation_field', S.project.file, S.sub, path, value),
    done: (page, keys) => {
      SUB.page = page; App.network.reload();
      const row = keys.includes('name') && S.project.substations.find((x) => x.id === S.sub);
      if (row) row.name = page.name;
    }
  });
  const edit = (key, label, html, help) => ST.mark(key, field(label, html, help, ST.err(key)));
  const text = (key, o = {}) => input('st-' + key, ST.shown(key) == null ? '' : String(ST.shown(key)), { invalid: !!ST.errors[key], ...o });
  const choice = (key, opts) => select('st-' + key, opts, ST.shown(key) || '', { invalid: !!ST.errors[key] });
  const brandName = (p, kind, id) => ((p.brands[kind] || []).find((b) => b.id === id) || { name: id }).name;
  function brandSelect(p, kind, label) {
    const own = p.project_choice[kind], from = own ? brandName(p, kind, own) : kind === 'mcb_dc' ? 'as the AC branches' : brandName(p, kind, 'default');
    const opts = [['', `Same as the project (${from})`], ...(p.brands[kind] || []).map((b) => [b.id, b.name])];
    return edit('brand_' + kind, esc(label), choice('brand_' + kind, opts));
  }
  const general = (p) => `<div class="form form--2">
    ${edit('name', 'Substation name', text('name'), 'Shown in the app and in each sheet header.')}
    ${field('Substation id', ro(input('s-id', p.id, { mono: true })), 'Names the substation in the register and in tags. Not printed.')}
    ${Object.keys(p.brands).length ? `<div class="span-2 section" style="margin:0">
      <h3>Catalogue brands</h3>
      <p class="lede">The project's brands apply unless this substation chooses its own.</p>
      <div class="form form--3" style="margin-top:var(--space-3)">${KINDS.map(([k, l]) => brandSelect(p, k, l)).join('')}</div></div>` : ''}
    <div class="span-2 section" style="margin:0">
      <h3>From the project</h3>
      <p class="lede">These come from the project and are the same for every substation in it.</p>
      <dl class="kv"><dt>Project</dt><dd>${esc(p.project.name)}</dd><dt>Client</dt><dd>${esc(p.project.client || '—')}</dd><dt>Device library</dt><dd>${esc(p.project.library.name)}, built with ${esc(p.project.library.version)}</dd></dl>
      <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary" data-action="goto" data-to="#/project/info">Open project overview</button></div>
    </div></div>`;
  const docOpts = (p) => p.documents.map((d) => [d.key, `${d.key} · ${d.doc_no} rev ${d.rev}`]);
  const entryOf = (p, key) => p.documents.find((d) => d.key === key);
  const docCells = (e) => (e ? `<td class="mono">${esc(e.doc_no)}</td><td class="mono">${esc(e.rev)}</td><td class="mono">${esc(e.issue_date)}</td>` : `<td colspan="3"><span class="err small">${icon('error')}<span>Not in the register</span></span></td>`);
  const documents = (p) => `<p class="lede muted" style="max-width:68ch;margin-bottom:var(--space-4)">Each calculation sheet prints the document number, revision and issue date of the register entry it names. Cabinet BOMs choose theirs on each panel. The register itself is on the project page.</p>
    <div class="table-wrap" style="max-width:980px"><table class="table"><thead><tr><th>Sheet</th><th style="width:300px">Register document</th><th>Document no.</th><th style="width:70px">Rev</th><th style="width:120px">Issue date</th></tr></thead>
    <tbody>${p.calculations.map((c) => { const key = 'calc_' + c.key; return `<tr><td>${esc(SHEETS[c.key])}<span class="cell-sub">${esc(c.scope)}</span></td><td${key in ST.draft ? ' class="changed"' : ''}><label class="sr-only" for="st-${key}">Register document, ${esc(SHEETS[c.key])}</label>${choice(key, docOpts(p))}${ST.errors[key] ? `<span class="err small">${icon('error')}<span>${ST.err(key)}</span></span>` : ''}</td>${docCells(entryOf(p, ST.shown(key)))}</tr>`; }).join('')}</tbody></table></div>
    <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary btn--sm" data-action="goto" data-to="#/project/documents">Open the register</button></div>`;
  const SHEET_LABELS = { loose_material: 'Loose material', power_consumption: 'Power', heat_dissipation: 'Heat dissipation', heat_calculations: 'Heat calculations' };
  const output = (p) => { const o = p.output; return `<div class="form">
    ${edit('document', 'Main document', choice('document', docOpts(p)), 'The document whose number and revision go into the workbook file name.')}
    ${edit('file_name', 'File name', text('file_name', { mono: true }), 'Fields: <span class="mono">{doc_no}</span> and <span class="mono">{rev}</span>. Empty it to use the default.')}
    ${o.result ? `<div class="banner banner--info">${icon('info')}<div class="grow"><b>Result:</b> <span class="mono">${esc(o.result)}</span>${ST.dirty() ? ' <span class="muted small">(as saved)</span>' : ''}</div></div>` : banner('bad', `<b>No file name.</b> The main document <span class="mono">${esc(o.document)}</span> is not in the register.`)}
    <div class="section" style="margin:0"><h3>Sheet names</h3><p class="lede">Cabinet sheets are named by each panel's sheet name. Empty a name to use the default.</p>
    <div class="stack">${Object.keys(SHEET_LABELS).map((k) => edit('sheet_' + k, SHEET_LABELS[k], text('sheet_' + k))).join('')}</div></div></div>`; };
  const constants = (p) => { const changedRows = p.constants.filter((c) => c.changed); return `<p class="muted" style="max-width:68ch;margin-bottom:var(--space-4)">Defaults come from the project's shared defaults. A value this substation writes itself is marked; Reset removes it so the default applies again.</p>
    <div class="table-wrap" style="max-width:860px"><table class="table"><thead><tr><th>Constant</th><th class="num" style="width:130px">Value</th><th>Unit</th><th style="width:230px">Default</th></tr></thead>
    <tbody>${p.constants.map((c) => { const [label, unit] = CONSTANTS[c.key] || [c.key, ''], key = 'c_' + c.key, pc = PCT.has(c.key), d = pc ? Math.round(c.default * 1000) / 10 : c.default; const reset = key in ST.draft && ST.draft[key] === '';
      return `<tr><td>${esc(label)}<span class="cell-sub mono">${esc(c.key)}</span>${ST.errors[key] ? `<span class="err small">${icon('error')}<span>${ST.err(key)}</span></span>` : ''}</td><td${key in ST.draft ? ' class="changed"' : ''}><label class="sr-only" for="st-${key}">${esc(label)}</label>${text(key, { num: true, mono: true, placeholder: String(d) })}</td><td class="muted">${esc(pc ? '%' : unit)}</td>
        <td>${reset ? '<span class="muted small">Reset on save</span>' : c.changed ? `${badge('info', `Changed from ${d}`)} <button class="btn btn--ghost btn--sm" data-action="st-reset" data-key="${key}">Reset</button>` : '<span class="muted small">Default</span>'}</td></tr>`; }).join('')}</tbody></table>
    <div class="table-foot"><span>${plural(changedRows.length, 'constant')} changed for this substation</span><span>${changedRows.length ? '<button class="btn btn--ghost btn--sm" data-action="st-reset-all">Reset all to defaults</button>' : ''}</span></div></div>`; };
  /* A tab with unsaved or refused values says so, since the save bar counts every tab. */
  const TAB_OF = (key) => (key === 'name' || key.startsWith('brand_') ? 'general' : key.startsWith('calc_') ? 'documents' : key.startsWith('c_') ? 'constants' : 'output');
  function tabMark(tab) {
    const bad = Object.keys(ST.errors).filter((k) => TAB_OF(k) === tab).length, changed = Object.keys(ST.draft).filter((k) => TAB_OF(k) === tab).length;
    if (bad) return ` <span class="dot dot--bad" aria-hidden="true"></span><span class="sr-only">(${bad} to fix)</span>`;
    return changed ? ` <span class="dot dot--warn" aria-hidden="true"></span><span class="sr-only">(${changed} unsaved)</span>` : '';
  }
  ACTIONS['st-reset'] = (el) => { ST.set(el.dataset.key, ''); S.dirty = true; App.render(); };
  ACTIONS['st-reset-all'] = () => { SUB.page.constants.filter((c) => c.changed).forEach((c) => ST.set('c_' + c.key, '')); S.dirty = true; App.render(); };
  const hl = (line) => esc(line).replace(/^(\s*)(- )?([A-Za-z_][\w]*)(:)/, '$1$2<span class="k">$3</span>$4').replace(/(#.*)$/, '<span class="c">$1</span>');
  function yaml(p) {
    const lines = p.yaml.replace(/\n$/, '').split('\n');
    const errs = {}; p.problems.filter((x) => x.line && x.file === p.file).forEach((x) => { errs[x.line] = (errs[x.line] ? errs[x.line] + ' ' : '') + x.message; });
    const n = Object.keys(errs).length, name = p.file.split(/[\\/]/).slice(-3).join('/');
    return `<div class="toolbar"><span class="mono" style="font-size:12.5px">${esc(name)}</span>${n ? badge('bad', plural(n, 'error'), 'error') : badge('ok', 'No errors', 'check')}<span class="sp"></span><span class="muted small">${icon('lock')} Read-only in the app for now</span></div>
      <div class="code" role="textbox" aria-readonly="true" aria-multiline="true" aria-label="${esc(name)} source" tabindex="0">
        <div class="gut" aria-hidden="true">${lines.map((_, i) => `<div class="${errs[i + 1] ? 'e' : ''}">${i + 1}</div>`).join('')}</div>
        <div class="src">${lines.map((l, i) => `<div class="${errs[i + 1] ? 'e' : ''}">${hl(l) || ' '}</div>`).join('')}</div></div>
      ${Object.entries(errs).map(([line, m]) => `<div class="err small" style="color:var(--color-danger-text);margin-top:8px;display:flex;gap:6px">${icon('error')}<span>Line ${line}: ${esc(m)}</span></div>`).join('')}`;
  }

  /* ---------- Network: the inputs, with the engine's ranking and result ---------- */
  const ROLES = { fopp: 'Fibre patch panel', l2_switch: 'L2 switch', l1_switch: 'L1 switch', ext_switch: 'External switch', firewall: 'Firewall', other: 'Other' };
  const SPARES = { port_fraction: ['Ports kept free on each switch', '%'], sfp_per_l1: ['Spare SFPs on each L1', ''], rack_u_reserved: ['Rack space kept free', 'U'], dc_branches_per_feed: ['Spare DC branches per feed', ''], ac_branches: ['Spare AC branches', ''] };
  const pct = (v) => Math.round(v * 100);
  /* Network inputs are edited on the page and saved together (docs/ui/editing.md); the model checks every value. */
  const NF = {  // key -> [path, kind]; an emptied spare is removed, so the project's value applies
    ied_count: [['network', 'ied_count'], 'int'], topology: [['network', 'topology'], 'text'], ring_max_switches: [['network', 'ring_max_switches'], 'int'],
    ...Object.fromEntries(Object.keys(SPARES).map((k) => [k, [['spares', k], k === 'port_fraction' ? 'pct' : 'int']]))
  };
  /* The model takes equipment only with its redundant L1 and L2 switches (Substation, ADR 0013), so the first add writes both. */
  const FIRST = 'Start with the core switches: the L2 switch you pick, and the L1 switches the sizing picks. Then add the rest.';
  const startButton = (cls) => `<button class="btn ${cls}" data-action="eq-start">${icon('plus')}Add the core switches…</button>`;
  const EQ = { qty: 'int', l2_ports: 'int', role: 'text', redundant: 'bool', part_id: 'text' };
  function nf(key) {  // [path, kind]; an equipment cell is eq.<row>.<field>
    const m = /^eq\.(\d+)\.(\w+)$/.exec(key);
    return m ? [['equipment', Number(m[1]), m[2]], EQ[m[2]]] : NF[key];
  }
  function netSaved(p, key) {
    const m = /^eq\.(\d+)\.(\w+)$/.exec(key);
    if (m) { const v = (p.equipment[Number(m[1])] || {})[m[2]]; return typeof v === 'boolean' ? String(v) : v; }
    if (key in p.network) return key === 'ied_count' && !p.network.ied_count ? '' : p.network[key];
    const row = p.spares.find((x) => x.key === key);
    return row ? (key === 'port_fraction' ? pct(row.value) : row.value) : '';
  }
  const NET = App.draftForm({
    prefix: 'n-', screen: 'network', file: 'substation.yaml', label: 'Save network', spec: nf,
    saved: (key) => (SUB.page && SUB.page.network ? netSaved(SUB.page, key) : ''),
    check: (path, value) => Bridge.call('check_substation_field', S.project.file, S.sub, path, value),
    write: (path, value) => Bridge.call('set_substation_field', S.project.file, S.sub, path, value),
    done: (page) => { if (page.id === S.sub) { SUB.page = page; App.network.reload(); } }
  });
  const netShown = (p, key) => NET.shown(key);
  const marked = NET.mark;
  function netInput(p, key, unit, help, o = {}) {
    const err = NET.errors[key], v = netShown(p, key);
    let html = input('n-' + key, v == null ? '' : String(v), { num: true, mono: true, invalid: !!err || !!o.required, placeholder: o.required ? 'Required' : '' });
    if (unit) html = `<div class="input-affix">${html}<span class="affix">${esc(unit)}</span></div>`;
    return marked(key, field(esc(o.label), html, help, err ? esc(err) : o.required ? 'Enter the number of field IEDs, for example 40.' : ''));
  }
  /* A new substation: what is left, in the order that works (components.md, Setup card). Gone once all is done. */
  function setupCard(p) {
    const hasIed = !!p.network.ied_count, hasEq = p.equipment.length > 0, hasPanels = !!p.panels;
    if (hasIed && hasEq && hasPanels) return '';
    const step = (done, now, title, text, act = '') => `<li class="${done ? 'done' : now ? 'now' : ''}">${icon(done ? 'check' : 'info')}<div><b>${title}</b><div class="muted small">${text}</div></div>${act}</li>`;
    return `<div class="setup" style="margin-bottom:var(--space-5)"><h3>Set up ${esc(p.name)}</h3><p class="muted small" style="margin-top:var(--space-1)">The panels appear on their own once the network and equipment are entered.</p>
      <ol>${step(true, false, 'Substation created', 'Its settings and calculation documents are in the register with blank numbers.', '<button class="btn btn--ghost btn--sm" data-action="goto" data-to="#/project/documents">Fill in numbers</button>')}
      ${step(hasIed, !hasIed, 'Enter the number of field IEDs', 'It sizes the L1 switches. It is never listed in the BOM.', hasIed ? '' : '<button class="btn btn--secondary btn--sm" data-action="net-focus-ied">Enter</button>')}
      ${step(hasEq, hasIed && !hasEq, 'Add the equipment', `Switches, patch panel, gateway, firewall and the rest. ${FIRST}`, hasEq ? '' : startButton('btn--secondary btn--sm'))}
      ${step(hasPanels, hasIed && hasEq && !hasPanels, 'Look at the panels', 'Check the layout, then run Checks and build.', hasIed && hasEq ? '<a class="btn btn--primary btn--sm" href="#/panels">See the panels</a>' : '')}</ol></div>`;
  }
  /* One equipment row: its cells are drafted like the inputs above; Remove writes at once, with Undo. */
  function eqRow(p, e, i) {
    const k = (f) => `eq.${i}.${f}`, err = (f) => NET.errors[k(f)], ch = (f) => (k(f) in NET.draft ? ' class="changed"' : '');
    const cellErr = ['part_id', 'role', 'redundant', 'qty', 'l2_ports'].map((f) => err(f) && `<span class="err small" id="n-${k(f)}-err">${icon('error')}<span>${esc(err(f))}</span></span>`).filter(Boolean).join('');
    const swap = k('part_id') in NET.draft ? NET.draft[k('part_id')] : '';
    if (swap) return `<tr><td class="changed"><span class="mono">${esc(swap)}</span><span class="cell-sub">Was <span class="mono">${esc(e.part_id || '—')}</span> · <span class="mono">${esc(e.id)}</span> · saved with the rest</span>${cellErr}${changeButton(e, i)}</td>${eqCells(p, e, i)}`;
    return `<tr><td><span class="mono">${esc(e.part_id || '—')}</span>${e.device && !e.device.known ? `<span class="err small">${icon('error')}<span>Not in ${esc(p.project.library.name)} ${esc(p.project.library.version)}</span></span>` : `<span class="cell-sub">${esc([e.device && e.device.make, e.device && e.device.model].filter(Boolean).join(' ') || (e.role === 'l1_switch' && !e.part_id ? 'Picked from the library by the sizing' : ''))} · <span class="mono">${esc(e.id)}</span></span>`}${cellErr}${changeButton(e, i)}</td>${eqCells(p, e, i)}`;
  }
  function eqCells(p, e, i) {
    const k = (f) => `eq.${i}.${f}`, err = (f) => NET.errors[k(f)], ch = (f) => (k(f) in NET.draft ? ' class="changed"' : '');
    const red = netShown(p, k('redundant')) === 'true', l1 = netShown(p, k('role')) === 'l1_switch';
    const num = (f, label) => `<input class="input input--num input--mono" id="n-${k(f)}" aria-label="${label}, ${esc(e.id)}" value="${esc(netShown(p, k(f)))}" ${err(f) ? 'aria-invalid="true"' : ''} data-dirty="1">`;
    return `
      <td${ch('role')}><select class="select" id="n-${k('role')}" aria-label="Role, ${esc(e.id)}" data-dirty="1">${Object.entries(ROLES).map(([v, t]) => `<option value="${v}" ${v === netShown(p, k('role')) ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select></td>
      <td${ch('redundant')}><label class="check"><input type="checkbox" id="n-${k('redundant')}" ${red ? 'checked' : ''} data-dirty="1"><span class="sr-only">A and B units, ${esc(e.id)}</span></label></td>
      <td class="num"${ch('qty')}>${l1 ? '<span class="muted">Sized</span>' : num('qty', 'Quantity')}</td>
      <td class="num"${ch('l2_ports')}>${num('l2_ports', 'L2 ports')}</td>
      <td class="num">${e.device && e.device.height_u != null ? (e.device.height_u ? e.device.height_u + ' U' : 'DIN') : '—'}</td>
      <td><button class="btn btn--ghost btn--sm btn--icon" data-action="eq-remove" data-i="${i}" aria-label="Remove ${esc(e.id)}" title="${Object.keys(NET.draft).length ? 'Save or discard the changes first' : 'Remove'}" ${Object.keys(NET.draft).length ? 'disabled' : ''}>${icon('trash')}</button></td></tr>`;
  }
  const relaid = (page) => { SUB.page = page; App.network.reload(); App.render(); };
  ACTIONS['eq-remove'] = (el) => {
    const i = Number(el.dataset.i), file = S.project.file, sub = S.sub, id = SUB.page.equipment[i].id;
    Bridge.call('remove_equipment', file, sub, i).then((r) => {
      relaid(r.page);
      toast(`Removed ${id}`, 'trash', () => Bridge.call('add_equipment', file, sub, r.row, i).then(relaid).catch((err) => toast(err.message, 'error')));
    }).catch((err) => toast(err.message, 'error'));
  };
  /* Add device: a library part, its role, and A and B units; the id names it in the layout and must be new. */
  const ROLE_OF = { firewall: 'firewall', patch_panel: 'fopp', network_switch: 'l2_switch' };
  let parts = null;
  const freeId = (part, taken) => { const base = (part || 'device').toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^[^a-z0-9]+|-+$/g, '') || 'device'; let id = base, n = 2; while (taken.includes(id)) id = `${base}-${n++}`; return id; };
  ACTIONS['eq-add'] = () => {
    const open = () => {
      const taken = SUB.page.equipment.map((e) => e.id), first = parts[0];
      App.dialog({ title: 'Add device', body: `<div class="form">
        ${field('Part', `<select class="select" id="eq-part">${parts.map((d) => `<option value="${esc(d.part_id)}">${esc(d.part_id)}${d.make || d.model ? ' · ' + esc([d.make, d.model].filter(Boolean).join(' ')) : ''}</option>`).join('')}</select>`, 'From the active library.')}
        ${field('Role', select('eq-role', Object.entries(ROLES), first ? ROLE_OF[first.category] || 'other' : 'other'))}
        <label class="check"><input type="checkbox" id="eq-red">A and B units (redundant)</label>
        ${field('Id', input('eq-id', first ? freeId(first.part_id, taken) : '', { mono: true }), 'Names the row in the layout. Not printed.')}
        <div id="eq-err" class="err small" role="alert"></div></div>`,
        actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="eq-add-do">Add device</button>' });
    };
    if (parts) return open();
    Bridge.call('library_overview').then((o) => { parts = o.devices; if (!parts.length) toast('The active library has no devices.', 'error'); else open(); }).catch((err) => toast(err.message, 'error'));
  };
  document.addEventListener('change', (e) => {
    if (e.target.id !== 'eq-part' || !parts) return;
    const d = parts.find((x) => x.part_id === e.target.value), taken = SUB.page.equipment.map((x) => x.id);
    document.getElementById('eq-id').value = freeId(d.part_id, taken);
    document.getElementById('eq-role').value = ROLE_OF[d.category] || 'other';
  });
  const withParts = (then) => (parts ? then() : Bridge.call('library_overview').then((o) => { parts = o.devices; then(); }).catch((err) => toast(err.message, 'error')));
  ACTIONS['eq-start'] = () => withParts(() => {
    const switches = parts.filter((d) => d.category === 'network_switch');
    if (!switches.length) { toast('The active library has no network switches.', 'error'); return; }
    App.dialog({ title: 'Add the core switches', body: `<div class="form">
      ${field('L2 switch', `<select class="select" id="es-l2">${switches.map((d) => `<option value="${esc(d.part_id)}">${esc(d.part_id)}${d.make || d.model ? ' · ' + esc([d.make, d.model].filter(Boolean).join(' ')) : ''}</option>`).join('')}</select>`, 'One redundant pair, A and B.')}
      <p class="small muted">The L1 switches come as a redundant pair too. Their model and count are picked by the sizing from the IED count; you can pin a model in the ranking afterwards.</p>
      <div id="es-err" class="err small" role="alert"></div></div>`,
      actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="eq-start-do">Add the switches</button>' });
  });
  ACTIONS['eq-start-do'] = () => {
    Bridge.call('start_equipment', S.project.file, S.sub, document.getElementById('es-l2').value).then((page) => { App.closeDialog(); relaid(page); toast('Added the L1 and L2 switches', 'check'); })
      .catch((err) => { document.getElementById('es-err').innerHTML = `${icon('error')}<span>${esc(err.message)}</span>`; });
  };
  ACTIONS['eq-add-do'] = () => {
    const v = (id) => document.getElementById(id), row = { id: v('eq-id').value.trim(), part_id: v('eq-part').value, role: v('eq-role').value };
    if (v('eq-red').checked) row.redundant = true;
    Bridge.call('add_equipment', S.project.file, S.sub, row, null).then((page) => { App.closeDialog(); relaid(page); toast(`Added ${row.id}`, 'check'); })
      .catch((err) => { v('eq-err').innerHTML = `${icon('error')}<span>${esc(err.message)}</span>`; });
  };
  /* Change part: the saved part's alternatives first, then the rest of the active library; the pick is a Network edit like Use this instead. */
  const changeButton = (e, i) => (e.part_id ? `<button class="btn btn--ghost btn--sm" style="padding-inline:0;min-height:0" data-action="eq-part-change" data-i="${i}" aria-label="Change the part of ${esc(e.id)}">Change…</button>` : '');
  const partText = (d) => `${esc(d.part_id)}${d.make || d.model ? ' · ' + esc([d.make, d.model].filter(Boolean).join(' ')) : ''}`;
  ACTIONS['eq-part-change'] = (el) => withParts(() => {
    const i = Number(el.dataset.i), e = SUB.page.equipment[i], was = e.part_id, now = NET.shown(`eq.${i}.part_id`);
    Bridge.call('library_alternatives', was).catch(() => ({ rows: [] })).then((a) => {
      const known = new Set(parts.map((d) => d.part_id));
      const alts = a.rows.filter((r) => !r.is_self && known.has(r.part_id)), altIds = new Set(alts.map((r) => r.part_id));
      const watts = (r) => { const w = Math.round(Math.abs(r.power_delta_w || 0) * 10) / 10; return w ? ` (${r.power_delta_w > 0 ? '+' : '−'}${w} W)` : ''; };
      const opt = (id, text) => `<option value="${esc(id)}" ${id === now ? 'selected' : ''}>${text}</option>`;
      const rest = parts.filter((d) => d.part_id !== was && !altIds.has(d.part_id));
      const same = parts.find((d) => d.part_id === was);
      App.dialog({ title: `Change the part of ${esc(e.id)}`, body: `<div class="form">
        ${field('Part', `<select class="select" id="eq-chg-part">${opt(was, `${same ? partText(same) : esc(was)} · as saved`)}
          ${alts.length ? `<optgroup label="Alternatives to ${esc(was)}">${alts.map((r) => opt(r.part_id, partText(r) + esc(watts(r)))).join('')}</optgroup>` : ''}
          <optgroup label="Other parts in the library">${rest.map((d) => opt(d.part_id, partText(d))).join('')}</optgroup></select>`,
          alts.length ? 'Alternatives fit the same place; the power change is per unit.' : `The library lists no alternatives to ${esc(was)}.`)}
        <p class="small muted">The row keeps its id, role and quantities. The change is saved with the rest of the network.</p></div>`,
        actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="eq-part-change-do" data-i="${i}">Change part</button>` });
    });
  });
  ACTIONS['eq-part-change-do'] = (el) => {
    const key = `eq.${el.dataset.i}.part_id`, value = NET.set(key, document.getElementById('eq-chg-part').value);
    App.closeDialog(); S.dirty = NET.dirty(); App.render();
    if (value == null) return;
    Bridge.call('check_substation_field', S.project.file, S.sub, nf(key)[0], value).then((msg) => {
      if (NET.draft[key] !== value) return;
      if (msg) NET.errors[key] = msg; else delete NET.errors[key];
      App.render();
    }).catch(() => {});
  };
  /* Use this instead (docs/ui/editing.md, Alternatives): the chosen rows get the other part as an unsaved Network edit. */
  App.holdParts = (indices, part) => {
    page();  // the open substation's draft; a different substation's would be dropped on load
    indices.forEach((i) => { NET.draft[`eq.${i}.part_id`] = part; delete NET.errors[`eq.${i}.part_id`]; });
    S.dirty = true; App.go('#/network');
  };
  ACTIONS['net-focus-ied'] = () => { const el = document.getElementById('n-ied_count'); if (el) { el.scrollIntoView({ block: 'center' }); el.focus(); } };
  SCREENS.network = () => {
    if (!real()) return example.network();
    const p = page(); if (!p) return waiting('Network');
    if (!p.network) return `<div class="page">${pageHead('Network', 'What the substation contains and how the network is sized.')}${problems(p)}</div>`;
    const eq = p.equipment, unset = !p.network.ied_count && !('ied_count' in NET.draft), topo = netShown(p, 'topology'), dirty = Object.keys(NET.draft).length > 0;
    return `<div class="page">${pageHead('Network', 'What the substation contains and how the network is sized. The panels are laid out from this.', '', '', '')}
      ${problems(p)}${setupCard(p)}
      <div class="net-grid">
        <div class="stack" style="gap:var(--space-6)">
          <section><h3>Field network</h3>
            <div class="form form--2" style="margin-top:var(--space-3)">
              ${netInput(p, 'ied_count', 'IEDs', unset ? '' : 'Sizes the L1 switches; never a BOM row.', { label: 'Field IEDs', required: unset })}
              ${marked('topology', field('Topology', select('n-topology', [['star', 'Star'], ['ring', 'Ring']], topo, { invalid: !!NET.errors.topology }), topo === 'ring' ? 'L1 switches in rings; two ports close each ring.' : 'One uplink per L1 switch plus an A–B interlink.', NET.errors.topology ? esc(NET.errors.topology) : ''))}
              ${topo === 'ring' ? netInput(p, 'ring_max_switches', '', 'Most L1 switches in one ring.', { label: 'Switches per ring' }) : ''}
            </div></section>
          <section><h3>L1 switch model</h3>${App.network.rankTable()}</section>
          <section><h3>Equipment</h3>
            <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">What the substation has, before any panel exists. Redundant devices come as an A and a B unit.</p>
            ${eq.length ? `<div class="table-wrap"><table class="table"><caption class="sr-only">Equipment</caption><thead><tr><th style="min-width:190px">Device</th><th style="width:160px">Role</th><th style="width:64px">A and B</th><th class="num" style="width:80px">Quantity</th><th class="num" style="width:80px">L2 ports</th><th class="num" style="width:64px">Height</th><th style="width:44px"><span class="sr-only">Remove</span></th></tr></thead><tbody>
              ${eq.map((e, i) => eqRow(p, e, i)).join('')}</tbody></table>
              <div class="table-foot"><span>${plural(eq.length, 'item')} · height and mounting come from the library</span><span><button class="btn btn--secondary btn--sm" data-action="eq-add" ${dirty ? 'disabled title="Save or discard the changes first"' : ''}>${icon('plus')}Add device</button></span></div></div>` : `<div class="empty"><b>No equipment yet.</b><div class="muted small" style="margin:var(--space-1) 0 var(--space-3)">${FIRST}</div>${startButton('btn--primary')}</div>`}</section>
          <section><h3>Spares</h3>
            <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">Every spare starts from the project's shared defaults; the ones this substation changes are marked. Empty a field to use the project's value again.</p>
            <div class="form form--3">${p.spares.map((s) => { const [label, unit] = SPARES[s.key] || [s.key, '']; const d = s.key === 'port_fraction' ? pct(s.default) : s.default; return netInput(p, s.key, unit, s.changed ? `Changed from ${d}${unit && unit !== '%' ? ' ' + unit : unit}.` : 'Project default.', { label }); }).join('')}</div></section>
        </div>
        <aside class="net-result" aria-live="polite">${App.network.resultCard()}</aside>
      </div>${NET.bar()}</div>`;
  };
})();
