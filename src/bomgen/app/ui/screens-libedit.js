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
  App.setPending = (p) => { PEND.page = p; PEND.state = 'loaded'; };  // after a CSV import (screens-libcsv.js)
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
      toast('Pending changes discarded', 'trash', r.discarded.length || r.discarded_records.length ? () => Bridge.call('add_library_edits', r.discarded, r.discarded_records).then((p) => { PEND.page = p; ED.key = ''; App.render(); }).catch((e) => toast(e.message, 'error')) : null);
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
    const line = (e) => `<div><span class="mono">${esc(e.label)}</span><span class="muted">${e.kind === 'changed' ? `${e.field ? `${esc(labelOf(e.field))}: ` : ''}${esc(withUnit(e.field, e.from))} → ${esc(withUnit(e.field, e.to))}` : esc(e.to || e.from)}</span></div>`;
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
  const ED = { key: '', state: 'idle', reply: null, error: null, draft: {}, errors: {}, refusal: '', saving: false, users: null };
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
    ports: ['Ports and mounting', [['height_u', 'Height', 'int', '0 for a DIN-rail part; empty if not known yet.', 0, 'U'], ['cores', 'Fibre cores', 'int', 'For patch panels.']]],
    parts: ['Parts it brings', []],
    /* The device-database record (rec__ keys: the record path with __ for each dot). */
    datasheet: ['Datasheet', [['rec__verified', 'Research status', 'choice', 'Confirmed once every figure is checked against the datasheet.'], ['rec__datasheet__mounting_kind', 'Mounting', 'choice'],
      ['rec__datasheet__summary', 'Summary', 'area', '', 2],
      ['rec__datasheet__height_u', 'Height', 'int', 'Above 0 exactly when the mounting is rack.', 0, 'U'], ['rec__datasheet__weight_kg', 'Weight', 'num', '', 0, 'kg'],
      ['rec__datasheet__power__input', 'Power input', 'text', 'As the datasheet gives it, e.g. 125 VDC.'], ['rec__datasheet__power__typical_w', 'Typical power', 'num', '', 0, 'W'], ['rec__datasheet__power__max_w', 'Maximum power', 'num', '', 0, 'W'],
      ['rec__datasheet__operating_temp_c__min', 'Lowest operating temperature', 'snum', '', 0, '°C'], ['rec__datasheet__operating_temp_c__max', 'Highest operating temperature', 'snum', '', 0, '°C'],
      ['rec__datasheet__dimensions_mm__h', 'Case height', 'num', '', 0, 'mm'], ['rec__datasheet__dimensions_mm__w', 'Case width', 'num', '', 0, 'mm'], ['rec__datasheet__dimensions_mm__d', 'Case depth', 'num', '', 0, 'mm'],
      ['rec__datasheet__certifications', 'Certifications', 'csv', 'Separated by commas.', 2],
      ['rec__datasheet__datasheet_url', 'Datasheet link', 'mono', '', 2], ['rec__datasheet__product_url', 'Product page', 'mono', '', 2],
      ['rec__sources', 'Sources', 'lines', 'One per line: where each figure was found.', 2]]]
  };
  const isRec = (key) => key.startsWith('rec__');
  const recPath = (key) => key.slice(5).split('__');
  const recKey = (path) => 'rec__' + path.replace(/\./g, '__');
  /* List fields are edited as a whole list: [title, tab, columns [key, label, kind], a new row]. Kinds: int, choice, part, qty, mono, text. */
  const LISTS = {
    ports: ['Port groups', 'ports', [['count', 'Count', 'int'], ['speed', 'Speed', 'choice'], ['media', 'Media', 'choice'], ['kind', 'Kind', 'choice'], ['usable_for', 'Used for', 'choice']], { count: 1, speed: '100M', media: 'RJ45', kind: 'fixed', usable_for: 'any' }],
    children: ['Child parts', 'parts', [['part_id', 'Part', 'part'], ['qty', 'Qty', 'qty']], { part_id: '', qty: 1 }],
    terminals: ['Terminals', 'parts', [['strip', 'Strip', 'mono'], ['block', 'Block', 'mono'], ['count', 'Count', 'int'], ['per', 'Per', 'choice']], { strip: 'X1', block: '', count: 1, per: 'unit' }],
    loose_items: ['Loose items', 'parts', [['part_id', 'Part', 'part'], ['qty', 'Qty', 'qty'], ['tag', 'Tag', 'text']], { part_id: '', qty: 1 }]
  };
  const FIELDS = Object.values(TABS).flatMap(([, f]) => f);
  const kindOf = (key) => (FIELDS.find((f) => f[0] === key) || [])[2];
  /* Review entries name a device field, or a record path such as datasheet.weight_kg. */
  const fieldOf = (key) => FIELDS.find((f) => f[0] === key) || FIELDS.find((f) => f[0] === recKey(key));
  const labelOf = (key) => (LISTS[key] ? LISTS[key][0] : (fieldOf(key) || [key, key])[1]);
  const withUnit = (key, v) => { const u = (fieldOf(key) || [])[5]; return v ? (u ? `${v} ${u}` : v) : 'empty'; };

  function loadDevice(id) {
    Object.assign(ED, { key: id, state: 'loading', reply: null, error: null, draft: {}, errors: {}, refusal: '', users: null });
    if (S.project && S.project.real && S.sub) {  /* who uses it in the open substation: the In use banner and the delete warning */
      Bridge.call('library_part_users', id, S.project.file, S.sub).then((u) => { if (ED.key === id) { ED.users = u; App.render(); } }).catch(() => {});
    }
    Bridge.call('library_device', id).then((r) => { if (ED.key === id) ED.reply = r; }).catch((e) => { if (ED.key === id) ED.error = e; })
      .then(() => { if (ED.key === id) { ED.state = 'loaded'; App.render(); } });
  }
  /* The value as it now stands (pending edits applied): a device field or a record path. */
  const current = (key) => (isRec(key) ? recPath(key).reduce((o, k) => (o == null ? null : o[k]), ED.reply.record) : ED.reply.device[key]);
  const value = (key) => (key in ED.draft ? ED.draft[key] : current(key));
  const same = (a, b) => (a == null && b == null) || JSON.stringify(a) === JSON.stringify(b);
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
    if (kind === 'snum') return /^-?\d+(\.\d+)?$/.test(t) ? [Number(t), null] : [t, 'Enter a number, for example -40 or 70.'];
    if (kind === 'csv') return [t.split(',').map((x) => x.trim()).filter(Boolean), null];
    if (kind === 'lines') return [t.split('\n').map((x) => x.trim()).filter(Boolean), null];
    return [t, null];
  }
  function control(f) {
    const [key, label, kind, help = '', , unit] = f, id = 'de-' + key, err = ED.errors[key];
    const raw = value(key), v = Array.isArray(raw) ? raw.join(kind === 'csv' ? ', ' : '\n') : raw;
    const changed = key in ED.draft, o = { invalid: !!err };
    const choices = (ED.reply.choices || {})[isRec(key) ? recPath(key).pop() : key] || [];
    let html;
    if (kind === 'fixed') html = input(id, v, { mono: true, readonly: true });
    else if (kind === 'bool') return `<div class="field${changed ? ' changed' : ''}"><label class="switch"><input type="checkbox" id="${id}" ${v ? 'checked' : ''}>${esc(label)}</label>${err ? `<span class="err" id="${id}-err">${icon('error')}<span>${esc(err)}</span></span>` : ''}</div>`;
    else if (kind === 'choice') html = select(id, [['', 'Not set'], ...choices.map((c) => [c, key === 'category' ? catName(c) : c])], v == null ? '' : String(v), o);
    else if (kind === 'feeds') html = select(id, [['0', 'None'], ['1', 'Single feed'], ['2', 'Dual feed (2 supplies)']], String(v || 0), o);
    else if (kind === 'area' || kind === 'lines') html = `<textarea class="input input--mono" id="${id}" rows="3" ${err ? 'aria-invalid="true"' : ''} style="height:auto;padding:8px 10px">${esc(v == null ? '' : v)}</textarea>`;
    else html = input(id, v == null ? '' : String(v), { ...o, mono: kind !== 'text' && kind !== 'csv', num: kind === 'int' || kind === 'num' || kind === 'snum' });
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
    const noRecord = t === 'datasheet' && !ED.reply.record;
    const fields = noRecord ? [] : TABS[t][1], spans = (f) => (f[4] === 2 ? `<div class="span-2">${control(f)}</div>` : control(f));
    const lists = Object.entries(LISTS).filter(([, l]) => l[1] === t).map(([key]) => listTable(key)).join('');
    const ledeText = { parts: 'Parts that come with each unit of this device. They appear as extra rows in the BOM.',
      datasheet: noRecord ? 'This part has no record in the library\'s device database, so there are no datasheet figures to edit.' : 'What the datasheet confirms. These figures are for reference; the BOM uses the Electrical and Ports values.' }[t];
    const lede = ledeText ? `<p class="muted small" style="max-width:68ch;margin-bottom:var(--space-3)">${ledeText}</p>` : '';
    const pend = ED.reply.pending_fields.length && ED.reply.saved ? `<div style="margin-bottom:var(--space-4)">${banner('info', `<b>This device has pending changes</b> (${ED.reply.pending_fields.map(esc).join(', ')}). The fields show them; the library keeps the saved values until you apply.`)}</div>` : '';
    const inUse = usesText();
    const used = inUse ? `<div style="margin-bottom:var(--space-4)">${banner('info', `<b>This device is in use.</b> ${inUse} Projects keep the library version they record, so an edit reaches a project only when it records the version you apply.`)}</div>` : '';
    const notice = ED.refusal ? `<div style="margin-bottom:var(--space-4)">${banner('bad', `<b>Not saved.</b> ${esc(ED.refusal)}`)}</div>` : '';
    const isNew = !ED.reply.saved;
    return `<div class="page">${pageHead(esc(d.part_id), esc([d.make, d.model, isNew ? 'new device, not applied yet' : ''].filter(Boolean).join(' · ')), `<button class="btn btn--danger" data-action="delete-device" data-id="${esc(d.part_id)}">${icon('trash')}Delete…</button>`, crumbs)}${notice}${used}${pend}
      ${tabs('devEdit', Object.entries(TABS).map(([k, [label]]) => [k, label]), t, 'Device sections')}
      <div role="tabpanel" aria-labelledby="tab-devEdit-${t}" style="margin-top:var(--space-4)">${t === 'parts' ? `<datalist id="dl-parts">${(ED.reply.part_ids || []).map((p) => `<option value="${esc(p)}">`).join('')}</datalist>` : ''}${lede}${fields.length ? `<div class="form ${t === 'identity' ? 'form--2' : 'form--3'}">${fields.map(spans).join('')}</div>` : ''}${lists}</div>${saveBar()}</div>`;
  }
  /* "GIS Substation uses it in 2 rows: the equipment row rtac (Network) and a row on panel psa3 (Panels)." Library rows that bring it are named apart. */
  function usesText() {
    const u = ED.users;
    if (!u || !u.uses || !u.uses.length) return '';
    const rows = u.uses.filter((x) => x.where !== 'library'), lib = u.uses.filter((x) => x.where === 'library');
    const m = (s) => `<span class="mono">${esc(s)}</span>`;
    const panels = {};
    rows.filter((x) => x.where === 'panel').forEach((x) => { panels[x.panel] = (panels[x.panel] || 0) + 1; });
    const parts = [
      ...rows.filter((x) => x.where === 'equipment').map((x) => `the equipment row ${m(x.name)} (Network)`),
      ...Object.entries(panels).map(([p, n]) => `${n === 1 ? 'a row' : `${n} rows`} on panel ${m(p)} (Panels)`),
      ...rows.filter((x) => x.where === 'loose material').map((x) => `the loose material row ${m(x.name)} (Loose material)`),
    ];
    const and = (xs) => xs.length > 1 ? `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}` : xs.join('');
    return [rows.length ? `${esc(u.substation)} uses it in ${plural(rows.length, 'row')}: ${and(parts)}.` : '',
      lib.length ? `In the library it comes with ${and(lib.map((x) => m(x.name)))}.` : ''].filter(Boolean).join(' ');
  }
  function listTable(key) {
    const [title, , cols] = LISTS[key], rows = value(key) || [], err = ED.errors[key], changed = key in ED.draft;
    const choices = ED.reply.choices || {};
    const cell = (i, [col, label, kind]) => {
      const id = `dl-${key}-${i}-${col}`, v = rows[i][col];
      const ctl = kind === 'choice' ? select(id, [...(col === 'media' ? [['', '—']] : []), ...(choices[col] || []).map((c) => [c, c])], v == null ? '' : String(v), { cls: 'ctl' })
        : input(id, v == null ? '' : String(v), { mono: kind !== 'text', num: kind === 'int' || kind === 'qty' }).replace('class="input', 'class="ctl input').replace('<input', `<input aria-label="${esc(label)}, row ${i + 1}"${kind === 'part' ? ' list="dl-parts"' : ''}`);
      return `<td>${ctl}</td>`;
    };
    const body = rows.length ? rows.map((r, i) => `<tr>${cols.map((c) => cell(i, c)).join('')}<td><button class="btn btn--ghost btn--icon btn--sm" data-action="dl-remove" data-key="${key}" data-i="${i}" aria-label="Remove ${esc(title.toLowerCase())} row ${i + 1}">${icon('trash')}</button></td></tr>`).join('')
      : `<tr class="empty-row"><td colspan="${cols.length + 1}" class="muted">None. Add one if each unit brings it.</td></tr>`;
    return `<section class="section${changed ? ' changed' : ''}" style="padding-top:var(--space-3)"><div class="row" style="justify-content:space-between;max-width:760px"><h3>${esc(title)}${changed ? ` ${badge('warn', 'Changed')}` : ''}</h3><button class="btn btn--ghost btn--sm" data-action="dl-add" data-key="${key}">${icon('plus')}Add</button></div>
      <div class="table-wrap" style="max-width:760px;margin-top:6px"><table class="table"><thead><tr>${cols.map(([, label]) => `<th>${esc(label)}</th>`).join('')}<th style="width:40px"><span class="sr-only">Actions</span></th></tr></thead><tbody>${body}</tbody></table></div>
      ${err ? `<span class="err" style="margin-top:6px" id="dl-${key}-err">${icon('error')}<span>${esc(err)}</span></span>` : ''}</section>`;
  }
  /* A list edit replaces the whole list; the model checks it, and setting it back to the saved list drops the change. */
  function setList(key, rows) {
    const saved = ED.reply.device[key] || [];
    if (JSON.stringify(rows) === JSON.stringify(saved)) { delete ED.draft[key]; delete ED.errors[key]; queueMicrotask(App.render); return; }
    ED.draft[key] = rows; delete ED.errors[key]; queueMicrotask(App.render);
    const id = ED.key;
    Bridge.call('check_library_field', id, key, rows).then((msg) => {
      if (ED.key !== id || ED.draft[key] !== rows) return;
      if (msg) ED.errors[key] = msg; else delete ED.errors[key];
      App.render();
    }).catch(() => {});
  }
  const listCopy = (key) => (value(key) || []).map((r) => ({ ...r }));
  ACTIONS['dl-add'] = (el) => { const key = el.dataset.key, rows = listCopy(key); rows.push({ ...LISTS[key][3] }); setList(key, rows); };
  ACTIONS['dl-remove'] = (el) => { const key = el.dataset.key, rows = listCopy(key); rows.splice(+el.dataset.i, 1); setList(key, rows); };
  const cellValue = (kind, raw) => { const t = String(raw).trim(); if (kind === 'int' || kind === 'qty') return /^\d+$/.test(t) ? Number(t) : t || null; return t || null; };

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
    const c = /^dl-(\w+?)-(\d+)-(\w+)$/.exec(e.target.id || '');
    if (c && ED.reply && LISTS[c[1]]) {
      const [, key, i, col] = c, rows = listCopy(key), kind = LISTS[key][2].find((x) => x[0] === col)[2];
      const v = cellValue(kind, e.target.value);
      rows[+i][col] = v;
      setList(key, rows); return;
    }
    const m = /^de-(\w+)$/.exec(e.target.id || '');
    if (!m || !ED.reply || App.route().b !== 'device') return;
    const key = m[1], kind = kindOf(key);
    if (!kind || kind === 'fixed') return;
    const [v, local] = parse(kind, kind === 'bool' ? e.target.checked : e.target.value);
    const was = current(key);
    if (same(v, was) || (Array.isArray(v) && !v.length && was == null)) { delete ED.draft[key]; delete ED.errors[key]; queueMicrotask(App.render); return; }
    ED.draft[key] = v;
    if (local) { ED.errors[key] = local; queueMicrotask(App.render); return; }
    delete ED.errors[key];
    queueMicrotask(App.render);
    const id = ED.key;
    (isRec(key) ? Bridge.call('check_library_record', id, recPath(key).join('.'), v) : Bridge.call('check_library_field', id, key, v)).then((msg) => {
      if (ED.key !== id || ED.draft[key] !== v) return;
      if (msg) ED.errors[key] = msg; else delete ED.errors[key];
      App.render();
    }).catch(() => {});
  });
  ACTIONS['de-discard'] = () => { ED.draft = {}; ED.errors = {}; ED.refusal = ''; App.render(); toast('Changes discarded', 'undo'); };
  function save() {  // resolves true once the edits are in the pending set
    if (ED.saving || !dirty() || invalid()) return Promise.resolve(false);
    const id = ED.key;
    const draft = Object.entries(ED.draft), rec = draft.filter(([k]) => isRec(k));
    const edits = draft.filter(([k]) => !isRec(k)).map(([k, v]) => (v == null ? { op: 'remove', path: ['devices', id, k] } : { op: 'set', path: ['devices', id, k], value: v }));
    const fields = Object.fromEntries(rec.map(([k, v]) => [recPath(k).join('.'), Array.isArray(v) && !v.length ? null : v]));
    ED.saving = true; ED.refusal = ''; App.render();
    /* Device fields first, then the record's; a refused record keeps its fields in the form. */
    return (edits.length ? Bridge.call('add_library_edits', edits) : Promise.resolve(null)).then((p) => {
      if (p) { PEND.page = p; PEND.state = 'loaded'; draft.filter(([k]) => !isRec(k)).forEach(([k]) => delete ED.draft[k]); }
      return rec.length ? Bridge.call('set_library_record_fields', id, fields) : p;
    }).then((p) => {
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

  /* ---------- Add device and Delete: records, so they go to the pending set at once ---------- */
  ACTIONS['add-device'] = () => {
    const devs = App.libraryDevices(), cats = (PEND.page && PEND.page.choices.category) || [...new Set(devs.map((d) => d.cat))];
    dialog({ title: 'Add a device', body: `<div class="stack">
      ${field('Start from', select('ad-from', [['', 'A blank device'], ...devs.map((d) => [d.id, `A copy of ${d.id}${d.model ? ` (${[d.make, d.model].filter(Boolean).join(' ')})` : ''}`])], ''), 'A copy keeps the electrical data, ports and parts, so you only change what differs.')}
      <div class="form form--2">${field('Part ID', input('ad-id', '', { mono: true, placeholder: 'e.g. SEL-2730M-EXT-B' }), 'Unique in the library. Fixed once created: projects refer to it.')}${field('Category', select('ad-cat', cats.map((c) => [c, catName(c)]), cats[0]))}
      ${field('Make', input('ad-make', ''))}${field('Model', input('ad-model', ''))}</div><div id="ad-err"></div></div>`,
      actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="add-device-do">Create and edit</button>' });
  };
  document.addEventListener('change', (e) => {  /* a copy starts with the source's category */
    if (e.target.id !== 'ad-from' || !e.target.value) return;
    const d = App.libraryDevices().find((x) => x.id === e.target.value);
    if (d && $('#ad-cat')) $('#ad-cat').value = d.cat;
  });
  ACTIONS['add-device-do'] = () => {
    const id = $('#ad-id').value.trim();
    if (!id) { $('#ad-id').setAttribute('aria-invalid', 'true'); $('#ad-id').focus(); return; }
    Bridge.call('add_library_device', id, $('#ad-cat').value, $('#ad-make').value.trim(), $('#ad-model').value.trim(), $('#ad-from').value || null).then((p) => {
      PEND.page = p; PEND.state = 'loaded'; closeDialog(); S.tab.devEdit = 'identity'; ED.key = '';
      toast(`${id} added to pending changes. It joins the library when you apply them.`, 'plus'); go('#/library/device/' + encodeURIComponent(id));
    }).catch((e) => { $('#ad-err').innerHTML = banner('bad', esc(e.message)); });
  };
  ACTIONS['delete-device'] = (el) => dialog({ title: `Delete ${esc(el.dataset.id)}?`, body: `<div class="stack"><p>The device is removed from the library when you apply the pending changes. You can still discard it before then.</p>${usesText() ? banner('bad', `<b>It is still used.</b> ${usesText()} After you apply this change, a project that records the new version reports an error until another part is picked.`) : '<p class="muted small">A project that uses it reports an error once it records the new version, until another part is picked.</p>'}<div id="dd-err"></div></div>`,
    actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--danger" data-action="delete-device-do" data-id="${esc(el.dataset.id)}">${icon('trash')}Delete device</button>` });
  ACTIONS['delete-device-do'] = (el) => {
    const id = el.dataset.id;
    Bridge.call('add_library_edits', [{ op: 'remove', path: ['devices', id] }]).then((p) => {
      PEND.page = p; PEND.state = 'loaded'; closeDialog(); ED.draft = {}; ED.errors = {}; ED.key = ''; go('#/library');
      toast(`${id} will be removed when you apply the changes`, 'trash');
    }).catch((e) => { $('#dd-err').innerHTML = banner('bad', esc(e.message)); });
  };

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
