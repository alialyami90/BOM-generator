/* Screen: Device preview (M22, part picking design §6). Each device with its panel, rack position and MCBs, and a
   front view of each panel, before the workbook is built. Read-only except dragging on the front views, which
   pins a unit as the Panels board does (editing.md, Drag and drop contract). The engine places; this only draws. */
(function () {
  const { esc, S, ACTIONS, SCREENS, banner, pageHead, illus, toast, go, $, $$ } = App;
  const PX = 18;  // px per rack unit on the front view
  const st = () => S.previewState || 'clean';
  const P = () => DB.preview;
  const rowOf = (key) => DB.partRows().find((r) => r.key === key);
  const waistU = () => Math.round((P().waistMm - P().rackStartMm) / 44.45);

  function state() {
    if (S.dp && S.dp.state === st()) return S.dp;
    const panels = JSON.parse(JSON.stringify(P().panels));
    if (st() === 'overflow') panels[0].units.push(U('PSA1-IO-01', 11, 4, 120), U('PSA1-IO-02', 7, 4, 120), U('PSA1-RTAC-01', 3, 3, 60));
    if (st() === 'nowaist') { const c = panels[1].units.find((u) => u.tag === 'PSA2-CON-01'); c.top = 9; c.noWaist = true; panels[1].units.find((u) => u.tag === 'PSA2-DA-B01').top = 20; }
    S.dp = { state: st(), panels, sel: '', filter: 0, history: [], refusal: '' };
    return S.dp;
  }
  function U(tag, top, h, w) {  // illustrative extra units for the overflow state
    return { tag, row: 'io', part: tag.includes('RTAC') ? 'SEL-3555-RTAC' : 'AXION-IO-RACK', pn: tag.includes('RTAC') ? 'SEL-3555-RTAC' : 'AXION-4U', top, h, w, supply: '125 VDC', mcb1: ['PSA1-F' + (30 + top), 4], mcb2: ['PSA1-F' + (40 + top), 4], strip: 'X2' };
  }
  const NOT_DRAWN = 7;  // overflow state: the RTAC I/O rack the engine could not place
  const errorsOf = (p) => (st() === 'overflow' && p.n === 1 ? [`${p.name} needs ${p.units.reduce((a, u) => a + u.h, 0) + NOT_DRAWN} U, only ${P().usableU} U may be used. The RTAC I/O rack (${NOT_DRAWN} U) is not drawn. Move a device to panel 3, or raise the rack space on Settings.`]
    : st() === 'nowaist' && p.n === 2 ? [`The console cannot sit just above the waist line (U ${waistU() + 1}): the DA server is there. Pin the DA server lower, or pin the console where it fits.`] : []);
  const allUnits = () => state().panels.flatMap((p) => p.units.map((u) => ({ u, p })));
  const occupied = (p, skip) => p.units.filter((u) => u.h > 0 && u.tag !== skip).map((u) => [u.top - u.h + 1, u.top]);
  const fits = (p, u, top) => top - u.h + 1 >= 1 && top <= P().usableU && occupied(p, u.tag).every(([lo, hi]) => top < lo || top - u.h + 1 > hi);
  const sideOk = (u, p) => !u.tag.includes('-A0') && !u.tag.includes('-B0') ? true : (u.tag.includes('-A0') ? p.side === 'A' : p.side === 'B');

  /* ---------- one front view ---------- */
  function elevation(p) {
    const d = state(), n = P().usableU, used = p.units.reduce((a, u) => a + u.h, 0), w = waistU();
    const errs = errorsOf(p), over = st() === 'overflow' && p.n === 1, need = used + (over ? NOT_DRAWN : 0);
    const din = p.units.filter((u) => !u.h);
    const units = p.units.filter((u) => u.h).map((u) => {
      const sel = d.sel === u.tag, atWaist = u.kvm && u.top - u.h === w, off = u.kvm && !atWaist;
      const row = rowOf(u.row);
      return `<button class="eu${u.cm ? ' has-cm' : ''}${sel ? ' is-sel' : ''}${u.pinned ? ' is-pinned' : ''}${off ? ' is-off' : ''}" data-action="dp-sel" data-tag="${esc(u.tag)}" aria-pressed="${sel}"
        style="top:${(n - u.top) * PX}px;height:${u.h * PX}px" aria-label="${esc(u.tag)}, ${esc(u.part)}, U ${u.top}, ${u.cm ? `${u.h - u.cm} U and a cable manager` : `${u.h} U`}${u.pinned ? ', pinned' : ''}${off ? ', away from waist height' : ''}" title="${esc(row ? row.label : '')} · ${esc(u.part)}">
        <span class="eu-tag">${esc(u.tag)}</span>${u.pinned ? `<span class="eu-flag">${icon('pin')}</span>` : ''}${atWaist ? `<span class="eu-flag eu-flag--ok" title="Bottom edge at waist height">${icon('check')}</span>` : ''}${off ? `<span class="eu-flag eu-flag--warn" title="${u.noWaist ? 'Cannot sit at waist height in this panel' : 'Pinned away from waist height'}">${icon('warn')}</span>` : ''}<span class="eu-h">${u.cm ? `${u.h - u.cm} U + CM` : `${u.h} U`}</span>${u.cm ? '<span class="eu-cm" aria-hidden="true">Cable manager</span>' : ''}</button>`;
    }).join('');
    const ruler = Array.from({ length: Math.floor(n / 5) }, (_, i) => (i + 1) * 5).filter((k) => Math.abs(k - w) > 1).map((k) => `<span style="bottom:${k * PX - 7}px">${k}</span>`).join('') + `<span class="elev-ruler-waist" style="bottom:${w * PX - 7}px" title="Waist height ${P().waistMm} mm">${w}</span>`;
    return `<section class="elev${d.filter === p.n ? ' is-filtered' : ''}" data-panel="${p.n}" aria-label="${esc(p.name)}, side ${p.side}, ${need} of ${n} U used">
      <header><button class="link-btn elev-name" data-action="dp-filter" data-n="${p.n}" aria-pressed="${d.filter === p.n}" title="Show only this panel's devices">${esc(p.name)}</button><span class="badge badge--plain">Side ${p.side}</span></header>
      <div class="elev-meta muted small"><span${need > n ? ' class="elev-need"' : ''}><b>${need}</b> of ${n} U used</span> · <span class="elev-key">waist ${P().waistMm} mm</span></div>
      ${d.panels.some((x) => errorsOf(x).length) ? `<div class="elev-meta small">${errs.length ? `<span class="elev-err">${icon('error')}${errs.length} error, see above</span>` : '<span class="muted">No errors</span>'}</div>` : ''}
      <div class="elev-body">
        <div class="elev-ruler" aria-hidden="true" style="height:${n * PX}px">${ruler}</div>
        <div class="elev-frame" style="height:${n * PX}px">
          ${units}
          <div class="elev-waist" style="bottom:${w * PX}px" aria-hidden="true"></div>
        </div>
      </div>
      <div class="elev-base" aria-hidden="true">Base frame ${P().baseMm} mm</div>
      <footer class="muted small">${din.length ? `${din.length} DIN-rail part${din.length === 1 ? '' : 's'}: ${din.map((u) => esc(u.tag)).join(', ')}` : 'No DIN-rail parts'} · no rack space</footer>
    </section>`;
  }

  /* ---------- the device table ---------- */
  const ovMark = (u, k, text) => (u.ov && u.ov.includes(k) ? `<span class="ov-cell" title="Overridden for this design"><i class="ov-dot" aria-hidden="true"></i>${text}<span class="sr-only"> (overridden)</span></span>` : text);
  const mcb = (m) => (!m ? '<span class="muted">—</span>' : `<span class="mono">${esc(m[0])}</span> ${m[1]} A${m[2] === 'min' ? ` <span class="flag" title="At the 2 A minimum. Check the running and inrush current." aria-label="At the 2 A minimum">${icon('warn')}</span>` : ''}`);
  function table() {
    const d = state(), list = allUnits().filter(({ p }) => !d.filter || p.n === d.filter);
    return `<p class="muted small dp-legend"><span class="flag">${icon('warn')}</span> an MCB at the 2 A minimum, a 0 W part or a missing part number · <i class="ov-dot" aria-hidden="true"></i> a value overridden on Parts</p>
      <div class="table-wrap"><table class="table dp-table"><caption class="sr-only">Devices with their panel, position and MCBs</caption>
      <thead><tr><th>Device</th><th>Part</th><th>Part number on the BOM</th><th>Panel</th><th class="num">U</th><th class="num">Watts</th><th>Supply</th><th>PS1 MCB</th><th>PS2 MCB</th><th>Strip</th></tr></thead>
      <tbody>${list.map(({ u, p }) => { const row = rowOf(u.row); return `<tr data-tag="${esc(u.tag)}" ${d.sel === u.tag ? 'aria-selected="true" class="is-sel"' : ''} data-action="dp-sel" tabindex="0">
        <td class="nowrap"><span class="mono">${esc(u.tag)}</span><span class="cell-sub">${esc(row ? row.label : '')}</span></td>
        <td class="mono nowrap">${esc(u.part)}</td>
        <td class="nowrap">${u.nopn ? `<span class="muted">${esc(u.part)}</span> <span class="flag" title="No part number: the BOM prints the library model">${icon('warn')}</span>` : `<span class="mono">${esc(u.pn)}</span>`}</td>
        <td class="nowrap">${p.n} · ${p.side}</td>
        <td class="num nowrap">${u.pinned ? '<span class="pin-tag">Pinned</span> ' : ''}${u.h ? `${ovMark(u, 'h', `${u.h > 1 ? (u.top - u.h + 1) + '–' : ''}${u.top}`)}` : '<span class="muted small">DIN rail</span>'}</td>
        <td class="num">${ovMark(u, 'w', String(u.w))}${u.w === 0 ? ` <span class="flag" title="0 W: check the part's power">${icon('warn')}</span>` : ''}</td>
        <td class="nowrap">${esc(u.supply)}</td><td class="nowrap">${mcb(u.mcb1)}</td><td class="nowrap">${mcb(u.mcb2)}</td><td class="mono">${esc(u.strip)}</td></tr>`; }).join('')}</tbody></table>
      <div class="table-foot"><span>${list.length} units${d.filter ? ` in panel ${d.filter}` : ''} · MCBs and strips come from the engine</span><span>${illus()}</span></div></div>`;
  }

  /* ---------- the selected unit: the keyboard path (Arrow Up and Down on a selected unit do the same) ---------- */
  function actionBar() {
    const hit = allUnits().find(({ u }) => u.tag === state().sel && u.h); if (!hit) return '';
    const { u, p } = hit, up = fits(p, u, u.top + 1), down = fits(p, u, u.top - 1);
    return `<div class="dp-bar" role="toolbar" aria-label="${esc(u.tag)}"><span><span class="mono">${esc(u.tag)}</span> <span class="muted">· panel ${p.n}, U ${u.h > 1 ? `${u.top - u.h + 1}–` : ''}${u.top}${u.pinned ? ' · pinned' : ''}</span></span>
      ${up ? `<button class="btn btn--secondary btn--sm" data-action="dp-step" data-d="1">${icon('chevu')}Up 1 U</button>` : ''}${down ? `<button class="btn btn--secondary btn--sm" data-action="dp-step" data-d="-1">${icon('chevd')}Down 1 U</button>` : ''}
      ${u.pinned ? `<button class="btn btn--ghost btn--sm" data-action="dp-unpin">${icon('x')}Unpin</button>` : ''}<span class="muted small">Or drag it on the front view.</span></div>`;
  }
  SCREENS['device-preview'] = () => {
    const d = state();
    const head = pageHead('Device preview', 'Where each device goes and what feeds it, before the workbook is built. Drag a device on a front view to pin it.', '<a class="btn btn--secondary" href="#/parts">Back to Parts</a>');
    if (st() === 'error') return `<div class="page page--wide">${head}${banner('bad', '<b>No preview.</b> The L1 switch on Parts is RST2228-L1-OLD, which is not in psa-devices 1.4.0. Pick another part for that row.', '<button class="btn btn--secondary btn--sm" data-action="dp-goto" data-row="l1">Go to the row</button>')}</div>`;
    const offWaist = allUnits().filter(({ u }) => u.kvm && u.pinned && u.top - u.h !== waistU()).map(({ u }) => ({ msg: `${u.tag} is pinned away from waist height, at U ${u.top}.`, row: u.row }));
    const issues = P().issues.concat(offWaist), errs = d.panels.flatMap(errorsOf);
    return `<div class="page page--wide">${head}
      ${st() === 'unsaved' ? `<div style="margin-bottom:var(--space-3)">${banner('info', 'Parts has unsaved changes. This preview shows the saved parts. Save on Parts, then generate the preview again.')}</div>` : ''}
      ${d.refusal ? `<div style="margin-bottom:var(--space-3)">${banner('bad', `<b>Not moved.</b> ${esc(d.refusal)} Nothing was changed.`, `<button class="btn btn--ghost btn--icon btn--sm" data-action="dp-refusal-close" aria-label="Close">${icon('x')}</button>`)}</div>` : ''}
      ${errs.length ? `<div style="margin-bottom:var(--space-3)">${banner('bad', errs.length === 1 ? errs[0] : `<ul class="dp-issues">${errs.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>`)}</div>` : ''}
      ${issues.length ? `<div style="margin-bottom:var(--space-4)">${banner('warn', `<b>${issues.length} warnings from the checks.</b><ul class="dp-issues">${issues.map((i) => `<li><span>${esc(i.msg)}</span><button class="link-btn small" data-action="dp-goto" data-row="${esc(i.row)}">Go to the row</button></li>`).join('')}</ul>`)}</div>` : ''}
      <div class="elev-strip" role="group" aria-label="Front view of each panel">${d.panels.map(elevation).join('')}</div>
      ${actionBar()}
      <div class="row dp-filter" role="group" aria-label="Show the devices of"><button class="chip" data-action="dp-filter" data-n="0" aria-pressed="${!d.filter}">All panels</button>${d.panels.map((p) => `<button class="chip" data-action="dp-filter" data-n="${p.n}" aria-pressed="${d.filter === p.n}">Panel ${p.n}<span class="count">${p.units.length}</span></button>`).join('')}</div>
      ${table()}</div>`;
  };

  /* ---------- selection, filter, Go to ---------- */
  const keep = (fn) => { const y = $('#main').scrollTop; fn(); App.render(); $('#main').scrollTop = y; };
  ACTIONS['dp-sel'] = (el) => {
    if (swallow) { swallow = false; return; }
    const tag = el.dataset.tag;
    keep(() => { const d = state(); d.sel = d.sel === tag ? '' : tag; });
    const row = $(`tr[data-tag="${CSS.escape(tag)}"]`); if (row && el.tagName === 'BUTTON') row.scrollIntoView({ block: 'nearest' });
  };
  ACTIONS['dp-filter'] = (el) => keep(() => { const d = state(), n = +el.dataset.n; d.filter = d.filter === n ? 0 : n; });
  ACTIONS['dp-goto'] = () => go('#/parts');  // the built app scrolls to and focuses the row
  ACTIONS['dp-refusal-close'] = () => keep(() => { state().refusal = ''; });
  document.addEventListener('keydown', (e) => { const r = e.target.closest && e.target.closest('tr[data-action="dp-sel"]'); if (r && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); r.click(); } });

  /* ---------- dragging on the front views: pointer events, as the board (M19) ---------- */
  let press = null, drag = null, swallow = false;
  const target = (e) => {
    const el = document.elementFromPoint(e.clientX, e.clientY), col = el && el.closest('.elev[data-panel]'); if (!col) return null;
    const fr = col.querySelector('.elev-frame').getBoundingClientRect();
    const fromTop = Math.max(0, Math.min(P().usableU - 1, Math.floor((e.clientY - drag.grab - fr.top) / PX)));
    return { n: +col.dataset.panel, top: P().usableU - fromTop };
  };
  function paint() {
    $$('.elev.drop-ok, .elev.drop-bad').forEach((x) => x.classList.remove('drop-ok', 'drop-bad'));
    $$('.elev-ghost').forEach((x) => x.remove());
    if (!drag || !drag.at) return;
    const p = state().panels.find((x) => x.n === drag.at.n), ok = sideOk(drag.u, p) && fits(p, drag.u, drag.at.top);
    const col = $(`.elev[data-panel="${drag.at.n}"]`); col.classList.add(ok ? 'drop-ok' : 'drop-bad');
    if (ok) col.querySelector('.elev-frame').insertAdjacentHTML('beforeend', `<div class="elev-ghost" style="top:${(P().usableU - drag.at.top) * PX}px;height:${drag.u.h * PX}px" aria-hidden="true">U ${drag.at.top}</div>`);
  }
  function end(cancelled) {
    const d = drag; drag = null; press = null; swallow = true; paint();
    $$('.eu.is-dragging').forEach((x) => x.classList.remove('is-dragging')); document.body.classList.remove('is-dragging-dev');
    if (cancelled || !d.at) return;
    const s = state(), to = s.panels.find((x) => x.n === d.at.n), u = d.u;
    if (to === d.from && d.at.top === u.top) return;
    if (!sideOk(u, to)) { keep(() => { s.refusal = `A side ${d.from.side} unit goes in ${d.from.side === 'A' ? 'an odd' : 'an even'} panel.`; }); return; }
    if (!fits(to, u, d.at.top)) { keep(() => { s.refusal = `${to.name} has no free ${u.h} U at U ${d.at.top}.`; }); return; }
    pin(u, d.from, to, d.at.top);
  }
  function pin(u, from, to, top) {
    const s = state(); s.history.push(JSON.stringify(s.panels));
    keep(() => { if (!u.pinned) { u.home = [from.n, u.top]; } from.units = from.units.filter((x) => x !== u); to.units.push(u); u.top = top; u.pinned = true; s.sel = u.tag; s.refusal = ''; });
    const off = u.kvm && u.top - u.h !== waistU();
    toast(`Pinned ${u.tag} to panel ${to.n}, U ${u.top}${off ? '. It is away from waist height' : ''}`, 'pin', () => keep(() => { s.panels = JSON.parse(s.history.pop()); }));
  }
  const selHit = () => allUnits().find(({ u }) => u.tag === state().sel && u.h);
  ACTIONS['dp-step'] = (el) => { const h = selHit(); if (h && fits(h.p, h.u, h.u.top + +el.dataset.d)) { pin(h.u, h.p, h.p, h.u.top + +el.dataset.d); const b = $(`[data-action="dp-step"][data-d="${el.dataset.d}"]`); if (b) b.focus(); } };
  ACTIONS['dp-unpin'] = () => {
    const h = selHit(); if (!h || !h.u.home) return;
    const s = state(), u = h.u, home = s.panels.find((x) => x.n === u.home[0]); s.history.push(JSON.stringify(s.panels));
    keep(() => { h.p.units = h.p.units.filter((x) => x !== u); home.units.push(u); u.top = u.home[1]; u.pinned = false; delete u.home; });
    toast(`Unpinned ${u.tag}. The layout places it again, at U ${u.top}`, 'pin', () => keep(() => { s.panels = JSON.parse(s.history.pop()); }));
  };
  document.addEventListener('keydown', (e) => {
    const el = e.target.closest && e.target.closest('.eu[data-tag]'); if (!el || drag || !['ArrowUp', 'ArrowDown'].includes(e.key) || state().sel !== el.dataset.tag) return;
    e.preventDefault(); const h = selHit(), dd = e.key === 'ArrowUp' ? 1 : -1;
    if (h && fits(h.p, h.u, h.u.top + dd)) { pin(h.u, h.p, h.p, h.u.top + dd); const n = $(`.eu[data-tag="${CSS.escape(h.u.tag)}"]`); if (n) n.focus(); }
  });
  document.addEventListener('pointerdown', (e) => {
    swallow = false;
    const el = e.target.closest && e.target.closest('.eu[data-tag]'); if (!el || e.button !== 0) return;
    press = { el, x: e.clientX, y: e.clientY, id: e.pointerId, grab: e.clientY - el.getBoundingClientRect().top };
  });
  document.addEventListener('pointermove', (e) => {
    if (drag) { if (e.pointerId === drag.id) { drag.at = target(e); paint(); } return; }
    if (!press || e.pointerId !== press.id || Math.hypot(e.clientX - press.x, e.clientY - press.y) < 4) return;
    const hit = allUnits().find(({ u }) => u.tag === press.el.dataset.tag); if (!hit) { press = null; return; }
    drag = { u: hit.u, from: hit.p, id: press.id, grab: press.grab, at: null };
    try { press.el.setPointerCapture(press.id); } catch (_) { /* pointer gone */ }
    press.el.classList.add('is-dragging'); document.body.classList.add('is-dragging-dev');
    drag.at = target(e); paint();
  });
  document.addEventListener('pointerup', (e) => { press = null; if (drag && e.pointerId === drag.id) end(false); });
  document.addEventListener('pointercancel', (e) => { press = null; if (drag && e.pointerId === drag.id) end(true); });
  document.addEventListener('keydown', (e) => { if (drag && e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); end(true); } }, true);
})();
