/* Screen: Device preview (plan M24; docs/ui/screens.md "Device preview", components.md "Parts and Device preview").
   Each generated unit with its panel, rack position and MCBs, and a front view of each panel, before the
   workbook is built. The engine places and sizes everything (device_preview); this only draws it, turning a
   unit's top U into pixels. Dragging or stepping a unit pins it through set_layout_overrides, as the Panels
   board does; the bridge refuses what the layout cannot take. */
(function () {
  const { esc, S, ACTIONS, SCREENS, banner, pageHead, toast, go, $, $$ } = App;
  const PX = 18;  // px per rack unit on the front view
  const DP = { key: '', state: 'idle', data: null, sel: '', filter: 0, refusal: '', busy: false, steps: null };
  const real = () => S.backend === 'yes' && S.project && S.project.real && S.sub;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;
  function load() {
    const key = `${S.project.file}#${S.sub}`;
    if (DP.key !== key) Object.assign(DP, { key, state: 'idle', data: null, sel: '', filter: 0, refusal: '', steps: null });
    if (DP.state === 'idle') {
      DP.state = 'loading';
      Bridge.call('device_preview', S.project.file, S.sub)
        .then((d) => { if (DP.key === key) { DP.data = d; probeSteps(); } })
        .catch((err) => { if (DP.key === key) toast(err.message, 'error'); })
        .then(() => { if (DP.key === key) { DP.state = 'loaded'; App.render(); } });
    }
    return DP.state === 'loaded' ? DP.data : null;
  }
  const reload = () => { DP.state = 'idle'; };

  /* ---------- units and the moves that pin them (the board's rules, screens-panels.js) ---------- */
  const uid = (p, u) => `${p.number}:${u.device}#${u.n}:${u.side || ''}`;
  const all = () => DP.data.panels.flatMap((p) => p.units.map((u) => ({ u, p })));
  const hit = (id) => all().find(({ p, u }) => uid(p, u) === id);
  const block = (u) => u.height_u + u.cable_manager_u;
  const inRack = (u) => u.placed && !u.din_rail && u.top_u != null;
  const name = (u) => u.tag || `${u.label}${u.n > 1 ? ' ' + u.n : ''}`;
  const span = (u) => `${block(u) > 1 ? `${u.top_u - block(u) + 1}–` : ''}${u.top_u}`;
  const pairPanels = (n) => (n % 2 ? [n, n + 1] : [n - 1, n]);
  const sideFits = (u, n) => !u.side || (u.side === 'a') === (n % 2 === 1);  // A units in odd panels, B in even
  const places = (o, u, alone) => (o.pair === u.device && (o.unit == null || o.unit === u.n) && !alone)
    || (o.device === u.device && (o.unit == null || o.unit === u.n) && (!o.side || !u.side || o.side === u.side));
  const others = (u, alone) => DP.data.overrides.filter((o) => !places(o, u, alone));
  const moveOf = (u, n, top, alone) => (u.side && !alone
    ? { pair: u.device, unit: u.n, panel: pairPanels(n), top_u: top }
    : { device: u.device, unit: u.n, ...(alone ? { side: u.side } : {}), panel: n, top_u: top });
  const sentence = (t) => { const x = String(t).replace(/^./, (m) => m.toUpperCase()); return /[.!?]$/.test(x) ? x : x + '.'; };
  const canPin = () => DP.data && DP.data.generated && !DP.busy;

  /* Write the overrides; a refusal stays on the page as a banner. Undo writes the previous list back. */
  function write(overrides, said, undoable = true) {
    const before = DP.data.overrides;
    DP.busy = true; DP.refusal = ''; App.render();
    return Bridge.call('set_layout_overrides', S.project.file, S.sub, overrides).then((r) => {
      if (!r.written) { DP.refusal = sentence((r.issues[0] || {}).message || 'The layout cannot take this move'); return false; }
      reload(); App.network.reload();
      if (said) toast(said, 'pin', undoable ? () => write(before, 'Undone', false) : null);
      return true;
    }).catch((err) => { toast(err.message, 'error'); return false; })
      .then((ok) => { DP.busy = false; App.render(); return ok; });
  }
  /* Up 1 U and Down 1 U are offered only when the bridge says the move fits. */
  function probeSteps() {
    const h = DP.sel && hit(DP.sel); DP.steps = null;
    if (!h || !inRack(h.u) || !DP.data.generated) return;
    const steps = { id: DP.sel }; DP.steps = steps;
    [['up', 1], ['down', -1]].forEach(([k, d]) => {
      const move = moveOf(h.u, h.p.number, h.u.top_u + d, false);
      Bridge.call('check_layout', S.project.file, S.sub, [...others(h.u, false), move], DP.data.removed)
        .then((r) => { if (DP.steps === steps) { steps[k] = r.fits; App.render(); } }).catch(() => {});
    });
  }
  function step(d) {
    const h = hit(DP.sel); if (!h || !DP.steps || !DP.steps[d > 0 ? 'up' : 'down'] || !canPin()) return;
    const top = h.u.top_u + d, move = moveOf(h.u, h.p.number, top, false);
    write([...others(h.u, false), move], `Pinned ${name(h.u)} at U ${top}`).then((ok) => {
      if (!ok) return;
      const n = $(`.eu[data-uid="${CSS.escape(DP.sel)}"]`); if (n) n.focus();
    });
  }

  /* ---------- one front view ---------- */
  const issuesOf = (sev, n) => DP.data.issues.filter((i) => i.severity === sev && (n == null || i.panel === n));
  function elevation(p) {
    const d = DP.data, n = d.capacity_u, w = d.waist_u, need = p.used_u + p.overflow_u, anyErr = issuesOf('error').length;
    const units = p.units.filter(inRack).map((u) => {
      const id = uid(p, u), sel = DP.sel === id, cm = u.cable_manager_u > 0;
      const atWaist = u.waist && !u.away_from_waist, off = u.away_from_waist;
      return `<button class="eu${cm ? ' has-cm' : ''}${sel ? ' is-sel' : ''}${u.pinned ? ' is-pinned' : ''}${off ? ' is-off' : ''}" data-action="dp-sel" data-uid="${esc(id)}" aria-pressed="${sel}"
        style="top:${(n - u.top_u) * PX}px;height:${block(u) * PX}px" aria-label="${esc(name(u))}, ${esc(u.library_part_id)}, U ${span(u)}, ${cm ? `${u.height_u} U and a cable manager` : `${u.height_u} U`}${u.pinned ? ', pinned' : ''}${off ? ', away from waist height' : ''}" title="${esc(u.label)} · ${esc(u.library_part_id)}">
        <span class="eu-tag">${esc(name(u))}</span>${u.pinned ? `<span class="eu-flag">${icon('pin')}</span>` : ''}${atWaist ? `<span class="eu-flag eu-flag--ok" title="Bottom edge at waist height">${icon('check')}</span>` : ''}${off ? `<span class="eu-flag eu-flag--warn" title="Pinned away from waist height">${icon('warn')}</span>` : ''}<span class="eu-h">${cm ? `${u.height_u} U + CM` : `${u.height_u} U`}</span>${cm ? '<span class="eu-cm" aria-hidden="true">Cable manager</span>' : ''}</button>`;
    }).join('');
    const ruler = Array.from({ length: Math.floor(n / 5) }, (_, i) => (i + 1) * 5).filter((k) => Math.abs(k - w) > 1)
      .map((k) => `<span style="bottom:${(k - 1) * PX + PX / 2 - 7}px">${k}</span>`).join('')
      + `<span class="elev-ruler-waist" style="bottom:${(w - 1) * PX + PX / 2 - 7}px" title="Waist height ${d.waist_height_mm} mm">${w}</span>`;
    const din = p.units.filter((u) => u.din_rail), lost = p.units.filter((u) => !u.placed && !u.din_rail), errs = issuesOf('error', p.number).length;
    const side = p.side ? p.side.toUpperCase() : '';
    return `<section class="elev${DP.filter === p.number ? ' is-filtered' : ''}" data-panel="${p.number}" aria-label="${esc(p.name)}${side ? `, side ${side}` : ''}, ${need} of ${n} U used">
      <header><button class="link-btn elev-name" data-action="dp-filter" data-n="${p.number}" aria-pressed="${DP.filter === p.number}" title="Show only this panel's devices">${esc(p.name)}</button>${side ? `<span class="badge badge--plain">Side ${side}</span>` : ''}</header>
      <div class="elev-meta muted small"><span${p.overflow_u ? ' class="elev-need"' : ''}><b>${need}</b> of ${n} U used</span> · <span class="elev-key">waist ${d.waist_height_mm} mm</span></div>
      ${anyErr ? `<div class="elev-meta small">${errs ? `<span class="elev-err">${icon('error')}${plural(errs, 'error')}, see above</span>` : '<span class="muted">No errors</span>'}</div>` : ''}
      <div class="elev-body">
        <div class="elev-ruler" aria-hidden="true" style="height:${n * PX}px">${ruler}</div>
        <div class="elev-frame" style="height:${n * PX}px">${units}<div class="elev-waist" style="bottom:${(w - 1) * PX}px" aria-hidden="true"></div></div>
      </div>
      ${p.base_frame_mm ? `<div class="elev-base" aria-hidden="true">Base frame ${p.base_frame_mm} mm</div>` : ''}
      ${lost.length ? `<footer class="small elev-need">Not placed: ${lost.map((u) => esc(name(u))).join(', ')}</footer>` : ''}
      <footer class="muted small">${din.length ? `${plural(din.length, 'DIN-rail part')}: ${din.map((u) => esc(name(u))).join(', ')}` : 'No DIN-rail parts'} · no rack space</footer>
    </section>`;
  }

  /* ---------- the device table ---------- */
  const flag = (title) => ` <span class="flag" title="${esc(title)}" aria-label="${esc(title)}">${icon('warn')}</span>`;
  const ov = (u, fields, text) => (fields.some((f) => u.overridden.includes(f)) ? `<span class="ov-cell" title="Overridden for this design"><i class="ov-dot" aria-hidden="true"></i>${text}<span class="sr-only"> (overridden)</span></span>` : text);
  const mcb = (m) => (m ? `<span class="mono">${esc(m.tag)}</span> ${m.rating_a} A${m.at_minimum ? flag('At the branch minimum. Check the running and inrush current.') : ''}`
    : '<span class="muted">—</span>');
  function table() {
    const list = all().filter(({ p }) => !DP.filter || p.number === DP.filter), strips = all().some(({ u }) => u.strips.length);
    return `<p class="muted small dp-legend"><span class="flag">${icon('warn')}</span> an MCB at the branch minimum, a 0 W part or a missing part number · <i class="ov-dot" aria-hidden="true"></i> a value overridden on Parts</p>
      <div class="table-wrap"><table class="table dp-table"><caption class="sr-only">Devices with their panel, position and MCBs</caption>
      <thead><tr><th>Device</th><th>Part</th><th>Part number on the BOM</th><th>Panel</th><th class="num">U</th><th class="num">Watts</th><th>Supply</th><th>PS1 MCB</th><th>PS2 MCB</th>${strips ? '<th>Strip</th>' : ''}</tr></thead>
      <tbody>${list.map(({ u, p }) => { const id = uid(p, u); return `<tr data-uid="${esc(id)}" ${DP.sel === id ? 'aria-selected="true" class="is-sel"' : ''} data-action="dp-sel" tabindex="0">
        <td class="nowrap"><span class="mono">${esc(u.tag || '—')}</span><span class="cell-sub">${esc(u.label)}</span></td>
        <td class="mono nowrap">${esc(u.library_part_id)}</td>
        <td class="dp-pn">${u.has_part_number ? `<span class="mono">${esc(u.bom_code || '')}</span>` : `<span class="muted">${esc(u.bom_code || u.library_part_id)}</span>${flag('No part number: the BOM prints the library model')}`}</td>
        <td class="nowrap">${p.number}${p.side ? ' · ' + p.side.toUpperCase() : ''}</td>
        <td class="num nowrap">${u.pinned ? '<span class="pin-tag">Pinned</span> ' : ''}${u.din_rail ? '<span class="muted small">DIN rail</span>' : !u.placed ? '<span class="elev-need small">Not placed</span>' : ov(u, ['height_u'], span(u))}</td>
        <td class="num">${u.watts == null ? '<span class="muted">—</span>' : ov(u, ['unit_power_w'], String(u.watts))}${u.watts === 0 ? flag("0 W: check the part's power") : ''}</td>
        <td class="nowrap">${u.supply ? ov(u, ['supply_type', 'voltage_v'], esc(u.supply)) : '<span class="muted">—</span>'}</td>
        <td class="nowrap">${mcb(u.ps1)}</td><td class="nowrap">${mcb(u.ps2)}</td>${strips ? `<td class="mono">${esc(u.strips.join(', '))}</td>` : ''}</tr>`; }).join('')}</tbody></table>
      <div class="table-foot"><span>${plural(list.length, 'unit')}${DP.filter ? ` in panel ${DP.filter}` : ''} · positions, MCBs and strips come from the engine</span></div></div>`;
  }

  /* ---------- the selected unit: the keyboard path (Arrow Up and Down on a selected unit do the same) ---------- */
  function actionBar() {
    const h = DP.sel && hit(DP.sel); if (!h || !inRack(h.u)) return '';
    const { u, p } = h, st = DP.steps && DP.steps.id === DP.sel ? DP.steps : {}, pin = canPin();
    return `<div class="dp-bar" role="toolbar" aria-label="${esc(name(u))}"><span><span class="mono">${esc(name(u))}</span> <span class="muted">· panel ${p.number}, U ${span(u)}${u.pinned ? ' · pinned' : ''}</span></span>
      ${pin && st.up ? `<button class="btn btn--secondary btn--sm" data-action="dp-step" data-d="1">${icon('chevu')}Up 1 U</button>` : ''}${pin && st.down ? `<button class="btn btn--secondary btn--sm" data-action="dp-step" data-d="-1">${icon('chevd')}Down 1 U</button>` : ''}
      ${pin && u.pinned ? `<button class="btn btn--ghost btn--sm" data-action="dp-unpin">${icon('x')}Unpin</button>` : ''}${pin ? '<span class="muted small">Or drag it on the front view.</span>' : ''}</div>`;
  }
  SCREENS['device-preview'] = () => {
    const head = pageHead('Device preview', 'Where each device goes and what feeds it, before the workbook is built. Drag a device on a front view to pin it.', '<a class="btn btn--secondary" href="#/parts">Back to Parts</a>');
    if (!real()) return `<div class="page page--wide">${head}<div class="empty"><b>Open a substation first.</b></div></div>`;
    const d = load(); if (!d) return `<div class="page page--wide">${head}<p class="muted" aria-busy="true">Generating the preview…</p></div>`;
    if (d.reason) return `<div class="page page--wide">${head}${banner('bad', `<b>No preview.</b> ${esc(d.reason)}. Checks lists them.`, '<a class="btn btn--secondary btn--sm" href="#/checks">Open Checks</a>')}</div>`;
    const errs = issuesOf('error'), warns = issuesOf('warning');
    const goto = (i) => (i.device ? `<button class="link-btn small" data-action="dp-goto" data-device="${esc(i.device)}">Go to the row</button>` : '');
    return `<div class="page page--wide">${head}
      ${d.generated ? '' : `<div style="margin-bottom:var(--space-3)">${banner('info', '<b>Hand-written panels.</b> This shows what <span class="mono">bomgen layout</span> would place; Build uses your panel files. Lay out the panels from the equipment on Panels to pin devices here.', '<a class="btn btn--secondary btn--sm" href="#/panels">Open Panels</a>')}</div>`}
      ${DP.refusal ? `<div style="margin-bottom:var(--space-3)">${banner('bad', `<b>Not moved.</b> ${esc(DP.refusal)} Nothing was changed.`, `<button class="btn btn--ghost btn--icon btn--sm" data-action="dp-refusal-close" aria-label="Close">${icon('x')}</button>`)}</div>` : ''}
      ${errs.length ? `<div style="margin-bottom:var(--space-3)">${banner('bad', errs.length === 1 ? `${esc(sentence(errs[0].message))} ${goto(errs[0])}` : `<b>${plural(errs.length, 'error')}.</b><ul class="dp-issues">${errs.map((i) => `<li><span>${esc(sentence(i.message))}</span>${goto(i)}</li>`).join('')}</ul>`)}</div>` : ''}
      ${warns.length ? `<div style="margin-bottom:var(--space-4)">${banner('warn', `<b>${plural(warns.length, 'warning')} from the checks.</b><ul class="dp-issues">${warns.map((i) => `<li><span>${esc(sentence(i.message))}</span>${goto(i)}</li>`).join('')}</ul>`)}</div>` : ''}
      <div class="elev-strip" role="group" aria-label="Front view of each panel">${d.panels.map(elevation).join('')}</div>
      ${actionBar()}
      <div class="row dp-filter" role="group" aria-label="Show the devices of"><button class="chip" data-action="dp-filter" data-n="0" aria-pressed="${!DP.filter}">All panels</button>${d.panels.map((p) => `<button class="chip" data-action="dp-filter" data-n="${p.number}" aria-pressed="${DP.filter === p.number}">Panel ${p.number}<span class="count">${p.units.length}</span></button>`).join('')}</div>
      ${table()}</div>`;
  };

  /* ---------- selection, filter, Go to ---------- */
  const keep = (fn) => { const m = $('#main'), y = m ? m.scrollTop : 0; fn(); App.render(); if (m) m.scrollTop = y; };
  ACTIONS['dp-sel'] = (el) => {
    const id = el.dataset.uid;
    keep(() => { DP.sel = DP.sel === id ? '' : id; probeSteps(); });
    const row = $(`tr[data-uid="${CSS.escape(id)}"]`); if (row && el.tagName === 'BUTTON') row.scrollIntoView({ block: 'nearest' });
  };
  ACTIONS['dp-filter'] = (el) => keep(() => { const n = +el.dataset.n; DP.filter = DP.filter === n ? 0 : n; });
  ACTIONS['dp-goto'] = (el) => go(`#/parts/${encodeURIComponent(el.dataset.device)}`);
  ACTIONS['dp-refusal-close'] = () => keep(() => { DP.refusal = ''; });
  ACTIONS['dp-step'] = (el) => step(+el.dataset.d);
  ACTIONS['dp-unpin'] = () => {
    const h = hit(DP.sel); if (!h || !h.u.pinned || !canPin()) return;
    write(others(h.u, false), `Unpinned ${name(h.u)}. The layout places it again`);
  };
  document.addEventListener('keydown', (e) => {
    if (App.route().a !== 'device-preview' || !e.target.closest) return;
    const r = e.target.closest('tr[data-action="dp-sel"]'); if (r && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); r.click(); return; }
    const el = e.target.closest('.eu[data-uid]');
    if (el && DP.sel === el.dataset.uid && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) { e.preventDefault(); step(e.key === 'ArrowUp' ? 1 : -1); }
  });

  /* ---------- dragging on the front views (drag.js); Alt moves one unit of a pair ---------- */
  let drag = null;  // { id, u, from, alone, grab, at: {n, top}, fits: {"n:top": true|false}, why }
  const spot = (at) => `${at.n}:${at.top}`;
  function target(e) {
    const el = document.elementFromPoint(e.clientX, e.clientY), col = el && el.closest('.elev[data-panel]'); if (!col) return null;
    const fr = col.querySelector('.elev-frame').getBoundingClientRect(), n = DP.data.capacity_u;
    const fromTop = Math.max(0, Math.min(n - block(drag.u), Math.round((e.clientY - drag.grab - fr.top) / PX)));
    return { n: +col.dataset.panel, top: n - fromTop };
  }
  function probe(at) {
    const k = spot(at), d = drag; if (k in d.fits) return;
    if (!sideFits(d.u, at.n)) { d.fits[k] = false; d.why[k] = `A side ${d.u.side.toUpperCase()} unit goes in ${d.u.side === 'a' ? 'an odd' : 'an even'} panel.`; return; }
    d.fits[k] = undefined;
    Bridge.call('check_layout', S.project.file, S.sub, [...others(d.u, d.alone), moveOf(d.u, at.n, at.top, d.alone)], DP.data.removed)
      .then((r) => { if (drag === d) { d.fits[k] = r.fits; d.why[k] = r.issues[0] ? sentence(r.issues[0].message) : ''; paint(); } }).catch(() => {});
  }
  function paint() {
    $$('.elev.drop-ok, .elev.drop-bad').forEach((x) => x.classList.remove('drop-ok', 'drop-bad'));
    $$('.elev-ghost').forEach((x) => x.remove());
    document.body.classList.remove('is-drop-bad');
    if (!drag || !drag.at) return;
    const ok = drag.fits[spot(drag.at)], col = $(`.elev[data-panel="${drag.at.n}"]`); if (!col) return;
    if (ok !== undefined) col.classList.add(ok ? 'drop-ok' : 'drop-bad');
    document.body.classList.toggle('is-drop-bad', ok === false);
    if (ok !== false) col.querySelector('.elev-frame').insertAdjacentHTML('beforeend', `<div class="elev-ghost" style="top:${(DP.data.capacity_u - drag.at.top) * PX}px;height:${block(drag.u) * PX}px" aria-hidden="true">U ${drag.at.top}</div>`);
  }
  function endDrag(cancelled) {
    const d = drag; drag = null; paint();
    $$('.eu.is-dragging').forEach((x) => x.classList.remove('is-dragging')); document.body.classList.remove('is-dragging-dev');
    if (cancelled || !d.at || (d.at.n === d.from && d.at.top === d.u.top_u)) return;
    const k = spot(d.at);
    if (d.fits[k] === false) { keep(() => { DP.refusal = d.why[k] || `Panel ${d.at.n} cannot take ${name(d.u)} at U ${d.at.top}.`; }); return; }
    const move = moveOf(d.u, d.at.n, d.at.top, d.alone);
    write([...others(d.u, d.alone), move], `Pinned ${name(d.u)}${d.u.side && !d.alone ? ' and its pair' : ''} to panel ${d.at.n}, U ${d.at.top}${d.u.waist && d.at.top - block(d.u) + 1 !== DP.data.waist_u ? '. It is away from waist height' : ''}`);
  }
  App.pointerDrag({
    handle: '.eu[data-uid]',
    enabled: () => App.route().a === 'device-preview' && canPin(),
    start: (el, e) => {
      const h = hit(el.dataset.uid); if (!h || !inRack(h.u)) return false;
      drag = { id: el.dataset.uid, u: h.u, from: h.p.number, alone: e.altKey && !!h.u.side, grab: Math.max(0, e.clientY - el.getBoundingClientRect().top), at: null, fits: {}, why: {} };
      el.classList.add('is-dragging'); document.body.classList.add('is-dragging-dev');
      return true;
    },
    move: (e) => { drag.at = target(e); if (drag.at) probe(drag.at); paint(); },
    drop: () => endDrag(false),
    cancel: () => endDrag(true)
  });
  /* Parts saves change the units: the next visit generates the preview again. */
  App.devicePreview = { reload };
})();
