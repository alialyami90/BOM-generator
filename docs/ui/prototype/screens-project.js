/* Screens: Home, Project, Panels (list and editor). */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, select, pageHead, illus, dialog, closeDialog, toast, go, counts, $, $$ } = App;
  const P = DB.project;

  /* ---------- Home ---------- */
  SCREENS.home = () => {
    if (S.project === 'empty') {
      return `<div class="page">
        ${pageHead('Welcome to BOM Generator', 'Build the bill of materials, power and heat calculations for a substation SCADA system from a project folder.')}
        <ol class="steps" style="max-width:560px;gap:18px">
          <li data-s="run">${icon('library')}<div><b>1. Install a device library</b><div class="muted small">The library is the list of devices the project can use. It arrives as a <span class="mono">.bomlib</span> file from whoever maintains it.</div></div></li>
          <li>${icon('folder')}<div><b>2. Open a project folder</b><div class="muted small">Or start a new one from the example.</div></div></li>
          <li>${icon('build')}<div><b>3. Check, preview and build the workbook</b></div></li>
        </ol>
        <div class="row" style="margin-top:var(--space-5)">
          <button class="btn btn--primary" data-action="goto" data-to="#/library/import">${icon('upload')}Install a library…</button>
          <button class="btn btn--secondary" disabled>${icon('folder')}Open project…</button>
        </div>
        <p class="muted small" style="margin-top:var(--space-4)">Open project is unavailable until a library is installed.</p>
      </div>`;
    }
    return `<div class="page">
      ${pageHead('Projects', 'Open a project folder to check it and build its workbook.',
        `<button class="btn btn--secondary" data-action="new-project">${icon('plus')}New project…</button><button class="btn btn--primary" data-action="open-project">${icon('folder')}Open project…</button>`)}
      <div class="table-wrap"><table class="table table--comfort${S.density === 'comfort' ? '' : ''}">
        <thead><tr><th>Project</th><th>Document no.</th><th class="num">Panels</th><th>Library</th><th>Last opened</th><th>Status</th></tr></thead>
        <tbody>${DB.recent.map((r, i) => `<tr class="clickable" data-action="open-recent" data-i="${i}" tabindex="0">
          <td><b style="font-weight:500">${esc(r.name)}</b><span class="cell-sub mono">${esc(r.path)}</span></td>
          <td class="mono">${esc(r.doc)}</td><td class="num">${r.panels}</td><td>${esc(r.lib)}</td><td>${esc(r.opened)}</td>
          <td>${badge(r.state, r.stateText, r.state === 'ok' ? 'check' : r.state === 'bad' ? 'error' : 'warn')}</td></tr>`).join('')}</tbody></table></div>
      <div class="section" style="margin-top:var(--space-5);border:0;padding-top:0">
        <div class="banner banner--info">${icon('info')}<div class="grow"><b>Got a device library update?</b><div class="small">Update packages are .bomlib files. Import one to review what it changes before it is installed.</div></div><a class="btn btn--secondary" href="#/library/import">Import update…</a></div>
      </div>
    </div>`;
  };
  ACTIONS['open-project'] = () => dialog({ title: 'Open project', body: '<p>The app shows the Windows folder picker here, then reads <span class="mono">project.yaml</span> and the files it points to. Problems are listed under Checks.</p>', actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="open-recent" data-i="0">Choose folder…</button>' });
  ACTIONS['new-project'] = () => dialog({ title: 'New project', body: `<div class="stack">${field('Project name', input('np-name', '', { placeholder: 'e.g. Substation C PSA' }))}${field('Folder', '<div class="row" style="flex-wrap:nowrap">' + input('np-dir', 'D:\\Projects\\', { mono: true }) + '<button class="btn btn--secondary">Browse…</button></div>')}<label class="check"><input type="checkbox" checked> Start from the example project</label></div>`, actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="open-recent" data-i="0">Create project</button>' });
  ACTIONS['open-recent'] = () => { closeDialog(); S.project = 'loaded'; go('#/project'); };
  document.addEventListener('keydown', (e) => { const r = e.target.closest && e.target.closest('tr.clickable[data-action]'); if (r && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); r.click(); } });

  /* ---------- Project ---------- */
  const tabsProject = [['general', 'General'], ['documents', 'Documents'], ['output', 'Output'], ['constants', 'Design constants'], ['loose', 'Loose material'], ['yaml', 'YAML']];
  SCREENS.project = () => {
    const rb = App.route().b; if (tabsProject.some(([k]) => k === rb)) S.tab.project = rb;
    const t = S.tab.project;
    const body = { general: projectGeneral, documents: projectDocuments, output: projectOutput, constants: projectConstants, loose: projectLoose, yaml: projectYaml }[t]();
    return `<div class="page">${pageHead('Project', 'Settings that apply to every cabinet in this workbook.',
      `<button class="btn btn--primary" data-action="save" ${S.dirty ? '' : 'aria-disabled="true" disabled'}>${icon('save')}Save</button>`)}
      ${tabs('project', tabsProject, t, 'Project settings')}
      <div role="tabpanel" aria-labelledby="tab-project-${t}">${body}</div></div>`;
  };
  ACTIONS.save = () => { S.dirty = false; App.render(); toast('Saved project.yaml'); };

  const projectGeneral = () => `<div class="form form--2">
    <div class="span-2">${field('Project name', input('p-name', P.name), 'Printed in bold at the top of every sheet header.')}</div>
    ${field('Substation', input('p-sub', P.substation), 'Second line of each BOM title.')}
    ${field('Document number', input('p-doc', P.docNo, { mono: true }), 'Default file name uses this.')}
    ${field('Revision', input('p-rev', P.rev, { mono: true }), 'Text, so "02" keeps its zero.')}
    ${field('Logo', `<div class="row" style="flex-wrap:nowrap">${input('p-logo', '', { mono: true, placeholder: 'No logo chosen' })}<button class="btn btn--secondary">Choose…</button></div>`, 'PNG. Appears in the left of the page header. <span style="color:var(--color-warning)">Not set: the header will have no picture.</span>')}
    <div class="span-2 section" style="margin:0">
      <h3>Device library</h3>
      <p class="lede">The project records which library version it was built with, so a colleague can reproduce the workbook.</p>
      <dl class="kv"><dt>Library</dt><dd>${esc(P.library.name)}</dd><dt>Built with</dt><dd>${esc(P.library.builtWith)} ${badge('warn', 'Older than active', 'warn')}</dd><dt>Active on this PC</dt><dd>${esc(P.library.active)}</dd></dl>
      <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary" data-action="goto" data-to="#/library">Open library</button><button class="btn btn--ghost" data-action="stamp">Record 1.4.0 in this project</button></div>
    </div></div>`;
  ACTIONS.stamp = () => { P.library.builtWith = P.library.active; S.dirty = true; App.render(); toast('Project now records psa-devices 1.4.0'); };

  const projectDocuments = () => `<p class="lede muted" style="max-width:68ch;margin-bottom:var(--space-4)">Each calculation sheet has its own document number and revision. BOM documents are set on each panel.</p>
    <div class="table-wrap" style="max-width:1100px"><table class="table"><thead><tr><th>Sheet</th><th>Document no.</th><th>Rev</th><th>Issue date</th><th>Scope (printed in the title)</th></tr></thead>
    <tbody>${P.documents.map((d, i) => `<tr><td>${esc(d.label)}</td><td>${input('d-no' + i, d.docNo, { mono: true }).replace('class="input', 'class="ctl input')}</td><td style="width:70px">${input('d-rev' + i, d.rev, { mono: true }).replace('class="input', 'class="ctl input')}</td><td style="width:150px">${input('d-dt' + i, d.issue, { mono: true }).replace('class="input', 'class="ctl input')}</td><td>${input('d-sc' + i, d.scope).replace('class="input', 'class="ctl input')}</td></tr>`).join('')}</tbody></table></div>`;

  const projectOutput = () => `<div class="form">
    ${field('File name', input('o-pat', P.output.pattern, { mono: true }), 'Fields: <span class="mono">{doc_no}</span> and <span class="mono">{rev}</span>.')}
    <div class="banner banner--info">${icon('info')}<div class="grow"><b>Result:</b> <span class="mono">${esc(P.docNo)}_PSA_BOM_Rev${esc(P.rev)}.xlsx</span></div></div>
    <div class="section" style="margin:0"><h3>Calculation sheet names</h3><p class="lede">Cabinet sheets are named by each panel's sheet name (1, 2, 3, 4).</p>
    <div class="stack">${P.output.sheets.map((s, i) => field(['Power', 'Heat dissipation', 'Heat calculations'][i], input('o-sh' + i, s))).join('')}</div></div></div>`;

  const projectConstants = () => `<p class="muted" style="max-width:68ch;margin-bottom:var(--space-4)">Defaults come from the spec. Change one only when the project's design basis says so; changed values are marked.</p>
    <div class="table-wrap" style="max-width:820px"><table class="table"><thead><tr><th>Constant</th><th class="num" style="width:130px">Value</th><th>Unit</th><th style="width:150px">Default</th></tr></thead>
    <tbody>${P.constants.map((c, i) => `<tr><td>${esc(c.label)}<span class="cell-sub mono">${esc(c.key)}</span></td><td>${input('c' + i, c.value, { num: true, mono: true }).replace('class="input', 'class="ctl input')}</td><td class="muted">${esc(c.unit)}</td><td>${c.value === c.def ? '<span class="muted small">Default</span>' : badge('info', 'Changed from ' + c.def)}</td></tr>`).join('')}</tbody></table></div>`;

  const projectLoose = () => `<p class="muted" style="max-width:68ch;margin-bottom:var(--space-4)">Items that are not mounted in any cabinet. They appear as a second table under the WS console BOM. Pick the cabinet that supplies power to an item that needs it.</p>
    <div class="toolbar"><button class="btn btn--secondary btn--sm">${icon('plus')}Add item</button></div>
    <div class="table-wrap" style="max-width:1100px"><table class="table"><thead><tr><th>Part</th><th>Designation</th><th class="num" style="width:70px">Qty</th><th style="width:130px">Fed from</th><th>Child parts</th><th style="width:40px"><span class="sr-only">Actions</span></th></tr></thead>
    <tbody>${P.loose.map((l, i) => `<tr><td class="mono">${esc(l.part)}</td><td>${esc(l.tag)}</td><td class="num">${esc(l.qty)}</td><td>${l.fed ? esc(l.fed.toUpperCase()) : '<span class="muted">—</span>'}</td><td class="mono">${esc(l.children || '—')}</td><td><button class="btn btn--ghost btn--icon btn--sm" aria-label="Remove ${esc(l.part)}">${icon('trash')}</button></td></tr>`).join('')}</tbody></table></div>`;

  /* YAML view shared by project and panel */
  const hl = (line) => esc(line).replace(/^(\s*)(- )?([A-Za-z_][\w]*)(:)/, '$1$2<span class="k">$3</span>$4').replace(/(#.*)$/, '<span class="c">$1</span>').replace(/: ("[^"]*"|'[^']*')/, ': <span class="s">$1</span>').replace(/: (\d[\d.]*)\b/, ': <span class="n">$1</span>');
  function yamlView(file, lines, errors = {}) {
    const hasErr = Object.keys(errors).length;
    return `<div class="toolbar"><span class="mono" style="font-size:12.5px">${esc(file)}</span>${hasErr ? badge('bad', `${hasErr} error${hasErr > 1 ? 's' : ''}`, 'error') : badge('ok', 'Matches the form', 'check')}<span class="sp"></span>
      <button class="btn btn--secondary btn--sm" data-action="yaml-revert">Revert</button><button class="btn btn--primary btn--sm" data-action="yaml-apply" ${hasErr ? 'disabled' : ''}>Apply to form</button></div>
      <div class="code" role="textbox" aria-multiline="true" aria-label="${esc(file)} source" tabindex="0">
        <div class="gut" aria-hidden="true">${lines.map((_, i) => `<div class="${errors[i + 1] ? 'e' : ''}">${i + 1}</div>`).join('')}</div>
        <div class="src">${lines.map((l, i) => `<div class="${errors[i + 1] ? 'e' : ''}">${hl(l) || ' '}</div>`).join('')}</div></div>
      ${Object.entries(errors).map(([n, m]) => `<div class="err small" style="color:var(--color-danger-text);margin-top:8px;display:flex;gap:6px">${icon('error')}<span>Line ${n}: ${esc(m)}</span></div>`).join('')}
      <p class="muted small" style="margin-top:var(--space-3)">Edits here and in the form change the same file. The library is not editable here; it changes only by importing an update package.</p>`;
  }
  ACTIONS['yaml-apply'] = () => toast('Applied YAML to the form');
  ACTIONS['yaml-revert'] = () => toast('Reverted to the saved file', 'info');
  const projectYaml = () => yamlView('project.yaml', [
    'project:', `  name: "${P.name}"`, `  substation: "${P.substation}"`, `  doc_no: ${P.docNo}`, `  rev: "${P.rev}"`, '  # logo: assets/logo.png', '', 'library: library.yaml', 'panels:', '  - panels/psa1.yaml', '  - panels/psa2.yaml', '  - panels/psa3.yaml', '  - panels/ws.yaml', '', 'output:', `  file_name: "${P.output.pattern}"`]);

  /* ---------- Panels ---------- */
  const kindLabel = { network: 'Network', control: 'Control', console: 'Console' };
  SCREENS.panels = () => {
    const { b } = App.route();
    if (b) return panelEditor(b);
    return `<div class="page">${pageHead('Panels', 'One sheet per cabinet, in the order shown. Mirror a panel to create its LAN-B twin.',
      `<button class="btn btn--secondary" data-action="mirror">${icon('mirror')}Mirror a panel…</button><button class="btn btn--primary" data-action="add-panel">${icon('plus')}Add panel</button>`)}
      <div class="table-wrap"><table class="table table--comfort"><thead><tr><th>Sheet</th><th>Cabinet</th><th>Name</th><th>Kind</th><th>LAN</th><th class="num">Devices</th><th>Mirror of</th><th>Status</th></tr></thead>
      <tbody>${DB.panels.map((p) => `<tr class="clickable" tabindex="0" data-action="open-panel" data-id="${p.id}">
        <td class="mono">${esc(p.sheet)}</td><td class="mono">${esc(p.cabinet)}</td><td><b style="font-weight:500">${esc(p.name)}</b></td><td>${kindLabel[p.kind]}</td><td>${p.lan || '—'}</td><td class="num">${p.devices}</td><td>${p.mirrorOf ? esc(p.mirrorOf.toUpperCase()) : '—'}</td>
        <td>${p.status === 'bad' && S.checks === 'errors' ? badge('bad', '1 error', 'error') : badge('ok', 'Ready', 'check')}</td></tr>`).join('')}</tbody></table></div></div>`;
  };
  ACTIONS['open-panel'] = (el) => { S.tab.panel = 'devices'; go('#/panels/' + el.dataset.id + '/devices'); };
  ACTIONS.mirror = () => dialog({ title: 'Mirror a panel', body: `<p style="margin-bottom:var(--space-3)">Creates a small file that points at the original. Devices, enclosure and port plans follow the original, and every tag swaps the cabinet prefix and LAN letter. Options and the document block are the new panel's own.</p><div class="form form--2">
      <div class="span-2">${field('Original panel', select('m-src', [['psa1', 'PSA Cabinet - 001 (LAN A)']], 'psa1'))}</div>
      ${field('Panel id', input('m-id', 'psa2', { mono: true }), 'File name: panels/psa2.yaml.')}${field('Cabinet number', input('m-cab', '861-GIS01-PSA-0002', { mono: true }))}
      ${field('Cabinet name', input('m-name', 'PSA Cabinet - 002'), 'Printed in the sheet title.')}${field('Sheet name', input('m-sheet', '2', { mono: true }), 'Workbook tab.')}
      ${field('Tag prefix', input('m-pre', 'PSA2', { mono: true }), 'Replaces PSA1 in every tag.')}${field('LAN', select('m-lan', ['B', 'A'], 'B'), 'Swaps A to B in tags. Shown because the original has a LAN.')}</div>`, actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="close">Create mirrored panel</button>' });
  ACTIONS['add-panel'] = () => dialog({ title: 'Add panel', body: `<div class="stack">${field('Kind', select('ap-k', [['network', 'Network cabinet'], ['control', 'Control cabinet'], ['console', 'Console']], 'network'), 'Sets the terminal strip defaults.')}${field('Cabinet number', input('ap-c', '', { mono: true }))}${field('Name', input('ap-n', ''))}</div>`, actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="close">Add panel</button>' });

  const panelTabs = [['enclosure', 'Enclosure'], ['devices', 'Devices'], ['ports', 'Port plans'], ['options', 'Options'], ['document', 'Document'], ['yaml', 'YAML']];
  function panelEditor(id) {
    const p = DB.panels.find((x) => x.id === id) || DB.panels[0];
    const rc = App.route().c; if (panelTabs.some(([k]) => k === rc)) S.tab.panel = rc;
    const t = S.tab.panel;
    const errs = S.checks === 'errors' && (p.id === 'psa1' || p.id === 'ws');
    const ro = (fn) => (p.mirrorOf ? `<fieldset class="readonly" disabled><legend class="sr-only">Follows ${p.mirrorOf.toUpperCase()}, read-only</legend>${fn()}</fieldset>` : fn());
    const body = { enclosure: () => ro(() => panelEnclosure(p)), devices: () => ro(() => panelDevices(p)), ports: () => ro(() => panelPorts(p)), options: () => panelOptions(p), document: () => panelDocument(p), yaml: () => panelYaml(p) }[t]();
    const badgeTab = (tab) => (errs && ((p.id === 'psa1' && tab === 'devices') || (p.id === 'ws' && tab === 'options')) ? badge('bad', '1', 'error') : '');
    return `<div class="page">${pageHead(esc(p.name), `<span class="mono" style="font-size:13px">${esc(p.cabinet)}</span> · ${kindLabel[p.kind]}${p.lan ? ' · LAN ' + p.lan : ''}${p.mirrorOf ? ' · mirror of ' + p.mirrorOf.toUpperCase() : ''}`,
      `<button class="btn btn--secondary" data-action="goto" data-to="#/preview/${p.id}">${icon('preview')}Preview BOM</button><button class="btn btn--primary" data-action="save" ${S.dirty ? '' : 'disabled'}>${icon('save')}Save</button>`,
      `<a href="#/panels">Panels</a>${icon('chevr')}<span>${esc(p.name)}</span>`)}
      ${p.mirrorOf ? `<div style="margin-bottom:var(--space-4)">${banner('info', `<b>Mirrored from ${p.mirrorOf.toUpperCase()}.</b> Enclosure, Devices and Port plans follow the original and are read-only here. Options (only the fields you fill in), Document and YAML are this panel's own.`, `<a class="btn btn--secondary btn--sm" href="#/panels/${p.mirrorOf}">Open ${p.mirrorOf.toUpperCase()}</a>`)}</div>` : ''}
      ${tabs('panel', panelTabs.map(([i, l]) => [i, l, badgeTab(i)]), t, 'Panel sections')}
      <div role="tabpanel" aria-labelledby="tab-panel-${t}">${body}</div></div>`;
  }

  const panelEnclosure = (p) => `<div class="form form--3">
    ${field('Make', input('e-make', 'Rawabi'))}${field('Model', input('e-model', 'Fixed Frame'))}${field('Ordering code', input('e-code', 'Fixed Frame', { mono: true }))}
    ${field('Height', `<div class="input-affix">${input('e-h', '2100', { num: true, mono: true })}<span class="affix">mm</span></div>`)}${field('Depth', `<div class="input-affix">${input('e-d', '1000', { num: true, mono: true })}<span class="affix">mm</span></div>`, p.id === 'psa3' ? '<span style="color:var(--color-warning)">Assumed value. Confirm from the datasheet.</span>' : '')}${field('Width', `<div class="input-affix">${input('e-w', '800', { num: true, mono: true })}<span class="affix">mm</span></div>`)}
    ${field('Base frame height', `<div class="input-affix">${input('e-bf', '100', { num: true, mono: true })}<span class="affix">mm</span></div>`)}${field('Cable entry', select('e-ce', ['top', 'side'], 'top'))}</div>`;

  function panelDevices(p) {
    const rows = p.id === 'psa1' || p.id === 'psa2' ? DB.psa1Devices.map((d) => p.id === 'psa2' ? Object.assign({}, d, { tag: d.tag.replace('PSA1', 'PSA2').replace(/-A/g, '-B').replace('GW-1', 'GW-2') }) : d) : DB.psa1Devices.slice(0, p.devices);
    const bad = S.checks === 'errors' && p.id === 'psa1';
    return `<div class="toolbar"><div class="popwrap" style="position:relative"><button class="btn btn--primary btn--sm" data-action="pick-open" aria-haspopup="listbox">${icon('plus')}Add device</button></div>
      <span class="muted small">Order here sets the order in the BOM and the DC breaker numbers.</span><span class="sp"></span><span class="muted small">Tags are generated by the engine</span></div>
      <div id="picker-slot"></div>
      <div class="table-wrap"><table class="table"><thead><tr><th style="width:28px"><span class="sr-only">Reorder</span></th><th>Device</th><th class="num" style="width:70px">Qty</th><th>Purpose (printed in description)</th><th class="num" style="width:90px">HWIO</th><th>Generated tag</th><th style="width:40px"><span class="sr-only">Actions</span></th></tr></thead>
      <tbody>${rows.map((d, i) => {
        const isBad = bad && i === 3;
        return `<tr data-row="${i}"><td class="grip" title="Drag to reorder. Keyboard: focus the row, then Alt+Up or Alt+Down.">${icon('grip')}</td>
        <td>${isBad ? `<div class="field"><input class="ctl input input--mono" aria-invalid="true" aria-describedby="derr" value="SEL-2730M-EXT2"><span id="derr" class="err small">${icon('error')}<span>Not in psa-devices ${esc(DB.library.version)}. Did you mean SEL-2730M-EXT?</span></span></div>` : `<span class="mono">${esc(d.part)}</span><span class="cell-sub">${esc(d.model)}</span>`}</td>
        <td>${input('q' + i, d.qty, { num: true, mono: true }).replace('class="input', 'class="ctl input')}</td>
        <td>${input('pu' + i, d.purpose, { placeholder: 'Optional' }).replace('class="input', 'class="ctl input')}</td>
        <td>${input('hw' + i, d.hwio, { num: true, mono: true, placeholder: 'Auto' }).replace('class="input', 'class="ctl input')}</td>
        <td class="mono muted">${isBad ? '—' : esc(d.tag)}</td>
        <td><button class="btn btn--ghost btn--icon btn--sm" data-action="remove-row" data-i="${i}" aria-label="Remove ${esc(d.part)}">${icon('trash')}</button></td></tr>`;
      }).join('')}</tbody></table>
      <div class="table-foot"><span>${rows.length} rows</span><span>HWIO is derived from the device unless you override it.</span></div></div>`;
  }
  ACTIONS['remove-row'] = (el) => { const tr = el.closest('tr'); tr.style.display = 'none'; App.toast('Device removed. Not saved yet: Revert on the Save bar brings it back.', 'trash'); };
  ACTIONS['pick-open'] = (el) => {
    const slot = $('#picker-slot');
    if (slot.innerHTML) { slot.innerHTML = ''; return; }
    slot.innerHTML = `<div class="popover" style="position:relative;max-width:620px;margin-bottom:var(--space-3);padding:8px">
      <div class="input-wrap"><label class="sr-only" for="pk-q">Search library</label>${icon('search')}<input class="input" id="pk-q" role="combobox" aria-expanded="true" aria-controls="pk-list" placeholder="Search part, make or model" autocomplete="off"></div>
      <div class="listbox" id="pk-list" role="listbox" aria-label="Devices in ${esc(DB.library.name)} ${esc(DB.library.version)}"></div>
      <div class="small muted" style="padding:6px 8px">Showing the active library, ${esc(DB.library.name)} ${esc(DB.library.version)}. <kbd class="kbd">↑</kbd> <kbd class="kbd">↓</kbd> to move, <kbd class="kbd">Enter</kbd> to add.</div></div>`;
    const draw = () => {
      const q = $('#pk-q').value.toLowerCase();
      const list = DB.devices.filter((d) => (d.id + d.make + d.model).toLowerCase().includes(q)).slice(0, 8);
      $('#pk-list').innerHTML = list.map((d, i) => `<div role="option" id="pk-${i}" aria-selected="${i === 0}" data-action="pick-add" data-id="${d.id}"><span><span class="mono">${esc(d.id)}</span></span><span class="sub">${esc(d.make)} ${esc(d.model)} · ${esc(d.supply)}${d.w ? ' · ' + d.w + ' W' : ''}</span><span class="right">${App.verified(d.verified)}</span></div>`).join('') || '<div class="muted" style="padding:12px">No device matches. Check the spelling, or install a library that has it.</div>';
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
  ACTIONS['pick-add'] = (el) => { $('#picker-slot').innerHTML = ''; S.dirty = true; toast(`Added ${el.dataset.id}`); App.render(); };

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
    return `${p.mirrorOf ? `<p class="muted" style="max-width:68ch;margin-bottom:var(--space-4)">Empty fields follow ${p.mirrorOf.toUpperCase()}. Only the fields you fill in are written to ${p.id}.yaml.</p>` : ''}<div class="form form--2">
    ${field('DC spare branches per feed', input('o1', bad ? 'two' : (p.id === 'ws' || p.id === 'psa3' ? '1' : '3'), { num: true, mono: true, invalid: bad }), 'Spare 2 A MCBs on each of feed 1 and feed 2.', bad ? 'Must be a whole number of 0 or more. Enter a number, for example 1.' : '')}
    ${field('AC spare branches', input('o2', '1', { num: true, mono: true }))}
    ${field('Ventilation', select('o3', [['auto', 'Automatic (from heat calculation)'], ['forced', 'Fans'], ['natural', 'Filters']], 'auto'), 'Automatic follows the heat calculation.')}
    ${field('Change-over diodes', select('o4', [['auto', 'Automatic'], ['true', 'Yes'], ['false', 'No']], 'auto'))}
    ${field('Main MCB override', `<div class="input-affix">${input('o5', p.id === 'psa1' ? '16' : '', { num: true, mono: true, placeholder: p.mirrorOf ? '16 from ' + p.mirrorOf.toUpperCase() : 'Calculated' })}<span class="affix">A</span></div>`, p.id === 'psa1' ? `<span style="color:var(--color-warning)">Overrides the calculated 10 A. Remove to use the sizing rule.</span>` : p.mirrorOf ? 'Left empty: follows ' + p.mirrorOf.toUpperCase() + '.' : 'Leave empty to use the sizing rule.')}
    ${field('Auxiliary socket', `<div class="input-affix">${input('o6', p.id === 'psa2' ? '10' : '', { num: true, mono: true, placeholder: 'None' })}<span class="affix">A</span></div>`)}
    ${field('Inter-panel terminals', input('o7', p.kind === 'console' ? '12' : '40', { num: true, mono: true }))}
    <div class="field"><span class="label">Other</span><label class="switch"><input type="checkbox" checked data-dirty="1">Smoke detector</label></div>
    <div class="span-2 field"><span class="label">Grounding busbars</span><div class="row"><label class="check"><input type="checkbox" checked> AC safety ground</label><label class="check"><input type="checkbox" checked> Instrument ground</label></div></div>
    <div class="span-2 section" style="margin:0"><h3>Terminal overrides</h3><p class="lede">Only where the spec gives no rule for a strip. Empty means the engine's rule is used.</p><button class="btn btn--secondary btn--sm">${icon('plus')}Add override</button></div></div>`;
  };

  const panelDocument = (p) => `<div class="form form--3">${field('Document number', input('dn', 'DOC-0001-GIS01-' + p.sheet.padStart(3, '0'), { mono: true }), 'Printed in the page header and footer.')}${field('Revision', input('dr', '02', { mono: true }))}${field('Issue date', input('di', '2026-10-28', { mono: true }), 'Assumed. Confirm before issuing.')}</div>
    <div class="section" style="margin-top:var(--space-5)"><h3>Revised cells</h3><p class="lede">Cells listed here are highlighted yellow in the workbook, as the spec's revision marking asks. You can also compare with the previous issue when you build.</p>
    <button class="btn btn--secondary btn--sm">${icon('plus')}Add revised cell</button></div>`;

  const panelYaml = (p) => (p.mirrorOf ? yamlView(`panels/${p.id}.yaml`, [
    `id: ${p.id}`, `mirror_of: ${p.mirrorOf}`, `cabinet_number: ${p.cabinet}`, `cabinet_name: "${p.name}"`, `tag_prefix: ${p.prefix}`, `lan: ${p.lan}`, `sheet_name: "${p.sheet}"`, '', 'options:', '  aux_socket_a: 10', '', 'document:', '  doc_no: DOC-0001-GIS01-002', '  rev: "02"', '  issue_date: 2026-10-28  # ASSUMED'], {}) : yamlView(`panels/${p.id}.yaml`, [
    `id: ${p.id}`, `cabinet_number: ${p.cabinet}`, `cabinet_name: "${p.name}"`, `tag_prefix: ${p.prefix}`, `lan: ${p.lan || 'null'}`, `sheet_name: "${p.sheet}"`, `kind: ${p.kind}`, '', 'enclosure:', '  make: Rawabi', '  model: "Fixed Frame"', '  h_mm: 2100', '  d_mm: 1000', '  w_mm: 800', '', 'devices:',
    '  - { part_id: FOPP-96SM, purpose: "L2-L3 uplink to CCR" }', '  - { part_id: RST2228-L2 }', '  - { part_id: RST2228-L1-24MM, qty: 6, hwio_points: 10 }',
    ...(p.id === 'psa1' ? [S.checks === 'errors' ? '  - { part_id: SEL-2730M-EXT2 }   # not in psa-devices 1.4.0' : '  - { part_id: SEL-2730M-EXT }'] : []), '', 'options:', p.id === 'ws' ? '  dc_spare_branches_per_feed: two' : '  dc_spare_branches_per_feed: 3'].slice(0, 22),
    S.checks === 'errors' && p.id === 'psa1' ? { 20: 'SEL-2730M-EXT2 is not in library psa-devices 1.4.0.' } : S.checks === 'errors' && p.id === 'ws' ? { 22: 'dc_spare_branches_per_feed must be a whole number, found "two".' } : {}));
})();
