/* Screen: substation Settings on bomgen.app.api (plan M10c), edited here (M17c). The page it
   loads is the Parts page's (parts_page, plan M23), which screens-parts.js shares through App.sub. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, select, pageHead, toast } = App;
  const ro = (html) => html.replace('data-dirty="1"', 'readonly').replace('class="input', 'class="ctl input');
  const fixed = (v, unit) => `<div class="input-affix">${ro(input('x', v, { num: true, mono: true }))}${unit ? `<span class="affix">${esc(unit)}</span>` : ''}</div>`;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;

  /* ---------- data: one substation page per (project file, substation id) ---------- */
  const SUB = { key: '', state: 'idle', page: null, error: null };
  const real = () => S.backend === 'yes' && S.project && S.project.real && S.sub;
  function page() {
    const key = `${S.project.file}#${S.sub}`;
    if (SUB.key !== key) { Object.assign(SUB, { key, state: 'idle', page: null, error: null }); ST.reset(); App.sub.resets.forEach((f) => f()); }
    if (SUB.state === 'idle') {
      SUB.state = 'loading';
      const current = () => SUB.key === key;  // the user may have moved on while it loaded
      Bridge.call('parts_page', S.project.file, S.sub)
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
    if (!real()) return `<div class="page">${pageHead('Settings')}<div class="empty"><b>Open a substation first.</b></div></div>`;
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
    const own = p.project_choice[kind], lib = (p.brands[kind] || [])[0] || {};
    const from = own ? brandName(p, kind, own) : lib.product || 'Library default';
    const same = !own && kind === 'mcb_dc' ? 'Same as AC branches' : `Same as the project (${from})`;
    const opts = [['', same], ...(p.brands[kind] || []).map((b) => [b.id, b.name])];
    return edit('brand_' + kind, esc(label), choice('brand_' + kind, opts));
  }
  const general = (p) => `<div class="form form--2">
    ${edit('name', 'Substation name', text('name'), 'Shown in the app and in each sheet header.')}
    ${field('Substation id', ro(input('s-id', p.id, { mono: true })), 'Names the substation in the register and in tags. Not printed.')}
    ${Object.keys(p.brands).length ? `<div class="span-2 section" style="margin:0">
      <h3>Catalogue brands</h3>
      <p class="lede">The project's brands apply unless this substation chooses its own.</p>
      <div class="form form--2" style="margin-top:var(--space-3)">${KINDS.map(([k, l]) => brandSelect(p, k, l)).join('')}</div></div>` : ''}
    <div class="span-2 section" style="margin:0">
      <h3>From the project</h3>
      <p class="lede">These come from the project and are the same for every substation in it.</p>
      <dl class="kv"><dt>Project</dt><dd>${esc(p.project.name)}</dd><dt>Client</dt><dd>${esc(p.project.client || '—')}</dd><dt>Device library</dt><dd>${esc(p.project.library.name)}, built with ${esc(p.project.library.version)}</dd></dl>
      <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary" data-action="goto" data-to="#/project/info">Open project overview</button></div>
    </div></div>`;
  const docOpts = (p) => p.documents.map((d) => [d.key, d.key]);
  const entryOf = (p, key) => p.documents.find((d) => d.key === key);
  const docCells = (e) => (e ? `<td class="mono">${esc(e.doc_no)}</td><td class="mono">${esc(e.rev)}</td><td class="mono">${esc(e.issue_date)}</td>` : `<td colspan="3"><span class="err small">${icon('error')}<span>Not in the register</span></span></td>`);
  const documents = (p) => `<p class="lede muted" style="max-width:68ch;margin-bottom:var(--space-4)">Each calculation sheet prints the document number, revision and issue date of the register entry it names. Cabinet BOMs choose theirs on each panel. The register itself is on the project page.</p>
    <div class="table-wrap" style="max-width:980px"><table class="table"><thead><tr><th>Sheet</th><th style="width:300px">Register document</th><th>Document no.</th><th style="width:70px">Rev</th><th style="width:120px">Issue date</th></tr></thead>
    <tbody>${p.calculations.map((c) => { const key = 'calc_' + c.key; return `<tr><td>${esc(SHEETS[c.key])}<span class="cell-sub">${esc(c.scope)}</span></td><td${App.changedCell(key in ST.draft)[0]}>${App.changedCell(key in ST.draft)[1]}<label class="sr-only" for="st-${key}">Register document, ${esc(SHEETS[c.key])}</label>${choice(key, docOpts(p))}${ST.errors[key] ? `<span class="err small">${icon('error')}<span>${ST.err(key)}</span></span>` : ''}</td>${docCells(entryOf(p, ST.shown(key)))}</tr>`; }).join('')}</tbody></table></div>
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
      return `<tr><td>${esc(label)}<span class="cell-sub mono">${esc(c.key)}</span>${ST.errors[key] ? `<span class="err small">${icon('error')}<span>${ST.err(key)}</span></span>` : ''}</td><td${App.changedCell(key in ST.draft)[0]}>${App.changedCell(key in ST.draft)[1]}<label class="sr-only" for="st-${key}">${esc(label)}</label>${text(key, { num: true, mono: true, placeholder: String(d) })}</td><td class="muted">${esc(pc ? '%' : unit)}</td>
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
  /* ---------- YAML: substation.yaml edited as text, checked by the engine, applied to the form (M37) ---------- */
  const YT = { text: null, check: null, seq: 0, timer: 0 };  // null text: the saved file, unedited
  /* Every Settings field, by its form key and its path in substation.yaml. */
  function formKeys(p) {
    return ['name', 'document', 'file_name', ...KINDS.map(([k]) => 'brand_' + k), ...p.calculations.map((c) => 'calc_' + c.key),
      ...Object.keys(SHEET_LABELS).map((k) => 'sheet_' + k), ...p.constants.map((c) => 'c_' + c.key)];
  }
  function yamlErrors(p) {  // line -> message, from the edited text's check or else the saved file's problems
    const errs = {}, list = YT.text == null ? p.problems.filter((x) => x.file === p.file) : (YT.check ? YT.check.problems : []);
    list.filter((x) => x.line).forEach((x) => { errs[x.line] = (errs[x.line] ? errs[x.line] + ' ' : '') + x.message; });
    return [errs, YT.text == null ? [] : (YT.check ? YT.check.problems.filter((x) => !x.line) : [])];
  }
  function yamlParts(p) {
    const text = YT.text == null ? p.yaml : YT.text, lines = text.replace(/\n$/, '').split('\n'), [errs, loose] = yamlErrors(p);
    const n = Object.keys(errs).length + loose.length, edited = YT.text != null && YT.text !== p.yaml;
    const ready = edited && YT.check && YT.check.text === YT.text && !n;
    return {
      badge: !edited || YT.check && YT.check.text === YT.text ? (n ? badge('bad', plural(n, 'error'), 'error') : badge('ok', 'No errors', 'check')) : '<span class="muted small"><span class="spinner"></span> Checking…</span>',
      gut: lines.map((_, i) => `<div class="${errs[i + 1] ? 'e' : ''}">${i + 1}</div>`).join(''),
      msgs: [...Object.entries(errs).map(([line, m]) => [`Line ${line}: ${m}`]), ...loose.map((x) => [`${x.location ? x.location + ': ' : ''}${x.message}`])]
        .map(([m]) => `<div class="err small" style="color:var(--color-danger-text);margin-top:8px;display:flex;gap:6px">${icon('error')}<span>${esc(m)}</span></div>`).join(''),
      rows: lines.length + 1, edited, ready
    };
  }
  function yaml(p) {
    const name = p.file.split(/[\\/]/).slice(-3).join('/'), y = yamlParts(p);
    return `<div class="toolbar"><span class="mono" style="font-size:12.5px">${esc(name)}</span><span id="yt-badge">${y.badge}</span><span class="sp"></span>
        <button class="btn btn--secondary btn--sm" data-action="yt-revert" id="yt-revert" ${y.edited ? '' : 'disabled'}>Revert</button>
        <button class="btn btn--primary btn--sm" data-action="yt-apply" id="yt-apply" ${y.ready ? '' : 'disabled'}>${icon('check')}Apply to form</button></div>
      <p class="muted small" style="margin:0 0 var(--space-2)">Apply to form drafts the Settings fields from this text; Save writes them. Other keys are edited on their own pages.</p>
      <div class="code code--edit"><div class="gut" id="yt-gut" aria-hidden="true">${y.gut}</div>
        <label class="sr-only" for="yt-src">${esc(name)} source</label><textarea id="yt-src" class="src" spellcheck="false" wrap="off" rows="${y.rows}">${esc(YT.text == null ? p.yaml : YT.text)}</textarea></div>
      <div id="yt-msgs">${y.msgs}</div>`;
  }
  function yamlPatch() {  // update around the editor without a render, which would drop the caret
    const p = SUB.page; if (!p || !document.getElementById('yt-src')) return;
    const y = yamlParts(p);
    document.getElementById('yt-badge').innerHTML = y.badge;
    document.getElementById('yt-gut').innerHTML = y.gut;
    document.getElementById('yt-msgs').innerHTML = y.msgs;
    document.getElementById('yt-src').rows = y.rows;
    document.getElementById('yt-apply').disabled = !y.ready;
    document.getElementById('yt-revert').disabled = !y.edited;
  }
  function yamlCheck() {
    const p = SUB.page, text = YT.text, seq = ++YT.seq;
    const paths = formKeys(p).map((k) => stSpec(k)[0]);
    Bridge.call('check_substation_yaml', S.project.file, S.sub, text, paths)
      .then((r) => { if (seq === YT.seq) { YT.check = { ...r, text }; yamlPatch(); } })
      .catch((err) => { if (seq === YT.seq) toast(err.message, 'error'); });
  }
  document.addEventListener('input', (e) => {
    if (e.target.id !== 'yt-src') return;
    YT.text = e.target.value; yamlPatch();
    clearTimeout(YT.timer); YT.timer = setTimeout(yamlCheck, 350);
  });
  ACTIONS['yt-revert'] = () => { Object.assign(YT, { text: null, check: null }); YT.seq++; App.render(); };
  ACTIONS['yt-apply'] = () => {
    const p = SUB.page, c = YT.check;
    if (!c || c.text !== YT.text || !c.values) return;
    if (c.other_changes.length) {
      toast(`Not applied: ${c.other_changes.join(', ')} ${c.other_changes.length === 1 ? 'has' : 'have'} no field on Settings. Revert ${c.other_changes.length === 1 ? 'that change' : 'those changes'} or edit ${c.other_changes.length === 1 ? 'it' : 'them'} on ${c.other_changes.length === 1 ? 'its' : 'their'} own page.`, 'error');
      return;
    }
    let n = 0;
    formKeys(p).forEach((key) => {
      const v = c.values[stSpec(key)[0].join('.')], before = key in ST.draft;
      const row = key.startsWith('c_') && p.constants.find((x) => 'c_' + x.key === key);
      let typed = v == null ? '' : PCT.has(key.slice(2)) && row ? String(Math.round(v * 1000) / 10) : String(v);
      if (row && v == null && !row.changed) typed = String(stSaved(key));  // not written, and not written before
      ST.apply(key, typed);
      if (key in ST.draft || before) n += 1;
    });
    S.dirty = ST.dirty();
    Object.assign(YT, { text: null, check: null }); YT.seq++;
    toast(n ? `Applied to the form: ${plural(Object.keys(ST.draft).length, 'unsaved change')}` : 'The form already matches the YAML', 'check');
    App.render();
  };

  /* The Parts screen (screens-parts.js) shares this substation page; it loads parts_page, a superset. */
  /* peek: the open substation's page if it is already loaded, without loading it (the rail asks on every render). */
  App.sub = { real, page, waiting, problems, resets: [], reload: () => { SUB.state = 'idle'; }, set: (p) => { SUB.page = p; }, peek: () => (real() && SUB.key === `${S.project.file}#${S.sub}` ? SUB.page : null) };
  App.sub.resets.push(() => Object.assign(YT, { text: null, check: null }));
})();
