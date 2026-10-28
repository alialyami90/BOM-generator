/* Screens: substation Settings and the Network inputs on bomgen.app.api (plan M10c).
   Settings are read-only until their writers are wired; the Network inputs are edited here (M17c). The L1 ranking and the Result card come from screens-panels.js.
   Opened in a plain browser, the prototype's screens in screens-project.js and screens-layout.js are used instead. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, select, pageHead, toast } = App;
  const example = { settings: SCREENS.settings, network: SCREENS.network };
  const LATER = 'Editing substations in the app is not available yet. Edit substation.yaml, then open the project again.';
  const ro = (html) => html.replace('data-dirty="1"', 'readonly').replace('class="input', 'class="ctl input');
  const fixed = (v, unit) => `<div class="input-affix">${ro(input('x', v, { num: true, mono: true }))}${unit ? `<span class="affix">${esc(unit)}</span>` : ''}</div>`;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;

  /* ---------- data: one substation page per (project file, substation id) ---------- */
  const SUB = { key: '', state: 'idle', page: null, error: null };
  const real = () => S.backend === 'yes' && S.project && S.project.real && S.sub;
  function page() {
    const key = `${S.project.file}#${S.sub}`;
    if (SUB.key !== key) { Object.assign(SUB, { key, state: 'idle', page: null, error: null }); NET.draft = {}; NET.errors = {}; }
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
    air_constant_m3k_per_wh: ['Air constant', 'm³·K/Wh'], steel_coefficient_w_per_m2c: ['Sheet-steel heat transfer', 'W/m²·°C'], min_main_mcb_a: ['Minimum main MCB', 'A']
  };
  const tabsSettings = [['general', 'General'], ['documents', 'Documents'], ['output', 'Output'], ['constants', 'Design constants'], ['yaml', 'YAML']];
  SCREENS.settings = () => {
    if (!real()) return example.settings();
    const p = page(); if (!p) return waiting('Settings');
    const rb = App.route().b; if (tabsSettings.some(([k]) => k === rb)) S.tab.settings = rb;
    const t = p.calculations || S.tab.settings === 'yaml' ? S.tab.settings : 'yaml';
    const body = { general, documents, output, constants, yaml }[t](p);
    return `<div class="page">${pageHead('Settings', `Settings of ${esc(p.name)} only. Project-wide values are on the project page.`, '', '', LATER)}
      ${problems(p)}${tabs('settings', tabsSettings, t, 'Substation settings')}
      <div role="tabpanel" aria-labelledby="tab-settings-${t}">${body}</div></div>`;
  };
  const general = (p) => `<div class="form form--2">
    ${field('Substation name', ro(input('s-name', p.name)), 'Shown in the app and in each sheet header.')}
    ${field('Substation id', ro(input('s-id', p.id, { mono: true })), 'Names the substation in the register and in tags. Not printed.')}
    <div class="span-2 section" style="margin:0">
      <h3>From the project</h3>
      <p class="lede">These come from the project and are the same for every substation in it.</p>
      <dl class="kv"><dt>Project</dt><dd>${esc(p.project.name)}</dd><dt>Client</dt><dd>${esc(p.project.client || '—')}</dd><dt>Device library</dt><dd>${esc(p.project.library.name)}, built with ${esc(p.project.library.version)}</dd></dl>
      <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary" data-action="goto" data-to="#/project/info">Open project overview</button></div>
    </div></div>`;
  const docCells = (e) => (e ? `<td class="mono">${esc(e.doc_no)}</td><td class="mono">${esc(e.rev)}</td><td class="mono">${esc(e.issue_date)}</td>` : `<td colspan="3"><span class="err small">${icon('error')}<span>Not in the register</span></span></td>`);
  const documents = (p) => `<p class="lede muted" style="max-width:68ch;margin-bottom:var(--space-4)">Each calculation sheet prints the document number, revision and issue date of the register entry it names. Cabinet BOMs choose theirs on each panel. The register itself is on the project page.</p>
    <div class="table-wrap" style="max-width:980px"><table class="table"><thead><tr><th>Sheet</th><th style="width:200px">Register document</th><th>Document no.</th><th style="width:70px">Rev</th><th style="width:120px">Issue date</th></tr></thead>
    <tbody>${p.calculations.map((c) => `<tr><td>${esc(SHEETS[c.key])}<span class="cell-sub">${esc(c.scope)}</span></td><td class="mono">${esc(c.document)}</td>${docCells(c.entry)}</tr>`).join('')}</tbody></table></div>
    <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary btn--sm" data-action="goto" data-to="#/project/documents">Open the register</button></div>`;
  const output = (p) => { const o = p.output; return `<div class="form">
    ${field('Main document', ro(input('o-main', o.document, { mono: true })), 'The document whose number and revision go into the workbook file name.')}
    ${field('File name', ro(input('o-pat', o.file_name, { mono: true })), 'Fields: <span class="mono">{doc_no}</span> and <span class="mono">{rev}</span>.')}
    ${o.result ? `<div class="banner banner--info">${icon('info')}<div class="grow"><b>Result:</b> <span class="mono">${esc(o.result)}</span></div></div>` : banner('bad', `<b>No file name.</b> The main document <span class="mono">${esc(o.document)}</span> is not in the register.`)}
    <div class="section" style="margin:0"><h3>Calculation sheet names</h3><p class="lede">Cabinet sheets are named by each panel's sheet name.</p>
    <div class="stack">${Object.keys(SHEETS).map((k, i) => field(['Power', 'Heat dissipation', 'Heat calculations'][i], ro(input('o-sh' + i, o.sheet_names[k])))).join('')}</div></div></div>`; };
  const constants = (p) => `<p class="muted" style="max-width:68ch;margin-bottom:var(--space-4)">Defaults come from the project's shared defaults. A value this substation writes itself is marked.</p>
    <div class="table-wrap" style="max-width:820px"><table class="table"><thead><tr><th>Constant</th><th class="num" style="width:130px">Value</th><th>Unit</th><th style="width:170px">Default</th></tr></thead>
    <tbody>${p.constants.map((c) => { const [label, unit] = CONSTANTS[c.key] || [c.key, '']; return `<tr><td>${esc(label)}<span class="cell-sub mono">${esc(c.key)}</span></td><td>${ro(input('c-' + c.key, c.value, { num: true, mono: true }))}</td><td class="muted">${esc(unit)}</td><td>${changed(c)}</td></tr>`; }).join('')}</tbody></table></div>`;
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
  const NET = { draft: {}, errors: {}, saving: false };
  const NF = {  // key -> [path, kind]; an emptied spare is removed, so the project's value applies
    ied_count: [['network', 'ied_count'], 'int'], topology: [['network', 'topology'], 'text'], ring_max_switches: [['network', 'ring_max_switches'], 'int'],
    ...Object.fromEntries(Object.keys(SPARES).map((k) => [k, [['spares', k], k === 'port_fraction' ? 'pct' : 'int']]))
  };
  function netSaved(p, key) {
    if (key in p.network) return key === 'ied_count' && !p.network.ied_count ? '' : p.network[key];
    const row = p.spares.find((x) => x.key === key);
    return row ? (key === 'port_fraction' ? pct(row.value) : row.value) : '';
  }
  const netShown = (p, key) => (key in NET.draft ? NET.draft[key] : netSaved(p, key));
  function toModel(kind, raw) {  // [value for the file, a message when it cannot be read]
    const t = String(raw == null ? '' : raw).trim();
    if (!t) return [null, null];
    if (kind === 'text') return [t, null];
    if (kind === 'int') return /^\d+$/.test(t) ? [Number(t), null] : [null, 'Enter a whole number, for example 40.'];
    return /^\d+(\.\d+)?$/.test(t) ? [Math.round(Number(t) * 10) / 1000, null] : [null, 'Enter a percentage, for example 20.'];
  }
  const marked = (key, html) => (key in NET.draft ? html.replace('<div class="field">', '<div class="field changed">') : html);
  function netInput(p, key, unit, help, o = {}) {
    const err = NET.errors[key], v = netShown(p, key);
    let html = input('n-' + key, v == null ? '' : String(v), { num: true, mono: true, invalid: !!err || !!o.required, placeholder: o.required ? 'Required' : '' });
    if (unit) html = `<div class="input-affix">${html}<span class="affix">${esc(unit)}</span></div>`;
    return marked(key, field(esc(o.label), html, help, err ? esc(err) : o.required ? 'Enter the number of field IEDs, for example 40.' : ''));
  }
  function netBar() {
    const n = Object.keys(NET.draft).length, bad = Object.keys(NET.errors).length;
    if (!n && !NET.saving) return '';
    return `<div class="savebar${bad ? ' savebar--bad' : ''}" role="region" aria-label="Unsaved changes"><span class="savebar-msg">${NET.saving ? '<span class="spinner"></span><b>Saving…</b>' : bad ? `${icon('error')}<b>${bad} ${bad === 1 ? 'field needs' : 'fields need'} fixing</b> before you can save.` : `<span class="dot dot--warn" aria-hidden="true"></span><b>${plural(n, 'unsaved change')}</b> · saved to substation.yaml`}</span>
      <span class="sp"></span><button class="btn btn--secondary" data-action="net-discard" ${NET.saving ? 'disabled' : ''}>Discard</button><button class="btn btn--primary" data-action="net-save" ${NET.saving || bad ? 'disabled' : ''}>${icon('save')}Save network <kbd class="kbd">Ctrl+S</kbd></button></div>`;
  }
  /* A new substation: what is left, in the order that works (components.md, Setup card). Gone once all is done. */
  function setupCard(p) {
    const hasIed = !!p.network.ied_count, hasEq = p.equipment.length > 0, hasPanels = !!p.panels;
    if (hasIed && hasEq && hasPanels) return '';
    const step = (done, now, title, text, act = '') => `<li class="${done ? 'done' : now ? 'now' : ''}">${icon(done ? 'check' : 'info')}<div><b>${title}</b><div class="muted small">${text}</div></div>${act}</li>`;
    return `<div class="setup" style="margin-bottom:var(--space-5)"><h3>Set up ${esc(p.name)}</h3><p class="muted small" style="margin-top:var(--space-1)">The panels appear on their own once the network and equipment are entered.</p>
      <ol>${step(true, false, 'Substation created', 'Its settings and calculation documents are in the register with blank numbers.', '<button class="btn btn--ghost btn--sm" data-action="goto" data-to="#/project/documents">Fill in numbers</button>')}
      ${step(hasIed, !hasIed, 'Enter the number of field IEDs', 'It sizes the L1 switches. It is never listed in the BOM.', hasIed ? '' : '<button class="btn btn--secondary btn--sm" data-action="net-focus-ied">Enter</button>')}
      ${step(hasEq, hasIed && !hasEq, 'Add the equipment', 'Switches, patch panel, gateway, firewall and the rest. Redundant devices come as an A and a B unit. For now they are written under <span class="mono">equipment</span> in substation.yaml.')}
      ${step(hasPanels, hasIed && hasEq && !hasPanels, 'Look at the panels', 'Check the layout, then run Checks and build.', hasIed && hasEq ? '<a class="btn btn--primary btn--sm" href="#/panels">See the panels</a>' : '')}</ol></div>`;
  }
  ACTIONS['net-focus-ied'] = () => { const el = document.getElementById('n-ied_count'); if (el) { el.scrollIntoView({ block: 'center' }); el.focus(); } };
  SCREENS.network = () => {
    if (!real()) return example.network();
    const p = page(); if (!p) return waiting('Network');
    if (!p.network) return `<div class="page">${pageHead('Network', 'What the substation contains and how the network is sized.')}${problems(p)}</div>`;
    const eq = p.equipment, unset = !p.network.ied_count && !('ied_count' in NET.draft), topo = netShown(p, 'topology');
    return `<div class="page">${pageHead('Network', 'What the substation contains and how the network is sized. The panels are laid out from this.', '', '', 'Equipment rows cannot be edited in the app yet. Edit substation.yaml, then open the project again.')}
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
            ${eq.length ? `<div class="table-wrap"><table class="table"><thead><tr><th>Device</th><th style="width:150px">Role</th><th style="width:90px">A and B</th><th class="num" style="width:90px">L2 ports</th><th class="num" style="width:64px">Height</th></tr></thead><tbody>
              ${eq.map((e) => `<tr><td><span class="mono">${esc(e.part_id || '—')}</span>${e.device && !e.device.known ? `<span class="err small">${icon('error')}<span>Not in ${esc(p.project.library.name)} ${esc(p.project.library.version)}</span></span>` : `<span class="cell-sub">${esc([e.device && e.device.make, e.device && e.device.model].filter(Boolean).join(' ') || (e.role === 'l1_switch' && !e.part_id ? 'Picked from the library by the sizing' : e.id))}${e.role === 'l1_switch' ? ' · count from the sizing' : e.qty > 1 ? ` · ${e.qty} units` : ''}</span>`}</td>
                <td>${esc(ROLES[e.role] || e.role)}</td><td>${e.redundant ? 'A + B' : e.side !== 'none' ? 'Side ' + esc(e.side.toUpperCase()) : '<span class="muted">Common</span>'}</td>
                <td class="num">${e.l2_ports || '<span class="muted">0</span>'}</td><td class="num">${e.device && e.device.height_u != null ? (e.device.height_u ? e.device.height_u + ' U' : 'DIN') : '—'}</td></tr>`).join('')}</tbody></table>
              <div class="table-foot"><span>${plural(eq.length, 'item')} · height and mounting come from the library</span></div></div>` : `<div class="empty"><b>No equipment yet.</b><div class="muted small">The switches, gateways and other devices this substation needs go under <span class="mono">equipment</span>.</div></div>`}</section>
          <section><h3>Spares</h3>
            <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">Every spare starts from the project's shared defaults; the ones this substation changes are marked. Empty a field to use the project's value again.</p>
            <div class="form form--3">${p.spares.map((s) => { const [label, unit] = SPARES[s.key] || [s.key, '']; const d = s.key === 'port_fraction' ? pct(s.default) : s.default; return netInput(p, s.key, unit, s.changed ? `Changed from ${d}${unit && unit !== '%' ? ' ' + unit : unit}.` : 'Project default.', { label }); }).join('')}</div></section>
        </div>
        <aside class="net-result" aria-live="polite">${App.network.resultCard()}</aside>
      </div>${netBar()}</div>`;
  };
  /* A field is read on change and checked by the model; the draft holds only what differs from the file. */
  document.addEventListener('change', (e) => {
    const m = /^n-(\w+)$/.exec(e.target.id || '');
    if (!m || !(m[1] in NF) || App.route().a !== 'network' || !real() || !SUB.page) return;
    const p = SUB.page, key = m[1], [path, kind] = NF[key], typed = e.target.value, was = netSaved(p, key);
    if (String(typed).trim() === String(was == null ? '' : was)) { delete NET.draft[key]; delete NET.errors[key]; queueMicrotask(App.render); return; }
    NET.draft[key] = typed;
    const [value, local] = toModel(kind, typed);
    if (local) { NET.errors[key] = local; queueMicrotask(App.render); return; }
    delete NET.errors[key]; queueMicrotask(App.render);
    if (value === null) return;  // emptied: removed on save
    Bridge.call('check_substation_field', S.project.file, S.sub, path, value).then((msg) => {
      if (NET.draft[key] !== typed || (NET.errors[key] || null) === (msg || null)) return;  // a render would drop what is being typed elsewhere
      if (msg) NET.errors[key] = msg; else delete NET.errors[key];
      App.render();
    }).catch(() => {});
  });
  const netReset = () => { NET.draft = {}; NET.errors = {}; S.dirty = false; };
  ACTIONS['net-discard'] = () => { netReset(); App.render(); toast('Changes discarded', 'undo'); };
  ACTIONS['net-save'] = () => {
    const keys = Object.keys(NET.draft), file = S.project.file, sub = S.sub, key0 = SUB.key;
    if (NET.saving || !keys.length || Object.keys(NET.errors).length) return;
    NET.saving = true; App.render();
    let saved = null;
    const next = (i) => {
      if (i === keys.length) return Promise.resolve();
      const key = keys[i], [path, kind] = NF[key];
      return Bridge.call('set_substation_field', file, sub, path, toModel(kind, NET.draft[key])[0]).then((r) => { saved = r; delete NET.draft[key]; return next(i + 1); })
        .catch((err) => { NET.errors[key] = err.message; throw err; });
    };
    next(0).then(() => { toast(`Saved ${plural(keys.length, 'change')} to substation.yaml`, 'check'); S.dirty = false; })
      .catch(() => toast('Not saved: a value was refused. It is marked on the page.', 'error'))
      .then(() => { NET.saving = false; if (saved && SUB.key === key0) { SUB.page = saved; App.network.reload(); } App.render(); });
  };
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's' && App.route().a === 'network' && Object.keys(NET.draft).length) {
      e.preventDefault(); if (document.activeElement) document.activeElement.blur(); queueMicrotask(ACTIONS['net-save']);
    }
  });
  window.addEventListener('hashchange', () => { if (App.route().a !== 'network') { NET.draft = {}; NET.errors = {}; } });
})();
