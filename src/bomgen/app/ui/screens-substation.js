/* Screens: substation Settings and the Network inputs on bomgen.app.api (plan M10c).
   Read-only until the substation writers exist. The L1 ranking and the Result card come from screens-panels.js.
   Opened in a plain browser, the prototype's screens in screens-project.js and screens-layout.js are used instead. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, pageHead, toast } = App;
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
    if (SUB.key !== key) Object.assign(SUB, { key, state: 'idle', page: null, error: null });
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
  const note = `<p class="muted small" style="margin-bottom:var(--space-4);max-width:68ch">${esc(LATER)}</p>`;
  const changed = (row, fmt = (v) => v) => (row.changed ? badge('info', `Changed from ${fmt(row.default)}`) : '<span class="muted small">Default</span>');

  /* ---------- Settings ---------- */
  const SHEETS = { power_consumption: 'Power Consumption', heat_dissipation: 'Heat Dissipation', heat_calculations: 'Heat Calculations' };
  const CONSTANTS = {
    dc_voltage_v: ['DC supply voltage', 'V'], ac_voltage_v: ['AC supply voltage', 'V'], power_margin: ['Power margin', '×'], current_factor: ['Current factor', '×'],
    btu_per_w: ['Heat conversion', 'BTU/h per W'], t_max_c: ['Maximum ambient', '°C'], t_int_c: ['Internal limit', '°C'],
    air_constant_m3k_per_wh: ['Air constant', 'm³·K/Wh'], steel_coefficient_w_per_m2c: ['Sheet-steel heat transfer', 'W/m²·°C'], min_main_mcb_a: ['Minimum main MCB', 'A']
  };
  const tabsSettings = [['general', 'General'], ['documents', 'Documents'], ['output', 'Output'], ['constants', 'Design constants'], ['loose', 'Loose material'], ['yaml', 'YAML']];
  SCREENS.settings = () => {
    if (!real()) return example.settings();
    const p = page(); if (!p) return waiting('Settings');
    const rb = App.route().b; if (tabsSettings.some(([k]) => k === rb)) S.tab.settings = rb;
    const t = p.calculations || S.tab.settings === 'yaml' ? S.tab.settings : 'yaml';
    const body = { general, documents, output, constants, loose, yaml }[t](p);
    return `<div class="page">${pageHead('Settings', `Settings of ${esc(p.name)} only. Project-wide values are on the project page.`)}
      ${problems(p)}${tabs('settings', tabsSettings, t, 'Substation settings')}
      <div role="tabpanel" aria-labelledby="tab-settings-${t}">${t === 'yaml' ? '' : note}${body}</div></div>`;
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
  const loose = (p) => { const m = p.loose_material; return m ? `<p class="muted" style="max-width:68ch;margin-bottom:var(--space-4)">Items that are not mounted in any cabinet. They appear as a second table, “${esc(m.title)}”, under the <span class="mono">${esc(m.host_panel)}</span> BOM.</p>
    <div class="table-wrap" style="max-width:1100px"><table class="table"><thead><tr><th>Part</th><th>Designation</th><th class="num" style="width:70px">Qty</th><th style="width:130px">Fed from</th><th>Child parts</th></tr></thead>
    <tbody>${m.items.map((l) => `<tr><td class="mono">${esc(l.part_id)}</td><td>${esc(l.tag || '—')}</td><td class="num">${esc(l.qty)}</td><td>${l.fed_from ? `<span class="mono">${esc(l.fed_from)}</span>` : '<span class="muted">—</span>'}</td><td class="mono">${esc(l.children.join(', ') || '—')}</td></tr>`).join('')}</tbody></table>
    <div class="table-foot"><span>${plural(m.items.length, 'item')}</span></div></div>` : '<div class="empty"><b>No loose material.</b><div class="muted small">This substation lists no items outside the cabinets.</div></div>'; };
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
  SCREENS.network = () => {
    if (!real()) return example.network();
    const p = page(); if (!p) return waiting('Network');
    if (!p.network) return `<div class="page">${pageHead('Network', 'What the substation contains and how the network is sized.')}${problems(p)}</div>`;
    const n = p.network, eq = p.equipment, unset = !n.ied_count;
    return `<div class="page">${pageHead('Network', 'What the substation contains and how the network is sized. The panels are laid out from this.')}
      ${problems(p)}${unset ? `<div style="margin-bottom:var(--space-4)">${banner('warn', '<b>The network is not set up yet.</b> Write the number of field IEDs and the equipment in substation.yaml.')}</div>` : ''}${note}
      <div class="net-grid">
        <div class="stack" style="gap:var(--space-6)">
          <section><h3>Field network</h3>
            <div class="form form--2" style="margin-top:var(--space-3)">
              ${field('Field IEDs', `<div class="input-affix">${ro(input('n-ied', unset ? '' : n.ied_count, { num: true, mono: true, invalid: unset, placeholder: 'Required' }))}<span class="affix">IEDs</span></div>`, 'Never listed in the BOM. Only used to size the L1 switches.')}
              ${field('Topology', ro(input('n-topo', n.topology === 'ring' ? 'Ring' : 'Star')), n.topology === 'star' ? 'Each L1 switch has one uplink to its L2 switch plus an A–B interlink.' : 'L1 switches are joined in rings. Two ports close each ring.')}
              ${n.topology === 'ring' ? field('Switches per ring', ro(input('n-ring', n.ring_max_switches, { num: true, mono: true })), 'Most L1 switches in one ring.') : ''}
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
            <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">Every spare starts from the project's shared defaults; the ones this substation changes are marked.</p>
            <div class="form form--3">${p.spares.map((s) => { const [label, unit] = SPARES[s.key] || [s.key, '']; const v = s.key === 'port_fraction' ? pct(s.value) : s.value; return field(label, fixed(v, unit), s.changed ? `Changed from ${s.key === 'port_fraction' ? pct(s.default) : s.default}${unit && unit !== '%' ? ' ' + unit : unit}.` : 'Project default.'); }).join('')}</div></section>
        </div>
        <aside class="net-result" aria-live="polite">${App.network.resultCard()}</aside>
      </div></div>`;
  };
})();
