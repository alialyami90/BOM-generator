/* Screens: Network (equipment, network, spares and the engine's sizing result) and Panels (board and list).
   The board only edits layout overrides and shows what Engine.layoutPreview returns; it holds no layout rules. */
(function () {
  const { esc, S, ACTIONS, SCREENS, badge, banner, tabs, field, input, select, pageHead, illus, dialog, closeDialog, toast, go, $, $$ } = App;
  const U = 18; // px per rack unit on the board
  const draftSub = () => S.sub === 'cb03';

  /* ---------- Network ---------- */
  const net = () => (S.net = S.net || JSON.parse(JSON.stringify(DB.sub.network)));
  const roles = [['fopp', 'Fibre patch panel'], ['l2_switch', 'L2 switch'], ['l1_switch', 'L1 switch'], ['ext_switch', 'External switch'], ['firewall', 'Firewall'], ['other', 'Other']];
  SCREENS.network = () => {
    const n = draftSub() ? { iedCount: '', topology: 'star', ringMax: '6', spares: net().spares } : net();
    const bad = S.checks === 'errors' && !draftSub();
    const eq = draftSub() ? [] : DB.equipment;
    return `<div class="page">${pageHead('Network', 'What the substation contains and how the network is sized. The panels are laid out from this.',
      `<button class="btn btn--primary" data-action="save" ${S.dirty ? '' : 'disabled'}>${icon('save')}Save</button>`)}
      ${draftSub() ? `<div style="margin-bottom:var(--space-4)">${banner('warn', '<b>The network is not set up yet.</b> Enter the number of field IEDs and add the equipment. The panels appear when there is something to place.')}</div>` : ''}
      <div class="net-grid">
        <div class="stack" style="gap:var(--space-6)">
          <section><h3>Field network</h3>
            <div class="form form--2" style="margin-top:var(--space-3)">
              ${field('Field IEDs', `<div class="input-affix">${input('n-ied', n.iedCount, { num: true, mono: true, invalid: draftSub(), placeholder: 'Required' })}<span class="affix">IEDs</span></div>`, draftSub() ? '' : 'Never listed in the BOM. Only used to size the L1 switches. <span style="color:var(--color-warning)">Assumed: confirm from the single-line diagram.</span>', draftSub() ? 'Enter the number of field IEDs, for example 40.' : '')}
              <div class="field"><span class="label" id="topo-l">Topology</span><div class="segmented" role="radiogroup" aria-labelledby="topo-l"><label><input type="radio" name="topo" value="star" data-action="net-topo" ${n.topology === 'star' ? 'checked' : ''}><span>Star</span></label><label><input type="radio" name="topo" value="ring" data-action="net-topo" ${n.topology === 'ring' ? 'checked' : ''}><span>Ring</span></label></div>
                <span class="help">${n.topology === 'star' ? 'Each L1 switch has one uplink to its L2 switch plus an A–B interlink.' : 'L1 switches are joined in rings. Two ports close each ring.'}</span></div>
              ${n.topology === 'ring' ? field('Switches per ring', input('n-ring', n.ringMax, { num: true, mono: true }), 'Most L1 switches in one ring.') : ''}
            </div></section>
          <section><h3>L1 switch model</h3>
            <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">The engine ranks the library's L1 switches for ${draftSub() ? 'the IED count' : n.iedCount + ' IEDs'}, fewest switches first. The best is used unless you pin another.</p>
            ${draftSub() ? `<div class="empty"><b>No ranking yet.</b><div class="muted small">It appears once the IED count is set.</div></div>` : rankTable()}</section>
          <section><div class="row" style="justify-content:space-between"><h3>Equipment</h3><div class="popwrap" style="position:relative"><button class="btn btn--secondary btn--sm" data-action="pick-open" aria-haspopup="listbox">${icon('plus')}Add device</button></div></div>
            <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">What the substation has, before any panel exists. Redundant devices come as an A and a B unit.</p>
            <div id="picker-slot"></div>
            ${eq.length ? `<div class="table-wrap"><table class="table"><thead><tr><th>Device</th><th style="width:150px">Role</th><th style="width:90px">A and B</th><th class="num" style="width:90px">L2 ports</th><th class="num" style="width:56px">Height</th><th style="width:40px"><span class="sr-only">Actions</span></th></tr></thead><tbody>
              ${eq.map((e, i) => { const isBad = bad && e.id === 'ext'; return `<tr><td>${isBad ? `<div class="field"><input class="ctl input input--mono" aria-label="Part id, row ${i + 1}" aria-invalid="true" aria-describedby="derr" value="SEL-2730M-EXT2"><span id="derr" class="err small">${icon('error')}<span>Not in psa-devices ${esc(DB.library.version)}. Did you mean SEL-2730M-EXT?</span></span></div>` : `<span class="mono">${esc(e.part)}</span><span class="cell-sub">${esc(e.label)}${e.count > 1 ? ` · ${e.count} per side, from the sizing` : ''}</span>`}</td>
                <td>${select('rl' + i, roles, e.role, { cls: 'ctl' })}</td><td><label class="check"><input type="checkbox" ${e.redundant ? 'checked' : ''} data-dirty="1" aria-label="Redundant: ${esc(e.label)}"> A + B</label></td>
                <td>${input('lp' + i, e.l2Ports, { num: true, mono: true, placeholder: '0' }).replace('class="input', 'class="ctl input')}</td><td class="num">${e.h} U</td>
                <td><button class="btn btn--ghost btn--icon btn--sm" data-action="toast" data-m="Removed ${esc(e.label)}" aria-label="Remove ${esc(e.label)}">${icon('trash')}</button></td></tr>`; }).join('')}</tbody></table>
              <div class="table-foot"><span>${eq.length} items · height and mounting come from the library</span><span>${illus()}</span></div></div>` : `<div class="empty"><b>No equipment yet.</b><div class="muted small">Add the switches, gateways and other devices this substation needs.</div></div>`}</section>
          <section><h3>Spares</h3>
            <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">Every spare can be changed. They start from the project's shared defaults; the ones you change are marked.</p>
            <div class="form form--3">
              ${field('Ports kept free on each switch', `<div class="input-affix">${input('sp-port', n.spares.portPercent, { num: true, mono: true })}<span class="affix">%</span></div>`)}
              ${field('Spare SFPs on each L1', input('sp-sfp', n.spares.sfpPerL1, { num: true, mono: true }))}
              ${field('Rack space kept free', `<div class="input-affix">${input('sp-u', n.spares.rackUReserved, { num: true, mono: true })}<span class="affix">U</span></div>`, `Leaves ${42 - (+n.spares.rackUReserved || 0)} U of 42 U to use in each panel.`)}
              ${field('Spare DC branches per feed', input('sp-dc', n.spares.dcBranches, { num: true, mono: true }))}
              ${field('Spare AC branches', input('sp-ac', n.spares.acBranches, { num: true, mono: true }))}
            </div></section>
        </div>
        <aside class="net-result" id="net-result" aria-live="polite">${resultCard()}</aside>
      </div></div>`;
  };
  const pinned = () => net().pin || '';
  const rankTable = () => `<div class="table-wrap"><table class="table"><caption class="sr-only">L1 switch models ranked by the engine</caption><thead><tr><th class="num" style="width:44px">Rank</th><th>Model</th><th class="num" style="width:56px">Ports</th><th class="num" style="width:76px">Per side</th><th class="num" style="width:96px">Spare ports</th><th style="width:200px">Use</th></tr></thead><tbody>
    ${DB.l1Ranking.map((r, i) => { const used = pinned() ? pinned() === r.part : i === 0; return `<tr${used ? ' aria-current="true"' : ''}><td class="num">${i + 1}</td><td class="nowrap" title="${esc(r.note)}"><span class="mono">${esc(r.part)}</span><span class="cell-sub">${esc(r.model)}</span></td><td class="num">${r.ports}</td><td class="num">${r.perSide}</td><td class="num">${r.spare}</td>
      <td>${used ? (pinned() ? `${badge('info', 'Pinned by you', 'check')} <button class="btn btn--ghost btn--sm" data-action="unpin-l1">Unpin</button>` : badge('ok', 'Tool\'s pick', 'check')) : `<button class="btn btn--secondary btn--sm" data-action="pin-l1" data-part="${esc(r.part)}">Use this one</button>${i === 0 ? ' <span class="muted small">Tool\'s pick</span>' : ''}`}</td></tr>`; }).join('')}</tbody></table>
    <div class="table-foot"><span>${pinned() ? 'Pinned: the engine sizes the network with this model until you unpin it.' : 'Nothing pinned: the engine uses the top row.'}</span><span>${illus()}</span></div></div>`;
  ACTIONS['pin-l1'] = (el) => { net().pin = el.dataset.part; S.dirty = true; App.render(); recalc(); };
  ACTIONS['unpin-l1'] = () => { net().pin = ''; S.dirty = true; App.render(); recalc(); };
  function resultCard() {
    if (draftSub()) return `<div class="card"><h3>Result</h3><p class="muted small" style="margin-top:var(--space-2)">Appears when the IED count and the equipment are set.</p></div>`;
    if (S.netPending) return `<div class="card"><h3>Result</h3><p class="row" style="margin-top:var(--space-3)"><span class="spinner"></span>Calculating…</p></div>`;
    const p = DB.networkPlan, A = p.sides.A, B = p.sides.B, ring = net().topology === 'ring';
    return `<div class="card"><h3>Result</h3><p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">Worked out by the engine. Read-only.</p>
      <table class="table table--plain"><thead><tr><th></th><th class="num">Side A</th><th class="num">Side B</th></tr></thead><tbody>
        <tr><td>L1 switches</td><td class="num"><b>${A.l1}</b></td><td class="num"><b>${B.l1}</b></td></tr>
        <tr><td>L2 switches</td><td class="num"><b>${A.l2}</b></td><td class="num"><b>${B.l2}</b></td></tr>
        <tr><td>L2 ports in use</td><td class="num">${A.l2Demand} of ${A.l2Usable}</td><td class="num">${B.l2Demand} of ${B.l2Usable}</td></tr>
        <tr><td>L1 to L2 links</td><td class="num">${A.links}</td><td class="num">${B.links}</td></tr></tbody></table>
      <p class="small" style="margin-top:var(--space-3)">L1 model: <span class="mono">${esc(pinned() || DB.l1Ranking[0].part)}</span>${pinned() ? ' (pinned)' : ''}.</p>
      <p class="small" style="margin-top:var(--space-2)">${net().iedCount || 0} field IEDs need ${A.l1} L1 switches on each side, ${A.l1Usable} usable ports each.</p>
      <p class="muted small" style="margin-top:var(--space-2)">${ring ? 'Rings: two ports close each ring.' : esc(p.note)}</p>
      <p class="muted small" style="margin-top:var(--space-2)">In the app this updates as you type. ${illus()}</p>
      <a class="btn btn--secondary btn--sm" href="#/panels" style="margin-top:var(--space-3)">${icon('panels')}See the panels</a></div>`;
  }
  const recalc = () => { S.netPending = true; const r = $('#net-result'); if (r) r.innerHTML = resultCard(); setTimeout(() => { S.netPending = false; const r2 = $('#net-result'); if (r2) r2.innerHTML = resultCard(); }, 700); };
  document.addEventListener('change', (e) => {
    const t = e.target; if (!t.id && !t.dataset.action) return;
    if (t.id === 'n-ied') { net().iedCount = t.value; recalc(); }
    if (t.id === 'n-ring') { net().ringMax = t.value; recalc(); }
    if (t.id === 'sp-port') { net().spares.portPercent = t.value; recalc(); }
    if (t.id === 'sp-u') { net().spares.rackUReserved = t.value; App.render(); }
  });
  ACTIONS['net-topo'] = (el) => { net().topology = el.value; S.dirty = true; App.render(); };

  /* ---------- Panels ---------- */
  const L = () => S.layout;
  const result = () => Engine.layoutPreview(L().overrides, L().removed);
  const findDev = (res, id) => { for (const p of res.panels) { const d = p.devices.find((x) => x.id === id); if (d) return { d, p }; } return null; };
  const snapshot = () => L().history.push({ overrides: L().overrides.slice(), removed: L().removed.slice() });
  const normalize = (ov) => { const auto = Engine.layoutPreview([], L().removed); return ov.filter((o) => (o.pair ? Engine.units().filter((u) => u.pair === o.pair).some((u) => { const a = findDev(auto, u.id); return !a || a.p.n !== 2 * o.pairIndex - (u.side === 'A' ? 1 : 0); }) : (() => { const a = findDev(auto, o.unit); return !a || a.p.n !== o.panel; })())); };
  const unitName = (id) => { const u = Engine.units().find((x) => x.id === id); return u ? u.name : id; };
  const describe = (m) => (m.pair ? `${unitName(m.pair + '.A')} (pair) to panels ${2 * m.pairIndex - 1} and ${2 * m.pairIndex}` : `${unitName(m.unit)} to panel ${m.panel}`);

  SCREENS.panels = () => {
    const { b } = App.route();
    if (b) return App.panelEditor(b);
    const t = S.tab.panels;
    const actions = `<button class="btn btn--ghost" data-action="undo-layout" ${L().history.length ? '' : 'disabled'}>${icon('undo')}Undo</button><button class="btn btn--secondary" data-action="reset-layout" ${L().overrides.length || L().removed.length ? '' : 'disabled'}>${icon('refresh')}Reset to automatic</button><button class="btn btn--secondary" data-action="add-panel">${icon('plus')}Add hand-written panel…</button>`;
    if (draftSub()) return `<div class="page">${pageHead('Panels', 'Laid out from the equipment and network.', '')}<div class="empty" style="max-width:640px"><b>No panels yet.</b><div class="muted small" style="margin:var(--space-1) 0 var(--space-3)">Panels are placed for you once the network has an IED count and equipment.</div><a class="btn btn--primary" href="#/network">${icon('network')}Set up the network</a></div></div>`;
    return `<div class="page page--wide">${pageHead('Panels', 'Placed by the layout from the equipment and network. Drag a device to another panel; a pair moves together.', actions)}
      ${tabs('panels', [['board', 'Board'], ['list', 'List']], t, 'Panels view')}
      <div role="tabpanel" aria-labelledby="tab-panels-${t}">${t === 'board' ? board() : list()}</div></div>`;
  };

  function list() {
    const r = result();
    return `<div class="table-wrap" style="margin-top:var(--space-4)"><table class="table table--comfort"><thead><tr><th>Sheet</th><th>Cabinet</th><th>Name</th><th>Written by</th><th>Side</th><th class="num">Rack space</th><th>Status</th></tr></thead>
      <tbody>${DB.panels.map((p) => { const lp = r.panels.find((x) => x.n === p.n);
        return `<tr class="clickable" tabindex="0" data-action="open-panel" data-id="${p.id}"><td class="mono">${esc(p.sheet)}</td><td class="mono">${esc(p.cabinet)}</td><td><b style="font-weight:500">${esc(p.name)}</b></td>
        <td>${p.generated ? 'Layout' : 'Hand-written'}</td><td>${p.generated ? 'Side ' + p.side : '—'}</td><td class="num">${lp ? `${lp.used} of ${lp.capacity} U` : '—'}</td>
        <td>${p.status === 'bad' && S.checks === 'errors' ? badge('bad', '1 error', 'error') : badge('ok', 'Ready', 'check')}</td></tr>`; }).join('')}</tbody></table>
      <div class="table-foot"><span>One sheet per cabinet, in the order shown</span><span>${illus()}</span></div></div>`;
  }

  function board() {
    const r = result(); const sel = L().selected; const selInfo = sel ? findDev(r, sel) : null;
    const pairsN = r.panels.length / 2;
    const partner = selInfo && selInfo.d.pair ? r.panels.flatMap((p) => p.devices).find((d) => d.pair === selInfo.d.pair && d.id !== sel) : null;
    const nChanges = L().overrides.length + L().removed.length;
    return `<div class="board-wrap">
      <div class="board-bar" role="status" aria-live="polite">
        ${L().error ? banner('bad', `<b>Not moved.</b> ${esc(L().error)}`, '<button class="btn btn--secondary btn--sm" data-action="dismiss-layout-error">Dismiss</button>') : ''}
        ${selInfo ? `<div class="sel-bar"><span><b>${esc(selInfo.d.name)}</b> <span class="mono muted">${esc(selInfo.d.tag)}</span> · ${selInfo.d.side ? 'Side ' + selInfo.d.side : 'Common'} · ${selInfo.d.dev} U${selInfo.d.cm ? ' + 1 U cable manager' : ''}</span><span class="sp"></span>
          ${selInfo.d.redundant ? `<button class="btn btn--secondary btn--sm" data-action="move-dialog" data-mode="pair">${icon('move')}Move pair…</button><button class="btn btn--ghost btn--sm" data-action="move-dialog" data-mode="unit">Move this unit only…</button>` : `<button class="btn btn--secondary btn--sm" data-action="move-dialog" data-mode="unit">${icon('move')}Move…</button>`}
          <button class="btn btn--ghost btn--sm" data-action="delete-dev">${icon('trash')}${selInfo.d.redundant ? 'Delete pair' : 'Delete'}</button><button class="btn btn--ghost btn--icon btn--sm" data-action="clear-sel" aria-label="Clear selection">${icon('x')}</button></div>`
          : `<div class="row board-hint"><span class="muted small">Select a device to see its tag, or drag it. ${icon('grip')} Blank plates are shown as gaps and are not in the BOM. A switch, firewall or patch panel counts with its 1 U cable manager.</span><span class="sp"></span>
          <button class="btn btn--ghost btn--sm" data-action="toggle-changes" aria-expanded="${L().openOverrides}">${nChanges ? `${nChanges} manual change${nChanges > 1 ? 's' : ''}` : 'No manual changes'}${icon('chevd')}</button></div>`}
        ${L().openOverrides && !selInfo ? changesList() : ''}
      </div>
      <div class="board" role="group" aria-label="Panels">${Array.from({ length: pairsN }, (_, i) => i + 1).map((k) => `<div class="pair" data-pair-index="${k}"><div class="pair-head">Pair ${k} <span class="muted">· panels ${2 * k - 1} and ${2 * k}</span></div><div class="pair-cols">${r.panels.filter((p) => p.pair === k).map((p) => column(p, sel, partner)).join('')}</div></div>`).join('')}</div>
      <p class="muted small" style="margin-top:var(--space-3)">${r.panels.length} panels from the layout, 1 hand-written (WS Console) · the layout runs again after every change. ${illus()}</p></div>`;
  }

  function changesList() {
    const rows = [...L().overrides.map((o, i) => `<li><span>${icon('move')}Moved ${esc(describe(o))}</span><button class="btn btn--ghost btn--sm" data-action="revert-change" data-kind="o" data-i="${i}">Revert</button></li>`),
      ...L().removed.map((id, i) => `<li><span>${icon('trash')}Deleted ${esc(unitName(Engine.units().find((u) => u.id === id || u.pair === id) ? (Engine.units().find((u) => u.id === id || u.pair === id)).id : id))}${Engine.units().some((u) => u.pair === id) ? ' (pair)' : ''}</span><button class="btn btn--ghost btn--sm" data-action="revert-change" data-kind="r" data-i="${i}">Restore</button></li>`)];
    return `<ul class="changes">${rows.join('') || '<li class="muted">Nothing changed by hand.</li>'}</ul>`;
  }

  function column(p, sel, partner) {
    const pct = Math.round((p.used / p.capacity) * 100);
    const full = p.free < 3;
    const cards = [];
    p.devices.forEach((d, i) => {
      if (i) cards.push(`<div class="plate" style="height:${U}px" title="Blank plate (not in the BOM)"></div>`);
      const isSel = d.id === sel, isPartner = partner && partner.id === d.id;
      cards.push(`<div class="dev ${d.cm ? 'has-cm' : ''} ${isSel ? 'is-sel' : ''} ${isPartner ? 'is-partner' : ''} ${d.moved ? 'is-moved' : ''}" draggable="true" tabindex="0" role="button" aria-pressed="${isSel}" data-action="select-dev" data-dev="${d.id}" data-pair="${d.pair}" style="height:${d.h * U}px"
        aria-label="${esc(d.name)}${d.side ? ', side ' + d.side : ', common'}, ${d.h} U${d.cm ? ` including a 1 U cable manager` : ''}, tag ${esc(d.tag)}${d.moved ? ', moved by you' : ''}" title="${esc(d.tag)}">
        <span class="dev-row" style="height:${d.dev * U - 2}px"><span class="dev-grip">${icon('grip')}</span><span class="dev-main"><b>${esc(d.name)}</b>${d.dev >= 2 ? `<span class="mono">${esc(d.tag)}</span>` : ''}</span>${d.moved ? `<span class="dev-flag" title="Moved by you">${icon('move')}</span>` : ''}<span class="dev-u">${d.dev} U</span></span>${d.cm ? '<span class="dev-cm">Cable manager<span class="dev-u">1 U</span></span>' : ''}</div>`);
    });
    return `<section class="bcol" data-panel="${p.n}" aria-label="${esc(p.name)}, side ${p.side}, ${p.used} of ${p.capacity} U used">
      <header><a href="#/panels/${p.id}"><b>${esc(p.name)}</b></a><span class="badge badge--plain">Side ${p.side}</span></header>
      <div class="umeter ${full ? 'is-full' : ''}" role="img" aria-label="${p.used} of ${p.capacity} U used"><i style="width:${pct}%"></i></div>
      <div class="ulabel"><b>${p.used}</b> of ${p.capacity} U used · ${p.free} U free</div>
      <div class="rack">${cards.join('')}${p.free > 0 ? `<div class="freeu" style="height:${p.free * U}px">${p.free} U free</div>` : ''}<div class="reserve" style="height:${p.reserved * U}px"><span>${p.reserved} U kept free for expansion</span></div></div>
      <footer>${p.din} DIN-rail parts · no rack space</footer></section>`;
  }

  /* ----- actions ----- */
  const commit = (move, label) => {
    const c = Engine.canMove(move, L().overrides, L().removed);
    if (!c.ok) { L().error = c.reason + ' Nothing was changed.'; App.render(); return false; }
    snapshot(); L().overrides = normalize(c.overrides); L().error = ''; S.dirty = true; App.render();
    toast(`Moved ${label}`, 'move', () => ACTIONS['undo-layout']());
    return true;
  };
  ACTIONS['select-dev'] = (el, e) => { if (e.target.closest('a')) return; L().selected = L().selected === el.dataset.dev ? '' : el.dataset.dev; App.render(); const n = $(`[data-dev="${el.dataset.dev}"]`); n && n.focus(); };
  ACTIONS['clear-sel'] = () => { L().selected = ''; App.render(); };
  ACTIONS['dismiss-layout-error'] = () => { L().error = ''; App.render(); };
  ACTIONS['toggle-changes'] = () => { L().openOverrides = !L().openOverrides; App.render(); };
  ACTIONS['undo-layout'] = () => { const h = L().history.pop(); if (!h) return; L().overrides = h.overrides; L().removed = h.removed; L().error = ''; App.render(); toast('Change undone', 'undo'); };
  ACTIONS['revert-change'] = (el) => { snapshot(); if (el.dataset.kind === 'o') L().overrides.splice(+el.dataset.i, 1); else L().removed.splice(+el.dataset.i, 1); App.render(); };
  ACTIONS['delete-dev'] = () => {
    const info = findDev(result(), L().selected); if (!info) return;
    snapshot(); L().removed.push(info.d.pair || info.d.id); L().selected = ''; S.dirty = true; App.render();
    toast(`Deleted ${info.d.name}${info.d.redundant ? ' (both units)' : ''} from the BOM`, 'trash', () => ACTIONS['undo-layout']());
  };
  ACTIONS['reset-layout'] = () => dialog({ title: 'Reset to automatic?', body: `<p>The layout places everything again and ${L().overrides.length + L().removed.length} manual change${L().overrides.length + L().removed.length > 1 ? 's are' : ' is'} removed: ${L().overrides.length} move${L().overrides.length === 1 ? '' : 's'} and ${L().removed.length} deletion${L().removed.length === 1 ? '' : 's'}. You can undo this straight after.</p>`, actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="reset-confirm">Reset to automatic</button>' });
  ACTIONS['reset-confirm'] = () => { closeDialog(); snapshot(); L().overrides = []; L().removed = []; L().selected = ''; L().error = ''; App.render(); toast('Layout reset to automatic', 'refresh', () => ACTIONS['undo-layout']()); };

  ACTIONS['move-dialog'] = (el) => {
    const r = result(); const info = findDev(r, L().selected); if (!info) return; const d = info.d; const pairMode = el.dataset.mode === 'pair' && d.redundant;
    let rows = '';
    if (pairMode) {
      for (let k = 1; k <= r.panels.length / 2 + 1; k++) {
        const c = Engine.canMove({ pair: d.pair, pairIndex: k }, L().overrides, L().removed); const cur = info.p.pair === k;
        const a = c.result.panels.find((p) => p.n === 2 * k - 1), b = c.result.panels.find((p) => p.n === 2 * k);
        rows += `<label class="check move-row ${c.ok && !cur ? '' : 'is-off'}"><input type="radio" name="mv" value="${k}" ${c.ok && !cur ? '' : 'disabled'}><span><b>Panels ${2 * k - 1} and ${2 * k}</b>${cur ? ' (now)' : ''}<span class="small muted">${cur ? 'Where it is now' : c.ok ? `After: ${a.used} U and ${b.used} U of ${a.capacity} U` : esc(c.reason)}</span></span></label>`;
      }
    } else {
      const sides = d.redundant ? r.panels.filter((p) => p.side === d.side) : r.panels.filter((p) => p.side === 'A' || true);
      sides.forEach((p) => {
        const c = Engine.canMove({ unit: d.id, panel: p.n }, L().overrides, L().removed); const cur = info.p.n === p.n; const lp = c.result.panels.find((x) => x.n === p.n);
        rows += `<label class="check move-row ${c.ok && !cur ? '' : 'is-off'}"><input type="radio" name="mv" value="${p.n}" ${c.ok && !cur ? '' : 'disabled'}><span><b>${esc(p.name)}</b> <span class="muted">side ${p.side}</span>${cur ? ' (now)' : ''}<span class="small muted">${cur ? 'Where it is now' : c.ok ? `After: ${lp.used} of ${lp.capacity} U` : esc(c.reason)}</span></span></label>`;
      });
    }
    dialog({ title: `Move ${esc(d.name)}${pairMode ? ' (pair)' : ''}`, body: `<p class="muted small" style="margin-bottom:var(--space-3)">${pairMode ? 'Both units move, A to the odd panel and B to the even one.' : d.redundant ? `Only this ${d.side} unit moves, and only to another side ${d.side} panel. The pair is no longer symmetric.` : 'This device has no side, so it can go in any panel.'} Choices that do not fit are greyed with the reason.</p><div class="stack" style="gap:6px">${rows}</div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="move-confirm" data-mode="${pairMode ? 'pair' : 'unit'}" data-id="${d.id}" data-pair="${d.pair}">Move</button>` });
  };
  ACTIONS['move-confirm'] = (el) => {
    const v = $('input[name="mv"]:checked'); if (!v) { toast('Choose a destination first', 'info'); return; }
    closeDialog(); const k = +v.value;
    if (el.dataset.mode === 'pair') commit({ pair: el.dataset.pair, pairIndex: k }, `${unitName(el.dataset.pair + '.A')} (pair) to panels ${2 * k - 1} and ${2 * k}`);
    else commit({ unit: el.dataset.id, panel: k }, `${unitName(el.dataset.id)} to panel ${k}`);
  };

  /* ----- drag and drop ----- */
  let drag = null;
  const targetFor = (d, n) => (d.redundant && d.mode !== 'unit' ? { pair: d.pair, pairIndex: Math.ceil(n / 2) } : { unit: d.id, panel: n });
  document.addEventListener('dragstart', (e) => { const c = e.target.closest && e.target.closest('.dev'); if (!c) return; const info = findDev(result(), c.dataset.dev); drag = { id: c.dataset.dev, pair: info.d.pair, redundant: info.d.redundant, mode: e.altKey ? 'unit' : 'pair', from: info.p.n, name: info.d.name }; e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', c.dataset.dev); c.classList.add('is-dragging'); });
  const clearDrop = () => $$('.bcol.drop-ok, .bcol.drop-bad').forEach((x) => x.classList.remove('drop-ok', 'drop-bad'));
  document.addEventListener('dragover', (e) => {
    const col = e.target.closest && e.target.closest('.bcol'); if (!drag || !col) return;
    const n = +col.dataset.panel; const mv = targetFor(drag, n); const c = Engine.canMove(mv, L().overrides, L().removed);
    clearDrop(); const same = $$('.bcol').filter((x) => (mv.pair ? Math.ceil(+x.dataset.panel / 2) === mv.pairIndex : +x.dataset.panel === n));
    same.forEach((x) => x.classList.add(c.ok ? 'drop-ok' : 'drop-bad')); e.preventDefault(); e.dataTransfer.dropEffect = 'move'; /* a refused drop still lands, so the error banner can say why */
  });
  document.addEventListener('dragleave', (e) => { if (!e.relatedTarget || !e.relatedTarget.closest || !e.relatedTarget.closest('.board')) clearDrop(); });
  document.addEventListener('drop', (e) => {
    const col = e.target.closest && e.target.closest('.bcol'); if (!drag || !col) return; e.preventDefault(); clearDrop();
    const n = +col.dataset.panel, mv = targetFor(drag, n), d = drag; drag = null;
    const cur = result(); const info = findDev(cur, d.id);
    if ((mv.pair && Math.ceil(info.p.n / 2) === mv.pairIndex) || (mv.unit && info.p.n === mv.panel)) return;
    commit(mv, mv.pair ? `${d.name} (pair) to panels ${2 * mv.pairIndex - 1} and ${2 * mv.pairIndex}` : `${d.name} to panel ${n}`);
  });
  document.addEventListener('dragend', () => { drag = null; clearDrop(); $$('.dev.is-dragging').forEach((x) => x.classList.remove('is-dragging')); });
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && location.hash.startsWith('#/panels') && !e.target.closest('input, textarea, select')) { e.preventDefault(); ACTIONS['undo-layout'](); }
    const dev = e.target.closest && e.target.closest('.dev');
    if (dev && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); dev.click(); }
    if (dev && e.key === 'Delete') { L().selected = dev.dataset.dev; ACTIONS['delete-dev'](); }
  });

  ACTIONS['add-panel'] = () => dialog({ title: 'Add a hand-written panel', body: `<p style="margin-bottom:var(--space-3)">For a cabinet the layout should not touch, such as a console. You list its devices yourself.</p><div class="stack">${field('Name', input('ap-n', ''))}${field('Cabinet number', input('ap-c', '', { mono: true }))}${field('Kind', select('ap-k', [['console', 'Console'], ['network', 'Network cabinet']], 'console'))}</div>`, actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="close">Add panel</button>' });
})();
