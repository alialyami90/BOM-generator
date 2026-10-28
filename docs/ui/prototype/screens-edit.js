/* v0.2 editors: create, rename and delete projects and substations; the document register; the row menu.
   Writes are shown as the app will do them: nothing is saved until the save bar says so, except create and delete,
   which act at once and say what they did. */
(function () {
  const { esc, S, ACTIONS, badge, banner, field, input, select, dialog, closeDialog, toast, go, $, curProject } = App;

  /* ---------- Row menu ---------- */
  function openMenu(btn, items) {
    closeMenu();
    const m = document.createElement('div'); m.className = 'menu'; m.id = 'menu'; m.setAttribute('role', 'menu');
    m.innerHTML = items.map((it) => it === '-' ? '<hr>' : `<button role="menuitem" class="${it.danger ? 'danger' : ''}" data-action="${it.action}" ${Object.entries(it.data || {}).map(([k, v]) => `data-${k}="${esc(v)}"`).join(' ')}>${icon(it.icon)}${esc(it.label)}</button>`).join('');
    const r = btn.getBoundingClientRect(); const host = $('#main');
    host.appendChild(m); m.style.position = 'fixed'; m.style.top = (r.bottom + 4) + 'px'; m.style.left = Math.max(8, r.right - m.offsetWidth) + 'px';
    btn.setAttribute('aria-expanded', 'true'); m.querySelector('[role=menuitem]').focus(); m._owner = btn;
  }
  function closeMenu(restore) { const m = $('#menu'); if (!m) return; const o = m._owner; m.remove(); if (o) { o.setAttribute('aria-expanded', 'false'); if (restore) o.focus(); } }
  document.addEventListener('click', (e) => { if (!e.target.closest('#menu') && !e.target.closest('[aria-haspopup="menu"]')) closeMenu(); else if (e.target.closest('#menu [role=menuitem]')) closeMenu(); });
  document.addEventListener('keydown', (e) => {
    const m = $('#menu'); if (!m) return;
    const list = [...m.querySelectorAll('[role=menuitem]')]; const i = list.indexOf(document.activeElement);
    if (e.key === 'Escape') { e.stopPropagation(); closeMenu(true); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); list[(i + 1) % list.length].focus(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); list[(i + list.length - 1) % list.length].focus(); }
  }, true);
  App.openMenu = openMenu; App.closeMenu = closeMenu;

  const sub = (id) => curProject().substations.find((s) => s.id === id);
  const slug = (t) => t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40);

  /* ---------- Substation: rename, create from, delete ---------- */
  ACTIONS['sub-menu'] = (el) => openMenu(el, [
    { icon: 'edit', label: 'Rename…', action: 'rename-sub', data: { id: el.dataset.id } },
    { icon: 'copy', label: 'Create from this…', action: 'new-substation', data: { from: el.dataset.id } },
    '-',
    { icon: 'trash', label: 'Delete…', action: 'delete-sub', data: { id: el.dataset.id }, danger: true }]);

  ACTIONS['rename-sub'] = (el) => {
    const s = sub(el.dataset.id);
    dialog({ title: 'Rename substation', body: `<div class="stack">${field('Substation name', input('rs-name', s.name), 'Shown in the app and in each sheet header. The folder name stays <span class="mono">' + esc(s.folder.split('\\').pop()) + '</span>, so the project file paths do not change.')}</div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="rename-sub-do" data-id="${s.id}">Rename</button>` });
  };
  ACTIONS['rename-sub-do'] = (el) => { const s = sub(el.dataset.id); const v = $('#rs-name').value.trim(); if (!v) return; s.name = v; closeDialog(); App.render(); toast(`Renamed to ${v}`); };

  ACTIONS['delete-sub'] = (el) => {
    const s = sub(el.dataset.id);
    dialog({ title: `Delete ${esc(s.name)}?`, body: `<div class="stack">
      <p>This removes the substation's network, ${s.panels} panels, settings and its documents in the register from the project. Build outputs in its folder are kept.</p>
      ${banner('info', 'A backup of the whole project is saved first, in the Backups folder, so you can restore it.')}
      <label class="check"><input type="checkbox" id="ds-ok"> I understand this substation will be removed</label></div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--danger" data-action="delete-sub-do" data-id="${s.id}">${icon('trash')}Delete substation</button>` });
    $('#ds-ok').addEventListener('change', () => {});
  };
  ACTIONS['delete-sub-do'] = (el) => {
    if (!$('#ds-ok').checked) { $('#ds-ok').focus(); toast('Tick the box to confirm', 'info'); return; }
    const p = curProject(); const s = sub(el.dataset.id); closeDialog();
    p.substations = p.substations.filter((x) => x.id !== s.id); p.documents = p.documents.filter((d) => d.sub !== s.id);
    p.backups.unshift({ file: 'eastern-province-before-delete.bomproj', date: 'Just now', size: '415 KB', lib: `${p.library.name} ${p.library.builtWith}`, note: `Before deleting ${s.name}` });
    if (S.sub === s.id) S.sub = null; App.render(); toast(`Deleted ${s.name}. Backup saved.`, 'trash');
  };

  /* ---------- New project: library, name, client, where it lives ---------- */
  ACTIONS['new-project'] = () => dialog({ title: 'New project', body: `<div class="stack">
    ${field('Project name', input('np-name', '', { placeholder: 'e.g. Western Region 380 kV Programme' }), 'Printed in bold at the top of every sheet header.')}
    ${field('Client', input('np-client', ''), 'Printed in the document header. You can leave it empty and add it later.')}
    ${field('Device library', select('np-lib', [['1.4.0', `${DB.library.name} ${DB.library.version} (active on this PC)`], ['1.3.2', 'psa-devices 1.3.2']], DB.library.version), 'The project records the version so a colleague can rebuild the same workbook.')}
    <div class="field"><span class="label">Where it is kept</span><div class="kv" style="grid-template-columns:90px 1fr"><dt>Folder</dt><dd class="mono" id="np-path">D:\\Projects\\western-region</dd></div>
      <span class="help">The app keeps projects in <span class="mono">D:\\Projects</span>. <button class="link-btn" data-action="np-where">Change where projects are kept</button></span></div>
    <label class="check"><input type="checkbox" id="np-first" checked> Add a first substation now</label>
    <div id="np-first-box">${field('Substation name', input('np-sub', '', { placeholder: 'e.g. GIS Substation 01' }))}</div></div>`,
    actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="create-project">Create project</button>' });
  document.addEventListener('input', (e) => { if (e.target.id === 'np-name') { const el = $('#np-path'); if (el) el.textContent = 'D:\\Projects\\' + (slug(e.target.value) || 'new-project'); } });
  document.addEventListener('change', (e) => { if (e.target.id === 'np-first') { const b = $('#np-first-box'); if (b) b.hidden = !e.target.checked; } });
  ACTIONS['np-where'] = () => toast('The app shows the Windows folder picker here', 'info');
  ACTIONS['create-project'] = () => {
    const name = $('#np-name').value.trim(); if (!name) { $('#np-name').setAttribute('aria-invalid', 'true'); $('#np-name').focus(); return; }
    const first = $('#np-first').checked; const sname = ($('#np-sub').value || '').trim() || 'Substation 01';
    const id = 'new-' + (DB.projects.length + 1);
    DB.projects.unshift({ id, name, client: $('#np-client').value.trim() || '—', path: 'D:\\Projects\\' + slug(name), logo: '', library: { name: DB.library.name, builtWith: $('#np-lib').value, active: DB.library.version }, opened: 'Just now', status: 'ok', statusText: 'Ready',
      substations: first ? [{ id: 'blank-1', blank: true, name: sname, folder: 'substations\\' + slug(sname), panels: 0, changed: 'Just now', status: 'warn', statusText: 'Network not set up', from: '' }] : [], documents: [], defaults: JSON.parse(JSON.stringify(DB.projects[1].defaults.length ? DB.projects[1].defaults : DB.projects[0].defaults)), backups: [] });
    closeDialog(); S.proj = id; S.sub = first ? 'blank-1' : null; App.clearEdits(); S.tab.project = first ? 'substations' : 'info';
    toast(`Created ${name}`); go(first ? '#/network' : '#/project/info');
  };

  /* ---------- Hand-written panel: delete ---------- */
  ACTIONS['delete-panel'] = (el) => dialog({ title: 'Delete this panel?', body: `<div class="stack"><p>The hand-written panel, its devices and its sheet are removed from this substation. The layout is not affected.</p>${banner('info', 'Nothing else changes. Undo is available straight after.')}</div>`,
    actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--danger" data-action="delete-panel-do">' + icon('trash') + 'Delete panel</button>' });
  ACTIONS['delete-panel-do'] = () => { closeDialog(); toast('Deleted the panel', 'trash', () => toast('Restored', 'undo')); go('#/panels'); };

  /* ---------- Project: delete ---------- */
  ACTIONS['delete-project'] = () => {
    const p = curProject();
    dialog({ title: `Delete ${esc(p.name)}?`, body: `<div class="stack">
      <p>The project and its ${p.substations.length} substations are removed from this PC. A backup <span class="mono">.bomproj</span> is saved in the app's Deleted folder first, and Home keeps a "Restore deleted project" link for 30 days.</p>
      ${field('Type the project name to confirm', input('dp-name', '', { placeholder: p.name }))}</div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--danger" data-action="delete-project-do">${icon('trash')}Delete project</button>` });
  };
  ACTIONS['delete-project-do'] = () => {
    const p = curProject(); if ($('#dp-name').value.trim() !== p.name) { $('#dp-name').setAttribute('aria-invalid', 'true'); $('#dp-name').focus(); return; }
    closeDialog(); DB.projects = DB.projects.filter((x) => x.id !== p.id); S.proj = null; S.sub = null; App.clearEdits(); toast(`Deleted ${p.name}. Backup saved.`, 'trash'); go('#/home');
  };

  /* ---------- Document register: add, remove, confirm a date ---------- */
  const PURPOSES = [['bom', 'Cabinet BOM'], ['power', 'Power Consumption'], ['heat', 'Heat Dissipation'], ['heatcalc', 'Heat Calculations'], ['other', 'Other']];
  ACTIONS['add-doc'] = (el) => {
    const p = curProject(); const sid = el.dataset.sub || (p.substations[0] && p.substations[0].id);
    if (!p.substations.length) { toast('Add a substation first', 'info'); return; }
    dialog({ title: 'Add a document', body: `<div class="stack">
      ${field('Substation', select('ad-sub', p.substations.map((s) => [s.id, s.name]), sid))}
      ${field('Name', input('ad-label', '', { placeholder: 'e.g. PSA Cabinet - 006 BOM' }), 'Shown in the register and in the pickers.')}
      <div class="form form--3">${field('Document no.', input('ad-no', '', { mono: true }))}${field('Rev', input('ad-rev', '00', { mono: true }))}${field('Issue date', input('ad-date', '2026-10-28', { mono: true }))}</div></div>`,
      actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="add-doc-do">Add document</button>' });
  };
  ACTIONS['add-doc-do'] = () => {
    const label = $('#ad-label').value.trim(); if (!label) { $('#ad-label').setAttribute('aria-invalid', 'true'); $('#ad-label').focus(); return; }
    const p = curProject(); p.documents.push({ key: slug(label) + '-' + p.documents.length, sub: $('#ad-sub').value, label, docNo: $('#ad-no').value.trim(), rev: $('#ad-rev').value.trim(), issue: $('#ad-date').value.trim(), assumed: false, usedBy: '' });
    closeDialog(); S.tab.project = 'documents'; App.render(); toast(`Added ${label}`);
  };
  ACTIONS['remove-doc'] = (el) => {
    if (el.getAttribute('aria-disabled') === 'true') { toast(el.title, 'info'); return; }
    const p = curProject(); const d = p.documents.find((x) => x.key === el.dataset.key); p.documents = p.documents.filter((x) => x !== d); App.render();
    toast(`Removed ${d.label}`, 'trash', () => { p.documents.push(d); App.render(); });
  };
  ACTIONS['confirm-date'] = (el) => { const d = curProject().documents.find((x) => x.key === el.dataset.key); d.assumed = false; S.dirty = true; S.changed.add('confirm-' + d.key); App.render(); };
})();
