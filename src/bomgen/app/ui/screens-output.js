/* Screens: Checks, Preview, Build. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, select, pageHead, illus, dialog, closeDialog, toast, go, counts, $ } = App;
  const P = DB.sub;
  const mainDoc = () => { const pr = App.curProject(); return (pr && pr.documents.find((d) => d.key === P.mainDoc)) || { rev: '' }; };
  const fmt = (n, d = 1) => n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

  /* ---------- Checks ---------- */
  let sevFilter = 'all'; let running = false;
  SCREENS.checks = () => {
    const c = counts();
    const list = DB.problems.filter((p) => !(S.checks === 'clean' && p.sev === 'error')).filter((p) => sevFilter === 'all' || p.sev === (sevFilter === 'errors' ? 'error' : 'warning'));
    return `<div class="page">${pageHead('Checks', 'Problems in the input files, then the engine\'s own checks on the result.',
      `<button class="btn btn--secondary" data-action="rerun" ${running ? 'aria-busy="true"' : ''}>${running ? '<span class="spinner"></span>Checking…' : icon('refresh') + 'Run checks again'}</button>`)}
      ${c.errors ? banner('bad', `<b>${c.errors} errors must be fixed before you can build.</b> Warnings do not block a build.`) : banner('ok', `<b>No errors.</b> You can build the workbook. ${c.warnings} warnings are worth reading first.`, '<a class="btn btn--primary btn--sm" href="#/build">Go to Build</a>')}
      <div class="toolbar" style="margin-top:var(--space-5)"><h2 style="margin-right:var(--space-3)">Problems</h2>
        ${[['all', `All ${c.errors + c.warnings}`], ['errors', `Errors ${c.errors}`], ['warnings', `Warnings ${c.warnings}`]].map(([k, t]) => `<button class="chip" aria-pressed="${sevFilter === k}" data-action="sev" data-v="${k}">${t}</button>`).join('')}</div>
      <div class="table-wrap"><table class="table"><thead><tr><th style="width:100px">Level</th><th>Where</th><th>What is wrong, and what to do</th><th style="width:110px"><span class="sr-only">Action</span></th></tr></thead><tbody>
        ${list.map((p) => `<tr><td style="vertical-align:top;padding-top:8px">${p.sev === 'error' ? badge('bad', 'Error', 'error') : badge('warn', 'Warning', 'warn')}</td>
          <td class="wrap" style="vertical-align:top"><span>${esc(p.where || p.path)}</span><span class="cell-sub mono">${esc(p.file)}:${p.line} · ${esc(p.path)}</span></td>
          <td class="wrap" style="vertical-align:top"><div>${esc(p.msg)}</div><div class="muted">${esc(p.fix)}</div></td>
          <td style="vertical-align:top;padding-top:5px"><button class="btn btn--secondary btn--sm" data-action="goto-problem" data-i="${DB.problems.indexOf(p)}">Go to field</button></td></tr>`).join('') || `<tr class="empty-row"><td colspan="4">Nothing here. ${sevFilter === 'errors' ? 'There are no errors.' : 'Nothing to show with this filter.'}</td></tr>`}</tbody></table></div>
      <div class="toolbar" style="margin-top:var(--space-6)"><h2>Engine checks</h2></div>
      ${c.errors ? `<p class="muted">${DB.engineChecks.length} engine checks will run once the files load without errors. Fix the errors above, then run the checks again.</p>` : `<div class="table-wrap" style="margin-top:var(--space-3)"><table class="table table--comfort"><thead><tr><th>Check</th><th>Result</th><th>Detail</th></tr></thead><tbody>
        ${DB.engineChecks.map((e) => `<tr><td>${esc(e.name)}</td><td style="width:140px">${e.result === 'pass' ? badge('ok', 'Pass', 'check') : badge('warn', 'Flag', 'warn')}</td><td class="wrap">${esc(e.detail)}</td></tr>`).join('')}</tbody></table></div>`}</div>`;
  };
  ACTIONS.sev = (el) => { sevFilter = el.dataset.v; App.render(); };
  ACTIONS.rerun = () => { running = true; App.render(); setTimeout(() => { running = false; App.render(); toast('Checks finished'); }, 900); };
  ACTIONS['goto-problem'] = (el) => {
    const p = DB.problems[+el.dataset.i];
    go(p.route);
  };

  /* ---------- Preview ---------- */
  let grp = 'all'; let q = ''; let showHwio = false; let showRev = false;
  const sheetTabs = [...DB.panels.map((p) => [p.id, p.sheet]), ['power', 'Power Consumption'], ['heatdiss', 'Heat Dissipation'], ['heatcalc', 'Heat Calculations']];
  SCREENS.preview = () => {
    const { b } = App.route(); if (b) S.tab.preview = b;
    const t = S.tab.preview;
    const panel = DB.panels.find((p) => p.id === t);
    const body = panel ? bomView(panel) : { power: powerView, heatdiss: heatDissView, heatcalc: heatCalcView }[t]();
    return `<div class="page">${pageHead('Preview', 'What the workbook will contain. Values are calculated by the engine; nothing here is editable.',
      S.checks === 'errors' ? `<a class="btn btn--secondary" href="#/build">${icon('build')}Build (blocked)</a>` : `<button class="btn btn--primary" data-action="goto" data-to="#/build">${icon('build')}Continue to Build</button>`)}
      ${S.checks === 'errors' ? `<div style="margin-bottom:var(--space-4)">${banner('warn', '<b>Preview is from the last successful load.</b> 2 errors in the input files mean some values may be out of date.', '<a class="btn btn--primary btn--sm" href="#/checks">Open checks</a>')}</div>` : ''}
      ${tabs('preview', sheetTabs.map(([i, l]) => [i, DB.panels.some((p) => p.id === i) ? `Sheet ${l}` : l]), t, 'Workbook sheets')}
      <div role="tabpanel" aria-labelledby="tab-preview-${t}">${body}</div></div>`;
  };
  ACTIONS.tab = ((prev) => (el) => {
    if (el.dataset.group === 'preview') { go('#/preview/' + el.dataset.value); S.tab.preview = el.dataset.value; setTimeout(() => { const n = document.getElementById(el.id); n && n.focus(); }, 0); }
    else prev(el);
  })(ACTIONS.tab);

  function bomView(p) {
    const rows = DB.bom[p.id];
    const counts_ = {}; rows.forEach((r) => { counts_[r.g] = (counts_[r.g] || 0) + 1; });
    const filtering = grp !== 'all' || q;
    let out = '', skip = 0;
    rows.forEach((r, i) => {
      const hay = (r.tag + r.desc + r.make + r.model + r.code).toLowerCase();
      if (filtering && ((grp !== 'all' && r.g !== grp) || (q && !hay.includes(q.toLowerCase())))) { return; }
      if (!filtering && r.gapBefore) out += `<tr class="gap" aria-hidden="true"><td colspan="${showHwio ? 9 : 8}"></td></tr>`;
      let tagCell;
      if (!filtering && skip > 0) { skip -= 1; tagCell = ''; }
      else if (!filtering && r.span) { skip = r.span - 1; tagCell = `<td class="merged mono" rowspan="${r.span}">${esc(r.tag)}</td>`; }
      else tagCell = `<td class="mono">${esc(r.tag)}</td>`;
      const rev = showRev && r.tag === 'PSA1-Q1.3' && p.id === 'psa1';
      out += `<tr><td class="muted" style="width:34px">${r.g}</td><td class="num" style="width:56px">${r.sr}</td>${tagCell}<td>${esc(r.desc)}</td><td class="num ${rev ? 'changed' : ''}" style="width:70px">${esc(r.qty)}</td><td>${esc(r.make)}</td><td class="mono">${esc(r.model)}</td><td class="mono">${esc(r.code)}</td>${showHwio ? `<td class="num">${r.hwio}</td>` : ''}</tr>`;
    });
    const hw = DB.hwioTotal[p.id];
    return `<div class="toolbar">
      <label class="sr-only" for="bom-grp">Show group</label>
      <select class="select" id="bom-grp" data-action="grp" style="width:230px">${['all', ...Object.keys(DB.groupNames)].map((g) => `<option value="${g}" ${grp === g ? 'selected' : ''}>${g === 'all' ? 'All groups' : `${g}  ${DB.groupNames[g]} (${counts_[g] || 0})`}</option>`).join('')}</select>
      <div class="input-wrap" style="width:220px;margin-left:var(--space-2)"><label class="sr-only" for="bom-q">Filter rows</label>${icon('search')}<input class="input" id="bom-q" type="search" placeholder="Filter rows" value="${esc(q)}"></div>
      <span class="sp"></span>
      <label class="switch"><input type="checkbox" data-action="hwio" ${showHwio ? 'checked' : ''}>HWIO column</label>
      <label class="switch"><input type="checkbox" data-action="rev" ${showRev ? 'checked' : ''}>Show revised cells</label></div>
    <div class="sheet-title">${esc(p.cabinet)}<small>${esc(P.titleLine)} - ${esc(p.name)}</small></div>
    <div class="table-wrap" style="max-height:calc(100vh - 380px)"><table class="table"><thead><tr><th title="Group (preview only)">Grp</th><th class="num">SR.NO</th><th>Item designation</th><th>Description</th><th class="num">Quantity</th><th>Make</th><th>Model</th><th>Ordering code</th>${showHwio ? '<th class="num">HWIO</th>' : ''}</tr></thead><tbody>${out || `<tr class="empty-row"><td colspan="9">No rows match. Clear the filter to see all ${rows.length} rows.</td></tr>`}</tbody></table></div>
    <div class="row" style="justify-content:space-between;margin-top:var(--space-2)"><span class="muted small">${rows.length} rows · Groups (A to H) and the HWIO column are for review. The issued sheet shows neither, and the HWIO column is hidden in the workbook.</span><span class="muted small">Panel HWIO total: <b>${hw}</b> ${illus()}</span></div>`;
  }
  ACTIONS.grp = (el) => { grp = el.value || el.dataset.v; App.render(); };
  ACTIONS.hwio = (el) => { showHwio = el.checked; App.render(); };
  ACTIONS.rev = (el) => { showRev = el.checked; App.render(); };
  document.addEventListener('input', (e) => { if (e.target.id === 'bom-q') { q = e.target.value; const pos = e.target.selectionStart; App.render(); const n = $('#bom-q'); n.focus(); n.setSelectionRange(pos, pos); } });

  /* Power and heat figures are literal engine output in data.js; this code only renders them. */
  const block = (t) => `<h3 style="margin:var(--space-4) 0 var(--space-2)">${t.title}</h3><div class="table-wrap"><table class="table"><thead><tr><th class="num">S.No</th><th>Supply</th><th>Input</th><th>Component</th><th class="num">Qty</th><th>Make</th><th>Model</th><th class="num">Unit W</th><th class="num">Total W</th><th>Load</th></tr></thead><tbody>
      ${t.rows.map((r, i) => `<tr><td class="num">${i + 1}</td><td>${t.volt}V</td><td>${t.type}</td><td>${esc(r.name)}</td><td class="num">${r.qty}</td><td>${esc(r.make)}</td><td class="mono">${esc(r.model)}</td><td class="num">${r.unitW}</td><td class="num">${fmt(r.totalW, 0)}</td><td>${t.load}</td></tr>`).join('')}
      <tr class="band"><td colspan="8">TOTAL POWER (W), with 25% margin</td><td class="num">${fmt(t.totalWithMargin)}</td><td></td></tr></tbody></table></div>`;
  const powerView = () => `<div class="metric-row" style="margin-bottom:var(--space-3)"><div><span class="muted small">125 V DC load</span><b>${fmt(DB.power.summary.dcW)} W</b></div><div><span class="muted small">230 V AUX AC load</span><b>${fmt(DB.power.summary.acW)} W</b></div><div><span class="muted small">Total power</span><b>${fmt(DB.power.summary.totalW)} W</b></div></div>
    <p class="muted small">Summary: the example project's totals. Blocks below: sample rows for Cabinet 1 to show the layout. ${illus()}</p>
    ${block(DB.power.dc)}${block(DB.power.ac)}`;
  const heatDissView = () => {
    const h = DB.heat;
    return `<p class="muted small" style="margin-bottom:var(--space-2)">Heat is the device power with no margin. ${illus()}</p><h3 style="margin-bottom:var(--space-2)">${esc(h.cabinet)}</h3><div class="table-wrap"><table class="table"><thead><tr><th class="num">S.No</th><th>Component</th><th class="num">Qty</th><th class="num">Unit W</th><th class="num">Unit BTU/h</th><th class="num">Total BTU/h</th><th class="num">Total W</th></tr></thead><tbody>
      ${h.rows.map((r, i) => `<tr><td class="num">${i + 1}</td><td>${esc(r.name)}</td><td class="num">${r.qty}</td><td class="num">${r.unitW}</td><td class="num">${fmt(r.unitBtu)}</td><td class="num">${fmt(r.totalBtu)}</td><td class="num">${fmt(r.totalW, 0)}</td></tr>`).join('')}
      <tr class="band"><td colspan="5">TOTAL</td><td class="num">${fmt(h.totalBtu)}</td><td class="num">${fmt(h.totalW, 0)}</td></tr></tbody></table></div>`;
  };
  const heatCalcView = () => `<h3 style="margin-bottom:var(--space-2)">Forced ventilation: PSA cabinets</h3>
    <div class="table-wrap" style="max-width:860px"><table class="table table--comfort"><thead><tr><th>Cabinet</th><th class="num">Required airflow (m³/h)</th><th class="num">Fan airflow (m³/h)</th><th>Result</th></tr></thead><tbody>
      ${[['PSA Cabinet - 001', 391], ['PSA Cabinet - 002', 391], ['Workstation Cabinet', 172]].map((r) => `<tr><td>${r[0]}</td><td class="num">${r[1]}</td><td class="num">716</td><td>${badge('ok', 'Enough', 'check')}</td></tr>`).join('')}
      <tr class="band"><td>Line-up, treated as one volume</td><td class="num">954.8</td><td class="num">2,148</td><td>${badge('ok', 'Enough', 'check')}</td></tr></tbody></table></div>
    <h3 style="margin:var(--space-5) 0 var(--space-2)">Natural convection: WS console</h3>
    <div class="metric-row" style="max-width:860px"><div><span class="muted small">Surface area</span><b>4.848 m²</b></div><div><span class="muted small">Temperature rise</span><b>6.96 °C</b></div><div><span class="muted small">Limit (TMax − TInt)</span><b>10 °C</b></div></div>
    <div style="margin-top:var(--space-3);max-width:860px">${banner('ok', 'The rise is under the limit, so natural convection is enough. The console gets ventilation filters and one thermostat, with no fans.')}</div>
    <p class="muted small" style="margin-top:var(--space-3)">Values are the spec's example results.</p>`;

  /* ---------- Build ---------- */
  const fileName = () => P.output.fileName; /* resolved from the pattern by the engine */
  SCREENS.build = () => {
    const c = counts();
    const blocked = S.build === 'ready' && c.errors > 0;
    const st = S.build;
    let status = '';
    if (st === 'success') status = `${banner('ok', `<b>Workbook written.</b><div class="mono" style="margin-top:2px">D:\\Projects\\eastern-province\\substations\\gis01\\out\\${esc(fileName())}</div><div class="small muted">86 KB · 8 sheets · opens in Excel 2016 or later</div>`, `<div class="row" style="flex-wrap:nowrap"><button class="btn btn--primary btn--sm" data-action="toast" data-m="Opening in Excel">${icon('ext')}Open workbook</button><button class="btn btn--secondary btn--sm" data-action="toast" data-m="Showing in folder">Show in folder</button></div>`)}
      <div class="stack" style="margin-top:var(--space-4)"><h3>Check report</h3><ul class="checklist"><li class="ok">${icon('check')}<span style="color:var(--color-text)">SFPs match the port plans</span></li><li class="ok">${icon('check')}<span style="color:var(--color-text)">Airflow covers the heat load in every cabinet</span></li><li class="ok">${icon('check')}<span style="color:var(--color-text)">Digital inputs cover the 40 hardwired points</span></li><li>${icon('warn')}<span>Main MCB overrides on PSA1 and PSA2 (16 A fixed)</span></li></ul></div>`;
    if (st === 'locked') status = banner('bad', `<b>The file could not be written.</b> <span class="mono">${esc(fileName())}</span> is open in Excel. Close it there and try again, or save under a different name.`, `<div class="row" style="flex-wrap:nowrap"><button class="btn btn--primary btn--sm" data-action="build">Try again</button><button class="btn btn--secondary btn--sm" data-action="rename-build">Save as new name</button></div>`);
    if (st === 'building') {
      const steps = ['Loading inputs and library', 'Running the layout and the engine for 5 panels', 'Building sheets and formulas', 'Writing the workbook'];
      status = `<div class="stack" style="max-width:520px"><h3>Building…</h3><div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="4" aria-valuenow="${S.buildStep}" aria-label="Build progress"><i style="width:${S.buildStep * 25}%"></i></div>
        <ul class="steps">${steps.map((s, i) => `<li data-s="${i < S.buildStep ? 'done' : i === S.buildStep ? 'run' : ''}">${i < S.buildStep ? icon('check') : i === S.buildStep ? '<span class="spinner"></span>' : '<span style="width:16px"></span>'}${s}</li>`).join('')}</ul></div>`;
    }
    return `<div class="page">${pageHead('Build', 'Write this substation\'s workbook once the checks are clear.')}
      ${blocked ? banner('bad', `<b>2 errors block the build.</b> Fix them under Checks, then come back.`, '<a class="btn btn--secondary btn--sm" href="#/checks">Open checks</a>') : ''}
      <div style="display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:var(--space-6);align-items:start;margin-top:${blocked ? 'var(--space-5)' : '0'}">
      <div>
        <div class="form" style="max-width:640px">
          ${field('File name', input('b-name', fileName(), { mono: true }), 'From the pattern in Settings → Output.')}
          ${field('Save in', `<div class="row" style="flex-wrap:nowrap">${input('b-dir', 'D:\\Projects\\eastern-province\\substations\\gis01\\out', { mono: true })}<button class="btn btn--secondary">Browse…</button></div>`)}
          <div class="field"><span class="label">Options</span><div class="stack"><label class="switch"><input type="checkbox" data-dirty="0">Highlight cells changed since the previous issue</label>
            <div class="row" style="margin-left:44px"><input class="input input--mono" style="width:320px" placeholder="Choose the previous issue (.xlsx)" disabled><button class="btn btn--secondary btn--sm" disabled>Browse…</button></div>
            <label class="switch"><input type="checkbox" checked data-dirty="0">Open the workbook when it is written</label></div></div>
        </div>
        <div style="margin-top:var(--space-5)" class="row"><button class="btn btn--primary" data-action="build" ${blocked || st === 'building' ? 'disabled' : ''} ${st === 'building' ? 'aria-busy="true"' : ''}>${st === 'building' ? '<span class="spinner"></span>Building…' : icon('build') + 'Build workbook'}</button>${blocked ? '<span class="muted small">Unavailable until the 2 errors are fixed.</span>' : ''}</div>
        <div style="margin-top:var(--space-5)">${status}</div>
      </div>
      <aside><h3>This workbook contains</h3><ul class="checklist" style="margin-top:var(--space-3)">${DB.panels.map((p) => `<li>${icon('preview')}<span>Sheet ${p.sheet}: ${esc(p.name)}</span></li>`).join('')}${P.output.sheets.map((s) => `<li>${icon('preview')}<span>${esc(s)}</span></li>`).join('')}</ul>
        <dl class="kv" style="margin-top:var(--space-4);grid-template-columns:120px 1fr"><dt>Library</dt><dd>${esc(DB.library.name)} ${esc(DB.library.version)}</dd><dt>Revision</dt><dd>${esc(mainDoc().rev)}</dd><dt>Warnings</dt><dd>${c.warnings} (do not block)</dd></dl></aside></div></div>`;
  };
  ACTIONS.build = () => {
    if (S.checks === 'errors' && S.build === 'ready') return;
    S.build = 'building'; S.buildStep = 0; App.render();
    const tick = () => { if (S.build !== 'building') return; S.buildStep += 1; if (S.buildStep >= 4) { S.build = 'success'; App.render(); toast('Workbook written'); } else { App.render(); setTimeout(tick, 650); } };
    setTimeout(tick, 650);
  };
  ACTIONS.toast = (el) => toast(el.dataset.m, 'info');
  ACTIONS['rename-build'] = () => { S.build = 'ready'; App.render(); $('#b-name') && $('#b-name').focus(); };
})();
