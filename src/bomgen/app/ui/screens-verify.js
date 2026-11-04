/* Screens: Checks and Build on bomgen.app.api (plan M10d).
   Checks lists the loader's located problems, then the engine's check report. Build writes the workbook
   the way `bomgen build` does. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, field, input, pageHead, dialog, closeDialog, toast, $ } = App;
  const real = () => S.backend === 'yes' && S.project && S.project.real && S.sub;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;
  const editable = (html) => html.replace('data-dirty="1"', 'data-dirty="0"');
  const tail = (file) => String(file).split(/[\\/]/).slice(-2).join('/');
  /* A path wraps only after its separators. */
  const breakable = (path) => esc(path).replace(/([\\/])/g, '$1<wbr>');
  const kb = (n) => `${Math.max(1, Math.round(n / 1024))} KB`;
  const CHECKS = {
    sfp_slots: 'SFPs fit the port plans', dc_main: 'Main MCB covers the feed current', airflow: 'Fans cover the heat load',
    line_up: 'Line-up airflow', natural_convection: 'Natural convection', di_capacity: 'Digital inputs cover the hardwired points',
    library_version: 'Library version', branch_mcb: 'Branch MCB covers the device', dc_float: 'Rated for the battery float voltage',
    part_number: 'Part number on the BOM', external_ac: 'AC loose loads left out of the totals', l2_link: 'Link to the L2 switch', external_link: 'External link',
    duplicate_tag: 'Unique device tags', untagged_device: 'Devices carry a tag', document_number_placeholder: 'Document number typed',
    part_source: 'Power and inrush from a source', vendor_list: 'Parts on the vendor list', part_state: 'Parts released, not draft or obsolete',
    design_basis: 'Design basis', override: 'Overrides (ADR 0040)'
  };
  const STATUS = { pass: ['ok', 'Pass', 'check'], warn: ['warn', 'Flag', 'warn'], fail: ['bad', 'Fail', 'error'] };
  const status = (s) => badge(...STATUS[s]);
  const open = (i) => i.status === 'warn' && !i.accepted;  // ADR 0036: an accepted warning is not open
  /* ADR 0040: a risky override warns until it has a reason; the reason is edited where the override is listed. */
  const reasonable = (i) => i.check === 'override' && (open(i) || !!(i.values && i.values.reason));

  /* One cached answer per (project file, substation id); "Run checks again" and a build reload it. */
  function cache(name, call) {
    const c = cache[name] || (cache[name] = { key: '', state: 'idle', data: null, error: null });
    const key = `${S.project.file}#${S.sub}`;
    if (c.key !== key) Object.assign(c, { key, state: 'idle', data: null, error: null });
    if (c.state === 'idle') {
      c.state = 'loading';
      const current = () => c.key === key;
      call().then((d) => { if (current()) { c.data = d; c.error = null; } }).catch((err) => { if (current()) { c.error = err; toast(err.message, 'error'); } })
        .then(() => { if (current()) { c.state = 'loaded'; summarize(); App.render(); } });
    }
    return c.state === 'loaded' || c.data ? c : null;  // a reload keeps showing the last answer
  }
  const reload = (name) => { if (cache[name]) cache[name].state = 'idle'; };
  App.onDiskChange(() => { Object.keys(cache).forEach(reload); });
  /* The nav and status bar show the last answer for this substation. */
  function summarize() {
    const c = cache.checks && cache.checks.data, t = cache.target && cache.target.data;
    const problems = (c || t || {}).problems;
    if (!problems) return;
    S.verify = { key: `${S.project.file}#${S.sub}`, errors: problems.filter((p) => p.level === 'error').length,
      warnings: problems.filter((p) => p.level === 'warning').length + (c ? c.engine.items.filter(open).length : 0),
      failed: !!(c && c.engine.failed) };
  }
  const waiting = (title, c, lede) => `<div class="page">${pageHead(title, c && c.error ? esc(c.error.message) : lede)}</div>`;

  /* ---------- Checks ---------- */
  let level = 'all'; let levelKey = ''; let running = false;
  SCREENS.checks = () => {
    if (!real()) return `<div class="page">${pageHead('Checks')}<div class="empty"><b>Open a substation first.</b></div></div>`;
    const c = cache('checks', () => Bridge.call('run_checks', S.project.file, S.sub)
      .finally(() => { if (running) { running = false; toast('Checks finished'); } }));
    if (!c || !c.data) return waiting('Checks', c, 'Loading the files and running the checks…');
    if (levelKey !== c.key) { level = 'all'; levelKey = c.key; }  // each substation opens on every problem
    const { problems, engine } = c.data;
    const flagged = engine.items.filter(open).length;
    const errors = problems.filter((p) => p.level === 'error').length, warnings = problems.length - errors;
    const shown = problems.filter((p) => level === 'all' || p.level === (level === 'errors' ? 'error' : 'warning'));
    const head = errors ? banner('bad', `<b>${plural(errors, 'error')} must be fixed before you can build.</b> Warnings do not block a build.`)
      : engine.failed ? banner('bad', '<b>An engine check failed.</b> The workbook can still be built; read the failed checks below first.', '<a class="btn btn--secondary btn--sm" href="#/build">Go to Build</a>')
      : banner('ok', `<b>No errors.</b> You can build the workbook.${warnings || flagged ? ` ${[warnings && plural(warnings, 'warning'), flagged && plural(flagged, 'engine flag')].filter(Boolean).join(' and ')} worth reading first.` : ''}`, '<a class="btn btn--primary btn--sm" href="#/build">Go to Build</a>');
    return `<div class="page">${pageHead('Checks', 'Problems in the input files, then the engine\'s own checks on the result.',
      `<button class="btn btn--secondary" data-action="checks-rerun" ${running ? 'aria-busy="true" disabled' : ''}>${running ? '<span class="spinner"></span>Checking…' : icon('refresh') + 'Run checks again'}</button>`)}
      ${head}
      <div class="toolbar" style="margin-top:var(--space-5)"><h2 style="margin-right:var(--space-3)">Problems</h2>
        ${problems.length < 2 ? '' : [['all', `All ${problems.length}`], ['errors', `Errors ${errors}`], ['warnings', `Warnings ${warnings}`]].map(([k, t]) => `<button class="chip" aria-pressed="${level === k}" data-action="checks-level" data-v="${k}">${t}</button>`).join('')}</div>
      ${!problems.length ? '<p class="muted">The input files load without problems.</p>' : `<div class="table-wrap"><table class="table"><thead><tr><th style="width:100px">Level</th><th>Where</th><th>What is wrong</th><th style="width:170px"><span class="sr-only">Action</span></th></tr></thead><tbody>
        ${shown.map((p) => `<tr><td style="vertical-align:top;padding-top:8px">${p.level === 'error' ? badge('bad', 'Error', 'error') : badge('warn', 'Warning', 'warn')}</td>
          <td class="wrap" style="vertical-align:top"><span class="mono small">${esc(tail(p.file))}${p.line ? ':' + p.line : ''}</span>${p.location ? `<span class="cell-sub mono">${esc(p.location)}</span>` : ''}</td>
          <td class="wrap" style="vertical-align:top">${esc(p.message)}</td>
          <td style="vertical-align:top;padding-top:5px"><button class="btn btn--secondary btn--sm" data-action="checks-goto" data-i="${problems.indexOf(p)}">${esc(App.whereToFix(p).label)}</button></td></tr>`).join('')
          || '<tr class="empty-row"><td colspan="4">Nothing to show with this filter.</td></tr>'}</tbody></table></div>`}
      <div class="toolbar" style="margin-top:var(--space-6)"><h2>Engine checks</h2></div>
      ${engine.run ? engineTable(engine.items) : `<p class="muted">${esc(engine.reason)} Then run the checks again.</p>`}
      ${unusedTable(c.data.unused || [])}</div>`;
  };
  function engineTable(items) {
    if (!items.length) return '<p class="muted">The engine has nothing to check in this substation yet.</p>';
    const groups = [...new Set(items.map((i) => i.check))];
    const worst = (list) => (list.some((i) => i.status === 'fail') ? 'fail' : list.some((i) => i.status === 'warn') ? 'warn' : 'pass');
    return `<div class="table-wrap" style="margin-top:var(--space-3)"><table class="table"><thead><tr><th>Check</th><th style="width:110px">Panel</th><th style="width:110px">Result</th><th>Detail</th><th style="width:110px"><span class="sr-only">Action</span></th></tr></thead><tbody>
      ${groups.map((g) => { const list = items.filter((i) => i.check === g), all = worst(list) === 'pass';  // groups that all pass stay folded into their header
        return `<tr class="band"><td colspan="2">${esc(CHECKS[g] || g)}</td><td>${status(worst(list))}</td><td class="muted small" colspan="2">${plural(list.length, 'item')}${all ? '' : ` · ${list.filter((i) => i.status === 'fail' || open(i)).length} to read`}</td></tr>
        ${all ? '' : list.map((i) => `<tr><td class="wrap">${esc(i.subject || '')}</td><td class="mono small">${esc(i.panel_id || '—')}</td><td>${i.accepted ? badge('info', 'Accepted', 'check') : status(i.status)}</td><td class="wrap">${esc(i.message)}${goto(i)}${i.accepted ? `<span class="cell-sub">Accepted: ${esc(i.accepted)}</span>` : ''}</td>
          <td>${reasonable(i) ? `<button class="btn btn--ghost btn--sm" data-action="checks-reason" data-i="${items.indexOf(i)}">${i.values.reason ? 'Edit the reason…' : 'Give a reason…'}</button>` : open(i) ? `<button class="btn btn--ghost btn--sm" data-action="checks-accept" data-i="${items.indexOf(i)}">Accept…</button>` : ''}</td></tr>`).join('')}`; }).join('')}</tbody></table></div>`;
  }
  /* ADR 0036: an acceptance no warning matches any more stays listed until removed. */
  const unusedTable = (list) => (!list.length ? '' : `<div class="toolbar" style="margin-top:var(--space-6)"><h2>Unused acceptances</h2></div>
    <p class="muted small">No warning matches these any more. They stay in the file until you remove them.</p>
    <div class="table-wrap" style="margin-top:var(--space-3)"><table class="table"><thead><tr><th>Check</th><th style="width:110px">Panel</th><th>Subject</th><th>Reason</th><th style="width:110px"><span class="sr-only">Action</span></th></tr></thead><tbody>
      ${list.map((a) => `<tr><td>${esc(CHECKS[a.check] || a.check)}</td><td class="mono small">${esc(a.panel_id || '—')}</td><td class="wrap">${esc(a.subject || '')}</td><td class="wrap">${esc(a.reason)}</td><td><button class="btn btn--ghost btn--sm" data-action="checks-unaccept" data-i="${a.index}">${icon('trash')}Remove</button></td></tr>`).join('')}</tbody></table></div>`);
  const rechecked = (page) => { cache.checks.data = page; reload('target'); summarize(); App.render(); };
  ACTIONS['checks-accept'] = (el) => {
    const i = cache.checks.data.engine.items[+el.dataset.i];
    dialog({ title: 'Accept this warning?', body: `<div class="form"><p>${esc(CHECKS[i.check] || i.check)}${i.panel_id ? ` · <span class="mono">${esc(i.panel_id)}</span>` : ''}: ${esc(i.message)}</p>
      ${field('Reason', editable(input('ac-reason', '', { placeholder: 'For example, agreed with the client on 2026-11-03' })), 'Saved with the substation and copied into the next issue record. The warning then no longer counts as open.')}
      ${field('Accepted by', editable(input('ac-by', '', { placeholder: 'Optional' })))}<div id="ac-err"></div></div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="checks-accept-do" data-i="${el.dataset.i}">Accept warning</button>` });
    setTimeout(() => { const n = $('#ac-reason'); if (n) n.focus(); }, 0);
  };
  ACTIONS['checks-accept-do'] = (el) => {
    const i = cache.checks.data.engine.items[+el.dataset.i];
    Bridge.call('accept_warning', S.project.file, S.sub, i.check, i.panel_id, i.subject, $('#ac-reason').value, $('#ac-by').value || null)
      .then((page) => { closeDialog(); rechecked(page); toast('Warning accepted'); })
      .catch((e) => { const n = $('#ac-err'); if (n) n.innerHTML = banner('bad', esc(e.message)); });
  };
  ACTIONS['checks-reason'] = (el) => {
    const i = cache.checks.data.engine.items[+el.dataset.i];
    dialog({ title: 'Why this override?', body: `<div class="form"><p>${i.panel_id ? `<span class="mono">${esc(i.panel_id)}</span> · ` : ''}${esc(i.subject)}: ${esc(i.message)}</p>
      ${field('Reason', editable(input('or-reason', (i.values && i.values.reason) || '', { placeholder: 'For example, the client feeds this panel at 6 A' })), 'Saved beside the override and printed on the Revision History sheet of the next issue. Empty removes it.')}<div id="or-err"></div></div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="checks-reason-do" data-i="${el.dataset.i}">Save reason</button>` });
    setTimeout(() => { const n = $('#or-reason'); if (n) n.focus(); }, 0);
  };
  ACTIONS['checks-reason-do'] = (el) => {
    const i = cache.checks.data.engine.items[+el.dataset.i];
    Bridge.call('set_override_reason', S.project.file, S.sub, i.panel_id, i.subject, $('#or-reason').value)
      .then((page) => { closeDialog(); rechecked(page); toast('Reason saved'); })
      .catch((e) => { const n = $('#or-err'); if (n) n.innerHTML = banner('bad', esc(e.message)); });
  };
  ACTIONS['checks-unaccept'] = (el) => Bridge.call('remove_acceptance', S.project.file, S.sub, +el.dataset.i)
    .then((page) => { rechecked(page); toast('Acceptance removed', 'trash'); }).catch((e) => toast(e.message, 'error'));
  /* Plan M54: a design basis item leads to its field on Settings › Design basis. */
  const goto = (i) => (i.values && i.values.field ? ` <button class="btn btn--secondary btn--sm" data-action="checks-field" data-loc="${esc(i.values.field)}">Go to the field</button>` : '');
  ACTIONS['checks-field'] = (el) => { App.fix({ file: 'substation.yaml', location: el.dataset.loc }); };
  ACTIONS['checks-level'] = (el) => { level = el.dataset.v; App.render(); };
  ACTIONS['checks-rerun'] = () => { running = true; reload('checks'); reload('target'); App.render(); };
  ACTIONS['checks-goto'] = (el) => {
    App.fix(cache.checks.data.problems[+el.dataset.i]);
  };

  /* ---------- Build ---------- */
  const B = { state: 'ready', result: null, error: null, name: null, folder: null, compare: false, previous: '', open: true, issue: null };
  SCREENS.build = () => {
    if (!real()) return `<div class="page">${pageHead('Build')}<div class="empty"><b>Open a substation first.</b></div></div>`;
    const c = cache('target', () => Bridge.call('build_target', S.project.file, S.sub));
    if (!c || !c.data) return waiting('Build', c, 'Reading the substation…');
    const t = c.data;
    if (B.key !== c.key) Object.assign(B, { key: c.key, state: 'ready', result: null, error: null, name: t.file_name || '', folder: t.folder, compare: false, previous: '' });
    const errors = t.problems.filter((p) => p.level === 'error').length, warnings = t.problems.length - errors + t.flags;
    const blocked = errors > 0, busy = B.state === 'building';
    let result = '';
    if (busy) result = `<div class="stack" style="max-width:520px"><h3>Building…</h3><div class="progress progress--busy" role="progressbar" aria-label="Build progress"><i></i></div>
      <p class="muted small">Loading the inputs, running the engine, building the sheets, then writing the workbook. This takes a few seconds.</p></div>`;
    if (B.state === 'open') result = banner('bad', `<b>The file could not be written.</b> <span class="mono">${esc(B.name)}</span> is open in another program, such as Excel. Close it there and try again, or save under a different name.`,
      '<div class="row" style="flex-wrap:nowrap"><button class="btn btn--primary btn--sm" data-action="build-run">Try again</button><button class="btn btn--secondary btn--sm" data-action="build-rename">Save as new name</button></div>');
    if (B.state === 'failed') result = banner('bad', `<b>The workbook was not written.</b> ${esc(B.error.message)}`);
    if (B.state === 'done') result = done(B.result);
    return `<div class="page">${pageHead('Build', 'Write this substation\'s workbook once the checks are clear.')}
      ${blocked ? banner('bad', `<b>${plural(errors, 'error')} ${errors === 1 ? 'blocks' : 'block'} the build.</b> Fix ${errors === 1 ? 'it' : 'them'} under Checks, then come back.`, '<a class="btn btn--secondary btn--sm" href="#/checks">Open checks</a>') : ''}
      <div style="display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:var(--space-6);align-items:start;margin-top:${blocked ? 'var(--space-5)' : '0'}">
      <div>
        <div class="form" style="max-width:640px">
          ${field('File name', editable(input('b-name', B.name, { mono: true })), t.file_name ? (B.name === t.file_name ? 'From the pattern in Settings → Output.' : `The pattern in Settings → Output gives <span class="mono">${esc(t.file_name)}</span>.`) : 'The pattern in Settings → Output gives the name once the files load.')}
          ${field('Save in', `<div class="row" style="flex-wrap:nowrap">${editable(input('b-dir', B.folder, { mono: true }))}<button class="btn btn--secondary" data-action="build-folder">Browse…</button></div>`)}
          <div class="field"><span class="label">Options</span><div class="stack"><label class="switch"><input type="checkbox" id="b-compare" data-action="build-compare" data-dirty="0" ${B.compare ? 'checked' : ''}>Highlight cells changed since the previous issue</label>
            ${record(t.issue.record)}
            <div class="row" style="margin-left:44px"><input class="input input--mono" id="b-previous" style="width:320px" placeholder="Choose the previous issue (.xlsx)" value="${esc(B.previous.split(/[\\/]/).pop())}" title="${esc(B.previous)}" readonly ${B.compare ? '' : 'disabled'}><button class="btn btn--secondary btn--sm" data-action="build-previous" ${B.compare ? '' : 'disabled'}>Browse…</button></div>
            <label class="switch"><input type="checkbox" id="b-summary" data-action="build-summary" data-dirty="0" ${t.include.includes('summary_bom') ? 'checked' : ''}>Add a Summary BOM sheet: every part totalled by ordering code, with where it is used</label>
            <label class="switch"><input type="checkbox" id="b-notes" data-action="build-notes" data-dirty="0" ${t.include.includes('notes') ? 'checked' : ''}>Add a Notes sheet: every row's note, which the BOM sheets never print</label>
            <label class="switch"><input type="checkbox" id="b-open" data-action="build-open-toggle" data-dirty="0" ${B.open ? 'checked' : ''}>Open the workbook when it is written</label></div></div>
        </div>
        <div style="margin-top:var(--space-5)" class="row"><button class="btn btn--primary" data-action="build-run" ${blocked || busy ? 'disabled' : ''} ${busy ? 'aria-busy="true"' : ''}>${busy ? '<span class="spinner"></span>Building…' : icon('build') + 'Build workbook'}</button><button class="btn btn--secondary" data-action="build-issue" ${blocked || busy || t.issue.refusal ? 'disabled' : ''} title="${esc(t.issue.refusal || 'Build, then record this revision as issued')}">Build as issued…</button>${blocked ? `<span class="muted small">Unavailable until the ${plural(errors, 'error')} ${errors === 1 ? 'is' : 'are'} fixed.</span>` : ''}</div>
        <div style="margin-top:var(--space-5)" aria-live="polite">${result}</div>
      </div>
      <aside><h3>This workbook contains</h3>${t.sheets ? `<ul class="checklist" style="margin-top:var(--space-3)">${t.sheets.map((s) => `<li>${icon('preview')}<span>${s.cabinet ? `Sheet ${esc(s.name)}: ${esc(s.cabinet)}` : esc(s.name)}</span></li>`).join('')}</ul>` : '<p class="muted small" style="margin-top:var(--space-2)">The sheets are listed once the files load without errors.</p>'}
        <dl class="kv" style="margin-top:var(--space-4);grid-template-columns:120px 1fr"><dt>Library</dt><dd>${esc(t.library.name)} ${esc(t.library.version)}</dd><dt>Revision</dt><dd>${esc(t.revision || '—')}${t.issue.refusal ? ' (issued)' : ''}</dd><dt>Warnings</dt><dd>${warnings ? `${warnings} (do not block)` : 'None'}</dd></dl></aside></div></div>`;
  };
  function done(r) {
    const notPass = r.checks.items.filter((i) => i.status !== 'pass');
    const changes = r.revisions ? r.revisions.changes.length : null;
    return `${banner(r.checks.failed ? 'warn' : 'ok', `<b>Workbook written.</b><div class="small muted">${kb(r.size)} · ${plural(r.sheets.length, 'sheet')}${changes !== null ? ` · ${plural(changes, 'change')} marked since the previous issue` : ''}</div>`,
      '<div class="row" style="flex-wrap:nowrap"><button class="btn btn--primary btn--sm" data-action="build-open">Open workbook</button><button class="btn btn--secondary btn--sm" data-action="build-show">Show in folder</button><button class="btn btn--ghost btn--sm" data-action="build-summary-csv">Export summary as CSV</button></div>')}
      <p class="mono small path-line">${breakable(r.path)}</p>
      ${r.issued ? banner('ok', `<b>Recorded Rev ${esc(r.issued.rev)} as issued.</b> The next build compares with it.`) : ''}
      ${r.not_issued ? banner('warn', `<b>${esc(r.not_issued)}</b> Read the failed checks below, fix them and build as issued again.`) : ''}
      ${r.record_warning ? banner('warn', `<b>Not compared with the recorded issue.</b> ${esc(r.record_warning)}`) : ''}
      <div class="stack" style="margin-top:var(--space-4)"><h3>Check report</h3>
        <p class="muted small">${plural(r.checks.items.length, 'check')}: ${r.checks.items.length - notPass.length} pass${notPass.length ? `, ${notPass.length} to read` : ''}. Saved next to the workbook as <span class="mono">.checks.json</span>.</p>
        ${notPass.length ? `<ul class="checklist">${notPass.slice(0, 6).map((i) => `<li class="${i.status === 'fail' ? 'bad' : ''}">${icon(i.status === 'fail' ? 'error' : 'warn')}<span>${esc(CHECKS[i.check] || i.check)}${i.subject ? ` · ${esc(i.subject)}` : ''}${i.panel_id ? ` · <span class="mono">${esc(i.panel_id)}</span>` : ''}: ${esc(i.message)}</span></li>`).join('')}</ul>${notPass.length > 6 ? '<a href="#/checks">All of them under Checks</a>' : ''}` : ''}</div>`;
  }
  const keep = () => { const n = $('#b-name'), d = $('#b-dir'); if (n) B.name = n.value.trim(); if (d) B.folder = d.value.trim(); };
  /* ADR 0036: with no previous issue chosen, the build compares with the latest recorded issue. */
  function record(r) {
    if (!r) return '';
    if (r.warning) return `<div style="margin-left:44px">${banner('warn', esc(r.warning))}</div>`;
    return `<p class="muted small" style="margin-left:44px">Without a choice here, the build compares with Rev ${esc(r.rev)} as issued: <span class="mono">${esc(r.file)}</span>.</p>`;
  }
  function build(replace = false, issue = B.issue) {
    keep();
    B.state = 'building'; B.issue = issue; App.render();
    Bridge.call('build_workbook', S.project.file, S.sub, B.folder, B.name, B.compare && B.previous ? B.previous : null, replace, issue || null)
      .then((r) => {
        Object.assign(B, { state: 'done', result: r, issue: null }); reload('checks'); toast(r.issued ? `Rev ${r.issued.rev} issued` : 'Workbook written');
        if (r.issued) { reload('target'); App.preview.reload(); }
        if (B.open) Bridge.call('open_file', r.path).catch((err) => toast(err.message, 'error'));
      })
      .catch((err) => {
        if (err.kind === 'file_exists') { B.state = 'ready'; confirmReplace(); return; }
        B.issue = null;
        Object.assign(B, { state: err.kind === 'file_open' ? 'open' : 'failed', error: err });
      })
      .then(() => App.render());
  }
  function confirmReplace() {
    dialog({ title: 'Replace the workbook?', body: `<p><span class="mono">${esc(B.name)}</span> is already in <span class="mono">${esc(B.folder)}</span>. Building replaces it.</p>`,
      actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="build-replace">Replace</button>' });
  }
  ACTIONS['build-run'] = () => { if (B.compare && !B.previous) { toast('Choose the previous issue first, or turn highlighting off.', 'warn'); return; } build(false, null); };
  ACTIONS['build-replace'] = () => { closeDialog(); build(true); };
  ACTIONS['build-issue'] = () => {
    if (B.compare && !B.previous) { toast('Choose the previous issue first, or turn highlighting off.', 'warn'); return; }
    keep();
    const t = cache.target.data;
    dialog({ title: `Build Rev ${esc(t.revision)} as issued`, body: `<div class="form"><p>Builds the workbook, then records Rev ${esc(t.revision)} with today's date, the file's fingerprint and the names in the register. Nothing is recorded if a check fails.</p>
      ${field('Description', editable(input('bi-desc', '', { placeholder: 'For example, Issued for approval' })), 'Printed on the Revision History sheet.')}<div id="bi-err"></div></div>`,
      actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="build-issue-do">Build as issued</button>' });
    setTimeout(() => { const n = $('#bi-desc'); if (n) n.focus(); }, 0);
  };
  ACTIONS['build-issue-do'] = () => {
    const text = $('#bi-desc').value.trim();
    if (!text) { $('#bi-err').innerHTML = banner('bad', 'Describe the issue, for example Issued for approval.'); return; }
    closeDialog(); build(false, text);
  };
  ACTIONS['build-rename'] = () => { keep(); B.state = 'ready'; App.render(); const n = $('#b-name'); if (n) { n.focus(); n.select(); } };
  ACTIONS['build-folder'] = () => { keep(); Bridge.call('choose_folder').then((f) => { if (f) { B.folder = f; App.render(); } }).catch((err) => toast(err.message, 'error')); };
  ACTIONS['build-compare'] = (el) => { keep(); B.compare = el.checked; App.render(); };
  ACTIONS['build-open-toggle'] = (el) => { B.open = el.checked; };
  /* ADR 0035: the Summary BOM and the Notes sheet (M71) are saved output settings, so the next build keeps the choice. */
  const includeSheet = (key) => (el) => {
    keep();
    const rest = cache.target.data.include.filter((k) => k !== key);
    const value = el.checked ? [...rest, key] : rest.length ? rest : null;
    Bridge.call('set_substation_field', S.project.file, S.sub, ['output', 'include'], value)
      .then(() => { reload('target'); App.preview.reload(); App.render(); })
      .catch((err) => { el.checked = !el.checked; toast(err.message, 'error'); });
  };
  ACTIONS['build-summary'] = includeSheet('summary_bom');
  ACTIONS['build-notes'] = includeSheet('notes');
  ACTIONS['build-summary-csv'] = () => Bridge.call('export_summary_csv', S.project.file, S.sub)
    .then((r) => { if (r) toast(`Summary exported: ${r.lines} lines`); })
    .catch((err) => toast(err.message, 'error'));
  ACTIONS['build-previous'] = () => { keep(); Bridge.call('choose_file', 'xlsx').then((f) => { if (f) { B.previous = f; App.render(); } }).catch((err) => toast(err.message, 'error')); };
  ACTIONS['build-open'] = () => Bridge.call('open_file', B.result.path).catch((err) => toast(err.message, 'error'));
  ACTIONS['build-show'] = () => Bridge.call('show_in_folder', B.result.path).catch((err) => toast(err.message, 'error'));
})();
