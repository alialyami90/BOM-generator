/* Screens: Home (all projects) and the Project page (overview, substations, documents, backup and share). */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, select, pageHead, illus, dialog, closeDialog, toast, go, $, curProject } = App;
  const statusIcon = { ok: 'check', bad: 'error', warn: 'warn' };
  const ctl = (html) => html.replace('class="input', 'class="ctl input');

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
    return `<div class="page">
      ${pageHead('Projects', 'Every project on this PC. A project holds several substations, each with its own panels and workbook.',
        `<button class="btn btn--secondary" data-action="import-project">${icon('download')}Import project file…</button><button class="btn btn--secondary" data-action="open-project">${icon('folder')}Open folder…</button><button class="btn btn--primary" data-action="new-project">${icon('plus')}New project…</button>`)}
      ${S.launch === 'bomproj' ? `<div style="margin-bottom:var(--space-4)">${banner('info', '<b>You opened a project file.</b> <span class="mono">eastern-province-2026-10-27-1640.bomproj</span> is not added yet. Review what it contains before it is imported.', '<button class="btn btn--primary btn--sm" data-action="import-project" data-file="eastern-province-2026-10-27-1640.bomproj">Review import…</button>')}</div>` : ''}
      <div class="table-wrap"><table class="table table--comfort">
        <thead><tr><th>Project</th><th>Client</th><th class="num">Substations</th><th>Library</th><th>Last opened</th><th>Status</th></tr></thead>
        <tbody>${DB.projects.map((r) => `<tr class="clickable" data-action="open-proj" data-id="${r.id}" tabindex="0">
          <td><b style="font-weight:500">${esc(r.name)}</b><span class="cell-sub mono">${esc(r.path)}</span></td>
          <td>${esc(r.client)}</td><td class="num">${r.substations.length}</td><td>${esc(r.library.name)} ${esc(r.library.builtWith)}</td><td>${esc(r.opened)}</td>
          <td>${badge(r.status, r.statusText, statusIcon[r.status])}</td></tr>`).join('')}</tbody></table>
        <div class="table-foot"><span>Select a project to open it</span><span>${illus()}</span></div></div>
      <div class="section" style="margin-top:var(--space-5);border:0;padding-top:0">
        <div class="banner banner--info">${icon('info')}<div class="grow"><b>Got a device library update?</b><div class="small">Update packages are .bomlib files. Import one to review what it changes before it is installed.</div></div><a class="btn btn--secondary" href="#/library/import">Import update…</a></div>
      </div>
    </div>`;
  };
  ACTIONS['open-proj'] = (el) => { closeDialog(); if (S.proj !== el.dataset.id) { S.proj = el.dataset.id; S.sub = null; } S.tab.project = S.tab.project || 'info'; go('#/project/substations'); S.tab.project = 'substations'; };
  ACTIONS['open-project'] = () => dialog({ title: 'Open a project folder', body: '<p>The app shows the Windows folder picker here. Choose a folder that contains <span class="mono">project.yaml</span>. The project is added to this list.</p>', actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="open-proj" data-id="ep132">Choose folder…</button>' });
  ACTIONS['new-project'] = () => dialog({ title: 'New project', body: `<div class="stack">
    ${field('Project name', input('np-name', '', { placeholder: 'e.g. Western Region 380 kV Programme' }))}
    ${field('Client', input('np-client', ''), 'Printed in the document header.')}
    ${field('Folder', '<div class="row" style="flex-wrap:nowrap">' + input('np-dir', 'D:\\Projects\\', { mono: true }) + '<button class="btn btn--secondary">Browse…</button></div>')}
    ${field('First substation', input('np-sub', '', { placeholder: 'e.g. GIS Substation 01' }), 'You can add more later, or copy one to start the next.')}</div>`, actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="open-proj" data-id="ep132">Create project</button>' });
  document.addEventListener('keydown', (e) => { const r = e.target.closest && e.target.closest('tr.clickable[data-action]'); if (r && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); r.click(); } });

  /* ---------- Project page ---------- */
  SCREENS.project = () => {
    const p = curProject();
    const tabList = [['info', 'Overview'], ['substations', 'Substations', `<span class="count">${p.substations.length}</span>`], ['documents', 'Documents'], ['share', 'Backup and share']];
    const rb = App.route().b; if (tabList.some(([k]) => k === rb)) S.tab.project = rb;
    const t = S.tab.project;
    const actions = { info: '',
      substations: `<button class="btn btn--primary" data-action="new-substation">${icon('plus')}New substation…</button>`,
      documents: `<button class="btn btn--secondary" data-action="add-doc">${icon('plus')}Add document…</button>`,
      share: `<button class="btn btn--primary" data-action="export-project">${icon('upload')}Export project…</button>` }[t];
    const body = { info: projectInfo, substations: projectSubs, documents: projectDocs, share: projectShare }[t](p);
    return `<div class="page">${pageHead(esc(p.name), `${esc(p.client)} · <span class="mono" style="font-size:13px">${esc(p.path)}</span>`, actions, `<a href="#/home">Projects</a>${icon('chevr')}<span>${esc(p.name)}</span>`)}
      ${tabs('project', tabList, t, 'Project sections')}
      <div role="tabpanel" aria-labelledby="tab-project-${t}">${body}</div></div>`;
  };
  ACTIONS['save-project'] = () => { S.dirty = false; App.render(); toast('Saved project.yaml'); };

  const projectInfo = (p) => `<div class="form form--2">
    <div class="span-2">${field('Project name', input('p-name', p.name), 'Printed in bold at the top of every sheet header, for every substation.')}</div>
    ${field('Client', input('p-client', p.client))}
    ${field('Logo', `<div class="row" style="flex-wrap:nowrap">${input('p-logo', p.logo, { mono: true, placeholder: 'No logo chosen' })}<button class="btn btn--secondary">Choose…</button></div>`, p.logo ? 'PNG. Appears in the left of the page header.' : 'PNG. Appears in the left of the page header. <span style="color:var(--color-warning)">Not set: the header will have no picture.</span>')}
    <div class="span-2 section" style="margin:0">
      <h3>Device library</h3>
      <p class="lede">The project records which library version it was built with, so a colleague can reproduce the workbook. All its substations use the same version.</p>
      <dl class="kv"><dt>Library</dt><dd>${esc(p.library.name)}</dd><dt>Built with</dt><dd>${esc(p.library.builtWith)} ${p.library.builtWith !== p.library.active ? badge('warn', 'Older than active', 'warn') : badge('ok', 'Matches active', 'check')}</dd><dt>Active on this PC</dt><dd>${esc(p.library.active)}</dd></dl>
      <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary" data-action="goto" data-to="#/library">Open library</button>${p.library.builtWith !== p.library.active ? `<button class="btn btn--ghost" data-action="stamp">Record ${esc(p.library.active)} in this project</button>` : ''}</div>
    </div>
    <div class="span-2 section" style="margin:0">
      <h3>Catalogue brands</h3>
      <p class="lede">Which make the engine takes ordering codes from for the breakers, contacts and terminal blocks. Every substation of the project uses these; the library default is the starting choice.</p>
      <div class="form form--3" style="margin-top:var(--space-3)">${[['mcb', 'MCBs'], ['aux', 'Aux contacts'], ['tb', 'Terminal blocks']].map(([k, t]) => { const c = DB.catalogues[k]; return field(t, select('br-' + k, c.brands.map((b) => [b.id, b.name + (b.id === c.active ? ' (library default)' : '')]), (p.brands && p.brands[k]) || c.active)); }).join('')}</div>
      <p class="muted small" style="margin-top:var(--space-2)">Changing a brand changes the codes on the next build. Ratings and sizes stay as they are. Edit the codes under Library › Catalogues.</p>
    </div>
    <div class="span-2 section" style="margin:0">
      <h3>Shared defaults</h3>
      <p class="lede">Every substation starts from these values. A substation can set its own; the ones it changes are marked there.</p>
      <div class="form form--3" style="margin-top:var(--space-3)">${p.defaults.map((x, i) => field(x.label, `<div class="input-affix">${input('df' + i, x.value, { num: true, mono: true })}${x.unit ? `<span class="affix">${esc(x.unit)}</span>` : ''}</div>`)).join('') || '<p class="muted">No shared defaults are set.</p>'}</div>
    </div>
    <div class="span-2 section" style="margin:0">
      <h3>Delete this project</h3>
      <p class="lede">Removes the project and all its substations from this PC. A backup is saved first, so it can be restored.</p>
      <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--danger" data-action="delete-project">${icon('trash')}Delete project…</button></div>
    </div></div>`;
  ACTIONS.stamp = () => { const p = curProject(); p.library.builtWith = p.library.active; S.dirty = true; App.render(); toast(`Project now records ${p.library.name} ${p.library.active}`); };

  const projectSubs = (p) => `<p class="muted" style="max-width:68ch;margin-bottom:var(--space-4)">Each substation has its own network, panels, checks and workbook. The menu on a row renames it, starts a new one from it, or deletes it.</p>
    <div class="table-wrap"><table class="table table--comfort"><thead><tr><th>Substation</th><th class="num">Panels</th><th>Last changed</th><th>Status</th><th style="width:130px"><span class="sr-only">Actions</span></th></tr></thead>
      <tbody>${p.substations.map((s) => `<tr class="clickable" tabindex="0" data-action="open-sub" data-id="${s.id}">
        <td><b style="font-weight:500">${esc(s.name)}</b><span class="cell-sub mono">${esc(s.folder)}</span>${s.from ? `<span class="cell-sub">Created from ${esc(s.from)}</span>` : ''}</td>
        <td class="num">${s.panels}</td><td>${esc(s.changed)}</td><td>${badge(s.status, s.statusText, statusIcon[s.status])}</td>
        <td style="text-align:right"><button class="btn btn--secondary btn--sm" data-action="open-sub" data-id="${s.id}">Open</button> <button class="btn btn--ghost btn--icon btn--sm" data-action="sub-menu" data-id="${s.id}" aria-haspopup="menu" aria-label="More actions for ${esc(s.name)}">${icon('dots')}</button></td></tr>`).join('')}</tbody></table>
      <div class="table-foot"><span>${p.substations.length} substations</span><span>${illus()}</span></div></div>`;
  ACTIONS['open-sub'] = (el) => { S.sub = el.dataset.id; S.dirty = false; S.layout = { overrides: [], removed: [], history: [], selected: '', openOverrides: false }; go('#/panels'); };

  ACTIONS['new-substation'] = (el) => {
    const p = curProject(); const from = el.dataset.from || '';
    dialog({ title: 'New substation', body: `<div class="stack">
      ${field('Start from', select('ns-from', [['', 'A blank substation'], ...p.substations.map((s) => [s.id, `A copy of ${s.name}`])], from), 'A copy keeps the equipment, network, spares and settings, so you only change what differs.')}
      <div class="form form--2">
        ${field('Substation name', input('ns-name', '', { placeholder: 'e.g. GIS Substation 04' }))}${field('Folder name', input('ns-id', '', { mono: true, placeholder: 'gis04' }), 'Inside the project\'s substations folder.')}
        ${field('First cabinet number', input('ns-cab', '', { mono: true, placeholder: '861-GIS04-PSA-0001' }), 'The next panels count up from this.')}${field('Tag prefix', input('ns-pre', 'PSA', { mono: true }), 'Panel 1 becomes PSA1, panel 2 PSA2, and so on.')}
      </div>
      <div class="banner banner--info" id="ns-note">${icon('info')}<div class="grow"><b>What a copy takes.</b><div class="small">Copied: equipment, network, spares, design constants, loose material. Not copied: manual changes to the panel layout, the build outputs. New rows are added to the document register with blank numbers.</div></div></div></div>`,
      actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="create-sub">Create substation</button>' });
  };
  ACTIONS['create-sub'] = () => { closeDialog(); const p = curProject(); const name = ($('#ns-name') && $('#ns-name').value) || 'GIS Substation 04'; p.substations.push({ id: 'gis04', name, folder: 'substations\\gis04', panels: 4, changed: 'Just now', status: 'ok', statusText: 'Ready', from: 'GIS Substation 01' }); App.render(); toast(`Created ${name}`); };

  const projectDocs = (p) => {
    const groups = p.substations.map((s) => ({ s, rows: p.documents.filter((d) => d.sub === s.id) })).filter((g) => g.rows.length);
    return `<p class="lede muted" style="max-width:68ch;margin-bottom:var(--space-4)">One register for the whole project. Each panel and calculation sheet picks a document from it, so a single transmittal list drives every header.</p>
      ${p.documents.some((d) => d.assumed) ? banner('warn', `<b>The issue date of ${p.documents.filter((d) => d.assumed).length} documents is assumed.</b> Confirm each date once you know it, before issuing.`) : ''}
      <div class="table-wrap" style="margin-top:var(--space-4)"><table class="table"><thead><tr><th>Document</th><th>Document no.</th><th style="width:70px">Rev</th><th style="width:150px">Issue date</th><th>Used by</th><th style="width:200px">State</th><th style="width:40px"><span class="sr-only">Actions</span></th></tr></thead>
      <tbody>${groups.map((g) => `<tr class="band"><td colspan="5"><b>${esc(g.s.name)}</b> <span class="muted">· ${g.rows.length} documents</span></td><td colspan="2" style="text-align:right"><button class="btn btn--ghost btn--sm" data-action="add-doc" data-sub="${g.s.id}">${icon('plus')}Add</button></td></tr>
        ${g.rows.map((d, i) => `<tr><td>${esc(d.label)}<span class="cell-sub mono">${esc(d.key)}</span></td><td>${ctl(input('dn-' + d.key, d.docNo, { mono: true }))}</td><td>${ctl(input('dr-' + d.key, d.rev, { mono: true }))}</td><td>${ctl(input('di-' + d.key, d.issue, { mono: true }))}</td><td>${esc(d.usedBy)}</td><td>${d.assumed ? `${badge('warn', 'Assumed date', 'warn')} <button class="btn btn--ghost btn--sm" data-action="confirm-date" data-key="${d.key}">Confirm</button>` : '<span class="muted small">Confirmed</span>'}</td>
        <td><button class="btn btn--ghost btn--icon btn--sm" data-action="remove-doc" data-key="${d.key}" ${d.usedBy ? 'aria-disabled="true" title="Used by ' + esc(d.usedBy) + '. Pick another document there first."' : ''} aria-label="Remove ${esc(d.label)}">${icon('trash')}</button></td></tr>`).join('')}`).join('')}</tbody></table>
      <div class="table-foot"><span>${p.documents.length} documents in ${groups.length} substations</span><span>${illus()}</span></div></div>`;
  };

  const projectShare = (p) => `<div class="stack" style="max-width:860px;gap:var(--space-6)">
    <section><h3>Share this project</h3>
      <p class="muted" style="max-width:68ch;margin:var(--space-2) 0 var(--space-3)">Export writes one <span class="mono">.bomproj</span> file with the project and all its substations. Send it by email or Teams. Build outputs and the Backups folder are not included. The file records the library version the project was built with.</p>
      <div class="row"><button class="btn btn--primary" data-action="export-project">${icon('upload')}Export project…</button><button class="btn btn--secondary" data-action="import-project">${icon('download')}Import project file…</button></div></section>
    <section><div class="row" style="justify-content:space-between;margin-bottom:var(--space-2)"><h3>Backups</h3><button class="btn btn--secondary btn--sm" data-action="backup-now">${icon('backup')}Back up now</button></div>
      <p class="muted" style="max-width:68ch;margin-bottom:var(--space-3)">A backup is a saved copy of the whole project in its <span class="mono">Backups</span> folder, in the same file format. Restore opens it the way an import does. Keep a copy of that folder somewhere safe as well.</p>
      ${p.backups.length ? `<div class="table-wrap"><table class="table"><thead><tr><th>Backup</th><th>Saved</th><th class="num">Size</th><th>Library</th><th style="width:200px"><span class="sr-only">Actions</span></th></tr></thead><tbody>
        ${p.backups.map((b, i) => `<tr><td class="mono">${esc(b.file)}${b.note ? `<span class="cell-sub" style="font-family:var(--font-sans)">${esc(b.note)}</span>` : ''}</td><td>${esc(b.date)}</td><td class="num">${esc(b.size)}</td><td>${esc(b.lib)}</td>
        <td style="text-align:right"><button class="btn btn--secondary btn--sm" data-action="import-project" data-file="${esc(b.file)}" data-restore="1">Restore…</button> <button class="btn btn--ghost btn--sm" data-action="toast" data-m="The app opens the Backups folder in Windows Explorer">Show in folder</button></td></tr>`).join('')}</tbody></table></div>` : `<div class="empty"><b>No backups yet.</b><div class="muted small">Use “Back up now” before a risky change, such as a library update.</div></div>`}</section></div>`;
  ACTIONS['backup-now'] = () => { const p = curProject(); p.backups.unshift({ file: 'eastern-province-2026-10-28-1105.bomproj', date: '2026-10-28 11:05', size: '415 KB', lib: `${p.library.name} ${p.library.builtWith}`, note: '' }); App.render(); toast('Backup saved in the Backups folder'); };

  ACTIONS['export-project'] = () => {
    const p = curProject();
    dialog({ title: 'Export project', body: `<div class="stack">
      <p>One file with the whole project. Send it to a colleague; they choose Import project file.</p>
      <ul class="checklist"><li>${icon('check')}<span>project.yaml and the document register</span></li><li>${icon('check')}<span>${p.substations.length} substations: network, equipment, panels, settings</span></li><li>${icon('check')}<span>The library version it was built with, <span class="mono">${esc(p.library.name)} ${esc(p.library.builtWith)}</span>, recorded in the file</span></li><li class="no">${icon('x')}<span>Build outputs and the Backups folder are left out</span></li></ul>
      ${field('Save as', '<div class="row" style="flex-wrap:nowrap">' + input('ex-file', 'eastern-province-2026-10-28.bomproj', { mono: true }) + '<button class="btn btn--secondary">Browse…</button></div>')}</div>`,
      actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="export-done">Export</button>' });
  };
  ACTIONS['export-done'] = () => { closeDialog(); toast('Exported eastern-province-2026-10-28.bomproj (412 KB)'); };

  ACTIONS['import-project'] = (el) => {
    const file = (el && el.dataset && el.dataset.file) || 'eastern-province-2026-10-27-1640.bomproj'; const restore = el && el.dataset && el.dataset.restore;
    dialog({ title: restore ? 'Restore a backup' : 'Import a project file', body: `<div class="stack">
      <dl class="kv" style="grid-template-columns:130px 1fr"><dt>File</dt><dd class="mono">${esc(file)}</dd><dt>Project</dt><dd>Eastern Province 132 kV Programme</dd><dt>Contains</dt><dd>3 substations, 11 documents</dd><dt>Built with</dt><dd>psa-devices 1.3.2</dd></dl>
      <ul class="checklist"><li class="ok">${icon('check')}<span style="color:var(--color-text)">File is intact: every checksum matches</span></li><li class="ok">${icon('check')}<span style="color:var(--color-text)">All paths stay inside the project folder</span></li><li class="warn">${icon('warn')}<span style="color:var(--color-text)">It was built with psa-devices 1.3.2; this PC has 1.4.0. Install the matching <span class="mono">.bomlib</span> to rebuild identically, or carry on with 1.4.0.</span></li></ul>
      ${banner('warn', '<b>This PC already has this project</b> (changed today 10:02). Choose what to do with it.')}
      <div class="stack" style="gap:8px"><label class="check"><input type="radio" name="imp-mode" checked> Keep both: import as <span class="mono">eastern-province-2</span></label>
      <label class="check"><input type="radio" name="imp-mode"> Replace my project. A backup of it is made first.</label></div></div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="import-done">${restore ? 'Restore' : 'Import'}</button>` });
  };
  ACTIONS['import-done'] = () => { closeDialog(); S.launch = 'normal'; toast('Imported eastern-province-2 (3 substations)'); App.render(); };
})();
