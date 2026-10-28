/* Screens: the Network result and L1 ranking, and the Panels board and list, on bomgen.app.api (plan M10c).
   Every figure comes from substation_layout, which flattens M1c's layout_preview; this file only draws it.
   Read-only until the substation writers exist: nothing is moved, pinned or deleted here.
   Opened in a plain browser, screens-layout.js shows the prototype. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, pageHead, toast, $ } = App;
  const example = SCREENS.panels;
  const real = () => S.backend === 'yes' && S.project && S.project.real && S.sub;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;
  const U = 18; // px per rack unit on the board, as in the prototype

  /* ---------- data: one layout per (project file, substation id) ---------- */
  const LAY = { key: '', state: 'idle', data: null, error: null };
  function layout() {
    const key = `${S.project.file}#${S.sub}`;
    if (LAY.key !== key) { Object.assign(LAY, { key, state: 'idle', data: null, error: null }); selected = ''; showIssues = false; }
    if (LAY.state === 'idle') {
      LAY.state = 'loading';
      const current = () => LAY.key === key;
      Bridge.call('substation_layout', S.project.file, S.sub)
        .then((d) => { if (current()) LAY.data = d; }).catch((err) => { if (current()) { LAY.error = err; toast(err.message, 'error'); } })
        .then(() => { if (current()) { LAY.state = 'loaded'; App.render(); } });
    }
    return LAY.state === 'loaded' ? LAY : null;
  }

  /* ---------- Network: L1 ranking and Result card (called from screens-substation.js) ---------- */
  function rankTable() {
    const l = layout();
    if (!l || !l.data) return `<p class="row muted small" style="margin-top:var(--space-3)"><span class="spinner"></span>Ranking the library’s L1 switches…</p>`;
    const d = l.data, plan = d.plan;
    if (!plan || !d.l1_ranking.length) return `<div class="empty" style="margin-top:var(--space-3)"><b>No ranking yet.</b><div class="muted small">${esc(d.reason || 'It appears once the IED count and the equipment are set.')}</div></div>`;
    return `<p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">The engine ranks the library's L1 switches for ${plan.ied_count} IEDs, fewest switches first. The best is used unless <span class="mono">substation.yaml</span> pins another.</p>
      <div class="table-wrap"><table class="table"><caption class="sr-only">L1 switch models ranked by the engine</caption><thead><tr><th style="width:48px;text-align:center">Rank</th><th>Model</th><th class="num" style="width:56px">Ports</th><th class="num" style="width:76px">Per side</th><th class="num" style="width:96px">Usable ports</th><th style="width:170px">Use</th></tr></thead><tbody>
      ${d.l1_ranking.map((r, i) => { const used = r.part_id === plan.l1_part_id; return `<tr${used ? ' aria-current="true"' : ''}><td style="text-align:center">${i + 1}</td><td class="nowrap"><span class="mono">${esc(r.part_id)}</span><span class="cell-sub">${esc([r.make, r.model].filter(Boolean).join(' '))}</span></td><td class="num">${r.ports}</td><td class="num">${r.per_side}</td><td class="num">${r.usable_ports}</td>
        <td>${used ? (plan.l1_pinned ? badge('info', 'Pinned', 'check') : badge('ok', 'Tool\'s pick', 'check')) : i === 0 ? '<span class="muted small">Tool\'s pick</span>' : ''}</td></tr>`; }).join('')}</tbody></table>
      <div class="table-foot"><span>${plan.l1_pinned ? `Pinned in substation.yaml: the engine sizes the network with ${esc(plan.l1_part_id)}.` : 'Nothing pinned: the engine uses the top row.'}</span></div></div>`;
  }

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
  App.network = { rankTable, resultCard };

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
        n ? `<button class="btn btn--secondary btn--sm" data-action="pv-issues" aria-expanded="${showIssues}">${showIssues ? 'Hide' : `Show ${plural(n, 'problem')}`}</button>` : '')}</div>`;
    }
    const errors = d.issues.filter((i) => i.level === 'error'), warnings = d.issues.filter((i) => i.level === 'warning');
    return (errors.length ? `<div style="margin-bottom:var(--space-3)">${banner('bad', `<b>${plural(errors.length, 'layout error')}.</b> Build is blocked until they are fixed.${issueList(errors)}`, '<a class="btn btn--secondary btn--sm" href="#/checks">Open checks</a>')}</div>` : '')
      + (warnings.length ? `<div style="margin-bottom:var(--space-3)">${banner('warn', `<b>${plural(warnings.length, 'layout warning')}.</b>${issueList(warnings)}`)}</div>` : '');
  };
  ACTIONS['pv-issues'] = () => { showIssues = !showIssues; App.render(); };

  SCREENS.panels = () => {
    if (!real()) return example();
    const { b } = App.route();
    if (b) return `<div class="page">${pageHead('Panel', 'The panel editor comes with the substation writers.')}<a class="btn btn--secondary" href="#/panels">Back to the panels</a></div>`;
    const l = layout();
    if (!l || !l.data) return `<div class="page">${pageHead('Panels', l && l.error ? esc(l.error.message) : 'Laying out the panels…')}</div>`;
    const d = l.data;
    if (d.reason) return `<div class="page">${pageHead('Panels', 'Laid out from the equipment and network.')}${banner('bad', `<b>No layout.</b> ${esc(d.reason)}.`, '<a class="btn btn--secondary btn--sm" href="#/checks">Open checks</a>')}</div>`;
    const t = ['board', 'list'].includes(S.tab.panels) ? S.tab.panels : 'board';
    return `<div class="page page--wide">${pageHead('Panels', 'Placed by the engine from the equipment and network.', '', '', 'Moving a device here is not available yet. To move one, add it to layout.overrides in substation.yaml.')}
      ${tabs('panels', [['board', 'Board'], ['list', 'List']], t, 'Panels view')}
      <div role="tabpanel" aria-labelledby="tab-panels-${t}" style="margin-top:var(--space-4)">${t === 'board' ? board(d) : list(d)}</div></div>`;
  };

  function board(d) {
    if (!d.panels.length) return `<div class="empty" style="max-width:640px"><b>No panels yet.</b><div class="muted small" style="margin:var(--space-1) 0 var(--space-3)">Panels are placed once the network has an IED count and equipment.</div><a class="btn btn--primary" href="#/network">${icon('network')}See the network</a></div>`;
    let sel = null;
    d.panels.forEach((p) => p.units.forEach((u) => { if (uid(p, u) === selected) sel = { p, u }; }));
    const changes = d.overrides.length + d.removed.length;
    const pairs = [...new Set(d.panels.map((p) => p.pair))];
    return `<div class="board-wrap">
      ${issuesBanner(d)}
      <div class="board-bar" role="status" aria-live="polite">
        ${sel ? `<div class="sel-bar"><span><b>${esc(name(sel.u))}</b> <span class="mono muted">${esc(sel.u.part_id)}</span> ${esc(sel.u.label)} · ${sel.u.side ? 'Side ' + sel.u.side : 'Common'} · ${sel.u.height_u} U${sel.u.cable_manager_u ? ` + ${sel.u.cable_manager_u} U cable manager` : ''} · ${esc(sel.p.cabinet_name)}${sel.u.pinned ? ' · pinned by an override' : ''}</span><span class="sp"></span><button class="btn btn--ghost btn--icon btn--sm" data-action="pv-clear-sel" aria-label="Clear selection">${icon('x')}</button></div>`
          : `<div class="row board-hint"><span class="muted small">Select a device to see its part and size.</span><span class="board-help" tabindex="0" role="img" aria-label="${esc(HELP)}" title="${esc(HELP)}">${icon('help')}</span><span class="sp"></span><span class="muted small">${changes ? `${[d.overrides.length ? `${d.overrides.length} pinned` : '', d.removed.length ? `${d.removed.length} deleted` : ''].filter(Boolean).join(' · ')} in substation.yaml` : 'Nothing pinned or deleted'}</span></div>`}
      </div>
      <div class="board" role="group" aria-label="Panels">${pairs.map((k) => { const cols = d.panels.filter((p) => p.pair === k); return `<div class="pair"><div class="pair-head">Pair ${k} <span class="muted">· panels ${cols.map((p) => p.number).join(' and ')}</span></div><div class="pair-cols">${cols.map((p) => column(p, d.reserved_u, sel)).join('')}</div></div>`; }).join('')}</div>
      <p class="muted small" style="margin-top:var(--space-3)">${plural(d.panels.length, 'panel')} from the layout${d.list.some((p) => p.manual) ? `, ${d.list.filter((p) => p.manual).length} hand-written (${d.list.filter((p) => p.manual).map((p) => esc(p.cabinet_name)).join(', ')})` : ''}.</p></div>`;
  }

  function column(p, reserved, sel) {
    const pct = Math.round((p.used_u / p.capacity_u) * 100);
    const rack = p.units.filter((u) => u.block_u > 0);
    const partner = sel && sel.u.side ? `${sel.u.key}:${sel.u.side === 'A' ? 'B' : 'A'}` : '';
    const cards = [];
    rack.forEach((u) => {
      const id = uid(p, u), isSel = id === selected, isPartner = partner && `${u.key}:${u.side}` === partner;
      cards.push(`<div class="dev ${u.cable_manager_u ? 'has-cm' : ''} ${isSel ? 'is-sel' : ''} ${isPartner ? 'is-partner' : ''} ${u.pinned ? 'is-pinned' : ''}" tabindex="0" role="button" aria-pressed="${isSel}" data-action="pv-select-dev" data-uid="${esc(id)}" style="height:${u.block_u * U}px"
        aria-label="${esc(name(u))}${u.side ? ', side ' + u.side : ', common'}, ${u.block_u} U${u.cable_manager_u ? ' including a 1 U cable manager' : ''}${u.pinned ? ', pinned by an override' : ''}" title="${esc(u.part_id)} · ${esc(u.label)}">
        <span class="dev-row" style="height:${u.height_u * U - 2}px"><span class="dev-main"><b>${esc(name(u))}</b>${u.height_u >= 2 ? `<span class="mono">${esc(u.part_id)}</span>` : ''}</span>${u.pinned ? `<span class="dev-flag" title="Pinned by an override: stays here when the network changes">${icon('pin')}</span>` : ''}<span class="dev-u">${u.height_u} U</span></span>${u.cable_manager_u ? `<span class="dev-cm">Cable manager<span class="dev-u">${u.cable_manager_u} U</span></span>` : ''}</div>`);
      if (u.plate_below_u) cards.push(`<div class="plate" style="height:${u.plate_below_u * U}px" title="Blank plate (not in the BOM)"></div>`);
    });
    const din = p.units.filter((u) => u.block_u === 0);
    return `<section class="bcol" aria-label="${esc(p.cabinet_name)}, side ${esc(p.side || '')}, ${p.used_u} of ${p.capacity_u} U used">
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

  ACTIONS['pv-select-dev'] = (el) => { selected = selected === el.dataset.uid ? '' : el.dataset.uid; App.render(); const n = $(`[data-uid="${CSS.escape(el.dataset.uid)}"]`); if (n) n.focus(); };
  ACTIONS['pv-clear-sel'] = () => { selected = ''; App.render(); };
  document.addEventListener('keydown', (e) => {
    const dev = e.target.closest && e.target.closest('[data-action="pv-select-dev"]');
    if (dev && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); dev.click(); }
  });
})();
