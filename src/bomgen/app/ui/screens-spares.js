/* Screen: Spares, the Spare Parts sheet's lines (plan M64, ADR 0035). The design basis policy gives each
   line its spare quantity; this page overrides one, leaves a line out or adds an item. Each edit is one
   substation field written at once (spares_list.items, excluded, extra), so there is no save bar. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, field, input, select, pageHead, dialog, closeDialog, toast, $ } = App;
  const real = () => S.backend === 'yes' && S.project && S.project.real && S.sub;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;
  const editable = (html) => html.replace('data-dirty="1"', 'data-dirty="0"');
  const SP = { key: '', state: 'idle', data: null };
  App.onDiskChange(() => { SP.state = 'idle'; });
  function load() {
    const key = `${S.project.file}#${S.sub}`;
    if (SP.key !== key) Object.assign(SP, { key, state: 'idle', data: null });
    if (SP.state === 'idle') {
      SP.state = 'loading';
      Bridge.call('spares', S.project.file, S.sub)
        .then((d) => { if (SP.key === key) SP.data = d; }).catch((err) => toast(err.message, 'error'))
        .then(() => { if (SP.key === key) { SP.state = 'loaded'; App.render(); } });
    }
    return SP.data;
  }
  /* One field write, then the page and Preview read the files again. */
  const write = (path, value, done) => Bridge.call('set_substation_field', S.project.file, S.sub, path, value)
    .then(() => { SP.state = 'idle'; App.preview.reload(); App.render(); if (done) toast(done); })
    .catch((err) => { toast(err.message, 'error'); App.render(); });

  const policyText = (p) => {
    if (!p || !p.categories.length) return 'The design basis has no spares policy, so only the lines you set or add are listed.';
    const cats = p.categories.map((c) => `${c.replace(/_/g, ' ')} ${p.percent[c] || 0}%`).join(', ');
    return `Policy from the design basis: ${esc(cats)}, rounded up, at least ${p.minimum_per_part} per part.`;
  };

  SCREENS.spares = () => {
    if (!real()) return `<div class="page">${pageHead('Spares')}<div class="empty"><b>Open a substation first.</b></div></div>`;
    const d = load();
    if (!d) return `<div class="page">${pageHead('Spares', 'Reading the spares list…')}</div>`;
    if (d.reason) return `<div class="page">${pageHead('Spares')}${banner('bad', `<b>Nothing to show.</b> ${esc(d.reason)}.`, '<a class="btn btn--secondary btn--sm" href="#/checks">Open checks</a>')}</div>`;
    let extra = -1;
    const rows = d.lines.map((l, i) => {
      const isExtra = l.installed == null;
      if (isExtra) extra += 1;
      const spare = isExtra ? `<span class="num">${l.spare}</span>`
        : `<label class="sr-only" for="sp-${i}">Spare quantity, ${esc(l.description.split('\n')[0])}</label>${editable(input('sp-' + i, String(l.spare), { num: true, mono: true })).replace('<input', `<input data-spare="${esc(l.key)}" inputmode="numeric" style="width:72px"`)}`;
      const action = isExtra ? `<button class="btn btn--ghost btn--sm" data-action="sp-extra-remove" data-i="${extra}">${icon('trash')}Remove</button>`
        : `${l.overridden ? `<button class="btn btn--ghost btn--sm" data-action="sp-reset" data-key="${esc(l.key)}">Reset</button>` : ''}<button class="btn btn--ghost btn--sm" data-action="sp-exclude" data-key="${esc(l.key)}">Leave out</button>`;
      return `<tr><td class="num">${i + 1}</td><td class="wrap">${esc(l.description.split('\n')[0])}</td><td class="num">${l.installed == null ? '' : l.installed}</td>
        <td>${spare}</td><td>${esc(l.make || '')}</td><td class="mono">${esc(l.model || '')}</td><td class="mono">${esc(l.ordering_code || '')}</td>
        <td class="small">${esc(l.basis)}${l.overridden ? ' ' + badge('info', 'Set by hand') : ''}</td><td><div class="row-actions">${action}</div></td></tr>`;
    }).join('');
    return `<div class="page">${pageHead('Spares', `The ${esc(d.sheet_name)} sheet. ${policyText(d.policy)}`,
      `<a class="btn btn--secondary" href="#/settings/basis">Edit the policy</a><button class="btn btn--primary" data-action="sp-add">${icon('plus')}Add item…</button>`)}
      <div class="table-wrap"><table class="table"><thead><tr><th class="num">S.No</th><th>Description</th><th class="num">Installed</th><th style="width:96px">Spare</th><th>Make</th><th>Model</th><th>Ordering code</th><th>Basis</th><th style="width:190px"><span class="sr-only">Actions</span></th></tr></thead>
        <tbody>${rows || '<tr class="empty-row"><td colspan="9">No spares yet. Set a policy in the design basis, or add an item.</td></tr>'}</tbody></table>
        <div class="table-foot"><span>${plural(d.lines.length, 'line')} · type a spare quantity to set it by hand; Reset gives the policy's back</span></div></div>
      ${d.excluded.length ? `<div class="toolbar" style="margin-top:var(--space-6)"><h2>Left out</h2></div>
        <ul class="checklist">${d.excluded.map((k, i) => `<li>${icon('x')}<span class="mono">${esc(k)}</span> <button class="btn btn--ghost btn--sm" data-action="sp-include" data-i="${i}">Put back</button></li>`).join('')}</ul>` : ''}</div>`;
  };

  document.addEventListener('change', (e) => {
    const key = e.target.dataset && e.target.dataset.spare;
    if (!key) return;
    const n = Number(e.target.value);
    if (!Number.isInteger(n) || n < 0) { toast('Enter a whole number of spares, 0 or more.', 'warn'); App.render(); return; }
    write(['spares_list', 'items', key], n, 'Spare quantity set');
  });
  ACTIONS['sp-reset'] = (el) => write(['spares_list', 'items', el.dataset.key], null, 'Back to the policy');
  ACTIONS['sp-exclude'] = (el) => write(['spares_list', 'excluded'], [...SP.data.excluded, el.dataset.key], 'Left out');
  ACTIONS['sp-include'] = (el) => {
    const rest = SP.data.excluded.filter((_, i) => i !== +el.dataset.i);
    write(['spares_list', 'excluded'], rest.length ? rest : null, 'Put back');
  };
  ACTIONS['sp-extra-remove'] = (el) => {
    const rest = SP.data.extra.filter((_, i) => i !== +el.dataset.i);
    write(['spares_list', 'extra'], rest.length ? rest : null, 'Item removed');
  };
  ACTIONS['sp-add'] = () => {
    const parts = [['', 'Free text (no library part)'], ...SP.data.parts.map((p) => [p.part_id, `${p.part_id}: ${p.description}`])];
    dialog({ title: 'Add a spare item', body: `<div class="form">
      ${field('Library part', editable(select('sa-part', parts, '')))}
      ${field('Description', editable(input('sa-desc', '', { placeholder: 'For a free-text item, e.g. Fuse kit' })))}
      ${field('Spare quantity', editable(input('sa-qty', '1', { num: true, mono: true })))}<div id="sa-err"></div></div>`,
      actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="sp-add-do">Add item</button>' });
  };
  ACTIONS['sp-add-do'] = () => {
    const part = $('#sa-part').value, desc = $('#sa-desc').value.trim(), qty = Number($('#sa-qty').value);
    const err = (m) => { $('#sa-err').innerHTML = banner('bad', esc(m)); };
    if (!Number.isInteger(qty) || qty < 1) { err('Enter a whole number of spares, 1 or more.'); return; }
    if (!part && !desc) { err('Pick a library part or describe the item.'); return; }
    const item = part ? { part_id: part, qty } : { description: desc, qty };
    closeDialog();
    write(['spares_list', 'extra'], [...SP.data.extra, item], 'Item added');
  };
})();
