/* Screens: the network Result card on Parts, and the Panels board and list, on bomgen.app.api (plan M10c).
   Every figure comes from substation_layout, which flattens M1c's layout_preview; this file only draws it.
   Moves, pins and deletes write layout.overrides and layout.removed at once through the bridge's
   writers, which refuse what the layout cannot take (docs/ui/editing.md, Panels board). */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, pageHead, toast, dialog, closeDialog, $ } = App;
  const $$ = (q) => [...document.querySelectorAll(q)];
  const real = () => S.backend === 'yes' && S.project && S.project.real && S.sub;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;
  const U = 18; // px per rack unit on the board, as in the design prototype
  /* Only generated panels follow pins and deletes; Build uses hand-written panel files as they are. */
  const editable = () => !!(LAY.data && LAY.data.generated);
  const READ_ONLY = 'These panels are hand-written, so Build uses your panel files and a pin or delete here would not change the BOM.';

  /* ---------- data: one layout per (project file, substation id) ---------- */
  const LAY = { key: '', state: 'idle', data: null, error: null };
  function layout() {
    const key = `${S.project.file}#${S.sub}`;
    if (LAY.key !== key) { Object.assign(LAY, { key, state: 'idle', data: null, error: null }); selected = ''; showIssues = false; history.length = 0; refusal = ''; showChanges = false; }
    if (LAY.state === 'idle') {
      LAY.state = 'loading';
      const current = () => LAY.key === key;
      Bridge.call('substation_layout', S.project.file, S.sub)
        .then((d) => { if (current()) LAY.data = d; }).catch((err) => { if (current()) { LAY.error = err; toast(err.message, 'error'); } })
        .then(() => { if (current()) { LAY.state = 'loaded'; App.render(); } });
    }
    return LAY.state === 'loaded' ? LAY : null;
  }

  /* ---------- Result card (called from screens-parts.js) ---------- */
  function resultCard() {
    const l = layout();
    if (!l || !l.data) return `<div class="card"><h3>Result</h3><p class="row" style="margin-top:var(--space-3)"><span class="spinner"></span>Calculating…</p></div>`;
    const d = l.data, p = d.plan;
    if (!p) return `<div class="card"><h3>Result</h3><p class="muted small" style="margin-top:var(--space-2)">${esc(d.reason || 'Appears when the IED count and the equipment are set.')}</p></div>`;
    const ring = p.topology === 'ring';
    const row = (label, v) => `<tr><td>${label}</td><td class="num">${v}</td></tr>`;
    return `<div class="card"><h3>Result</h3><p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">Worked out by the engine. Read-only.</p>
      <table class="table table--plain"><thead><tr><th></th><th class="num">Each side</th></tr></thead><tbody>
        ${row('L1 switches', `<b>${p.l1_per_side}</b>`)}${row('L2 switches', `<b>${p.l2_per_side}</b>`)}
        ${row('L2 ports in use', `${p.l2_demand_per_side} of ${p.l2_usable_ports * p.l2_per_side}`)}${row(ring ? 'Rings' : 'L1 to L2 links', ring ? p.rings_per_side : p.l1_links_per_side)}</tbody></table>
      <p class="small" style="margin-top:var(--space-3)">L1 model: <span class="mono">${esc(p.l1_part_id)}</span>${p.l1_pinned ? ' (pinned)' : ''}. L2 model: <span class="mono">${esc(p.l2_part_id)}</span>.</p>
      <p class="small" style="margin-top:var(--space-2)">${p.ied_count} field IEDs need ${plural(p.l1_per_side, 'L1 switch')} on each side, ${p.l1_usable_ports} usable ports each.</p>
      <p class="muted small" style="margin-top:var(--space-2)">${ring ? 'Rings: two ports close each ring.' : 'Star: each L1 switch has one uplink to its L2 switch plus an A–B interlink.'}</p>
      <a class="btn btn--secondary btn--sm" href="#/panels" style="margin-top:var(--space-3)">${icon('panels')}See the panels</a></div>`;
  }
  App.network = { resultCard, reload: () => { LAY.state = 'idle'; } };  // after a Parts input is saved

  /* ---------- Panels ---------- */
  let selected = '';  // `${panel}:${key}:${side}` of the selected unit
  const ROLES = { fopp: 'Fibre patch panel', l2_switch: 'L2 switch', l1_switch: 'L1 switch', ext_switch: 'External switch', firewall: 'Firewall' };
  const name = (u) => (ROLES[u.role] ? `${ROLES[u.role]}${u.of > 1 ? ' ' + u.n : ''}` : u.label);
  const uid = (p, u) => `${p.number}:${u.key}:${u.side || ''}`;
  let showIssues = false;
  const HELP = 'Blank plates are the gaps under a device that has no cable manager below it. They are not in the BOM. A switch, firewall or patch panel counts with its 1 U cable manager.';
  const issueList = (xs) => `<ul style="margin:6px 0 0;padding-left:18px">${xs.slice(0, 8).map((i) => `<li><span class="mono small">${esc(i.subject)}</span> ${esc(i.message)}</li>`).join('')}</ul>`;
  const issuesBanner = (d) => {
    if (!d.generated) {  // one banner: what the board is, and what the layout would report
      const n = d.issues.length;
      return `<div style="margin-bottom:var(--space-3)">${banner('info', `<b>Hand-written panels.</b> The board shows what <span class="mono">bomgen layout</span> would write; Build uses your panel files.${n && showIssues ? `<div style="margin-top:6px">Running it would report ${plural(n, 'problem')}:</div>${issueList(d.issues)}` : ''}`,
        (n ? `<button class="btn btn--secondary btn--sm" data-action="pv-issues" aria-expanded="${showIssues}">${showIssues ? 'Hide' : `Show ${plural(n, 'problem')}`}</button>` : '')
        + (d.panels.length ? '<button class="btn btn--secondary btn--sm" data-action="pv-generate">Lay out panels from the equipment</button>' : ''))}</div>`;
    }
    const errors = d.issues.filter((i) => i.level === 'error'), warnings = d.issues.filter((i) => i.level === 'warning');
    return (errors.length ? `<div style="margin-bottom:var(--space-3)">${banner('bad', `<b>${plural(errors.length, 'layout error')}.</b> Build is blocked until they are fixed.${issueList(errors)}`, '<a class="btn btn--secondary btn--sm" href="#/checks">Open checks</a>')}</div>` : '')
      + (warnings.length ? `<div style="margin-bottom:var(--space-3)">${banner('warn', `<b>${plural(warnings.length, 'layout warning')}.</b>${issueList(warnings)}`)}</div>` : '');
  };
  ACTIONS['pv-issues'] = () => { showIssues = !showIssues; App.render(); };

  SCREENS.panels = () => {
    if (!real()) return `<div class="page">${pageHead('Panels')}<div class="empty"><b>Open a substation first.</b></div></div>`;
    const { b } = App.route();
    if (b) return `<div class="page">${pageHead('Panel', 'The panel editor comes with the substation writers.')}<a class="btn btn--secondary" href="#/panels">Back to the panels</a></div>`;
    const l = layout();
    if (!l || !l.data) return `<div class="page">${pageHead('Panels', l && l.error ? esc(l.error.message) : 'Laying out the panels…')}</div>`;
    const d = l.data;
    if (d.reason) return `<div class="page">${pageHead('Panels', 'Laid out from the equipment and network.')}${banner('bad', `<b>No layout.</b> ${esc(d.reason)}.`, '<a class="btn btn--secondary btn--sm" href="#/checks">Open checks</a>')}</div>`;
    const t = ['board', 'list'].includes(S.tab.panels) ? S.tab.panels : 'board';
    return `<div class="page page--wide">${pageHead('Panels', d.generated ? 'Placed by the engine from the equipment and network. Drag a device to another panel or position, or pin it where it is. A pair moves together; hold Alt to move one unit.' : 'Laid out by the engine from the equipment and network.', history.length ? `<button class="btn btn--secondary" data-action="pv-undo">${icon('undo')}Undo</button>` : '')}
      ${tabs('panels', [['board', 'Board'], ['list', 'List']], t, 'Panels view')}
      <div role="tabpanel" aria-labelledby="tab-panels-${t}" style="margin-top:var(--space-4)">${t === 'board' ? board(d) : list(d)}</div></div>`;
  };

  function board(d) {
    if (!d.panels.length) return `<div class="empty" style="max-width:640px"><b>No panels yet.</b><div class="muted small" style="margin:var(--space-1) 0 var(--space-3)">Panels are placed once the network has an IED count and equipment.</div><a class="btn btn--primary" href="#/parts">${icon('parts')}Open Parts</a></div>`;
    let sel = null;
    learn(d);
    d.panels.forEach((p) => p.units.forEach((u) => { if (uid(p, u) === selected) sel = { p, u }; }));
    const changes = d.overrides.length + d.removed.length;
    const pairs = [...new Set(d.panels.map((p) => p.pair))];
    return `<div class="board-wrap${busy ? ' is-busy' : ''}" aria-busy="${busy}">
      ${refusal ? `<div style="margin-bottom:var(--space-3)">${banner('bad', `<b>Not moved.</b> ${esc(refusal)} Nothing was changed.`, '<button class="btn btn--ghost btn--icon btn--sm" data-action="pv-refusal-close" aria-label="Close">' + icon('x') + '</button>')}</div>` : ''}
      ${issuesBanner(d)}
      <div class="board-bar" role="status" aria-live="polite">
        ${sel ? `<div class="sel-bar"><span><b>${esc(name(sel.u))}</b> <span class="mono muted">${esc(sel.u.part_id)}</span> ${esc(sel.u.label)} · ${sel.u.side ? 'Side ' + sel.u.side : 'Common'} · ${sel.u.height_u} U${sel.u.cable_manager_u ? ` + ${sel.u.cable_manager_u} U cable manager` : ''} · ${esc(sel.p.cabinet_name)}${sel.u.pinned ? ' · pinned' : ''}</span><span class="sp"></span>
          ${!d.generated ? '' : sel.u.pinned ? `<button class="btn btn--ghost btn--sm" data-action="pv-unpin">${icon('pin')}Unpin</button>` : `<button class="btn btn--ghost btn--sm" data-action="pv-pin">${icon('pin')}Pin here</button>`}
          ${d.generated ? `<button class="btn btn--ghost btn--sm" data-action="pv-move" aria-keyshortcuts="Alt+ArrowUp Alt+ArrowDown Alt+ArrowLeft Alt+ArrowRight">${icon('move')}Move…</button>
          <button class="btn btn--ghost btn--sm" data-action="pv-delete">${icon('trash')}Delete${sel.u.side ? ' pair' : ''}</button>` : ''}
          <button class="btn btn--ghost btn--icon btn--sm" data-action="pv-clear-sel" aria-label="Clear selection">${icon('x')}</button></div>`
          : `<div class="row board-hint"><span class="muted small">Select a device to see its part and size.</span><span class="board-help" tabindex="0" role="img" aria-label="${esc(HELP)}" title="${esc(HELP)}">${icon('help')}</span><span class="sp"></span>${changes ? `<button class="btn btn--ghost btn--sm" data-action="pv-changes" aria-expanded="${showChanges}">${[d.overrides.length ? `${d.overrides.length} pinned` : '', d.removed.length ? `${d.removed.length} deleted` : ''].filter(Boolean).join(' · ')}${icon('chevd')}</button>` : '<span class="muted small">Nothing pinned or deleted</span>'}</div>`}
      </div>
      ${d.generated ? '' : `<p class="muted small" style="margin-bottom:var(--space-3)">${READ_ONLY}</p>`}
      ${changes && showChanges ? changesList(d) : ''}
      <div class="board" role="group" aria-label="Panels">${pairs.map((k) => { const cols = d.panels.filter((p) => p.pair === k); return `<div class="pair"><div class="pair-head">Pair ${k} <span class="muted">· panels ${cols.map((p) => p.number).join(' and ')}</span></div><div class="pair-cols">${cols.map((p) => column(p, d.reserved_u, sel, d.generated)).join('')}</div></div>`; }).join('')}</div>
      <p class="muted small" style="margin-top:var(--space-3)">${plural(d.panels.length, 'panel')} from the layout${d.list.some((p) => p.manual) ? `, ${d.list.filter((p) => p.manual).length} hand-written (${d.list.filter((p) => p.manual).map((p) => esc(p.cabinet_name)).join(', ')})` : ''}.</p></div>`;
  }

  function column(p, reserved, sel, movable) {
    const pct = Math.round((p.used_u / p.capacity_u) * 100);
    const rack = p.units.filter((u) => u.block_u > 0);
    const partner = sel && sel.u.side ? `${sel.u.key}:${sel.u.side === 'A' ? 'B' : 'A'}` : '';
    const cards = [];
    rack.forEach((u) => {
      const id = uid(p, u), isSel = id === selected, isPartner = partner && `${u.key}:${u.side}` === partner;
      cards.push(`<div class="dev ${u.cable_manager_u ? 'has-cm' : ''} ${isSel ? 'is-sel' : ''} ${isPartner ? 'is-partner' : ''} ${u.pinned ? 'is-pinned' : ''} ${movable ? 'is-movable' : ''}" tabindex="0" role="button" aria-pressed="${isSel}" data-action="pv-select-dev" data-uid="${esc(id)}" style="height:${u.block_u * U}px"
        aria-label="${esc(name(u))}${u.side ? ', side ' + u.side : ', common'}, ${u.block_u} U${u.cable_manager_u ? ' including a 1 U cable manager' : ''}${u.pinned ? ', pinned by an override' : ''}" title="${esc(u.part_id)} · ${esc(u.label)}">
        <span class="dev-row" style="height:${u.height_u * U - 2}px">${movable ? `<span class="dev-grip">${icon('grip')}</span>` : ''}<span class="dev-main"><b>${esc(name(u))}</b>${u.height_u >= 2 ? `<span class="mono">${esc(u.part_id)}</span>` : ''}</span>${u.pinned ? `<span class="dev-flag" title="Pinned by an override: stays here when the network changes">${icon('pin')}</span>` : ''}<span class="dev-u">${u.height_u} U</span></span>${u.cable_manager_u ? `<span class="dev-cm">Cable manager<span class="dev-u">${u.cable_manager_u} U</span></span>` : ''}</div>`);
      if (u.plate_below_u) cards.push(`<div class="plate" style="height:${u.plate_below_u * U}px" title="Blank plate (not in the BOM)"></div>`);
    });
    const din = p.units.filter((u) => u.block_u === 0);
    return `<section class="bcol" data-panel="${p.number}" aria-label="${esc(p.cabinet_name)}, side ${esc(p.side || '')}, ${p.used_u} of ${p.capacity_u} U used">
      <header><b title="${esc(p.cabinet_name)}">${esc(p.cabinet_name)}</b>${p.side ? `<span class="badge badge--plain">Side ${esc(p.side)}</span>` : ''}</header>
      <div class="umeter ${p.free_u < 3 ? 'is-full' : ''}" role="img" aria-label="${p.used_u} of ${p.capacity_u} U used"><i style="width:${Math.min(100, pct)}%"></i></div>
      <div class="ulabel"><b>${p.used_u}</b> of ${p.capacity_u} U used · ${p.free_u} U free</div>
      <div class="rack">${cards.join('')}${p.free_u > 0 ? `<div class="freeu" style="height:${p.free_u * U}px">${p.free_u} U free</div>` : ''}${reserved ? `<div class="reserve" style="height:${reserved * U}px"><span>${reserved} U kept free for expansion</span></div>` : ''}</div>
      <footer title="${esc(din.map(name).join(', '))}">${plural(p.din_rail, 'DIN-rail part')} · no rack space</footer></section>`;
  }

  function list(d) {
    const used = Object.fromEntries(d.panels.map((p) => [p.id, p]));
    return `<div class="table-wrap"><table class="table table--comfort"><thead><tr><th>Sheet</th><th>Cabinet</th><th>Name</th><th>Written by</th><th>Side</th><th class="num">Rack space</th></tr></thead>
      <tbody>${d.list.map((p) => { const lp = p.generated ? used[p.id] : null; return `<tr><td class="mono">${esc(p.sheet)}</td><td class="mono">${esc(p.cabinet_number)}</td><td><b style="font-weight:500">${esc(p.cabinet_name)}</b></td>
        <td>${p.generated ? 'Layout' : p.manual ? 'Hand-written (manual)' : 'Hand-written'}</td><td>${p.side ? 'Side ' + esc(p.side) : '—'}</td><td class="num">${lp ? `${lp.used_u} of ${lp.capacity_u} U` : '—'}</td></tr>`; }).join('')}</tbody></table>
      <div class="table-foot"><span>One sheet per cabinet, in the order shown</span></div></div>`;
  }

  /* ---------- writing: pins, moves and deletes (docs/ui/editing.md, Panels board) ---------- */
  let busy = false, refusal = '', showChanges = false;
  const history = [];  // {overrides, removed} before each write, for Undo
  const unitOf = (id) => { for (const p of LAY.data.panels) for (const u of p.units) if (uid(p, u) === id) return { p, u }; return null; };
  const seen = {};  // device id -> {name, of}, kept so a deleted device still has its name
  const learn = (d) => d.panels.forEach((p) => p.units.forEach((u) => { seen[u.device] = { name: ROLES[u.role] || u.label, of: u.of }; }));
  const deviceName = (device) => (seen[device] ? seen[device].name : device);
  const nth = (device, unit) => (unit && (!seen[device] || seen[device].of > 1) ? ' ' + unit : '');
  const lower = (side) => (side ? side.toLowerCase() : null);
  /* An override that places this unit: its pair move, or a move of the unit itself. */
  const places = (o, u, alone) => (o.pair === u.device && (o.unit == null || o.unit === u.n) && !alone)
    || (o.device === u.device && (o.unit == null || o.unit === u.n) && (!o.side || !u.side || o.side === lower(u.side)));
  const pairPanels = (n) => (n % 2 ? [n, n + 1] : [n - 1, n]);
  const sideFits = (u, n) => !u.side || (u.side === 'A') === (n % 2 === 1);  // A units in odd panels, B in even
  const moveOf = (u, n, position, alone) => (u.side && !alone
    ? { pair: u.device, unit: u.n, panel: pairPanels(n), position }
    : { device: u.device, unit: u.n, side: alone ? lower(u.side) : null, panel: n, position });
  const describe = (o) => {
    const at = o.position ? `, position ${o.position}` : '';
    return o.pair ? `${deviceName(o.pair)}${nth(o.pair, o.unit)} (pair) to panels ${o.panel[0]} and ${o.panel[1]}${at}`
      : `${deviceName(o.device)}${nth(o.device, o.unit)}${o.side ? ' side ' + o.side.toUpperCase() : ''} to panel ${o.panel}${at}`;
  };
  const sentence = (t) => { const x = String(t).replace(/^./, (m) => m.toUpperCase()); return /[.!?]$/.test(x) ? x : x + '.'; };
  const unitName = (r) => `${deviceName(r.device)}${nth(r.device, r.unit)}${r.side ? ' side ' + r.side.toUpperCase() : ''}`;

  /* Write overrides and/or removed; the bridge refuses what the layout cannot take. */
  function write(change, said, undoable = true, ic = 'pin') {
    if (!editable()) return Promise.resolve(false);
    const d = LAY.data, before = { overrides: d.overrides, removed: d.removed };
    const calls = [];
    if (change.overrides) calls.push(() => Bridge.call('set_layout_overrides', S.project.file, S.sub, change.overrides));
    if (change.removed) calls.push(() => Bridge.call('set_layout_removed', S.project.file, S.sub, change.removed));
    busy = true; refusal = ''; App.render();
    let chain = Promise.resolve(null);
    calls.forEach((call) => { chain = chain.then((prev) => (prev && !prev.written ? prev : call())); });
    return chain.then((reply) => {
      if (reply.written) {
        LAY.data = reply.page; App.devicePreview.reload();  // the preview shows the new pins on its next visit
        if (undoable) history.push(before);
        if (said) toast(said, ic, undoable ? () => ACTIONS['pv-undo']() : null);
      } else {
        refusal = sentence((reply.issues[0] && reply.issues[0].message) || 'The layout cannot take this change');
      }
      return reply.written;
    }).catch((err) => { toast(err.message, 'error'); return false; }).then((written) => { busy = false; App.render(); return written; });
  }
  ACTIONS['pv-undo'] = () => {
    const last = history.pop(); if (!last || busy) return;
    const d = LAY.data, change = {};
    if (JSON.stringify(last.overrides) !== JSON.stringify(d.overrides)) change.overrides = last.overrides;
    if (JSON.stringify(last.removed) !== JSON.stringify(d.removed)) change.removed = last.removed;
    write(change, 'Change undone', false, 'undo');
  };
  ACTIONS['pv-refusal-close'] = () => { refusal = ''; App.render(); };
  ACTIONS['pv-changes'] = () => { showChanges = !showChanges; App.render(); };
  ACTIONS['pv-pin'] = () => {
    const sel = unitOf(selected); if (!sel) return;
    const o = moveOf(sel.u, sel.p.number, sel.u.position, false);  // the position too, so the pin holds where it is
    write({ overrides: [...LAY.data.overrides.filter((x) => !places(x, sel.u, false)), o] }, `Pinned ${describe(o)}`);
  };
  ACTIONS['pv-unpin'] = () => {
    const sel = unitOf(selected); if (!sel) return;
    write({ overrides: LAY.data.overrides.filter((x) => !places(x, sel.u, false)) }, `Unpinned ${name(sel.u)}. The layout places it again.`);
  };
  ACTIONS['pv-unpin-at'] = (el) => { const d = LAY.data, o = d.overrides[+el.dataset.i]; write({ overrides: d.overrides.filter((_, i) => i !== +el.dataset.i) }, `Unpinned ${describe(o)}`); };
  ACTIONS['pv-restore-at'] = (el) => { const d = LAY.data, r = d.removed[+el.dataset.i]; write({ removed: d.removed.filter((_, i) => i !== +el.dataset.i) }, `Restored ${unitName(r)}`); };
  ACTIONS['pv-delete'] = () => {
    const sel = unitOf(selected); if (!sel) return;
    const u = sel.u, r = { device: u.device, unit: u.n };
    selected = '';
    write({ removed: [...LAY.data.removed, r], overrides: LAY.data.overrides.filter((x) => !places(x, u, false)) }, `Deleted ${name(u)}${u.side ? ' (both units)' : ''} from the BOM`, true, 'trash');
  };
  ACTIONS['pv-reset'] = () => {
    const d = LAY.data;
    dialog({ title: 'Reset to automatic?', body: `<p>This releases ${[d.overrides.length ? plural(d.overrides.length, 'pin') : '', d.removed.length ? plural(d.removed.length, 'deleted device') : ''].filter(Boolean).join(' and ')}. The layout then places every device again. You can undo it.</p>`,
      actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="pv-reset-go">Reset to automatic</button>' });
  };
  /* Hand-written panels to generated ones: the bridge copies the files it replaces first. */
  ACTIONS['pv-generate'] = () => {
    const d = LAY.data, ids = d.panels.map((p) => p.id);
    const replaced = d.list.filter((p) => !p.generated && !p.manual && ids.includes(p.id));
    const dropped = d.list.filter((p) => !p.generated && !p.manual && !ids.includes(p.id));
    dialog({ title: 'Lay out panels from the equipment?', body: `<p>${replaced.length ? `This replaces ${plural(replaced.length, 'hand-written panel file')} with panels` : 'This writes the panels'} laid out from the equipment. ${replaced.length ? 'Copies are kept in <span class="mono">panels/hand-written-…/</span>.' : ''}</p>
      ${dropped.length ? `<p>${dropped.map((p) => esc(p.cabinet_name)).join(', ')} ${dropped.length === 1 ? 'is' : 'are'} no longer listed, so ${dropped.length === 1 ? 'it leaves' : 'they leave'} the BOM; the ${dropped.length === 1 ? 'file stays' : 'files stay'}.</p>` : ''}
      <p>The board can then move, pin and delete devices.</p>`,
      actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="pv-generate-go">Lay out panels</button>' });
  };
  ACTIONS['pv-generate-go'] = () => {
    closeDialog();
    busy = true; App.render();
    Bridge.call('generate_panels', S.project.file, S.sub).then((r) => {
      LAY.data = r.page; history.length = 0; showIssues = false; App.devicePreview.reload();
      toast(`Laid out ${plural(r.written.length, 'panel')}.${r.backup ? ` Hand-written files copied to panels/${r.backup.split(/[\\/]/).pop()}.` : ''}`);
    }).catch((err) => toast(err.message, 'error')).then(() => { busy = false; App.render(); });
  };
  ACTIONS['pv-reset-go'] = () => { closeDialog(); showChanges = false; write({ overrides: [], removed: [] }, 'Reset to automatic'); };
  function changesList(d) {
    const act = (a, i, t) => (d.generated ? `<button class="btn btn--ghost btn--sm" data-action="${a}" data-i="${i}">${t}</button>` : '');
    const rows = [...d.overrides.map((o, i) => `<li><span>${icon('pin')}Pinned ${esc(describe(o))}</span>${act('pv-unpin-at', i, 'Unpin')}</li>`),
      ...d.removed.map((r, i) => `<li><span>${icon('trash')}Deleted ${esc(unitName(r))}</span>${act('pv-restore-at', i, 'Restore')}</li>`)];
    return `<div style="margin-bottom:var(--space-3)"><ul class="changes">${rows.join('')}</ul>${d.generated ? '<div class="row" style="justify-content:flex-end;margin-top:var(--space-2)"><button class="btn btn--secondary btn--sm" data-action="pv-reset">Reset to automatic</button></div>' : ''}</div>`;
  }

  /* ---------- drag and drop: the bridge says which panels can take the move ---------- */
  let drag = null;  // { id, u, from, alone, fits: {panel: true|false|undefined}, why, at: {panel, index}, el }
  const onBoard = () => real() && LAY.data && !LAY.data.reason && editable() && (S.tab.panels || 'board') === 'board';
  const others = (u, alone) => LAY.data.overrides.filter((x) => !places(x, u, alone));
  function probe(n) {
    const u = drag.u;
    if (!sideFits(u, n)) { drag.fits[n] = false; return; }
    const d = drag, move = moveOf(u, n, null, d.alone);
    Bridge.call('check_layout', S.project.file, S.sub, [...others(u, d.alone), move], LAY.data.removed)
      .then((r) => { if (drag === d) { d.fits[n] = r.fits; d.why[n] = r.issues[0] ? r.issues[0].message : ''; paint(); } }).catch(() => {});
  }
  function clearMarks() { document.body.classList.remove('is-drop-bad'); $$('.bcol.drop-ok, .bcol.drop-bad').forEach((x) => x.classList.remove('drop-ok', 'drop-bad')); $$('.dev.ins-before, .dev.ins-after').forEach((x) => x.classList.remove('ins-before', 'ins-after')); }
  function paint() {
    clearMarks();
    if (!drag || !drag.at) return;
    const n = drag.at.panel, cols = drag.u.side && !drag.alone ? pairPanels(n) : [n];
    const ok = drag.fits[n];
    document.body.classList.toggle('is-drop-bad', ok === false);  // the captured block sets the cursor, so say it on the body
    cols.forEach((k) => { const c = document.querySelector(`.bcol[data-panel="${k}"]`); if (c && ok !== undefined) c.classList.add(ok ? 'drop-ok' : 'drop-bad'); });
    if (ok) { const devs = [...document.querySelectorAll(`.bcol[data-panel="${n}"] .dev`)]; const i = drag.at.index; if (devs[i]) devs[i].classList.add('ins-before'); else if (devs.length) devs[devs.length - 1].classList.add('ins-after'); }
  }
  /* The shared pointer drag (drag.js): a press becomes a drag after 4 px; Alt moves one unit of a pair. */
  function startDrag(el, e) {
    const sel = unitOf(el.dataset.uid); if (!sel) return false;
    drag = { id: el.dataset.uid, u: sel.u, from: sel.p.number, alone: e.altKey && !!sel.u.side, fits: {}, why: {}, at: null, el };
    el.classList.add('is-dragging'); document.body.classList.add('is-dragging-dev');
    LAY.data.panels.forEach((x) => probe(x.number));
    return true;
  }
  function moveDrag(e) {
    const under = document.elementFromPoint(e.clientX, e.clientY);
    const col = under && under.closest('.bcol[data-panel]'); if (!col) { drag.at = null; paint(); return; }
    const n = +col.dataset.panel, devs = [...col.querySelectorAll('.dev')];
    const index = devs.filter((x) => { const r = x.getBoundingClientRect(); return r.top + r.height / 2 < e.clientY; }).length;  // the gap under the pointer
    drag.at = { panel: n, index };
    paint();
  }
  /* Ends a drag; only a drop that was not cancelled writes. A refused drop still lands, so the banner can say why. */
  function endDrag(cancelled) {
    const d = drag; drag = null;
    clearMarks();
    $$('.dev.is-dragging').forEach((x) => x.classList.remove('is-dragging')); document.body.classList.remove('is-dragging-dev');
    if (cancelled || !d.at) return;
    const n = d.at.panel, u = d.u;
    const devs = [...document.querySelectorAll(`.bcol[data-panel="${n}"] .dev`)];
    const own = devs.findIndex((x) => x.dataset.uid === d.id);
    let position = d.at.index + 1;
    if (own >= 0 && own < d.at.index) position -= 1;  // the unit leaves its own place first
    if (n === d.from && position === u.position) return;  // dropped where it is
    if (d.fits[n] === false) { refusal = d.why[n] ? sentence(d.why[n]) : (sideFits(u, n) ? `Panel ${n} cannot take ${name(u)}.` : `A side ${u.side} unit goes in ${u.side === 'A' ? 'an odd' : 'an even'} panel.`); App.render(); return; }
    const move = moveOf(u, n, position, d.alone);
    write({ overrides: [...others(u, d.alone), move] }, `Pinned ${describe(move)}`);
  }
  App.pointerDrag({ handle: '.dev.is-movable[data-uid]', enabled: () => onBoard() && !busy, start: startDrag, move: moveDrag, drop: () => endDrag(false), cancel: () => endDrag(true) });

  /* ---------- keyboard moves and Move… (docs/ui/editing.md, Keyboard) ---------- */
  const panelOf = (n) => LAY.data.panels.find((p) => p.number === n);
  const rackCount = (n) => { const p = panelOf(n); return p ? p.units.filter((x) => x.block_u > 0).length : 0; };
  const landsIn = (u, n, alone) => (u.side && !alone ? pairPanels(n)[u.side === 'A' ? 0 : 1] : n);  // the panel this unit ends up in
  function focusSelected() { const n = selected && $(`[data-uid="${CSS.escape(selected)}"]`); if (n) n.focus(); }
  /* Pin u at panel n (the pair's panels for a pair) and position; the selection follows the unit. */
  function moveTo(u, from, n, position, alone) {
    if (n === from && position === u.position) return;
    const move = moveOf(u, n, position, alone), id = `${landsIn(u, n, alone)}:${u.key}:${u.side || ''}`;
    write({ overrides: [...others(u, alone), move] }, `Pinned ${describe(move)}`).then((written) => {
      if (written) { selected = id; App.render(); }
      focusSelected();
    });
  }
  function keyMove(key) {
    const sel = unitOf(selected); if (!sel || busy) return;
    const { p, u } = sel;
    if (key === 'ArrowUp' || key === 'ArrowDown') {
      const position = u.position + (key === 'ArrowUp' ? -1 : 1);
      if (position >= 1 && position <= rackCount(p.number)) moveTo(u, p.number, p.number, position, false);
      return;
    }
    const step = (key === 'ArrowLeft' ? -1 : 1) * (u.side ? 2 : 1), n = p.number + step;  // a pair moves to the neighbouring pair
    if (panelOf(n) && (!u.side || panelOf(pairPanels(n)[0]) && panelOf(pairPanels(n)[1]))) moveTo(u, p.number, n, null, false);
    else toast(`There is no panel ${key === 'ArrowLeft' ? 'before' : 'after'} ${u.side ? 'this pair' : 'this one'}.`, 'info');
  }

  /* The Move… dialog: every destination, with panels that cannot take the unit greyed out and the reason. */
  let mv = null;  // { u, from, alone, where, fits: {n: bool}, why: {n: text}, after: {n: text} }
  const WHERE = [['auto', 'Where the layout puts it'], ['top', 'At the top'], ['bottom', 'At the bottom']];
  const dests = (m) => (m.u.side && !m.alone
    ? [...new Set(LAY.data.panels.map((p) => pairPanels(p.number)[0]))].filter((n) => panelOf(n) && panelOf(n + 1))
    : LAY.data.panels.map((p) => p.number));
  const destName = (m, n) => (m.u.side && !m.alone ? `Panels ${n} and ${n + 1}` : `Panel ${n}`);
  const here = (m, n) => landsIn(m.u, n, m.alone) === m.from;
  function moveBody(m) {
    const side = m.u.side;
    return `<p>Pin <b>${esc(name(m.u))}</b>${side && !m.alone ? ' and its partner' : ''} to another panel or position.</p>
      <fieldset class="mv-where"><legend class="small muted">Position</legend>${WHERE.map(([k, t]) => `<label class="check"><input type="radio" name="mv-where" value="${k}" data-action="pv-move-where" ${m.where === k ? 'checked' : ''}> ${t}</label>`).join('')}</fieldset>
      ${side ? `<label class="check" style="margin-top:var(--space-2)"><input type="checkbox" data-action="pv-move-alone" ${m.alone ? 'checked' : ''}> Move this unit only (side ${esc(side)})</label>` : ''}
      <ul class="changes mv-dests" style="margin-top:var(--space-3)">${dests(m).map((n) => { const p = panelOf(landsIn(m.u, n, m.alone)); return `<li data-n="${n}"><span><b>${destName(m, n)}</b><span class="muted small">${esc(p ? p.cabinet_name : '')}${here(m, n) ? ' · here now' : ''}</span><span class="mv-why small"></span></span><button class="btn btn--secondary btn--sm" data-action="pv-move-go" data-n="${n}" disabled>Move here</button></li>`; }).join('')}</ul>`;
  }
  function paintMove() {
    if (!mv) return;
    $$('.mv-dests li[data-n]').forEach((li) => {
      const n = +li.dataset.n, ok = mv.fits[n], btn = li.querySelector('button'), why = li.querySelector('.mv-why');
      btn.disabled = ok !== true || stays(mv, n);
      li.classList.toggle('is-off', ok === false);
      why.textContent = ok === undefined ? 'Checking…' : ok ? mv.after[n] : mv.why[n];
    });
  }
  const positionOf = (m, n) => ({ auto: null, top: 1, bottom: rackCount(landsIn(m.u, n, m.alone)) + (here(m, n) ? 0 : 1) }[m.where]);
  /* Moving to where it is changes nothing unless the position does. */
  const stays = (m, n) => here(m, n) && (m.where === 'auto' ? !m.u.pinned : positionOf(m, n) === m.u.position);
  const afterText = (m, n, panels) => {
    const used = (m.u.side && !m.alone ? [n, n + 1] : [n]).map((k) => panels.find((p) => p.number === k)).filter(Boolean);
    return used.length ? `After: ${used.map((p) => p.used_u + ' U').join(' and ')} of ${used[0].capacity_u} U` : '';
  };
  function probeMove() {
    const m = mv;
    dests(m).forEach((n) => {
      if (!sideFits(m.u, n)) { m.fits[n] = false; m.why[n] = `A side ${m.u.side} unit goes in ${m.u.side === 'A' ? 'an odd' : 'an even'} panel.`; return; }
      Bridge.call('check_layout', S.project.file, S.sub, [...others(m.u, m.alone), moveOf(m.u, n, null, m.alone)], LAY.data.removed)
        .then((r) => { if (mv === m) { m.fits[n] = r.fits; m.why[n] = r.issues[0] ? sentence(r.issues[0].message) : ''; m.after[n] = afterText(m, n, r.panels); paintMove(); } })
        .catch((err) => { if (mv === m) { m.fits[n] = false; m.why[n] = err.message; paintMove(); } });
    });
    paintMove();
  }
  ACTIONS['pv-move'] = () => {
    const sel = unitOf(selected); if (!sel || busy) return;
    mv = { u: sel.u, from: sel.p.number, alone: false, where: 'auto', fits: {}, why: {}, after: {} };
    dialog({ title: `Move ${esc(name(sel.u))}`, body: moveBody(mv), actions: '<button class="btn btn--secondary" data-action="close">Cancel</button>' });
    probeMove();
  };
  ACTIONS['pv-move-where'] = (el) => { if (mv) { mv.where = el.value; paintMove(); } };
  ACTIONS['pv-move-alone'] = (el) => {
    if (!mv) return;
    Object.assign(mv, { alone: el.checked, fits: {}, why: {}, after: {} });
    $('.dialog .body').innerHTML = moveBody(mv);
    $('.dialog [data-action="pv-move-alone"]').focus();
    probeMove();
  };
  ACTIONS['pv-move-go'] = (el) => {
    const m = mv; if (!m) return;
    const n = +el.dataset.n, position = positionOf(m, n);
    mv = null; closeDialog();
    moveTo(m.u, m.from, m.alone ? n : landsIn(m.u, n, m.alone), position, m.alone);
  };

  ACTIONS['pv-select-dev'] = (el) => { selected = selected === el.dataset.uid ? '' : el.dataset.uid; App.render(); const n = $(`[data-uid="${CSS.escape(el.dataset.uid)}"]`); if (n) n.focus(); };
  ACTIONS['pv-clear-sel'] = () => { selected = ''; App.render(); };
  document.addEventListener('keydown', (e) => {
    const dev = e.target.closest && e.target.closest('[data-action="pv-select-dev"]');
    if (dev && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); dev.click(); }
    if (!onBoard() || e.target.closest('input, textarea, select') || $('#overlay .dialog')) return;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') { e.preventDefault(); ACTIONS['pv-undo'](); }
    if (e.key === 'Delete' && selected) { e.preventDefault(); ACTIONS['pv-delete'](); }
    if (e.altKey && !e.ctrlKey && !e.metaKey && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key) && (dev || selected)) {
      e.preventDefault();  // Alt+Left would otherwise go back a page
      if (dev) selected = dev.dataset.uid;
      keyMove(e.key);
    }
  });
})();
