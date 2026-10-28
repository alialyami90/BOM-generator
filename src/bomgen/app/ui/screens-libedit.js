/* Screens: library editing (plan M16, docs/ui/editing.md "Library editing (v0.2)", ADR 0018).
   Saved device edits collect in a pending set kept by the app; Review and apply writes them as a new local
   library version. The Device editor is a form over one device; the model checks every value it sends. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, select, pageHead, dialog, closeDialog, toast, go, $ } = App;
  const real = () => S.backend === 'yes';
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;
  const onLibrary = () => App.route().a === 'library';

  /* ---------- the pending set ---------- */
  const PEND = { state: 'idle', page: null };
  function loadPending() {
    PEND.state = 'loading';
    return Bridge.call('library_pending').then((p) => { PEND.page = p; }).catch(() => { PEND.page = null; })
      .then(() => { PEND.state = 'loaded'; App.render(); });
  }
  const pending = () => { if (real() && PEND.state === 'idle') loadPending(); return PEND.page; };
  function pendingBar() {
    const p = pending();
    if (!p || (!p.count && !p.problem)) return '';
    const msg = p.problem ? `${icon('error')}<b>The pending changes cannot be read.</b> ${esc(p.problem)}.`
      : `<span class="dot dot--warn" aria-hidden="true"></span><b>${plural(p.count, 'pending change')}</b> · not applied yet. Projects keep using ${esc(p.base)} until you apply them.`;
    return `<div class="savebar savebar--pending${p.problem ? ' savebar--bad' : ''}" role="region" aria-label="Pending library changes"><span class="savebar-msg">${msg}</span><span class="sp"></span>
      <button class="btn btn--secondary" data-action="pending-discard">Discard all</button>${p.problem ? '' : '<a class="btn btn--primary" href="#/library/review">Review and apply…</a>'}</div>`;
  }
  ACTIONS['pending-discard'] = () => dialog({ title: 'Discard all pending changes?', body: `<p>${plural(PEND.page.count, 'pending change')} will be removed. The library stays at ${esc(PEND.page.base || PEND.page.active || '')}.</p>`,
    actions: '<button class="btn btn--secondary" data-action="close">Keep them</button><button class="btn btn--danger" data-action="pending-discard-do">Discard all</button>' });
  ACTIONS['pending-discard-do'] = () => {
    closeDialog();
    Bridge.call('discard_library_edits').then((r) => {
      PEND.page = r.page; ED.key = ''; App.render();
      toast('Pending changes discarded', 'trash', r.discarded.length ? () => Bridge.call('add_library_edits', r.discarded).then((p) => { PEND.page = p; ED.key = ''; App.render(); }).catch((e) => toast(e.message, 'error')) : null);
    }).catch((e) => toast(e.message, 'error'));
  };

  /* ---------- routes: the editor and the review live under #/library ---------- */
  const base = SCREENS.library;
  SCREENS.library = () => {
    const { b, c } = App.route();
    const page = b === 'device' && real() ? editor(decodeURIComponent(c || '')) : b === 'review' && real() ? review() : base();
    return b === 'device' || b === 'review' ? page : page.replace(/<\/div>\s*$/, `${pendingBar()}</div>`);
  };

  /* ---------- Review and apply ---------- */
  function review() {
    const p = pending();
    const crumbs = `<a href="#/library">Library</a>${icon('chevr')}<span>Review changes</span>`;
    if (!p) return `<div class="page">${pageHead('Review library changes', 'Reading the pending changes…', '', crumbs)}</div>`;
    const head = pageHead('Review library changes', `These edits become a new local version of ${esc(p.name)}. Nothing changes in any project until you apply them and a project records the new version.`, '', crumbs);
    if (!p.count) return `<div class="page">${head}<div class="empty" style="max-width:640px"><b>Nothing to review</b><div class="muted small" style="margin:4px 0 12px">Device edits you save appear here before they are applied.</div><a class="btn btn--secondary" href="#/library">Back to the library</a></div></div>`;
    const of = (k) => p.entries.filter((e) => e.kind === k);
    const line = (e) => `<div><span class="mono">${esc(e.label)}</span><span class="muted">${e.kind === 'changed' ? `${e.field ? `${esc(labelOf(e.field))}: ` : ''}${esc(e.from || 'empty')} → ${esc(e.to || 'empty')}` : esc(e.to || e.from)}</span></div>`;
    const group = (title, items, tone) => (items.length ? `<details open><summary>${icon('chevr', 'chev')}${esc(title)} ${badge(tone, items.length)}</summary><div class="items">${items.map(line).join('')}</div></details>` : '');
    const moved = p.active && p.active !== p.base ? `<div style="margin-bottom:var(--space-4)">${banner('warn', `<b>Started from ${esc(p.base)}; ${esc(p.active)} is now active.</b> Applying builds on ${esc(p.base)}, the version these edits started from.`)}</div>` : '';
    return `<div class="page">${head}${moved}<div class="stack" style="max-width:920px">
      <section><h3>What changes</h3><div class="row" style="margin:var(--space-2) 0 var(--space-3)">${badge('ok', `${of('added').length} added`)}${badge('info', `${of('changed').length} changed`)}${badge('bad', `${of('removed').length} removed`)}</div>
        <div class="diff-list table-wrap" style="padding:0 var(--space-4)">${group('Added', of('added'), 'ok')}${group('Changed', of('changed'), 'info')}${group('Removed', of('removed'), 'bad')}</div></section>
      <section><h3>New version</h3><dl class="kv" style="margin-top:var(--space-2);grid-template-columns:150px 1fr"><dt>Now active</dt><dd class="mono">${esc(p.name)} ${esc(p.active || '—')}</dd><dt>Will become</dt><dd class="mono">${esc(p.name)} ${esc(p.next_version)}</dd><dt>Kept</dt><dd>${esc(p.base)} stays installed under Installed versions, so you can go back.</dd></dl>
        <div class="form" style="margin-top:var(--space-3);max-width:520px">${field('Note', input('rv-note', 'Local edits'), 'Shown next to the version.')}</div></section>
      <div class="actionbar"><button class="btn btn--primary" data-action="apply-pending">${icon('check')}Apply and activate ${esc(p.next_version)}</button><a class="btn btn--secondary" href="#/library">Back to the library</a></div></div></div>`;
  }
  ACTIONS['apply-pending'] = (el) => {
    el.disabled = true;
    Bridge.call('apply_library_edits', ($('#rv-note') && $('#rv-note').value.trim()) || 'Local edits').then((r) => {
      PEND.state = 'idle'; ED.key = ''; App.reloadLibrary(); go('#/library'); toast(`${PEND.page.name} ${r.version} is active`, 'check');
    }).catch((e) => { el.disabled = false; toast(e.message, 'error'); });
  };

  /* ---------- Device editor ---------- */
  const ED = { key: '', state: 'idle', reply: null, error: null, draft: {}, errors: {}, refusal: '', saving: false };
  const CAT = { io: 'IO', gps: 'GPS', rtac: 'RTAC', sfp: 'SFP' };
  const catName = (c) => c.split('_').map((w) => CAT[w] || w).join(' ').replace(/^./, (m) => m.toUpperCase());
  /* [key, label, kind, help]; kinds: text, mono, area, int, num, choice, feeds, bool. The model checks every value. */
  const TABS = {
    identity: ['Identity', [['part_id', 'Part ID', 'fixed', 'Fixed: projects refer to it. To rename, add a copy and retire this one.'], ['category', 'Category', 'choice'], ['make', 'Make', 'text'], ['model', 'Model', 'text'],
      ['ordering_code', 'Ordering code', 'mono', 'Printed in the BOM. Leave empty if the manufacturer gives none.', 2],
      ['description_template', 'Description in the BOM', 'area', 'Placeholders in braces, such as <span class="mono">{side}</span> and <span class="mono">{level}</span>, are filled in by the engine.', 2],
      ['tag_type', 'Tag type', 'mono', 'First part of the generated tag, e.g. ESW.'], ['purdue_level', 'Purdue level', 'choice']]],
    electrical: ['Electrical', [['supply_type', 'Supply type', 'choice'], ['voltage_v', 'Voltage', 'int', '', 0, 'V'], ['power_supplies', 'Power supplies', 'feeds'],
      ['unit_power_w', 'Rated power', 'num', 'What the power sheet uses.', 0, 'W'], ['inrush_a', 'Inrush current', 'num', 'The branch MCB is sized to clear it.', 0, 'A'], ['load_type', 'Load type', 'choice'],
      ['min_branch_mcb_a', 'Minimum branch MCB', 'int', '', 0, 'A'], ['hwio_points', 'HWIO points', 'int', 'Hardwired points one unit gives.'], ['di_inputs', 'Digital inputs', 'int'],
      ['alarm_on_branch_mcb', 'Alarm on the branch MCB', 'bool'], ['excluded_from_power', 'Leave out of the power total', 'bool']]],
    ports: ['Ports and mounting', [['height_u', 'Height', 'int', '0 for a DIN-rail part; empty if not known yet.', 0, 'U'], ['cores', 'Fibre cores', 'int', 'For patch panels.']]]
  };
  const FIELDS = Object.values(TABS).flatMap(([, f]) => f);
  const kindOf = (key) => (FIELDS.find((f) => f[0] === key) || [])[2];
  const labelOf = (key) => (FIELDS.find((f) => f[0] === key) || [key, key])[1];

  function loadDevice(id) {
    Object.assign(ED, { key: id, state: 'loading', reply: null, error: null, draft: {}, errors: {}, refusal: '' });
    Bridge.call('library_device', id).then((r) => { if (ED.key === id) ED.reply = r; }).catch((e) => { if (ED.key === id) ED.error = e; })
      .then(() => { if (ED.key === id) { ED.state = 'loaded'; App.render(); } });
  }
  const value = (key) => (key in ED.draft ? ED.draft[key] : ED.reply.device[key]);
  const changes = () => Object.keys(ED.draft).length;
  const invalid = () => Object.keys(ED.errors).length;
  const dirty = () => !!ED.reply && changes() > 0;
  /* What a typed value means; a number field takes digits and one decimal point, anything else waits to be fixed. */
  function parse(kind, raw) {
    const t = String(raw).trim();
    if (kind === 'bool') return [raw === true, null];
    if (kind === 'feeds') return [Number(t), null];
    if (!t) return [null, null];
    if (kind === 'int') return /^\d+$/.test(t) ? [Number(t), null] : [t, 'Enter a whole number, for example 2.'];
    if (kind === 'num') return /^\d+(\.\d+)?$/.test(t) ? [Number(t), null] : [t, 'Enter a number, for example 25 or 12.5.'];
    return [t, null];
  }
  function control(f) {
    const [key, label, kind, help = '', , unit] = f, v = value(key), id = 'de-' + key, err = ED.errors[key];
    const changed = key in ED.draft, o = { invalid: !!err };
    const choices = (ED.reply.choices || {})[key] || [];
    let html;
    if (kind === 'fixed') html = input(id, v, { mono: true, readonly: true });
    else if (kind === 'bool') return `<div class="field${changed ? ' changed' : ''}"><label class="switch"><input type="checkbox" id="${id}" ${v ? 'checked' : ''}>${esc(label)}</label>${err ? `<span class="err" id="${id}-err">${icon('error')}<span>${esc(err)}</span></span>` : ''}</div>`;
    else if (kind === 'choice') html = select(id, [['', 'Not set'], ...choices.map((c) => [c, key === 'category' ? catName(c) : c])], v == null ? '' : String(v), o);
    else if (kind === 'feeds') html = select(id, [['0', 'None'], ['1', 'Single feed'], ['2', 'Dual feed (2 supplies)']], String(v || 0), o);
    else if (kind === 'area') html = `<textarea class="input input--mono" id="${id}" rows="3" ${err ? 'aria-invalid="true"' : ''} style="height:auto;padding:8px 10px">${esc(v == null ? '' : v)}</textarea>`;
    else html = input(id, v == null ? '' : String(v), { ...o, mono: kind !== 'text', num: kind === 'int' || kind === 'num' });
    if (unit) html = `<div class="input-affix">${html}<span class="affix">${unit}</span></div>`;
    const out = field(esc(label), html, help, err ? esc(err) : '');
    return changed ? out.replace('<div class="field">', '<div class="field changed">') : out;
  }
  function editor(id) {
    if (ED.key !== id) loadDevice(id);
    const crumbs = `<a href="#/library">Library</a>${icon('chevr')}<span class="mono">${esc(id)}</span>`;
    if (ED.state !== 'loaded') return `<div class="page">${pageHead(esc(id), 'Reading the device…', '', crumbs)}</div>`;
    if (!ED.reply) return `<div class="page">${pageHead('Device not found', esc(ED.error ? ED.error.message : ''), '<a class="btn btn--secondary" href="#/library">Back to the library</a>', crumbs)}</div>`;
    const d = ED.reply.device, t = TABS[S.tab.devEdit] ? S.tab.devEdit : 'identity';
    const fields = TABS[t][1], spans = (f) => (f[4] === 2 ? `<div class="span-2">${control(f)}</div>` : control(f));
    const ports = t === 'ports' ? `<h3 style="margin-top:var(--space-5)">Port groups</h3>${d.ports.length ? `<div class="table-wrap" style="max-width:760px;margin-top:var(--space-2)"><table class="table"><thead><tr><th class="num">Count</th><th>Speed</th><th>Media</th><th>Kind</th><th>Used for</th></tr></thead><tbody>
      ${d.ports.map((g) => `<tr><td class="num">${esc(g.count)}</td><td>${esc(g.speed || '—')}</td><td>${esc(g.media || '—')}</td><td>${esc(g.kind || '—')}</td><td>${esc(g.usable_for || '—')}</td></tr>`).join('')}</tbody></table></div>` : '<p class="muted small" style="margin-top:var(--space-2)">No port groups.</p>'}
      <p class="muted small" style="margin-top:var(--space-2)">Editing port groups comes with the next library update of the app.</p>` : '';
    const pend = ED.reply.pending_fields.length && ED.reply.saved ? `<div style="margin-bottom:var(--space-4)">${banner('info', `<b>This device has pending changes</b> (${ED.reply.pending_fields.map(esc).join(', ')}). The fields show them; the library keeps the saved values until you apply.`)}</div>` : '';
    const notice = ED.refusal ? `<div style="margin-bottom:var(--space-4)">${banner('bad', `<b>Not saved.</b> ${esc(ED.refusal)}`)}</div>` : '';
    return `<div class="page">${pageHead(esc(d.part_id), esc([d.make, d.model].filter(Boolean).join(' ')), '', crumbs)}${notice}${pend}
      ${tabs('devEdit', Object.entries(TABS).map(([k, [label]]) => [k, label]), t, 'Device sections')}
      <div role="tabpanel" aria-labelledby="tab-devEdit-${t}" style="margin-top:var(--space-4)"><div class="form ${t === 'identity' ? 'form--2' : 'form--3'}">${fields.map(spans).join('')}</div>${ports}</div>${saveBar()}</div>`;
  }
  function saveBar() {
    if (!dirty() && !ED.saving) return '';
    const bad = invalid();
    return `<div class="savebar${bad ? ' savebar--bad' : ''}" role="region" aria-label="Unsaved changes">
      <span class="savebar-msg">${ED.saving ? '<span class="spinner"></span><b>Saving…</b>' : bad ? `<button class="btn btn--ghost btn--sm" data-action="de-first-bad">${icon('error')}<b>${bad} ${bad === 1 ? 'field needs' : 'fields need'} fixing</b></button> before you can save.` : `<span class="dot dot--warn" aria-hidden="true"></span><b>${plural(changes(), 'unsaved change')}</b> · added to pending changes`}</span>
      <span class="sp"></span><button class="btn btn--secondary" data-action="de-discard" ${ED.saving ? 'disabled' : ''}>Discard</button>
      <button class="btn btn--primary" data-action="de-save" ${ED.saving || bad ? 'disabled' : ''}>${icon('save')}Save device <kbd class="kbd">Ctrl+S</kbd></button></div>`;
  }
  ACTIONS['de-first-bad'] = () => { const k = Object.keys(ED.errors)[0]; const el = k && document.getElementById('de-' + k); if (el) el.focus(); else if (k) { S.tab.devEdit = Object.keys(TABS).find((t) => TABS[t][1].some((f) => f[0] === k)); App.render(); } };

  /* A field is checked by the model as it is left; the draft holds only what differs from the saved device. */
  document.addEventListener('change', (e) => {
    const m = /^de-(\w+)$/.exec(e.target.id || '');
    if (!m || !ED.reply || App.route().b !== 'device') return;
    const key = m[1], kind = kindOf(key);
    if (!kind || kind === 'fixed') return;
    const [v, local] = parse(kind, kind === 'bool' ? e.target.checked : e.target.value);
    const was = ED.reply.device[key];
    if (v === was || (v == null && was == null)) { delete ED.draft[key]; delete ED.errors[key]; queueMicrotask(App.render); return; }
    ED.draft[key] = v;
    if (local) { ED.errors[key] = local; queueMicrotask(App.render); return; }
    delete ED.errors[key];
    queueMicrotask(App.render);
    const id = ED.key;
    Bridge.call('check_library_field', id, key, v).then((msg) => {
      if (ED.key !== id || ED.draft[key] !== v) return;
      if (msg) ED.errors[key] = msg; else delete ED.errors[key];
      App.render();
    }).catch(() => {});
  });
  ACTIONS['de-discard'] = () => { ED.draft = {}; ED.errors = {}; ED.refusal = ''; App.render(); toast('Changes discarded', 'undo'); };
  function save() {  // resolves true once the edits are in the pending set
    if (ED.saving || !dirty() || invalid()) return Promise.resolve(false);
    const id = ED.key;
    const edits = Object.entries(ED.draft).map(([k, v]) => (v == null ? { op: 'remove', path: ['devices', id, k] } : { op: 'set', path: ['devices', id, k], value: v }));
    ED.saving = true; ED.refusal = ''; App.render();
    return Bridge.call('add_library_edits', edits).then((p) => {
      PEND.page = p; PEND.state = 'loaded'; ED.key = ''; toast(`${id} saved to pending changes`, 'check'); return true;
    }).catch((e) => { ED.refusal = /[.!?]$/.test(e.message) ? e.message : e.message + '.'; return false; })
      .then((ok) => { ED.saving = false; App.render(); return ok; });
  }
  ACTIONS['de-save'] = () => { save().then((ok) => { if (ok) go('#/library'); }); };
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's' && onLibrary() && App.route().b === 'device') {
      e.preventDefault();
      if (document.activeElement) document.activeElement.blur();  /* commits the field being typed in */
      ACTIONS['de-save']();
    }
  });

  /* Leaving the editor with unsaved changes asks first. */
  let here = location.hash;
  window.addEventListener('hashchange', () => {
    const was = here; here = location.hash;
    if (!was.startsWith('#/library/device/') || location.hash === was || !dirty() || ED.saving) return;
    const to = location.hash;
    history.replaceState(null, '', was); here = was; App.render();
    const bad = invalid(), why = bad ? `${plural(bad, 'field')} ${bad === 1 ? 'needs' : 'need'} fixing before you can save.` : '';
    dialog({ title: 'Save the device first?', body: `<p>You have ${plural(changes(), 'unsaved change')} on this device.</p>${bad ? `<p class="small" id="de-leave-why" style="color:var(--color-danger-text);display:flex;gap:6px">${icon('error')}${esc(why)}</p>` : ''}`,
      actions: `<button class="btn btn--secondary" data-action="close">Keep editing</button><button class="btn btn--secondary" data-action="de-leave-discard" data-to="${esc(to)}">Discard changes</button><button class="btn btn--primary" data-action="de-leave-save" data-to="${esc(to)}" ${bad ? `disabled aria-describedby="de-leave-why" title="${esc(why)}"` : ''}>${icon('save')}Save and leave</button>` });
  });
  ACTIONS['de-leave-discard'] = (el) => { closeDialog(); ED.draft = {}; ED.errors = {}; go(el.dataset.to); };
  ACTIONS['de-leave-save'] = (el) => { const to = el.dataset.to; closeDialog(); save().then((ok) => { if (ok) go(to); }); };
})();
