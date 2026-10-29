/* Screen: Loose material, the substation's own list of items not mounted in a cabinet (plan M18,
   docs/ui/editing.md "Loose material (v0.2)", ADRs 0020 and 0022). It is a form: edits are held in a draft
   until Save, which writes them through the loose_edit writers one by one; each writer refuses what the
   project cannot take, and the page shows why. Opened in a plain browser, the prototype has no such page. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, field, input, select, pageHead, dialog, closeDialog, toast, go, $, $$ } = App;
  const real = () => S.backend === 'yes' && S.project && S.project.real && S.sub;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;
  const KEYS = ['part_id', 'description', 'qty', 'tag', 'children', 'fed_from'];

  /* ---------- data: the file's list (data) and the draft the page edits ---------- */
  const LM = { key: '', state: 'idle', data: null, error: null };
  let draft = null;  // { rows: [{ orig, base, item }], removed: [orig], host }
  let saving = false, refusal = '';
  const clean = (item) => {  // the keys the writers take, without the empty ones
    const o = {};
    KEYS.forEach((k) => { const v = item[k]; if (v != null && v !== '' && !(Array.isArray(v) && !v.length) && !(k === 'qty' && v === 1)) o[k] = v; });  // qty 1 is the default
    return o;
  };
  const same = (a, b) => JSON.stringify(clean(a)) === JSON.stringify(clean(b));
  function reset(d) {
    LM.data = d;
    draft = { rows: d.items.map((it, i) => ({ orig: i, base: it, item: { ...it } })), removed: [], host: d.host_panel };
  }
  function load() {
    const key = `${S.project.file}#${S.sub}`;
    if (LM.key !== key) { Object.assign(LM, { key, state: 'idle', data: null, error: null }); draft = null; refusal = ''; }
    if (LM.state === 'idle') {
      LM.state = 'loading';
      const current = () => LM.key === key;
      Bridge.call('loose_material', S.project.file, S.sub)
        .then((d) => { if (current()) reset(d); }).catch((err) => { if (current()) { LM.error = err; toast(err.message, 'error'); } })
        .then(() => { if (current()) { LM.state = 'loaded'; App.render(); } });
    }
    return LM.state === 'loaded' ? LM : null;
  }
  const changes = () => {
    if (!draft) return 0;
    return draft.removed.length + draft.rows.filter((r) => r.orig == null || !same(r.item, r.base)).length
      + (draft.host !== LM.data.host_panel ? 1 : 0);
  };
  const dirty = () => changes() > 0;
  /* A row's fields that cannot be saved as typed; the engine checks the rest on Save. */
  const QTY = 'Enter a number, or 1 Lot.';  // short enough for the cell; the table foot gives the rule
  const fieldProblems = (it) => {
    const p = {}, q = it.qty;
    if (!((Number.isInteger(q) && q > 0) || q === '1 Lot')) p.qty = QTY;
    if (!it.part_id && !(it.description || '').trim()) p.description = 'Describe the item.';
    return p;
  };
  const invalid = () => (draft ? draft.rows.reduce((n, r) => n + Object.keys(fieldProblems(r.item)).length, 0) : 0);
  const described = (html, id, msg) => (msg ? html.replace('<input', `<input aria-describedby="${id}-err"`) : html);
  const cellErr = (id, msg) => (msg ? `<span class="cell-err" id="${id}-err">${icon('error')}${esc(msg)}</span>` : '');
  App.looseCount = () => (draft && LM.key === `${S.project.file}#${S.sub}` ? draft.rows.length : null);

  /* ---------- page ---------- */
  const part = (id) => (LM.data.parts.find((p) => p.part_id === id) || null);
  const makeModel = (it) => [it.make, it.model].filter(Boolean).join(' ');
  const fedOptions = () => [['', 'Not fed'], ...LM.data.fed_options.map((p) => [p.id, p.name])];
  const ctl = (html) => html.replace('class="input', 'class="ctl input').replace('class="select', 'class="ctl select');
  const ADD = `<button class="btn btn--secondary" data-action="lm-add-free" ${saving ? 'disabled' : ''}>${icon('plus')}Add free text…</button><button class="btn btn--primary" data-action="lm-add-lib" ${saving ? 'disabled' : ''}>${icon('plus')}Add from library…</button>`;
  const LEDE = 'Items that are not mounted in any cabinet: software, cables, displays, patch cords. They are issued on their own sheet, after the cabinet sheets.';

  SCREENS.loose = () => {
    if (!real()) return `<div class="page">${pageHead('Loose material', LEDE)}<div class="empty"><b>Open a substation first.</b></div></div>`;
    const l = load();
    if (!l || !l.data) return `<div class="page">${pageHead('Loose material', l && l.error ? esc(l.error.message) : 'Reading the list…')}</div>`;
    const d = l.data;
    if (d.reason) return `<div class="page">${pageHead('Loose material', LEDE)}${banner('bad', `<b>The list cannot be shown.</b> ${esc(d.reason)}.`, '<a class="btn btn--secondary btn--sm" href="#/checks">Open checks</a>')}</div>`;
    const head = pageHead('Loose material', LEDE, ADD);
    const notice = refusal ? `<div style="margin-bottom:var(--space-4)">${banner('bad', `<b>Not saved.</b> ${esc(refusal)}`, '<button class="btn btn--ghost btn--icon btn--sm" data-action="lm-refusal-close" aria-label="Close">' + icon('x') + '</button>')}</div>` : '';
    if (!draft.rows.length) {
      return `<div class="page">${head}${notice}<div class="empty" style="max-width:720px"><b>No loose material.</b><div class="muted small" style="max-width:56ch;margin:4px auto 12px">With no items the workbook has no Loose Material sheet. Add an item from the library, or type one in when it is not in the library.</div>
        <div class="row" style="justify-content:center"><button class="btn btn--primary" data-action="lm-add-lib">${icon('plus')}Add from library…</button><button class="btn btn--secondary" data-action="lm-add-free">Add free text…</button></div></div>${saveBar()}</div>`;
    }
    const rows = draft.rows.map((r, i) => {
      const it = r.item, free = !it.part_id, bad = fieldProblems(it);
      const first = free
        ? `${described(ctl(input('lm-desc-' + i, it.description || '', { placeholder: 'Describe the item', invalid: !!bad.description })), 'lm-desc-' + i, bad.description)}${cellErr('lm-desc-' + i, bad.description)}<span class="cell-sub">${badge('info', 'Free text')}</span>`
        : `<span class="mono">${esc(it.part_id)}</span><span class="cell-sub">${esc(makeModel(it) || 'Library part')}${it.children && it.children.length ? ` · comes with <span class="mono">${esc(it.children.join(', '))}</span>` : ''}</span>`;
      const fed = free ? '<span class="muted small" title="A free-text item has no library data, so it cannot be fed"><span aria-hidden="true">—</span><span class="sr-only">Not fed: a free-text item has no library part</span></span>'
        : ctl(select('lm-fed-' + i, fedOptions().concat(it.fed_from && !d.fed_options.some((p) => p.id === it.fed_from) ? [[it.fed_from, it.fed_from]] : []), it.fed_from || ''));
      /* Changed marker: a new row's first cell, or each edited cell of a saved row. */
      const isNew = r.orig == null, [ncls, ndot] = App.changedCell(isNew);
      const ch = (k) => App.changedCell(!isNew && !same({ [k]: it[k] }, { [k]: r.base[k] }));
      const [c1, d1] = ch(free ? 'description' : 'part_id'), [c2, d2] = ch('tag'), [c3, d3] = ch('qty'), [c4, d4] = free ? ['', ''] : ch('fed_from');
      return `<tr><td class="num muted${ncls ? ' is-changed' : ''}" style="width:44px">${ndot}${i + 1}</td><td${c1}>${d1}${first}</td><td${c2}>${d2}${ctl(input('lm-tag-' + i, it.tag || '', { placeholder: 'Designation on the sheet' }))}</td>
        <td${c3}>${d3}${described(ctl(input('lm-qty-' + i, it.qty == null ? '' : String(it.qty), { num: true, mono: true, invalid: !!bad.qty })), 'lm-qty-' + i, bad.qty)}${cellErr('lm-qty-' + i, bad.qty)}</td><td${c4}>${d4}${fed}</td>
        <td><button class="btn btn--ghost btn--icon btn--sm btn--del" data-action="lm-remove" data-i="${i}" aria-label="Remove ${esc(free ? (it.description || 'item ' + (i + 1)) : it.part_id)}" ${saving ? 'disabled' : ''}>${icon('trash')}</button></td></tr>`;
    }).join('');
    const host = d.host_options.map((p) => [p.id, `${p.name} (${p.sheet})`]);
    return `<div class="page">${head}${notice}
      <div class="stack" style="gap:var(--space-5)">
        <div><div class="table-wrap"><table class="table"><caption class="sr-only">Loose material, in the sheet's order</caption><thead><tr><th class="num">No.</th><th style="min-width:190px">Part or description</th><th style="min-width:230px">Designation</th><th style="width:110px">Qty</th><th style="width:200px">Fed from</th><th style="width:40px"><span class="sr-only">Actions</span></th></tr></thead><tbody>${rows}</tbody></table>
          <div class="table-foot"><span>${plural(draft.rows.length, 'item')}</span><span>Quantity: A whole number, or 1 Lot.</span></div></div>
          <p class="muted small" style="margin-top:var(--space-3);max-width:68ch">An item that needs power names the cabinet that feeds it, and the engine adds its load to that cabinet. Parts that come with an item are added by the library and listed under it.</p></div>
        <aside class="lm-cards" aria-label="Where it goes in the workbook">
          <section class="card" style="padding:var(--space-4)"><h3>On the workbook</h3>
            <dl class="kv" style="margin-top:var(--space-2);grid-template-columns:78px 1fr"><dt>Sheet</dt><dd><b style="font-weight:500">${esc(d.sheet_name)}</b></dd><dt>Position</dt><dd>After the cabinet sheets, before Power Consumption</dd><dt>Written</dt><dd>Only while there are items</dd></dl>
            <p class="small muted" style="margin-top:var(--space-2)">Rename the sheet under Settings › Output. <a href="#/preview">See it in Preview</a></p></section>
          <section class="card" style="padding:var(--space-4)"><h3>Issued under</h3>
            ${field('Document of', select('lm-host', host, draft.host || ''), 'Its document number, revision and date print in the sheet header.')}</section>
        </aside></div>${saveBar()}</div>`;
  };

  function saveBar() {
    if (!dirty() && !saving) return '';
    const n = changes(), bad = invalid();
    return `<div class="savebar${bad ? ' savebar--bad' : ''}" role="region" aria-label="Unsaved changes">
      <span class="savebar-msg">${saving ? '<span class="spinner"></span><b>Saving…</b>' : bad ? App.fixLine('lm-first-bad', bad) : `<span class="dot dot--warn" aria-hidden="true"></span><b>${plural(n, 'unsaved change')}</b> · saved to substation.yaml`}</span>
      <span class="sp"></span>
      <button class="btn btn--secondary" data-action="lm-discard" ${saving ? 'disabled' : ''}>Discard</button>
      <button class="btn btn--primary" data-action="lm-save" ${saving || bad ? 'disabled' : ''}>${icon('save')}Save changes <kbd class="kbd">Ctrl+S</kbd></button></div>`;
  }

  /* Row edits change the draft; the file is written on Save. */
  const qtyOf = (v) => (/^\d+$/.test(v.trim()) ? Number(v.trim()) : v.trim());
  document.addEventListener('change', (e) => {
    if (!draft || !real() || App.route().a !== 'loose') return;
    const t = e.target, m = /^lm-(tag|qty|fed|desc)-(\d+)$/.exec(t.id || ''), r = m && draft.rows[+m[2]];
    if (r) r.item[{ tag: 'tag', qty: 'qty', fed: 'fed_from', desc: 'description' }[m[1]]] = m[1] === 'qty' ? qtyOf(t.value) : t.value.trim() || null;
    if (t.id === 'lm-host') draft.host = t.value;
    if (r || t.id === 'lm-host') queueMicrotask(App.render);  /* change can fire on a blur inside a render */
  });
  ACTIONS['lm-remove'] = (el) => {
    const i = +el.dataset.i, [r] = draft.rows.splice(i, 1);
    if (r.orig != null) draft.removed.push(r.orig);
    App.render();
    toast(`Removed ${r.item.part_id || r.item.description || 'the item'}`, 'trash', () => {
      draft.rows.splice(i, 0, r); if (r.orig != null) draft.removed = draft.removed.filter((x) => x !== r.orig); App.render();
    });
  };
  ACTIONS['lm-discard'] = () => { reset(LM.data); refusal = ''; App.render(); toast('Changes discarded', 'undo'); };
  ACTIONS['lm-first-bad'] = () => { const el = $('#main [aria-invalid="true"]'); if (el) { el.scrollIntoView({ block: 'center' }); el.focus(); } };
  ACTIONS['lm-refusal-close'] = () => { refusal = ''; App.render(); };

  /* ---------- Save: removes, then edits, then additions, then the host panel ----------
     After each write the draft is moved onto the file, so a refused step leaves the rest to save again. */
  function step(call, after) {
    return call(S.project.file, S.sub).then((reply) => {
      if (!reply.written) throw new Error((reply.issues[0] && reply.issues[0].message) || 'The project cannot take this change.');
      LM.data = reply.page; after();
    });
  }
  function plan() {
    const steps = [];
    [...draft.removed].sort((a, b) => b - a).forEach((orig) => steps.push(() => step((f, s) => Bridge.call('remove_loose_item', f, s, orig), () => {
      draft.removed = draft.removed.filter((x) => x !== orig);
      draft.rows.forEach((r) => { if (r.orig != null && r.orig > orig) r.orig -= 1; });
    })));
    draft.rows.forEach((r) => steps.push(() => (r.orig == null || same(r.item, r.base) ? null
      : step((f, s) => Bridge.call('set_loose_item', f, s, r.orig, clean(r.item)), () => { r.base = { ...r.item }; }))));
    draft.rows.forEach((r, i) => steps.push(() => (r.orig != null ? null
      : step((f, s) => Bridge.call('add_loose_item', f, s, clean(r.item), i, LM.data.host_panel ? null : draft.host || (LM.data.host_options[0] || {}).id), () => {
        draft.rows.forEach((x) => { if (x.orig != null && x.orig >= i) x.orig += 1; });
        r.orig = i; r.base = { ...r.item };
      }))));
    steps.push(() => (draft.host === LM.data.host_panel || LM.data.host_panel == null ? null : step((f, s) => Bridge.call('set_loose_host_panel', f, s, draft.host), () => {})));
    return steps;
  }
  function save() {  // resolves true once everything is written
    if (saving || !dirty() || invalid()) return Promise.resolve(false);
    const n = changes();
    saving = true; refusal = ''; App.render();
    return plan().reduce((chain, s) => chain.then(() => s()), Promise.resolve())
      .then(() => { reset(LM.data); toast(`Saved ${plural(n, 'change')}`, 'check'); return true; })
      .catch((err) => { refusal = /[.!?]$/.test(err.message) ? err.message : err.message + '.'; return false; })
      .then((ok) => { saving = false; App.render(); return ok; });
  }
  ACTIONS['lm-save'] = () => { save(); };
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's' && real() && App.route().a === 'loose') {
      e.preventDefault();
      if (document.activeElement) document.activeElement.blur();  /* commits the field being typed in */
      ACTIONS['lm-save']();
    }
  });

  /* ---------- Add: from the library, or free text; the engine checks the item before it joins the draft ---------- */
  const pickRows = (q) => {
    const l = LM.data.parts.filter((p) => [p.part_id, p.make, p.model].join(' ').toLowerCase().includes(q.toLowerCase())).slice(0, 40);
    return l.map((p) => `<label class="pick-row"><input type="radio" name="lm-part" value="${esc(p.part_id)}"><span><span class="mono">${esc(p.part_id)}</span><span class="cell-sub">${esc([p.make, p.model].filter(Boolean).join(' '))}</span></span>${p.data_quality ? `${App.verified(p.data_quality)}` : ''}</label>`).join('')
      || '<div class="muted" style="padding:12px">No library part matches. Use free text, or add the part to the library.</div>';
  };
  const LABELS = { part_id: 'Part', fed_from: 'Fed from', children: 'Comes with', qty: 'Quantity', tag: 'Designation', description: 'Description' };
  const labelOf = (k) => LABELS[k.replace(/\[\d+\]$/, '').split('.')[0]] || k.replace(/_/g, ' ');
  const errorLine = (msgs) => Object.entries(msgs).map(([k, v]) => `${k ? labelOf(k) + ': ' : ''}${v}`).join(' ');
  function check(item, done) {
    Bridge.call('validate_loose_item', S.project.file, S.sub, null, item).then((msgs) => {
      if (Object.keys(msgs).length) { $('#lm-err').innerHTML = banner('bad', esc(errorLine(msgs))); return; }
      draft.rows.push({ orig: null, base: {}, item: { ...item, ...(item.part_id ? { make: (part(item.part_id) || {}).make, model: (part(item.part_id) || {}).model } : {}) } });
      closeDialog(); App.render(); done();
    }).catch((err) => { $('#lm-err').innerHTML = banner('bad', esc(err.message)); });
  }
  ACTIONS['lm-add-lib'] = () => dialog({ title: 'Add a library part as loose material', body: `<div class="stack">
    <div class="input-wrap"><label class="sr-only" for="lm-q">Search library</label>${icon('search')}<input class="input" id="lm-q" type="search" placeholder="Search part, make or model" autocomplete="off"></div>
    <div class="pick-list" id="lm-list" role="radiogroup" aria-label="Library parts">${pickRows('')}</div>
    <div class="form form--3">${field('Quantity', input('lm-nq', '1', { num: true, mono: true }), 'A whole number, or 1 Lot.')}${field('Designation', input('lm-nt', '', { placeholder: 'e.g. SRV/OAS - HMI Software' }))}${field('Fed from', select('lm-nf', fedOptions(), ''))}</div>
    <p class="muted small">Anything that comes with the part, such as a cable or a mounting kit, is added from the library.</p><div id="lm-err"></div></div>`,
    actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="lm-add-lib-do">Add item</button>' });
  document.addEventListener('input', (e) => { if (e.target.id === 'lm-q') $('#lm-list').innerHTML = pickRows(e.target.value); });
  ACTIONS['lm-add-lib-do'] = () => {
    const picked = $('input[name="lm-part"]:checked'), qty = $('#lm-nq').value.trim();
    if (!picked) { $('#lm-err').innerHTML = banner('bad', 'Choose a part from the list.'); return; }
    if (!qty) { $('#lm-nq').setAttribute('aria-invalid', 'true'); $('#lm-nq').focus(); return; }
    const p = part(picked.value);
    const item = clean({ part_id: picked.value, qty: qtyOf(qty), tag: $('#lm-nt').value.trim() || [p && p.make, p && p.model].filter(Boolean).join(' ') || null, fed_from: $('#lm-nf').value || null });
    check(item, () => toast(`Added ${picked.value}. Save to write it.`, 'plus'));
  };
  ACTIONS['lm-add-free'] = () => dialog({ title: 'Add a free-text item', body: `<div class="stack">
    <div class="form">${field('Description', input('lm-fd', '', { placeholder: 'e.g. Fibre optic patch cords, LC to LC' }), 'Printed as it is. Required.')}</div>
    <div class="form form--3">${field('Quantity', input('lm-fq', '1', { num: true, mono: true }), 'A whole number, or 1 Lot.')}${field('Designation', input('lm-ft', ''))}</div>
    ${banner('info', 'A free-text item has no part, so the sheet shows no ordering code, make or model for it, and it cannot be fed from a cabinet. Add the part to the library to get them.')}<div id="lm-err"></div></div>`,
    actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="lm-add-free-do">Add item</button>' });
  ACTIONS['lm-add-free-do'] = () => {
    const desc = $('#lm-fd').value.trim(), qty = $('#lm-fq').value.trim();
    if (!desc) { $('#lm-fd').setAttribute('aria-invalid', 'true'); $('#lm-fd').focus(); return; }
    if (!qty) { $('#lm-fq').setAttribute('aria-invalid', 'true'); $('#lm-fq').focus(); return; }
    check(clean({ description: desc, qty: qtyOf(qty), tag: $('#lm-ft').value.trim() || null }), () => toast('Added a free-text item. Save to write it.', 'plus'));
  };

  /* Leaving the page or the substation with unsaved changes asks first. */
  let here = location.hash;
  window.addEventListener('hashchange', () => {
    const was = here; here = location.hash;
    if (!was.startsWith('#/loose') || location.hash.startsWith('#/loose') || !dirty() || saving) return;
    const to = location.hash;
    history.replaceState(null, '', was); here = was; App.render();
    const bad = invalid(), why = bad ? `${plural(bad, 'field')} ${bad === 1 ? 'needs' : 'need'} fixing before you can save.` : '';
    dialog({ title: 'Save the loose material first?', body: `<p>You have ${plural(changes(), 'unsaved change')} on this page.</p>${bad ? `<p class="small" id="lm-leave-why" style="color:var(--color-danger-text);display:flex;gap:6px">${icon('error')}${esc(why)}</p>` : ''}`,
      actions: `<button class="btn btn--secondary" data-action="close">Keep editing</button><button class="btn btn--secondary" data-action="lm-leave-discard" data-to="${esc(to)}">Discard changes</button><button class="btn btn--primary" data-action="lm-leave-save" data-to="${esc(to)}" ${bad ? `disabled aria-describedby="lm-leave-why" title="${esc(why)}"` : ''}>${icon('save')}Save and leave</button>` });
  });
  ACTIONS['lm-leave-discard'] = (el) => { closeDialog(); reset(LM.data); go(el.dataset.to); };
  ACTIONS['lm-leave-save'] = (el) => {
    const to = el.dataset.to;
    closeDialog(); save().then((ok) => { if (ok) go(to); });  /* refused: stay, the banner says why */
  };
})();
