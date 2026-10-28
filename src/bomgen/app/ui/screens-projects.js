/* Screens: Home (all projects) and the Project page (overview, substations, documents, backup and share),
   on bomgen.app.api (plan M10b). Opened in a plain browser they show the prototype's illustrative projects. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, pageHead, illus, dialog, closeDialog, toast, go, $, curProject } = App;
  const statusIcon = { ok: 'check', bad: 'error', warn: 'warn' };
  const ro = (html) => html.replace('data-dirty="1"', 'readonly').replace('class="input', 'class="ctl input');
  const offline = () => S.backend === 'no';
  const fail = (err) => toast(err.kind === 'no_backend' ? 'This works in the app, not in a browser.' : err.message, 'error');
  const day = (iso) => (iso ? String(iso).replace('T', ' ').slice(0, 16) : '—');
  const kb = (b) => (b == null ? '—' : b < 1024 ? `${b} bytes` : `${Math.round(b / 1024)} KB`);
  const inside = (file, folder) => (file.startsWith(folder) ? file.slice(folder.length).replace(/^[\\/]/, '') : file);
  const count = (n, one, many = one + 's') => `${n} ${n === 1 ? one : many}`;
  const LATER = 'Creating and editing projects in the app is not available yet. Edit the YAML files, then open the project again.';
  const later = () => `disabled title="${esc(LATER)}"`;

  /* ---------- the screens' view of a project (the prototype's shape) ---------- */
  const PROJECTS = { state: 'idle', rows: [], once: false };  // once: the list has been read at least once
  function view(row) {
    const active = S.library && row.library && S.library.name === row.library.name ? S.library.version : '';
    return {
      id: row.id, name: row.name, client: row.client || '', path: row.folder, file: row.file, logo: row.project && row.project.logo ? row.project.logo : '',
      library: row.library ? { name: row.library.name, builtWith: row.library.version, active: row.library.local_file ? row.library.version : active || '—', note: row.library.note, local: row.library.local_file } : { name: '—', builtWith: '—', active: '—' },
      opened: day(row.changed), status: row.status.level, statusText: row.status.text,
      substations: row.substations.map((s) => ({ id: s.id, name: s.name, folder: inside(s.file, row.folder), file: s.file, panels: s.panels == null ? '—' : s.panels, changed: day(s.changed), status: s.errors ? 'bad' : 'ok', statusText: s.errors ? `${s.errors} error${s.errors === 1 ? '' : 's'}` : row.status.level === 'bad' ? 'Not checked' : 'Ready', from: '' })),
      documents: (row.documents || []).map((d) => ({ key: d.key, sub: d.substation, label: d.title || d.key, docNo: d.doc_no, rev: d.rev, issue: d.issue_date || '', assumed: false, usedBy: '' })),
      defaults: row.defaults ? defaultsRows(row.defaults) : [],
      problems: row.problems || [], backups: null, real: true
    };
  }
  const defaultsRows = (d) => [
    { label: 'Power margin', value: d.constants.power_margin, unit: '×' },
    { label: 'Spare ports on each switch', value: Math.round(d.spares.port_fraction * 100), unit: '%' },
    { label: 'Spare SFPs per L1 switch', value: d.spares.sfp_per_l1, unit: '' },
    { label: 'Rack space kept free', value: d.spares.rack_u_reserved, unit: 'U' },
    { label: 'Spare DC branches per feed', value: d.spares.dc_branches_per_feed, unit: 'per feed' },
    { label: 'Spare AC branches', value: d.spares.ac_branches, unit: '' }
  ];
  const projects = () => (offline() ? DB.projects : PROJECTS.rows.map(view));
  function loadProjects() {
    PROJECTS.state = 'loading';
    return Bridge.call('list_projects').then((rows) => { PROJECTS.rows = rows; }).catch(fail)
      .then(() => { PROJECTS.state = 'loaded'; PROJECTS.once = true; App.render(); });
  }
  function openProject(file, tab = 'substations') {
    return Bridge.call('open_project', file).then((page) => {
      S.project = view(page); S.proj = S.project.id; S.sub = null; S.dirty = false;
      S.tab.project = tab; PROJECTS.state = 'idle'; go(`#/project/${tab}`);
    }).catch(fail);
  }

  /* ---------- Home: all projects ---------- */
  SCREENS.home = () => {
    if (S.firstRun) {
      return `<div class="page">
        ${pageHead('Welcome to BOM Generator', 'Build the bill of materials, power and heat calculations for substation SCADA systems, one project at a time.')}
        <ol class="steps" style="max-width:600px;gap:18px">
          <li>${icon('library')}<div><b>1. Install a device library</b><div class="muted small">The library is the list of devices a project can use. It arrives as a <span class="mono">.bomlib</span> file from whoever maintains it.</div></div></li>
          <li>${icon('folder')}<div><b>2. Create a project, or import one</b><div class="muted small">A colleague can send you a <span class="mono">.bomproj</span> file. Import it to get their project with all its substations.</div></div></li>
          <li>${icon('panels')}<div><b>3. Add a substation</b><div class="muted small">Enter the network and equipment. The panels are laid out for you, and you can adjust them.</div></div></li>
          <li>${icon('build')}<div><b>4. Check, preview and build the workbook</b></div></li>
        </ol>
        <div class="row" style="margin-top:var(--space-5)">
          <button class="btn btn--primary" data-action="goto" data-to="#/library/import">${icon('upload')}Install a library…</button>
          <button class="btn btn--secondary" disabled>${icon('plus')}New project…</button>
          <button class="btn btn--secondary" disabled>${icon('download')}Import project file…</button>
        </div>
        <p class="muted small" style="margin-top:var(--space-4)">New project and Import are unavailable until a library is installed.</p>
      </div>`;
    }
    if (!offline() && S.backend === 'yes' && PROJECTS.state === 'idle') loadProjects();
    const rows = projects();
    const loading = !offline() && !PROJECTS.once;
    return `<div class="page">
      ${pageHead('Projects', 'Every project on this PC. A project holds several substations, each with its own panels and workbook.',
        `<button class="btn btn--secondary" data-action="import-project">${icon('download')}Import project file…</button><button class="btn btn--secondary" data-action="open-project">${icon('folder')}Open folder…</button><button class="btn btn--primary" data-action="new-project" ${later()}>${icon('plus')}New project…</button>`)}
      <p class="muted small" style="margin:calc(-1 * var(--space-3)) 0 var(--space-4);text-align:right">${esc(LATER)}</p>
      ${S.launch === 'bomproj' ? `<div style="margin-bottom:var(--space-4)">${banner('info', `<b>You opened a project file.</b> <span class="mono">${esc(S.launchFile)}</span> is not added yet. Review what it contains before it is imported.`, `<button class="btn btn--primary btn--sm" data-action="import-launched">Review import…</button>`)}</div>` : ''}
      ${loading ? '<p class="muted">Reading the projects on this PC…</p>' : rows.length ? `<div class="table-wrap"><table class="table table--comfort">
        <thead><tr><th>Project</th><th>Client</th><th class="num">Substations</th><th>Library</th><th>Last changed</th><th>Status</th></tr></thead>
        <tbody>${rows.map((r) => `<tr class="clickable" data-action="open-proj" data-id="${esc(r.id)}" data-file="${esc(r.file || '')}" tabindex="0">
          <td><b style="font-weight:500">${esc(r.name)}</b><span class="cell-sub mono">${esc(r.path)}</span></td>
          <td>${esc(r.client || '—')}</td><td class="num">${r.substations.length}</td><td>${esc(r.library.name)} ${esc(r.library.builtWith)}</td><td>${esc(r.opened)}</td>
          <td>${badge(r.status, r.statusText, statusIcon[r.status])}</td></tr>`).join('')}</tbody></table>
        <div class="table-foot"><span>Select a project to open it</span>${offline() ? `<span>${illus()}</span>` : ''}</div></div>`
        : `<div class="empty"><h3>No projects yet</h3><p class="muted">Import a project file from a colleague, or open a folder that holds a <span class="mono">project.yaml</span>.${S.app ? ` New projects go in <span class="mono">${esc(S.app.workspace)}</span>.` : ''}</p></div>`}
      <div class="section" style="margin-top:var(--space-5);border:0;padding-top:0">
        <div class="banner banner--info">${icon('info')}<div class="grow"><b>Got a device library update?</b><div class="small">Update packages are .bomlib files. Import one to review what it changes before it is installed.</div></div><a class="btn btn--secondary" href="#/library/import">Import update…</a></div>
      </div>
    </div>`;
  };
  ACTIONS['open-proj'] = (el) => {
    closeDialog();
    if (offline()) { if (S.proj !== el.dataset.id) { S.proj = el.dataset.id; S.sub = null; } S.tab.project = 'substations'; go('#/project/substations'); return; }
    openProject(el.dataset.file);
  };
  ACTIONS['open-project'] = () => {
    Bridge.call('choose_project_folder').then((file) => file && openProject(file)).catch(fail);
  };
  window.addEventListener('hashchange', () => { if (App.route().a !== 'home' && PROJECTS.state === 'loaded') PROJECTS.state = 'idle'; });  // re-read on the next visit
  document.addEventListener('keydown', (e) => { const r = e.target.closest && e.target.closest('tr.clickable[data-action]'); if (r && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); r.click(); } });

  /* ---------- Project page ---------- */
  SCREENS.project = () => {
    const p = curProject();
    const tabList = [['info', 'Overview'], ['substations', 'Substations', `<span class="count">${p.substations.length}</span>`], ['documents', 'Documents'], ['share', 'Backup and share']];
    const rb = App.route().b; if (tabList.some(([k]) => k === rb)) S.tab.project = rb;
    const t = S.tab.project;
    const actions = {
      substations: `<button class="btn btn--primary" data-action="new-substation" ${later()}>${icon('plus')}New substation…</button>`,
      share: `<button class="btn btn--primary" data-action="export-project">${icon('upload')}Export project…</button>` }[t] || '';
    const body = { info: projectInfo, substations: projectSubs, documents: projectDocs, share: projectShare }[t](p);
    const problems = p.problems && p.problems.length ? `<div style="margin-bottom:var(--space-4)">${banner('bad', `<b>${p.problems.length} ${p.problems.length === 1 ? 'problem' : 'problems'} in the project files.</b> ${problemList(p.problems)}`)}</div>` : '';
    return `<div class="page">${pageHead(esc(p.name), `${p.client ? esc(p.client) + ' · ' : ''}<span class="mono" style="font-size:13px">${esc(p.path)}</span>`, actions, `<a href="#/home">Projects</a>${icon('chevr')}<span>${esc(p.name)}</span>`)}
      ${problems}${tabs('project', tabList, t, 'Project sections')}
      <div role="tabpanel" aria-labelledby="tab-project-${t}">${body}</div></div>`;
  };
  const MAX_PROBLEMS = 8;
  const problemList = (list) => `<ul style="margin:6px 0 0;padding-left:18px">${list.slice(0, MAX_PROBLEMS).map((x) => `<li><span class="mono small">${esc(x.file.split(/[\\/]/).slice(-2).join('/'))}${x.line ? ':' + x.line : ''}</span>${x.location ? ` <span class="mono small">${esc(x.location)}</span>` : ''}: ${esc(x.message)}</li>`).join('')}</ul>${list.length > MAX_PROBLEMS ? `<div class="small">and ${list.length - MAX_PROBLEMS} more; the Checks screen lists them all.</div>` : ''}`;
  const editNote = (p) => (p.real ? `<p class="muted small" style="margin-bottom:var(--space-4);max-width:68ch">${esc(LATER)}</p>` : '');

  const projectInfo = (p) => `${editNote(p)}<div class="form form--2">
    <div class="span-2">${field('Project name', ro(input('p-name', p.name)), 'Printed in bold at the top of every sheet header, for every substation.')}</div>
    ${field('Client', ro(input('p-client', p.client)))}
    ${field('Logo', ro(input('p-logo', p.logo, { mono: true, placeholder: 'No logo chosen' })), p.logo ? 'PNG. Appears in the left of the page header.' : 'PNG. Appears in the left of the page header. <span style="color:var(--color-warning)">Not set: the header will have no picture.</span>')}
    <div class="span-2 section" style="margin:0">
      <h3>Device library</h3>
      <p class="lede">The project records which library version it was built with, so a colleague can reproduce the workbook. All its substations use the same version.</p>
      <dl class="kv"><dt>Library</dt><dd>${esc(p.library.name)}</dd><dt>Built with</dt><dd>${esc(p.library.builtWith)} ${p.library.local ? badge('plain', "The project's own library file") : p.library.note ? badge('warn', 'Differs from active', 'warn') : badge('ok', 'Matches active', 'check')}</dd><dt>Active on this PC</dt><dd>${esc(p.library.active)}</dd></dl>
      ${p.library.note ? `<p class="small" style="margin-top:var(--space-2);color:var(--color-warning)">${esc(p.library.note)}</p>` : ''}
      <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary" data-action="goto" data-to="#/library">Open library</button></div>
    </div>
    <div class="span-2 section" style="margin:0">
      <h3>Shared defaults</h3>
      <p class="lede">Every substation starts from these values. A substation can set its own; the ones it changes are marked there.</p>
      <div class="form form--3" style="margin-top:var(--space-3)">${p.defaults.map((x, i) => field(x.label, `<div class="input-affix">${ro(input('df' + i, x.value, { num: true, mono: true }))}${x.unit ? `<span class="affix">${esc(x.unit)}</span>` : ''}</div>`)).join('') || '<p class="muted">No shared defaults are set.</p>'}</div>
    </div></div>`;

  const projectSubs = (p) => `<p class="muted" style="max-width:68ch;margin-bottom:var(--space-4)">Each substation has its own network, panels, checks and workbook. To start a new one from an existing one, use “Create from this”.</p>${editNote(p)}
    <div class="table-wrap"><table class="table table--comfort"><thead><tr><th>Substation</th><th class="num">Panels</th><th>Last changed</th><th>Status</th><th style="width:300px"><span class="sr-only">Actions</span></th></tr></thead>
      <tbody>${p.substations.map((s) => `<tr class="clickable" tabindex="0" data-action="open-sub" data-id="${esc(s.id)}">
        <td><b style="font-weight:500">${esc(s.name)}</b><span class="cell-sub mono">${esc(s.folder)}</span>${s.from ? `<span class="cell-sub">Created from ${esc(s.from)}</span>` : ''}</td>
        <td class="num">${esc(s.panels)}</td><td>${esc(s.changed)}</td><td>${badge(s.status, s.statusText, statusIcon[s.status])}</td>
        <td style="text-align:right"><button class="btn btn--secondary btn--sm" data-action="open-sub" data-id="${esc(s.id)}">Open</button> <button class="btn btn--ghost btn--sm" data-action="new-substation" data-from="${esc(s.id)}" ${later()}>${icon('copy')}Create from this…</button></td></tr>`).join('')}</tbody></table>
      <div class="table-foot"><span>${count(p.substations.length, 'substation')}</span>${p.real ? '' : `<span>${illus()}</span>`}</div></div>`;
  ACTIONS['open-sub'] = (el) => { S.sub = el.dataset.id; S.dirty = false; S.layout = { overrides: [], removed: [], history: [], selected: '', openOverrides: false }; go('#/panels'); };

  const projectDocs = (p) => {
    const ids = [...new Set([...p.substations.map((s) => s.id), ...p.documents.map((d) => d.sub)])];
    const groups = ids.map((id) => ({ s: p.substations.find((x) => x.id === id) || { id, name: id }, rows: p.documents.filter((d) => d.sub === id) })).filter((g) => g.rows.length);
    const assumed = p.documents.filter((d) => d.assumed).length;
    return `<p class="lede muted" style="max-width:68ch;margin-bottom:var(--space-4)">One register for the whole project. Each panel and calculation sheet picks a document from it, so a single transmittal list drives every header.</p>
      ${editNote(p)}${assumed ? banner('warn', `<b>The issue date of ${assumed} documents is assumed.</b> Confirm the dates before issuing.`) : ''}
      ${groups.length ? `<div class="table-wrap" style="margin-top:var(--space-4)"><table class="table"><thead><tr><th>Document</th><th>Document no.</th><th style="width:70px">Rev</th><th style="width:150px">Issue date</th>${p.real ? '' : '<th>Used by</th><th style="width:110px">State</th>'}</tr></thead>
      <tbody>${groups.map((g) => `<tr class="band"><td colspan="${p.real ? 4 : 6}"><b>${esc(g.s.name)}</b> <span class="muted">· ${count(g.rows.length, 'document')}</span></td></tr>
        ${g.rows.map((d) => `<tr><td>${esc(d.label)}${d.label !== d.key ? `<span class="cell-sub mono">${esc(d.key)}</span>` : ''}</td><td>${ro(input('dn-' + d.key, d.docNo, { mono: true }))}</td><td>${ro(input('dr-' + d.key, d.rev, { mono: true }))}</td><td>${ro(input('di-' + d.key, d.issue, { mono: true }))}</td>${p.real ? '' : `<td>${esc(d.usedBy)}</td><td>${d.assumed ? badge('warn', 'Assumed date', 'warn') : '<span class="muted small">Confirmed</span>'}</td>`}</tr>`).join('')}`).join('')}</tbody></table>
      <div class="table-foot"><span>${count(p.documents.length, 'document')} in ${count(groups.length, 'substation')}</span>${p.real ? '' : `<span>${illus()}</span>`}</div></div>` : '<div class="empty"><b>No documents in the register.</b></div>'}`;
  };

  /* ---------- Backup and share ---------- */
  function loadBackups(p) {
    p.backups = 'loading';
    Bridge.call('list_backups', p.file).then((list) => { p.backups = list; }).catch((err) => { p.backups = []; fail(err); }).then(() => App.render());
  }
  const backupRows = (p) => (p.real ? (Array.isArray(p.backups) ? p.backups : []) : p.backups.map((b) => ({ path: b.file, saved: b.date, size: null, sizeText: b.size, library_name: b.lib, library_version: '', note: b.note })));
  const projectShare = (p) => {
    if (p.real && p.backups === null) loadBackups(p);
    const rows = backupRows(p);
    return `<div class="stack" style="max-width:860px;gap:var(--space-6)">
    <section><h3>Share this project</h3>
      <p class="muted" style="max-width:68ch;margin:var(--space-2) 0 var(--space-3)">Export writes one <span class="mono">.bomproj</span> file with the project and all its substations. Send it by email or Teams. Build outputs and the Backups folder are not included. The file records the library version the project was built with.</p>
      <div class="row"><button class="btn btn--primary" data-action="export-project">${icon('upload')}Export project…</button><button class="btn btn--secondary" data-action="import-project">${icon('download')}Import project file…</button></div></section>
    <section><div class="row" style="justify-content:space-between;margin-bottom:var(--space-2)"><h3>Backups</h3><button class="btn btn--secondary btn--sm" data-action="backup-now">${icon('backup')}Back up now</button></div>
      <p class="muted" style="max-width:68ch;margin-bottom:var(--space-3)">A backup is a saved copy of the whole project in its <span class="mono">Backups</span> folder, in the same file format. Restore opens it the way an import does. Keep a copy of that folder somewhere safe as well.</p>
      ${p.backups === 'loading' ? '<p class="muted">Reading the Backups folder…</p>' : rows.length ? `<div class="table-wrap"><table class="table"><thead><tr><th>Backup</th><th>Saved</th><th class="num">Size</th><th>Library</th><th style="width:240px"><span class="sr-only">Actions</span></th></tr></thead><tbody>
        ${rows.map((b) => `<tr><td class="mono">${esc(String(b.path).split(/[\\/]/).pop())}${b.note ? `<span class="cell-sub" style="font-family:var(--font-sans)">${esc(b.note)}</span>` : ''}${b.problem ? `<span class="cell-sub" style="font-family:var(--font-sans);color:var(--color-danger-text)">${esc(b.problem)}</span>` : ''}</td><td>${esc(day(b.saved))}</td><td class="num">${esc(b.sizeText || kb(b.size))}</td><td>${esc([b.library_name, b.library_version].filter(Boolean).join(' ') || '—')}</td>
        <td class="nowrap" style="text-align:right"><button class="btn btn--secondary btn--sm" data-action="restore-backup" data-path="${esc(b.path)}" ${b.problem ? 'disabled' : ''}>Restore…</button> <button class="btn btn--ghost btn--sm" data-action="show-in-folder" data-path="${esc(b.path)}">Show in folder</button></td></tr>`).join('')}</tbody></table></div>`
        : `<div class="empty"><b>No backups yet.</b><div class="muted small">Use “Back up now” before a risky change, such as a library update.</div></div>`}</section></div>`;
  };
  ACTIONS['backup-now'] = () => {
    const p = curProject();
    Bridge.call('backup_project', p.file).then((saved) => { toast(`Backup saved: ${String(saved.path).split(/[\\/]/).pop()}`); loadBackups(p); }).catch(fail);
  };
  ACTIONS['show-in-folder'] = (el) => Bridge.call('show_in_folder', el.dataset.path).catch(fail);
  ACTIONS['export-project'] = () => {
    const p = curProject();
    dialog({ title: 'Export project', body: `<div class="stack">
      <p>One file with the whole project. Send it to a colleague; they choose Import project file.</p>
      <ul class="checklist"><li>${icon('check')}<span>project.yaml and the document register</span></li><li>${icon('check')}<span>${count(p.substations.length, 'substation')}: network, equipment, panels, settings</span></li><li>${icon('check')}<span>The library version it was built with, <span class="mono">${esc(p.library.name)} ${esc(p.library.builtWith)}</span>, recorded in the file</span></li><li class="no">${icon('x')}<span>Build outputs and the Backups folder are left out</span></li></ul></div>`,
      actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="export-save">Choose where to save…</button>' });
  };
  ACTIONS['export-save'] = () => {
    const p = curProject(); closeDialog();
    Bridge.call('export_project', p.file).then((out) => { if (out) toast(`Exported ${String(out.path).split(/[\\/]/).pop()} (${kb(out.size)})`); }).catch(fail);
  };

  /* ---------- Import and restore: one review dialog over the dry-run ---------- */
  const PENDING = { path: '', restore: false, preview: null };
  function review(path, restore) {
    PENDING.path = path; PENDING.restore = restore;
    return Bridge.call(restore ? 'preview_backup_restore' : 'preview_project_import', path).then((preview) => { PENDING.preview = preview; reviewDialog(); }).catch(fail);
  }
  function reviewDialog() {
    const { preview: v, restore } = PENDING, m = v.manifest;
    const failed = v.checks.find((c) => c.status === 'failed');
    const facts = `<dl class="kv" style="grid-template-columns:130px 1fr"><dt>File</dt><dd class="mono">${esc(v.file_name)}</dd><dt>Size</dt><dd>${kb(v.package_size)}</dd>${m ? `<dt>Project</dt><dd class="mono">${esc(m.project_id)}</dd><dt>Contains</dt><dd>${count(Object.keys(m.files).length, 'file')}</dd><dt>Built with</dt><dd>${esc([m.library_name, m.library_version].filter(Boolean).join(' ') || '—')}</dd><dt>Saved</dt><dd>${esc(day(m.created))}</dd>` : ''}</dl>`;
    const clash = !failed && v.exists ? banner('warn', restore ? '<b>Restoring replaces the project as it is now.</b> A backup of the current state is made first.' : `<b>This PC already has the project <span class="mono">${esc(v.project_id)}</span>.</b> Importing replaces it; a backup of it is made first.`) : '';
    const primary = failed ? '' : `<button class="btn btn--primary" data-action="import-confirm">${restore ? 'Restore' : v.exists ? 'Replace my project' : 'Import'}</button>`;
    dialog({ title: restore ? 'Restore a backup' : 'Import a project file', body: `<div class="stack">${facts}
      <ul class="checklist">${App.checkList(v.checks)}</ul>
      ${v.library_note ? banner('warn', esc(v.library_note)) : ''}${clash}</div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button>${primary}` });
  }
  ACTIONS['import-project'] = () => {
    Bridge.call('choose_file', 'bomproj').then((path) => path && review(path, false)).catch(fail);
  };
  ACTIONS['import-launched'] = () => review(S.app.project_file, false);
  ACTIONS['restore-backup'] = (el) => review(el.dataset.path, true);
  ACTIONS['import-confirm'] = () => {
    const { path, restore, preview } = PENDING; closeDialog();
    const call = restore ? Bridge.call('restore_backup', path) : Bridge.call('import_project', path, !!preview.exists);
    call.then((result) => {
      if (S.app && path === S.app.project_file) S.launch = 'normal';
      toast(restore ? 'Backup restored. The previous state was backed up first.' : `Imported ${result.manifest.project_id}`);
      if (result.library_note) toast(result.library_note, 'warn');
      return openProject(result.project_file, restore ? 'share' : 'substations');
    }).catch(fail);
  };
})();
