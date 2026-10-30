/* Screen: Preview on bomgen.app.api (plan M10d). Every figure comes from preview_substation, which flattens the
   engine's build result; this file only lays the rows out. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, pageHead, toast, go, $ } = App;
  const LOOSE = 'loose-material';  // not a panel id: those name panel files
  const real = () => S.backend === 'yes' && S.project && S.project.real && S.sub;
  const GROUPS = { A: 'Enclosure', B: 'Main equipment', C: 'Network and IO accessories', D: 'Cabinet housekeeping', E: 'AC distribution', F: 'DC distribution', G: 'Terminal blocks', H: 'Grounding' };  // the spec's group names, labels only
  const fmt = (n, d = 1) => Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  const seg = (code) => esc(code || '').replace(/([+\-])/g, '$1<wbr>');  // long codes break between segments
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;

  const P = { key: '', state: 'idle', data: null, error: null };
  function page() {
    const key = `${S.project.file}#${S.sub}`;
    if (P.key !== key) Object.assign(P, { key, state: 'idle', data: null, error: null });
    if (P.state === 'idle') {
      P.state = 'loading';
      const current = () => P.key === key;
      Bridge.call('preview_substation', S.project.file, S.sub)
        .then((d) => { if (current()) P.data = d; }).catch((err) => { if (current()) { P.error = err; toast(err.message, 'error'); } })
        .then(() => { if (current()) { P.state = 'loaded'; App.render(); } });
    }
    return P.state === 'loaded' ? P : null;
  }

  let grp = 'all'; let q = ''; let showHwio = false; let viewKey = '';
  SCREENS.preview = () => {
    if (!real()) return `<div class="page">${pageHead('Preview')}<div class="empty"><b>Open a substation first.</b></div></div>`;
    const p = page();
    if (!p || !p.data) return `<div class="page">${pageHead('Preview', p && p.error ? esc(p.error.message) : 'Running the engine…')}</div>`;
    const d = p.data;
    if (viewKey !== p.key) { grp = 'all'; q = ''; viewKey = p.key; }  // each substation opens unfiltered
    const errors = d.problems.filter((x) => x.level === 'error').length;
    if (d.reason) {
      return `<div class="page">${pageHead('Preview', 'What the workbook will contain.')}
        ${banner('bad', `<b>Nothing to preview.</b> ${esc(d.reason)}${errors ? ' must be fixed first' : ''}.`, '<a class="btn btn--secondary btn--sm" href="#/checks">Open checks</a>')}</div>`;
    }
    // short labels keep all tabs in view; the cabinet is the tooltip and the sheet's title block
    // the workbook's order: panel sheets, the loose material sheet, then the calculations (ADR 0020)
    const sheets = [...d.panels.map((x) => [x.panel_id, `Sheet ${x.sheet}`, '', x.cabinet]),
      ...(d.loose ? [[LOOSE, `${d.loose.sheet} (${d.loose.rows.length})`, '', 'Shipped loose, not in a panel']] : []),
      ['power', 'Power', '', d.calc_sheets.power], ['heatdiss', 'Heat dissipation', '', d.calc_sheets.heat_dissipation],
      ['heatcalc', 'Heat calculations', '', d.calc_sheets.heat_calculations]];
    const { b } = App.route();
    let t = b || S.tab.preview;
    if (!sheets.some(([k]) => k === t)) t = sheets[0][0];
    S.tab.preview = t;
    const panel = t === LOOSE ? d.loose : d.panels.find((x) => x.panel_id === t);
    const body = panel ? bomView(panel, t === LOOSE) : t === 'power' ? powerView(d) : t === 'heatdiss' ? heatDissView(d) : heatCalcView(d);
    return `<div class="page">${pageHead('Preview', 'What the workbook will contain. Values are calculated by the engine; nothing here is editable.',
      `<a class="btn btn--primary" href="#/build">${icon('build')}Continue to Build</a>`)}
      ${tabs('preview', sheets, t, 'Workbook sheets')}
      <div role="tabpanel" aria-labelledby="tab-preview-${esc(t)}">${body}</div></div>`;
  };

  /* ---------- BOM sheet ---------- */
  const matches = (r) => (grp === 'all' || r.group === grp) && (!q || [r.tag, r.description, r.make, r.model, r.ordering_code].join(' ').toLowerCase().includes(q.toLowerCase()));
  function bomRows(rows, filtering) {
    const cols = showHwio ? 9 : 8;
    let out = '', skip = 0;
    rows.forEach((r) => {
      if (filtering && !matches(r)) return;
      if (!filtering && r.separator_before) out += `<tr class="gap" aria-hidden="true"><td colspan="${cols}"></td></tr>`;
      let tag;
      if (!filtering && skip > 0) { skip -= 1; tag = ''; }
      else if (!filtering && r.tag_rows > 1) { skip = r.tag_rows - 1; tag = `<td class="merged mono" rowspan="${r.tag_rows}">${esc(r.tag || '')}</td>`; }
      else tag = `<td class="mono">${esc(r.tag || '')}</td>`;
      const rev = (c) => (r.revised.includes(c) ? 'changed' : '');
      out += `<tr><td class="muted" style="width:34px">${r.group}</td><td class="num" style="width:56px">${r.sr}</td>${tag}<td class="wrap pv-desc ${rev('D')}">${esc(r.description).replace(/\n/g, '<br>')}</td><td class="num ${rev('E')}" style="width:70px">${esc(r.qty)}</td><td class="${rev('F')}">${esc(r.make || '')}</td><td class="mono pv-code ${rev('G')}">${seg(r.model)}</td><td class="mono pv-code ${rev('H')}">${r.ordering_code && r.ordering_code === r.model ? '<span class="muted small pv-same" title="The workbook repeats the model here">Same as model</span>' : seg(r.ordering_code)}</td>${showHwio ? `<td class="num">${r.hwio || ''}</td>` : ''}</tr>`;
    });
    return out;
  }
  const head = () => `<thead><tr><th title="Group (preview only)">Grp</th><th class="num">SR.NO</th><th>Item designation</th><th>Description</th><th class="num">Quantity</th><th>Make</th><th>Model</th><th>Ordering code</th>${showHwio ? '<th class="num">HWIO</th>' : ''}</tr></thead>`;
  function bomView(p, loose) {
    const counts = {}; p.rows.forEach((r) => { counts[r.group] = (counts[r.group] || 0) + 1; });
    const filtering = grp !== 'all' || !!q;
    const out = bomRows(p.rows, filtering);
    return `<div class="toolbar">
      <label class="sr-only" for="bom-grp">Show group</label>
      <select class="select" id="bom-grp" data-action="pv-grp" style="width:260px"><option value="all">All groups</option>${Object.keys(GROUPS).filter((g) => counts[g]).map((g) => `<option value="${g}" ${grp === g ? 'selected' : ''}>${g}  ${esc(GROUPS[g])} (${counts[g]})</option>`).join('')}</select>
      <div class="input-wrap" style="width:220px;margin-left:var(--space-2)"><label class="sr-only" for="pv-q">Filter rows</label>${icon('search')}<input class="input" id="pv-q" type="search" placeholder="Filter rows" value="${esc(q)}"></div>
      <span class="sp"></span>
      ${loose ? `<a class="btn btn--secondary btn--sm" href="#/loose" style="margin-right:var(--space-3)">${icon('edit')}Edit the list</a>` : ''}
      <label class="switch"><input type="checkbox" data-action="pv-hwio" ${showHwio ? 'checked' : ''}>HWIO column</label></div>
      <div class="sheet-title">${esc(p.title[0])}<small>${esc(p.title[1])}</small></div>
      <div class="table-wrap" style="max-height:calc(100vh - 380px)"><table class="table">${head()}<tbody>${out || `<tr class="empty-row"><td colspan="9">No rows match. Clear the filter to see all ${p.rows.length} rows.</td></tr>`}</tbody></table></div>
      <div class="row" style="justify-content:space-between;margin-top:var(--space-2)"><span class="muted small">${plural(p.rows.length, 'row')} · Groups (A to H) and the HWIO column are for review. The issued sheet shows neither, and the HWIO column is hidden in the workbook.</span><span class="muted small">${loose ? 'HWIO total' : 'Panel HWIO total'}: <b>${p.hwio_total}</b></span></div>`;
  }
  ACTIONS['pv-grp'] = (el) => { grp = el.value; App.render(); };
  ACTIONS['pv-hwio'] = (el) => { showHwio = el.checked; App.render(); };
  document.addEventListener('input', (e) => { if (e.target.id === 'pv-q') { q = e.target.value; const pos = e.target.selectionStart; App.render(); const n = $('#pv-q'); if (n) { n.focus(); n.setSelectionRange(pos, pos); } } });

  /* ---------- Calculation sheets ---------- */
  const name = (x) => esc(x.cabinet || x.panel_id || 'PSA Auxiliary Equipment');
  function block(title, b) {
    if (!b) return '';
    return `<h3 style="margin:var(--space-4) 0 var(--space-2)">${title}</h3><div class="table-wrap"><table class="table"><thead><tr><th class="num">S.No</th><th>Supply</th><th>Component</th><th class="num">Qty</th><th>Make</th><th>Model</th><th class="num">Unit W</th><th class="num">Total W</th><th>Load</th><th class="num">MCB A</th></tr></thead><tbody>
      ${b.lines.map((r, i) => `<tr><td class="num">${i + 1}</td><td>${esc(r.supply)} ${esc(r.supply_type)}</td><td class="wrap">${esc(r.description.split('\n')[0])}</td><td class="num">${r.qty}</td><td>${esc(r.make || '')}</td><td class="mono">${esc(r.model || '')}</td><td class="num">${fmt(r.unit_w)}</td><td class="num">${fmt(r.total_w)}</td><td>${r.load_type === 'CONTINUOUS' ? 'Continuous' : 'Intermittent'}</td><td class="num">${r.device_mcb_a}</td></tr>`).join('')}
      <tr class="band"><td colspan="7">TOTAL POWER (W), with ${Math.round(b.margin * 100)}% margin</td><td class="num">${fmt(b.total_w)}</td><td colspan="2"></td></tr></tbody></table></div>`;
  }
  const powerView = (d) => {
    const p = d.power;
    if (!p) return '<p class="muted">The engine gives no power figures for this substation.</p>';
    return `<div class="metric-row" style="margin-bottom:var(--space-3)"><div><span class="muted small">DC load</span><b>${fmt(p.dc_total_w)} W</b></div><div><span class="muted small">AC load</span><b>${fmt(p.ac_total_w)} W</b></div><div><span class="muted small">Total power</span><b>${fmt(p.total_w)} W</b></div></div>
      ${p.cabinets.map((c) => `<h2 style="margin-top:var(--space-6)">${name(c)}</h2>${block('DC loads', c.dc)}${block('AC loads', c.ac)}`).join('')}
      ${p.external ? `<h2 style="margin-top:var(--space-6)">External equipment</h2>${block('DC loads', p.external)}` : ''}`;
  };
  const heatDissView = (d) => {
    if (!d.heat_dissipation) return '<p class="muted">The engine gives no heat figures for this substation.</p>';
    return `<p class="muted small" style="margin-bottom:var(--space-2)">Heat is the device power with no margin.</p>
      ${d.heat_dissipation.map((h) => `<h3 style="margin:var(--space-4) 0 var(--space-2)">${name(h)}</h3><div class="table-wrap"><table class="table"><thead><tr><th class="num">S.No</th><th>Component</th><th class="num">Qty</th><th class="num">Unit W</th><th class="num">Unit BTU/h</th><th class="num">Total BTU/h</th><th class="num">Total W</th></tr></thead><tbody>
        ${h.lines.map((r, i) => `<tr><td class="num">${i + 1}</td><td class="wrap">${esc(r.description.split('\n')[0])}</td><td class="num">${r.qty}</td><td class="num">${fmt(r.unit_w)}</td><td class="num">${fmt(r.unit_btu_h)}</td><td class="num">${fmt(r.total_btu_h)}</td><td class="num">${fmt(r.total_w)}</td></tr>`).join('')}
        <tr class="band"><td colspan="5">TOTAL</td><td class="num">${fmt(h.total_btu_h)}</td><td class="num">${fmt(h.total_w)}</td></tr></tbody></table></div>`).join('')}`;
  };
  const enough = (ok) => (ok ? badge('ok', 'Enough', 'check') : badge('bad', 'Not enough', 'error'));
  const heatCalcView = (d) => {
    const h = d.heat_calculations;
    if (!h) return '<p class="muted">The engine gives no heat figures for this substation.</p>';
    const forced = h.cabinets.filter((c) => c.ventilation !== 'natural'), natural = h.cabinets.filter((c) => c.ventilation === 'natural');
    return `${forced.length ? `<h3 style="margin-bottom:var(--space-2)">Forced ventilation</h3>
      <div class="table-wrap" style="max-width:860px"><table class="table table--comfort"><thead><tr><th>Cabinet</th><th class="num">Heat (W)</th><th class="num">Required airflow (m³/h)</th><th class="num">Fan airflow (m³/h)</th><th>Result</th></tr></thead><tbody>
        ${forced.map((c) => `<tr><td>${name(c)}</td><td class="num">${fmt(c.forced.heat_w)}</td><td class="num">${fmt(c.forced.required_m3h)}</td><td class="num">${fmt(c.forced.fan_m3h, 0)}</td><td>${enough(c.forced.passes)}</td></tr>`).join('')}
        ${h.line_up ? `<tr class="band"><td>Line-up, treated as one volume</td><td></td><td class="num">${fmt(h.line_up.required_m3h)}</td><td class="num">${fmt(h.line_up.fan_m3h, 0)}</td><td>${enough(h.line_up.passes)}</td></tr>` : ''}</tbody></table></div>` : ''}
      ${natural.map((c) => `<h3 style="margin:var(--space-5) 0 var(--space-2)">Natural convection: ${name(c)}</h3>
        <div class="metric-row" style="max-width:860px"><div><span class="muted small">Surface area</span><b>${fmt(c.natural.area_m2, 3)} m²</b></div><div><span class="muted small">Temperature rise</span><b>${fmt(c.natural.delta_t_c, 2)} °C</b></div><div><span class="muted small">Limit (TMax − TInt)</span><b>${fmt(c.natural.limit_c, 0)} °C</b></div></div>
        <div style="margin-top:var(--space-3);max-width:860px">${c.natural.passes ? banner('ok', 'The rise is under the limit, so natural convection is enough.') : banner('bad', 'The rise is over the limit; natural convection is not enough for this cabinet.')}</div>`).join('')}`;
  };
})();
