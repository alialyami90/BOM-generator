/* v0.2 Loose material: the substation's own editable list of items that are not mounted in a cabinet.
   It is printed on its own sheet (ADR 0020), so it has its own page, a place in Preview and its own sheet name. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, field, input, select, pageHead, verified, dialog, closeDialog, toast, go, $, $$ } = App;
  const P = DB.sub;
  const list = () => (App.isBlank() ? (S.blankLoose = S.blankLoose || []) : (P.loose = P.loose || []));
  /* The list is edited in place, so a copy taken before the first edit lets Discard bring it back. */
  const snap = () => { if (!S.looseSnap) S.looseSnap = JSON.stringify(list()); };
  const restore = () => { if (!S.looseSnap) return; const back = JSON.parse(S.looseSnap); const l = list(); l.length = 0; l.push(...back); S.looseSnap = null; };
  const baseDiscard = ACTIONS.discard; ACTIONS.discard = (el, e) => { restore(); baseDiscard(el, e); };
  const baseSave = ACTIONS['save-all']; ACTIONS['save-all'] = (el, e) => { S.looseSnap = null; baseSave(el, e); };
  const baseDiscardDo = ACTIONS['leave-discard']; if (baseDiscardDo) ACTIONS['leave-discard'] = (el, e) => { restore(); baseDiscardDo(el, e); };
  const lib = (id) => DB.devices.find((d) => d.id === id);
  const panelName = (id) => { const p = DB.panels.find((x) => x.id === id); return p ? p.name : id.toUpperCase(); };
  const fedOptions = () => [['', 'Not fed'], ...DB.panels.filter((p) => p.id !== 'ws').map((p) => [p.id, p.name])];
  const ctl = (html) => html.replace('class="input', 'class="ctl input').replace('class="select', 'class="ctl select');
  /* ADR 0022: a free-text item has no library data, so it cannot be fed; "—" is text, not a control. */
  const NOT_FED = '<span class="muted" aria-hidden="true">—</span><span class="sr-only">Not fed: a free-text item has no library part</span>';
  const countText = (n) => (n === 1 ? '1 item' : `${n} items`);
  const docLabel = () => { const pn = DB.panels.find((x) => x.id === (P.hostPanel || 'ws')); const d = pn && App.curProject().documents.find((x) => x.key === pn.doc); return d ? d.docNo : ''; };

  SCREENS.loose = () => {
    const items = list();
    const head = pageHead('Loose material', 'Items that are not mounted in any cabinet: software, cables, displays, patch cords. They are issued on their own sheet, after the cabinet sheets.',
      `<button class="btn btn--secondary" data-action="lm-add-free">${icon('plus')}Add free text…</button><button class="btn btn--primary" data-action="lm-add-lib">${icon('plus')}Add from library…</button>`);
    if (!items.length) return `<div class="page">${head}<div class="empty" style="max-width:720px"><b>No loose material.</b><div class="muted small" style="max-width:56ch;margin:4px auto 12px">With no items the workbook has no Loose Material sheet. Add an item from the library, or type one in when it is not in the library.</div>
      <div class="row" style="justify-content:center"><button class="btn btn--primary" data-action="lm-add-lib">${icon('plus')}Add from library…</button><button class="btn btn--secondary" data-action="lm-add-free">Add free text…</button></div></div></div>`;
    const rows = items.map((l, i) => {
      const d = l.free ? null : lib(l.part);
      const first = l.free
        ? `${ctl(input('lm-desc-' + i, l.desc || '', { placeholder: 'Describe the item' }))}<span class="cell-sub">${badge('info', 'Free text')}</span>`
        : `<span class="mono">${esc(l.part)}</span><span class="cell-sub">${d ? esc(`${d.make} ${d.model}`) : 'Library part'}${l.children ? ` · comes with <span class="mono">${esc(l.children)}</span>` : ''}</span>`;
      return `<tr><td class="num muted" style="width:44px">${i + 1}</td><td>${first}</td><td>${ctl(input('lm-tag-' + i, l.tag, { placeholder: 'Designation on the sheet' }))}</td>
        <td>${ctl(input('lm-qty-' + i, l.qty, { num: true, mono: true }))}</td><td>${l.free ? NOT_FED : ctl(select('lm-fed-' + i, fedOptions(), l.fed || ''))}</td>
        <td><button class="btn btn--ghost btn--icon btn--sm" data-action="lm-remove" data-i="${i}" aria-label="Remove ${esc(l.free ? (l.desc || 'item ' + (i + 1)) : l.part)}">${icon('trash')}</button></td></tr>`;
    }).join('');
    const host = DB.panels.map((p) => [p.id, `${p.name} (${p.id === 'ws' ? 'sheet ' + p.sheet : 'sheet ' + p.sheet})`]);
    return `<div class="page">${head}
      <div class="stack" style="gap:var(--space-5)">
        <div><div class="table-wrap"><table class="table"><thead><tr><th class="num">No.</th><th style="min-width:190px">Part or description</th><th style="min-width:230px">Designation</th><th style="width:110px">Qty</th><th style="width:200px">Fed from</th><th style="width:40px"><span class="sr-only">Actions</span></th></tr></thead><tbody>${rows}</tbody></table>
          <div class="table-foot"><span>${countText(items.length)}</span><span>Quantity is a whole number, or 1 Lot.</span></div></div>
          <p class="muted small" style="margin-top:var(--space-3);max-width:68ch">An item that needs power names the cabinet that feeds it, and the engine adds its load to that cabinet. Parts that come with an item are added by the library and listed under it. A free-text item is never fed and brings nothing with it.</p></div>
        <aside style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--space-5);align-items:start" aria-label="Where it goes in the workbook">
          <section class="card" style="padding:var(--space-4)"><h3>On the workbook</h3>
            <dl class="kv" style="margin-top:var(--space-2);grid-template-columns:78px 1fr"><dt>Sheet</dt><dd><b style="font-weight:500">${esc(P.output.sheets[0])}</b></dd><dt>Position</dt><dd>After the cabinet sheets, before ${esc(P.output.sheets[1])}</dd><dt>Written</dt><dd>Only while there are items</dd></dl>
            <p class="small muted" style="margin-top:var(--space-2)">Rename the sheet under Settings › Output. <a href="#/preview/loose">See it in Preview</a></p></section>
          <section class="card" style="padding:var(--space-4)"><h3>Issued under</h3>
            ${field('Document of', select('lm-host', host, P.hostPanel || 'ws'), `Its document number, revision and date print in the sheet header${docLabel() ? ` (now ${esc(docLabel())})` : ''}.`)}</section>
        </aside></div></div>`;
  };

  /* Edits write through to the list; the save bar holds them like any other form. */
  document.addEventListener('change', (e) => {
    const t = e.target; const m = /^lm-(tag|qty|fed|desc)-(\d+)$/.exec(t.id || ''); const items = list();
    if (m && items[+m[2]]) { snap(); const k = { tag: 'tag', qty: 'qty', fed: 'fed', desc: 'desc' }[m[1]]; items[+m[2]][k] = t.value; if (m[1] === 'fed') App.render(); }
    if (t.id === 'lm-host') { P.hostPanel = t.value; App.render(); }
  });

  /* ---------- Add ---------- */
  const pickRows = (q) => {
    const l = DB.devices.filter((d) => (d.id + d.make + d.model).toLowerCase().includes(q.toLowerCase())).slice(0, 7);
    return l.map((d) => `<label class="pick-row"><input type="radio" name="lm-part" value="${esc(d.id)}"><span><span class="mono">${esc(d.id)}</span><span class="cell-sub">${esc(d.make)} ${esc(d.model)}</span></span><span class="right">${verified(d.verified)}</span></label>`).join('') || '<div class="muted" style="padding:12px">No library part matches. Use free text, or add the part to the library.</div>';
  };
  ACTIONS['lm-add-lib'] = () => dialog({ title: 'Add a library part as loose material', body: `<div class="stack">
    <div class="input-wrap"><label class="sr-only" for="lm-q">Search library</label>${icon('search')}<input class="input" id="lm-q" type="search" placeholder="Search part, make or model" autocomplete="off"></div>
    <div class="pick-list" id="lm-list" role="radiogroup" aria-label="Library parts">${pickRows('')}</div>
    <div class="form form--3">${field('Quantity', input('lm-nq', '1', { num: true, mono: true }), 'A whole number, or 1 Lot.')}${field('Designation', input('lm-nt', '', { placeholder: 'e.g. SRV/OAS - HMI Software' }))}${field('Fed from', select('lm-nf', fedOptions(), ''))}</div>
    <p class="muted small">Anything that comes with the part, such as a cable or a mounting kit, is added from the library.</p></div>`,
    actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="lm-add-lib-do">Add item</button>' });
  document.addEventListener('input', (e) => { if (e.target.id === 'lm-q') $('#lm-list').innerHTML = pickRows(e.target.value); });
  ACTIONS['lm-add-lib-do'] = () => {
    const part = $('input[name="lm-part"]:checked'); const qty = $('#lm-nq').value.trim();
    if (!part) { toast('Choose a part from the list', 'error'); return; }
    if (!qty) { $('#lm-nq').setAttribute('aria-invalid', 'true'); $('#lm-nq').focus(); return; }
    snap(); const d = lib(part.value); list().push({ part: part.value, tag: $('#lm-nt').value.trim() || (d ? `${d.make} ${d.model}` : part.value), qty, fed: $('#lm-nf').value, children: '' });
    closeDialog(); S.dirty = true; S.changed.add('loose-add'); App.render(); toast(`Added ${part.value}`);
  };
  ACTIONS['lm-add-free'] = () => dialog({ title: 'Add a free-text item', body: `<div class="stack">
    <div class="form">${field('Description', input('lm-fd', '', { placeholder: 'e.g. Fibre optic patch cords, LC to LC' }), 'Printed as it is. Required.')}</div>
    <div class="form form--2">${field('Quantity', input('lm-fq', '1', { num: true, mono: true }), 'A whole number, or 1 Lot.')}${field('Designation', input('lm-ft', ''))}</div>
    ${banner('info', 'A free-text item has no part, so the sheet shows no ordering code, make or model for it, and it cannot be fed from a cabinet. An item that needs power must be added to the library first.')}</div>`,
    actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="lm-add-free-do">Add item</button>' });
  ACTIONS['lm-add-free-do'] = () => {
    const desc = $('#lm-fd').value.trim(); const qty = $('#lm-fq').value.trim();
    if (!desc) { $('#lm-fd').setAttribute('aria-invalid', 'true'); $('#lm-fd').focus(); return; }
    if (!qty) { $('#lm-fq').setAttribute('aria-invalid', 'true'); $('#lm-fq').focus(); return; }
    snap(); list().push({ free: true, part: '', desc, tag: $('#lm-ft').value.trim(), qty, fed: '', children: '' });
    closeDialog(); S.dirty = true; S.changed.add('loose-add'); App.render(); toast('Added a free-text item');
  };
  ACTIONS['lm-remove'] = (el) => {
    snap(); const items = list(); const i = +el.dataset.i; const [it] = items.splice(i, 1); S.dirty = true; S.changed.add('loose-remove'); App.render();
    toast(`Removed ${it.free ? it.desc || 'the item' : it.part}`, 'trash', () => { items.splice(i, 0, it); App.render(); });
  };

  /* ---------- Preview: the Loose Material sheet ---------- */
  App.looseSheet = () => {
    const items = list(); const title = 'PSA Panels Loose Material and Auxiliary Equipment';
    const rows = []; let sr = 1;
    items.forEach((l) => {
      const d = l.free ? null : lib(l.part);
      rows.push(`<tr><td class="num">${sr++}</td><td class="mono">${esc(l.tag || '')}</td><td>${esc(l.free ? l.desc : (d ? d.model : l.part))}</td><td class="num">${esc(l.qty)}</td><td>${esc(d ? d.make : '')}</td><td>${esc(d ? d.model : '')}</td><td class="mono">${esc(d && d.code ? d.code : (l.free ? '' : l.part))}</td></tr>`);
      if (l.children) rows.push(`<tr><td class="num">${sr++}</td><td></td><td class="muted">Comes with ${esc(l.part)}</td><td class="num">1</td><td></td><td></td><td class="mono">${esc(l.children)}</td></tr>`);
    });
    return `<div class="toolbar"><span class="muted small">Document ${esc(docLabel() || P.mainDoc)}, from ${esc(panelName(P.hostPanel || 'ws'))}.</span><span class="sp"></span><a class="btn btn--secondary btn--sm" href="#/loose">${icon('edit')}Edit the list</a></div>
      <div class="table-wrap"><table class="table"><caption class="sheet-title">${esc(title)}</caption><thead><tr><th class="num" style="width:56px">SR.NO</th><th>Tag</th><th>Description</th><th class="num" style="width:70px">Qty</th><th>Make</th><th>Model</th><th>Ordering code</th></tr></thead><tbody>${rows.join('')}</tbody></table>
      <div class="table-foot"><span>${countText(items.length)}</span><span>Printed A4 portrait, one page wide, with the cabinet sheets' header and footer.</span></div></div>`;
  };
})();
