/* Screens: substation Settings, and the panel editor (read-only for generated panels). */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, select, pageHead, illus, dialog, closeDialog, toast, go, counts, $, $$, curProject } = App;
  const P = DB.sub;
  const register = () => curProject().documents.filter((d) => d.sub === 'gis01');
  const docByKey = (k) => curProject().documents.find((d) => d.key === k);
  const docOptions = () => register().map((d) => [d.key, `${d.label} (${d.key})`]);

  /* ---------- Substation settings ---------- */
  const tabsSettings = [['general', 'General'], ['documents', 'Documents'], ['output', 'Output'], ['constants', 'Design constants'], ['yaml', 'YAML']];
  SCREENS.settings = () => {
    const rb = App.route().b; if (tabsSettings.some(([k]) => k === rb)) S.tab.settings = rb;
    const t = S.tab.settings;
    const body = { general: settingsGeneral, documents: settingsDocuments, output: settingsOutput, constants: settingsConstants, yaml: settingsYaml }[t]();
    return `<div class="page">${pageHead('Settings', `Settings of ${esc(App.curSub().name)} only. Project-wide values are on the project page.`)}
      ${tabs('settings', tabsSettings, t, 'Substation settings')}
      <div role="tabpanel" aria-labelledby="tab-settings-${t}">${body}</div></div>`;
  };
  ACTIONS.save = () => { S.dirty = false; App.render(); toast('Saved substation.yaml'); };

  const settingsGeneral = () => `<div class="form form--2">
    ${field('Substation name', input('p-name', P.name), 'Shown in the app and used for the folder.')}
    ${field('Title line', input('p-sub', P.titleLine), 'Second line of each BOM title, under the project name.')}
    <div class="span-2 section" style="margin:0">
      <h3>Catalogue brands</h3>
      <p class="lede">Which make this substation takes ordering codes from. It uses the project's choice unless you set one here.</p>
      <div class="form form--3" style="margin-top:var(--space-3)">${[['mcb', 'MCBs'], ['aux', 'Aux contacts'], ['tb', 'Terminal blocks']].map(([k, t]) => { const c = DB.catalogues[k]; const pb = (curProject().brands && curProject().brands[k]) || c.active; return field(t, select('sb-' + k, [['', `Same as the project (${c.brands.find((b) => b.id === pb).name})`], ...c.brands.map((b) => [b.id, b.name])], (P.brands && P.brands[k]) || '')); }).join('')}</div>
    </div>
    <div class="span-2 section" style="margin:0">
      <h3>From the project</h3>
      <p class="lede">These come from the project and are the same for every substation in it.</p>
      <dl class="kv"><dt>Project</dt><dd>${esc(curProject().name)}</dd><dt>Client</dt><dd>${esc(curProject().client)}</dd><dt>Device library</dt><dd>${esc(curProject().library.name)}, built with ${esc(curProject().library.builtWith)}</dd></dl>
      <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary" data-action="goto" data-to="#/project/info">Open project overview</button></div>
    </div></div>`;

  const settingsDocuments = () => `<p class="lede muted" style="max-width:68ch;margin-bottom:var(--space-4)">Each calculation sheet prints the document number, revision and issue date of the register entry you pick. Cabinet BOMs choose theirs on each panel. The register itself is on the project page.</p>
    <div class="table-wrap" style="max-width:900px"><table class="table"><thead><tr><th>Sheet</th><th style="width:300px">Register document</th><th>Document no.</th><th style="width:70px">Rev</th><th style="width:120px">Issue date</th></tr></thead>
    <tbody>${P.sheetDocs.map((x, i) => { const d = docByKey(x.key); return `<tr><td>${esc(x.label)}</td><td>${select('sd' + i, docOptions(), x.key, { cls: 'ctl' })}</td><td class="mono">${esc(d.docNo)}</td><td class="mono">${esc(d.rev)}</td><td class="mono">${esc(d.issue)}</td></tr>`; }).join('')}</tbody></table></div>
    <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary btn--sm" data-action="goto" data-to="#/project/documents">Edit the register</button></div>`;

  const settingsOutput = () => `<div class="form">
    ${field('Main document', select('o-main', docOptions(), P.mainDoc), 'The document whose number and revision go into the workbook file name.')}
    ${field('File name', input('o-pat', P.output.pattern, { mono: true }), 'Fields: <span class="mono">{doc_no}</span> and <span class="mono">{rev}</span>.')}
    <div class="banner banner--info">${icon('info')}<div class="grow"><b>Result:</b> <span class="mono">${esc(P.output.fileName)}</span></div></div>
    <div class="section" style="margin:0"><h3>Sheet names</h3><p class="lede">Cabinet sheets are named by each panel's sheet name (1 to 5). The Loose Material sheet is written only when the substation has loose material; its list is on the Loose material page.</p>
    <div class="stack">${P.output.sheets.map((s, i) => field(['Loose material', 'Power', 'Heat dissipation', 'Heat calculations'][i], input('o-sh' + i, s))).join('')}</div></div></div>`;

  const settingsConstants = () => `<p class="muted" style="max-width:68ch;margin-bottom:var(--space-4)">Defaults come from the spec and the project's shared defaults. Change one only when this substation's design basis says so; changed values are marked.</p>
    <div class="table-wrap" style="max-width:820px"><table class="table"><thead><tr><th>Constant</th><th class="num" style="width:130px">Value</th><th>Unit</th><th style="width:150px">Default</th></tr></thead>
    <tbody>${P.constants.map((c, i) => `<tr><td>${esc(c.label)}<span class="cell-sub mono">${esc(c.key)}</span></td><td>${input('c' + i, c.value, { num: true, mono: true }).replace('class="input', 'class="ctl input')}</td><td class="muted">${esc(c.unit)}</td><td>${c.value === c.def ? '<span class="muted small">Default</span>' : `${badge('info', 'Changed from ' + c.def)} <button class="btn btn--ghost btn--sm" data-action="reset-const" data-i="${i}">Reset</button>`}</td></tr>`).join('')}</tbody></table>
    <div class="table-foot"><span>${P.constants.filter((c) => c.value !== c.def).length} changed from the default</span><button class="btn btn--ghost btn--sm" data-action="reset-const" data-i="all" ${P.constants.some((c) => c.value !== c.def) ? '' : 'disabled'}>Reset all to defaults</button></div></div>`;
  ACTIONS['reset-const'] = (el) => { P.constants.forEach((c, i) => { if (el.dataset.i === 'all' || +el.dataset.i === i) c.value = c.def; }); S.dirty = true; S.changed.add('constants'); App.render(); };
  document.addEventListener('change', (e) => { const m = /^c(\d+)$/.exec(e.target.id || ''); if (m && P.constants[+m[1]] && /^\d+(\.\d+)?$/.test(e.target.value.trim())) { P.constants[+m[1]].value = e.target.value; App.render(); } });

  /* YAML view shared by project and panel */
  const hl = (line) => esc(line).replace(/^(\s*)(- )?([A-Za-z_][\w]*)(:)/, '$1$2<span class="k">$3</span>$4').replace(/(#.*)$/, '<span class="c">$1</span>').replace(/: ("[^"]*"|'[^']*')/, ': <span class="s">$1</span>').replace(/: (\d[\d.]*)\b/, ': <span class="n">$1</span>');
  function yamlView(file, lines, errors = {}, o = {}) {
    const hasErr = Object.keys(errors).length;
    return `<div class="toolbar"><span class="mono" style="font-size:12.5px">${esc(file)}</span>${hasErr ? badge('bad', `${hasErr} error${hasErr > 1 ? 's' : ''}`, 'error') : o.readonly ? badge('info', 'Generated', 'info') : badge('ok', 'Matches the form', 'check')}<span class="sp"></span>
      ${o.readonly ? `<span class="muted small">${icon('lock')} Read-only: written by the layout</span>` : `<button class="btn btn--secondary btn--sm" data-action="yaml-revert">Revert</button><button class="btn btn--primary btn--sm" data-action="yaml-apply" ${hasErr ? 'disabled' : ''}>Apply to form</button>`}</div>
      <div class="code" role="textbox" aria-multiline="true" aria-label="${esc(file)} source" tabindex="0">
        <div class="gut" aria-hidden="true">${lines.map((_, i) => `<div class="${errors[i + 1] ? 'e' : ''}">${i + 1}</div>`).join('')}</div>
        <div class="src">${lines.map((l, i) => `<div class="${errors[i + 1] ? 'e' : ''}">${hl(l) || ' '}</div>`).join('')}</div></div>
      ${Object.entries(errors).map(([n, m]) => `<div class="err small" style="color:var(--color-danger-text);margin-top:8px;display:flex;gap:6px">${icon('error')}<span>Line ${n}: ${esc(m)}</span></div>`).join('')}
      <p class="muted small" style="margin-top:var(--space-3)">Edits here and in the form change the same file. The library is not editable here; it changes only by importing an update package.</p>`;
  }
  ACTIONS['yaml-apply'] = () => toast('Applied YAML to the form');
  ACTIONS['yaml-revert'] = () => toast('Reverted to the saved file', 'info');
  const settingsYaml = () => yamlView('substation.yaml', [
    'substation:', `  name: "${P.name}"`, `  title_line: "${P.titleLine}"`, '', 'network:', `  ied_count: ${DB.sub.network.iedCount}   # ASSUMED`, `  topology: ${DB.sub.network.topology}`, '', 'spares:', `  port_fraction: 0.${DB.sub.network.spares.portPercent}`, `  sfp_per_l1: ${DB.sub.network.spares.sfpPerL1}`, `  rack_u_reserved: ${DB.sub.network.spares.rackUReserved}`, '', 'equipment:',
    ...DB.equipment.map((e) => `  - { id: ${e.id}, part_id: ${S.checks === 'errors' && e.id === 'ext' ? 'SEL-2730M-EXT2' : e.part}, redundant: ${e.redundant} }`).slice(0, 4), '  # …', '', 'manual_panels: [panels/ws.yaml]'], S.checks === 'errors' ? { 18: 'SEL-2730M-EXT2 is not in library psa-devices 1.4.0.' } : {});

  /* ---------- Panel editor ---------- */
  /* Generated panels: enclosure and options are shared by every generated panel; options can be set for one panel. */
  const scopeNote = (what) => (what === 'enclosure'
    ? `<div style="margin-bottom:var(--space-4)">${banner('info', 'The enclosure is shared by all 4 generated panels. A change here applies to each of them.')}</div>`
    : `<div class="field" style="margin-bottom:var(--space-4)"><span class="label" id="sc-l">Apply to</span><div class="segmented" role="radiogroup" aria-labelledby="sc-l"><label><input type="radio" name="scope" value="all" data-action="opt-scope" ${S.optScope !== 'own' ? 'checked' : ''}><span>All generated panels</span></label><label><input type="radio" name="scope" value="own" data-action="opt-scope" ${S.optScope === 'own' ? 'checked' : ''}><span>This panel only</span></label></div>
      <span class="help">${S.optScope === 'own' ? 'Values you change are kept for this panel and marked <b>Own value</b>. Use the shared value to go back.' : 'Values you change apply to every generated panel that has no value of its own.'}</span></div>`);
  ACTIONS['opt-scope'] = (el) => { S.optScope = el.value; App.render(); };
  const kindLabel = { network: 'Network', control: 'Control', console: 'Console' };
  ACTIONS['open-panel'] = (el) => { S.tab.panel = 'devices'; go('#/panels/' + el.dataset.id + '/devices'); };

  const panelTabs = [['enclosure', 'Enclosure'], ['devices', 'Devices'], ['ports', 'Port plans'], ['options', 'Options'], ['document', 'Document'], ['yaml', 'YAML']];
  function panelEditor(id) {
    const p = DB.panels.find((x) => x.id === id) || DB.panels[0];
    const rc = App.route().c; if (panelTabs.some(([k]) => k === rc)) S.tab.panel = rc;
    const t = S.tab.panel;
    const gen = p.generated;
    const errs = S.checks === 'errors' && p.id === 'ws';
    const ro = (fn) => (gen ? `<fieldset class="readonly" disabled><legend class="sr-only">Written by the layout, read-only</legend>${fn()}</fieldset>` : fn());
    const body = { enclosure: () => (gen ? scopeNote('enclosure') : '') + panelEnclosure(p), devices: () => (gen ? generatedDevices(p) : panelDevices(p)), ports: () => (gen ? '<p class="muted small" style="max-width:68ch;margin-bottom:var(--space-3)">A port plan belongs to the equipment, so a change here also applies to the other panels with the same device, on both sides.</p>' : '') + panelPorts(p), options: () => (gen ? scopeNote('options') : '') + panelOptions(p), document: () => panelDocument(p), yaml: () => panelYaml(p) }[t]();
    const badgeTab = (tab) => (errs && tab === 'options' ? badge('bad', '1', 'error') : '');
    const meta = gen ? `<span class="mono" style="font-size:13px">${esc(p.cabinet)}</span> · ${kindLabel[p.kind]} · Side ${p.side} · pair ${p.pair} (panels ${2 * p.pair - 1} and ${2 * p.pair})` : `<span class="mono" style="font-size:13px">${esc(p.cabinet)}</span> · ${kindLabel[p.kind]} · hand-written`;
    return `<div class="page">${pageHead(esc(p.name), meta,
      `<button class="btn btn--secondary" data-action="goto" data-to="#/preview/${p.id}">${icon('preview')}Preview BOM</button>${gen ? '' : `<button class="btn btn--danger" data-action="delete-panel" data-id="${p.id}">${icon('trash')}Delete panel…</button>`}`,
      `<a href="#/panels">Panels</a>${icon('chevr')}<span>${esc(p.name)}</span>`)}
      ${gen ? `<div style="margin-bottom:var(--space-4)">${banner('info', `<b>Written by the layout.</b> The devices follow from the Network page and the Panels board, so the Devices tab is read-only here. Enclosure, port plans, options and the document are yours to set.`, `<a class="btn btn--secondary btn--sm" href="#/panels">Open Panels board</a><a class="btn btn--secondary btn--sm" href="#/network">Open Network</a>`)}</div>` : `<div style="margin-bottom:var(--space-4)">${banner('info', `<b>Hand-written panel.</b> The layout does not touch it. Its devices are edited here.`)}</div>`}
      ${tabs('panel', panelTabs.map(([i, l]) => [i, l, badgeTab(i)]), t, 'Panel sections')}
      <div role="tabpanel" aria-labelledby="tab-panel-${t}">${body}</div></div>`;
  }
  App.panelEditor = panelEditor;

  const panelEnclosure = (p) => `<div class="form form--3">
    ${field('Make', input('e-make', 'Rawabi'))}${field('Model', input('e-model', 'Fixed Frame'))}${field('Ordering code', input('e-code', 'Fixed Frame', { mono: true }))}
    ${field('Height', `<div class="input-affix">${input('e-h', '2100', { num: true, mono: true })}<span class="affix">mm</span></div>`)}${field('Depth', `<div class="input-affix">${input('e-d', '1000', { num: true, mono: true })}<span class="affix">mm</span></div>`)}${field('Width', `<div class="input-affix">${input('e-w', '800', { num: true, mono: true })}<span class="affix">mm</span></div>`)}
    ${field('Base frame height', `<div class="input-affix">${input('e-bf', '100', { num: true, mono: true })}<span class="affix">mm</span></div>`)}${field('Cable entry', select('e-ce', ['top', 'side'], 'top'))}
    ${p.kind === 'network' ? field('Rack height', `<div class="input-affix">${input('e-u', '42', { num: true, mono: true })}<span class="affix">U</span></div>`, `${DB.sub.network.spares.rackUReserved} U kept free, so ${42 - DB.sub.network.spares.rackUReserved} U may be used.`) : ''}</div>`;

  /* Generated panels: the devices the layout placed, read-only. */
  function generatedDevices(p) {
    const r = Engine.layoutPreview(S.layout.overrides, S.layout.removed); const lp = r.panels.find((x) => x.n === p.n);
    return `<div class="toolbar"><span class="muted small">Moved or removed devices are changed on the Panels board.</span><span class="sp"></span><a class="btn btn--secondary btn--sm" href="#/panels">Show on the board</a></div>
      <div class="table-wrap"><table class="table"><thead><tr><th>Device</th><th>Generated tag</th><th class="num" style="width:70px">Height</th><th style="width:90px">Side</th><th style="width:130px">Origin</th></tr></thead>
      <tbody>${lp.devices.map((d) => `<tr><td><span class="mono">${esc(d.part)}</span><span class="cell-sub">${esc(d.name)}</span></td><td class="mono">${esc(d.tag)}</td><td class="num">${d.h} U</td><td>${d.side ? 'Side ' + d.side : 'Common'}</td><td>${d.moved ? badge('info', 'Moved by you', 'move') : '<span class="muted small">Automatic</span>'}</td></tr>`).join('')}</tbody></table>
      <div class="table-foot"><span>${lp.devices.length} rack devices · ${lp.used} of ${lp.capacity} U used (${lp.plates} blank plates, not in the BOM) · ${lp.din} DIN-rail parts take no rack space</span><span>${illus()}</span></div></div>`;
  }

  /* Hand-written panels (the WS console): an editable device table. */
  function panelDevices(p) {
    const rows = DB.wsDevices;
    return `<div class="toolbar"><div class="popwrap" style="position:relative"><button class="btn btn--primary btn--sm" data-action="pick-open" aria-haspopup="listbox">${icon('plus')}Add device</button></div>
      <span class="muted small">Order here sets the order in the BOM.</span><span class="sp"></span><span class="muted small">Tags are generated by the engine</span></div>
      <div id="picker-slot"></div>
      <div class="table-wrap"><table class="table"><thead><tr><th style="width:28px"><span class="sr-only">Reorder</span></th><th>Device</th><th class="num" style="width:70px">Qty</th><th>Purpose (printed in description)</th><th class="num" style="width:90px">HWIO</th><th>Generated tag</th><th style="width:40px"><span class="sr-only">Actions</span></th></tr></thead>
      <tbody>${rows.map((d, i) => `<tr data-row="${i}"><td class="grip" title="Drag to reorder. Keyboard: focus the row, then Alt+Up or Alt+Down.">${icon('grip')}</td>
        <td><span class="mono">${esc(d.part)}</span><span class="cell-sub">${esc(d.model)}</span></td>
        <td>${input('q' + i, d.qty, { num: true, mono: true }).replace('class="input', 'class="ctl input')}</td>
        <td>${input('pu' + i, d.purpose, { placeholder: 'Optional' }).replace('class="input', 'class="ctl input')}</td>
        <td>${input('hw' + i, d.hwio, { num: true, mono: true, placeholder: 'Auto' }).replace('class="input', 'class="ctl input')}</td>
        <td class="mono muted">${esc(d.tag)}</td>
        <td><button class="btn btn--ghost btn--icon btn--sm" data-action="remove-row" data-i="${i}" aria-label="Remove ${esc(d.part)}">${icon('trash')}</button></td></tr>`).join('')}</tbody></table>
      <div class="table-foot"><span>${rows.length} rows</span><span>HWIO is derived from the device unless you override it.</span></div></div>`;
  }
  ACTIONS['remove-row'] = (el) => { const tr = el.closest('tr'); tr.style.display = 'none'; toast('Device removed. Not saved yet: Revert on the Save bar brings it back.', 'trash'); };
  ACTIONS['pick-open'] = (el) => {
    S.pickReplace = el.dataset && el.dataset.replace != null ? el.dataset.replace : null;
    const slot = $('#picker-slot');
    if (slot.innerHTML) { slot.innerHTML = ''; return; }
    slot.innerHTML = `<div class="popover" style="position:relative;max-width:620px;margin-bottom:var(--space-3);padding:8px">
      <div class="input-wrap"><label class="sr-only" for="pk-q">Search library</label>${icon('search')}<input class="input" id="pk-q" role="combobox" aria-expanded="true" aria-controls="pk-list" placeholder="Search part, make or model" autocomplete="off"></div>
      <div class="listbox" id="pk-list" role="listbox" aria-label="Devices in ${esc(DB.library.name)} ${esc(DB.library.version)}"></div>
      <div class="small muted" style="padding:6px 8px">Showing the active library, ${esc(DB.library.name)} ${esc(DB.library.version)}. <kbd class="kbd">↑</kbd> <kbd class="kbd">↓</kbd> to move, <kbd class="kbd">Enter</kbd> to add.</div></div>`;
    const draw = () => {
      const q = $('#pk-q').value.toLowerCase();
      const list = DB.devices.filter((d) => (d.id + d.make + d.model).toLowerCase().includes(q)).slice(0, 8);
      const rowsNow = App.route().a === 'network' ? DB.equipment : DB.wsDevices; const cur = S.pickReplace != null && rowsNow ? rowsNow[+S.pickReplace] : null;
      const curDev = cur && DB.devices.find((d) => d.id === (cur.part || cur.id)); const alts = !q && curDev && curDev.alt ? DB.altList(curDev).filter((r) => !r.self).slice(0, 3) : [];
      const altHtml = alts.length ? `<div class="group-label" role="presentation">Alternatives to <span class="mono">${esc(curDev.id)}</span></div>${alts.map((r, k) => `<div role="option" id="pk-a${k}" data-action="pick-add" data-id="${esc(r.id)}"><span><span class="mono">${esc(r.id)}</span></span><span class="sub">${esc(r.tier)} · ${esc(r.make)} · ${r.w} W</span><span class="right">${App.verified(r.verified)}</span></div>`).join('')}<div class="group-label" role="presentation">All devices</div>` : '';
      $('#pk-list').innerHTML = altHtml + list.map((d, i) => `<div role="option" id="pk-${i}" aria-selected="${i === 0}" data-action="pick-add" data-id="${d.id}"><span><span class="mono">${esc(d.id)}</span></span><span class="sub">${esc(d.make)} ${esc(d.model)} · ${esc(d.supply)}${d.w ? ' · ' + d.w + ' W' : ''}</span><span class="right">${App.verified(d.verified)}</span></div>`).join('') || '<div class="muted" style="padding:12px">No device matches. Check the spelling, or install a library that has it.</div>';
    };
    let active = 0;
    const mark = () => $$('#pk-list [role=option]').forEach((o, i) => { o.setAttribute('aria-selected', String(i === active)); if (i === active) { $('#pk-q').setAttribute('aria-activedescendant', o.id); o.scrollIntoView({ block: 'nearest' }); } });
    $('#pk-q').addEventListener('input', () => { active = 0; draw(); });
    $('#pk-q').addEventListener('keydown', (e) => {
      const n = $$('#pk-list [role=option]').length;
      if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, n - 1); mark(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); mark(); }
      else if (e.key === 'Enter' && n) { e.preventDefault(); $$('#pk-list [role=option]')[active].click(); }
      else if (e.key === 'Escape') { e.stopPropagation(); $('#picker-slot').innerHTML = ''; const b = document.querySelector('[data-action="pick-open"]'); b && b.focus(); }
    });
    draw(); $('#pk-q').focus();
  };
  ACTIONS['pick-add'] = (el) => { $('#picker-slot').innerHTML = ''; S.dirty = true; S.changed.add('pick-' + el.dataset.id); toast(S.pickReplace != null ? `Part changed to ${el.dataset.id}` : `Added ${el.dataset.id}`); if (S.pickReplace == null && App.isBlank()) S.eqAdded = (S.eqAdded || 0) + 1; App.render(); };

  const panelPorts = (p) => `<p class="muted" style="max-width:68ch;margin-bottom:var(--space-4)">Describe the ports each switch uses. The engine works out the SFPs and shows the result beside it.</p>
    ${[['RST2228-L2', 'PSA1-L2-ESW-A01', [['Uplink to L3', 2, '1G', 'SM', 0], ['Downlink', 15, '1G', 'MM', 0], ['Downlink', 2, '100M', 'MM', 0]], '2 × 1000BASE-LX SM, 15 × 1000BASE-SX MM, 2 × 100BASE-FX MM'],
       ['RST2228-L1-24MM', 'PSA1-L1-ESW-A11 to A16', [['Uplink', 24, '1G', 'MM', 3]], '=24+3 × 1000BASE-SX MM'],
       ['FGR-60F', 'PSA1-EXT-FW-A', [['Downlink', 2, '1G', 'MM', 0]], '2 × 1000BASE-SX MM']].map(([id, tag, rows, res]) => `
      <section class="section" style="padding-top:var(--space-4)"><div class="row" style="justify-content:space-between;margin-bottom:var(--space-2)"><h3><span class="mono" style="font-size:14px">${esc(tag)}</span> <span class="muted" style="font-weight:400">${esc(id)}</span></h3><button class="btn btn--ghost btn--sm">${icon('plus')}Add allocation</button></div>
      <div class="table-wrap" style="max-width:820px"><table class="table"><thead><tr><th>Use</th><th class="num" style="width:90px">Ports</th><th style="width:100px">Speed</th><th style="width:100px">Media</th><th class="num" style="width:90px">Spare</th></tr></thead><tbody>
      ${rows.map(([u, n, s, m, sp], i) => `<tr><td>${esc(u)}</td><td>${input(id + 'n' + i, n, { num: true, mono: true }).replace('class="input', 'class="ctl input')}</td><td>${select(id + 's' + i, ['100M', '1G', '10G'], s, { cls: 'ctl' })}</td><td>${select(id + 'm' + i, ['MM', 'SM', 'RJ45'], m, { cls: 'ctl' })}</td><td>${input(id + 'p' + i, sp, { num: true, mono: true }).replace('class="input', 'class="ctl input')}</td></tr>`).join('')}</tbody></table>
      <div class="table-foot"><span>Engine result</span><span class="mono" style="color:var(--color-text)">${esc(res)}</span></div></div></section>`).join('')}`;

  const panelOptions = (p) => {
    const bad = S.checks === 'errors' && p.id === 'ws';
    return `<div class="form form--2">
    ${field('DC spare branches per feed', input('o1', bad ? 'two' : (p.id === 'ws' ? '1' : DB.sub.network.spares.dcBranches), { num: true, mono: true, invalid: bad }), 'Spare 2 A MCBs on each of feed 1 and feed 2.', bad ? 'Must be a whole number of 0 or more. Enter a number, for example 1.' : '')}
    ${field('AC spare branches', input('o2', '1', { num: true, mono: true }))}
    ${field('Ventilation', select('o3', [['auto', 'Automatic (from heat calculation)'], ['forced', 'Fans'], ['natural', 'Filters']], 'auto'), 'Automatic follows the heat calculation.')}
    ${field('Change-over diodes', select('o4', [['auto', 'Automatic'], ['true', 'Yes'], ['false', 'No']], 'auto'))}
    ${field('Main MCB override', `<div class="input-affix">${input('o5', '', { num: true, mono: true, placeholder: 'Calculated' })}<span class="affix">A</span></div>`, 'Leave empty to use the sizing rule.')}
    ${field('Auxiliary socket', `<div class="input-affix">${input('o6', '', { num: true, mono: true, placeholder: 'None' })}<span class="affix">A</span></div>`)}
    ${field('Inter-panel terminals', input('o7', p.kind === 'console' ? '12' : '40', { num: true, mono: true }))}
    <div class="field"><span class="label">Other</span><label class="switch"><input type="checkbox" checked data-dirty="1">Smoke detector</label></div>
    <div class="span-2 field"><span class="label">Grounding busbars</span><div class="row"><label class="check"><input type="checkbox" checked> AC safety ground</label><label class="check"><input type="checkbox" checked> Instrument ground</label></div></div>
    <div class="span-2 section" style="margin:0"><h3>Terminal overrides</h3><p class="lede">Only where the spec gives no rule for a strip. Empty means the engine's rule is used.</p><button class="btn btn--secondary btn--sm">${icon('plus')}Add override</button></div></div>`;
  };

  const panelDocument = (p) => { const d = docByKey(p.doc); return `<div class="form form--3">${field('Register document', select('pd', docOptions(), p.doc), 'Chosen from the project\'s document register.')}${field('Document number', input('dn', d.docNo, { mono: true, readonly: true }), 'Printed in the page header and footer.')}${field('Revision', input('dr', d.rev, { mono: true, readonly: true }))}</div>
    <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary btn--sm" data-action="goto" data-to="#/project/documents">Edit in the register</button></div>
    <div class="section" style="margin-top:var(--space-5)"><h3>Revised cells</h3><p class="lede">Cells listed here are highlighted yellow in the workbook, as the spec's revision marking asks. You can also compare with the previous issue when you build.</p>
    <button class="btn btn--secondary btn--sm">${icon('plus')}Add revised cell</button></div>`; };

  const panelYaml = (p) => {
    if (p.generated) {
      const lp = Engine.layoutPreview(S.layout.overrides, S.layout.removed).panels.find((x) => x.n === p.n);
      const base = [`# generated: true. Written by the layout from substation.yaml; do not edit.`, `id: ${p.id}`, ...(p.side === 'B' ? [`mirror_of: psa${p.n - 1}`] : []), `cabinet_number: ${p.cabinet}`, `cabinet_name: "${p.name}"`, `tag_prefix: ${p.prefix}`, `sheet_name: "${p.sheet}"`, `document: ${p.doc}`];
      const dev = ['', 'devices:', ...lp.devices.map((d) => `  - { part_id: ${d.part}, tag: ${d.tag} }`)];
      return yamlView(`panels/${p.id}.yaml`, p.side === 'B' ? base : base.concat(dev), {}, { readonly: true });
    }
    return yamlView(`panels/${p.id}.yaml`, [
      `id: ${p.id}`, `cabinet_number: ${p.cabinet}`, `cabinet_name: "${p.name}"`, `tag_prefix: ${p.prefix}`, `sheet_name: "${p.sheet}"`, `kind: ${p.kind}`, '', 'enclosure:', '  make: Rittal', '  model: "Console"', '  h_mm: 1600', '  d_mm: 636', '  w_mm: 800', '', 'devices:',
      '  - { part_id: WS-HP-Z }', '  - { part_id: MON-24 }', '  - { part_id: KB-MK120 }', '', 'options:', '  dc_spare_branches_per_feed: two'].slice(0, 22),
      S.checks === 'errors' ? { 22: 'dc_spare_branches_per_feed must be a whole number, found "two".' } : {});
  };
})();
