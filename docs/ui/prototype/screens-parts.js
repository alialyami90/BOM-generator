/* Screen: Parts (M22, part picking design §3). Replaces Network: the network inputs, one row per device type with
   its library part, the BOM part number and this design's overrides, and the catalogue brands. A form page. */
(function () {
  const { esc, S, ACTIONS, SCREENS, banner, field, input, select, pageHead, illus, toast, go, $, $$ } = App;
  const st = () => S.partsState || 'clean';  // clean | new | invalid | missing | many
  const isNew = () => App.isBlank() || st() === 'new';
  const lib = (cat, id) => (DB.partLib[cat] || []).find((p) => p.id === id) || null;
  const anyPart = (id) => Object.values(DB.partLib).flat().find((p) => p.id === id) || null;

  /* Rows live in S.pp so edits survive re-renders; the prototype state picks the starting set. */
  function rows() {
    if (S.pp && S.pp.state === st() && S.pp.sub === S.sub) return S.pp.rows;
    let r = DB.partRows();
    if (isNew()) r = r.filter((x) => !x.added).map((x) => ({ ...x, part: '', pn: '', ov: {}, acc: x.acc ? [] : undefined, sfp: x.sfp ? x.sfp.map((f) => ({ ...f, part: '' })) : undefined }));
    if (st() === 'missing') r[1] = { ...r[1], part: 'RST2228-L2-OLD' };
    if (st() === 'invalid') r[3] = { ...r[3], ov: { w: 'approx 180' } };
    if (st() === 'many') for (let i = 0; i < 12; i++) r.push({ key: 'io' + i, label: 'I/O rack', cat: 'io_rack', part: 'AXION-IO-RACK', pn: 'AXION-' + (i + 1), qty: 1, ab: true, ov: i % 4 ? {} : { w: 55 }, added: true });
    ft().ied = isNew() ? '' : (ft().ied || '40');
    S.pp = { state: st(), sub: S.sub, rows: r, open: { tuning: isNew() }, editing: '', menu: -1, expanded: new Set() };
    if (st() === 'invalid') { S.dirty = true; S.changed.add('ov-ows-w'); S.invalid.add('ov-ows-w'); }
    return r;
  }
  const many = () => rows().length >= 20;

  /* ---------- details strip ---------- */
  const KEYS = [['h', 'Height', (v) => (+v ? `${v} U` : 'DIN rail')], ['w', 'Power', (v) => `${v} W`], ['supply', 'Supply', (v) => (v ? `${v}` : '—')], ['v', 'Voltage', (v) => (v ? `${v} V` : '—')],
    ['ps', 'Supplies', (v) => `${v}`], ['inrush', 'Inrush', (v) => `${v} A`], ['load', 'Load', (v) => ({ continuous: 'Continuous', intermittent: 'Intermittent' }[v] || '—')]];
  const LOADS = [['continuous', 'Continuous'], ['intermittent', 'Intermittent']];
  const badNumber = (v) => typeof v === 'string' && !/^\d+(\.\d+)?$/.test(v.trim());
  function strip(r, i) {
    const sized = (r.qty === 'sized') && !r.part;
    if (sized) return `<div class="prow-strip"><span class="muted small">Pick the switch to change its data.</span></div>`;
    const p = lib(r.cat, r.part);
    if (!r.part) return `<div class="prow-strip"><span class="muted small">Pick a part to see its data.</span></div>`;
    if (!p) return '<div class="prow-strip"></div>';
    if (!p.supply && !p.h) return `<div class="prow-strip"><span class="muted small">Passive part: no rack space, no power.</span></div>`;
    const keys = p.supply ? KEYS : KEYS.filter(([k]) => k === 'h');  // an unpowered part has only a height
    const n = Object.keys(r.ov).length;
    if (many() && !S.pp.expanded.has(i)) {
      return `<div class="prow-strip"><button class="link-btn small prow-summary" data-action="pp-expand" data-i="${i}" aria-label="Show the data of ${esc(r.label)}">${[KEYS[0][2](r.ov.h ?? p.h), `${r.ov.w ?? p.w} W`, p.supply ? `${r.ov.v ?? p.v} V${r.ov.supply ?? p.supply}` : ''].filter(Boolean).join(' · ')}${n ? ` · <i class="ov-dot" aria-hidden="true"></i>${n} override${n === 1 ? '' : 's'}` : ''}</button></div>`;
    }
    const vals = keys.map(([k, label, fmt]) => {
      const has = Object.prototype.hasOwnProperty.call(r.ov, k), val = has ? r.ov[k] : p[k], id = `ov-${r.key}-${k}`;
      if (S.pp.editing === `${i}:${k}`) {
        const ctl = k === 'load' ? `<select class="select dv-input" id="${id}" data-dv="${i}:${k}">${LOADS.map(([v, t]) => `<option value="${v}" ${v === val ? 'selected' : ''}>${t}</option>`).join('')}</select>`
          : k === 'supply' ? `<select class="select dv-input" id="${id}" data-dv="${i}:${k}">${['DC', 'AC'].map((v) => `<option ${v === val ? 'selected' : ''}>${v}</option>`).join('')}</select>`
          : `<input class="input input--mono input--num dv-input" id="${id}" data-dv="${i}:${k}" value="${esc(val)}" aria-label="${label} of ${esc(r.label)}">`;
        return `<span class="dv is-editing"><span class="dv-label">${label}</span>${ctl}</span>`;
      }
      const bad = has && badNumber(val);
      return `<span class="dv${has ? ' is-ov' : ''}${bad ? ' is-bad' : ''}"><button class="dv-btn" data-action="pp-edit" data-i="${i}" data-k="${k}" aria-label="${label} ${esc(bad ? val : fmt(val))}${has ? `, overridden; library ${esc(fmt(p[k]))}` : ''}. Change">
          <span class="dv-label">${label}</span><span class="dv-val">${has ? '<i class="ov-dot" aria-hidden="true"></i>' : ''}${esc(bad ? val : fmt(val))}</span></button>${has ? `<span class="dv-lib">Library ${esc(fmt(p[k]))}</span><button class="btn btn--ghost btn--icon btn--xs" data-action="pp-reset" data-i="${i}" data-k="${k}" aria-label="Reset ${label.toLowerCase()} to the library's ${esc(fmt(p[k]))}" title="Reset to the library value">${icon('undo')}</button>` : ''}</span>`;
    }).join('');
    const err = KEYS.filter(([k]) => badNumber(r.ov[k])).map(([, label]) => `<span class="err small" id="ov-${r.key}-err">${icon('error')}<span>${label}: enter a number, for example ${label === 'Power' ? '180 W' : '2'}.</span></span>`).join('');
    return `<div class="prow-strip">${vals}${n ? `<button class="btn btn--ghost btn--sm" data-action="pp-reset-all" data-i="${i}">Reset all</button>` : ''}</div>${err ? `<div class="prow-err">${err}</div>` : ''}`;
  }

  /* ---------- one part row ---------- */
  function partSelect(r, i) {
    const opts = DB.partLib[r.cat] || [];
    const sized = r.qty === 'sized';
    const missing = r.part && !lib(r.cat, r.part);
    const first = sized ? `<option value="" ${!r.part ? 'selected' : ''}>The sizing picks the switch</option>` : `<option value="" ${!r.part ? 'selected' : ''} disabled>Pick a part</option>`;
    return `<div class="prow-partwrap"><select class="select prow-part${missing ? ' is-missing' : ''}" id="pp-part-${r.key}" data-pp="${i}" aria-label="Part for ${esc(r.label)}" ${missing ? 'aria-invalid="true" aria-describedby="pp-part-' + r.key + '-err"' : ''}>
        ${first}${missing ? `<option selected>${esc(r.part)}</option>` : ''}${opts.map((p) => `<option value="${esc(p.id)}" ${p.id === r.part ? 'selected' : ''}>${esc(p.id)} · ${esc(p.make)} ${esc(p.model)}</option>`).join('')}</select>
      ${missing ? `<span class="err small" id="pp-part-${r.key}-err">${icon('error')}<span>Not in ${esc(DB.library.name)} ${esc(DB.library.version)}. Pick another part.</span></span>` : ''}</div>`;
  }
  function partRow(r, i) {
    const changed = S.changed.has('pp-row-' + r.key) || Object.keys(r.ov).some((k) => S.changed.has(`ov-${r.key}-${k}`));
    const fixed = r.key === 'l1' || r.key === 'l2';
    const p = lib(r.cat, r.part);
    const pnId = `pp-pn-${r.key}`;
    return `<div class="prow" role="group" aria-label="${esc(r.label)}${r.part ? ', ' + esc(r.part) : ', no part yet'}">
      <div class="prow-top">
        <span class="prow-role">${changed ? '<span class="chg-dot" aria-hidden="true"></span><span class="sr-only">changed, </span>' : ''}${esc(r.label)}</span>
        <span class="sp"></span>
        <label class="check prow-ab"><input type="checkbox" ${r.ab ? 'checked' : ''} data-dirty="1" id="pp-ab-${r.key}"> A and B</label>
        <div class="prow-menu-wrap"><button class="btn btn--ghost btn--icon btn--sm" data-action="pp-menu" data-i="${i}" aria-haspopup="menu" aria-expanded="${S.pp.menu === i}" aria-label="More for ${esc(r.label)}">${icon('dots')}</button>
          ${S.pp.menu === i ? `<div class="menu" role="menu" style="right:0;top:34px"><button role="menuitem" data-action="pp-move" data-i="${i}" data-d="-1" ${i === 0 ? 'disabled' : ''}>Move up</button><button role="menuitem" data-action="pp-move" data-i="${i}" data-d="1" ${i === rows().length - 1 ? 'disabled' : ''}>Move down</button>${fixed ? '' : `<hr><button role="menuitem" class="danger" data-action="pp-remove" data-i="${i}">${icon('trash')}Remove</button>`}</div>` : ''}</div>
      </div>
      <div class="prow-fields">
        ${partSelect(r, i)}
        <div class="prow-pn"><label class="sr-only" for="${pnId}">Part number for ${esc(r.label)}</label><input class="input input--mono" id="${pnId}" value="${esc(r.pn)}" placeholder="${p ? `Prints ${esc(p.id)}` : 'Part number'}" data-dirty="1" ${!r.part ? 'disabled' : ''}></div>
        <div class="prow-qty">${r.qty === 'sized' ? '<span class="muted small" title="The sizing sets the quantity">Sized</span>' : `<label class="sr-only" for="pp-qty-${r.key}">Quantity of ${esc(r.label)}</label>${input('pp-qty-' + r.key, r.qty, { num: true, mono: true })}`}</div>
      </div>
      ${strip(r, i)}
      ${r.sfp ? r.sfp.map((f, j) => `<div class="prow-sub"><span class="prow-sub-what">${esc(f.speed)} · ${esc(f.media)} SFP <span class="muted">· ${f.need} needed</span></span>
          <select class="select" id="pp-sfp-${r.key}-${j}" data-dirty="1" aria-label="SFP for ${esc(f.speed)} ${esc(f.media)}"><option value="">Automatic: ${esc(DB.partLib.sfp.find((x) => x.model.includes(f.media === 'Multi-mode' ? 'multi' : 'single')).id)}, same make first</option>${DB.partLib.sfp.filter((x) => x.model.includes(f.media === 'Multi-mode' ? 'multi' : 'single')).map((x) => `<option ${x.id === f.part ? 'selected' : ''}>${esc(x.id)} · ${esc(x.make)} ${esc(x.model)}</option>`).join('')}</select></div>`).join('') : ''}
      ${r.acc ? `${r.acc.map((a, j) => `<div class="prow-sub"><span class="prow-sub-what">Accessory</span><select class="select" id="pp-acc-${j}" data-dirty="1" aria-label="Time accessory ${j + 1}">${DB.partLib.time_accessory.map((x) => `<option ${x.id === a.part ? 'selected' : ''}>${esc(x.id)} · ${esc(x.model)}</option>`).join('')}</select>
          <div class="prow-qty">${input('pp-accq-' + j, a.qty, { num: true, mono: true }).replace('<input ', '<input aria-label="Quantity" ')}</div><button class="btn btn--ghost btn--icon btn--sm" data-action="pp-acc-remove" data-j="${j}" aria-label="Remove ${esc(anyPart(a.part) ? anyPart(a.part).model : a.part)}">${icon('trash')}</button></div>`).join('')}
        <div class="prow-sub prow-sub--foot"><button class="btn btn--ghost btn--sm" data-action="pp-acc-add">${icon('plus')}Add accessory</button><span class="muted small">Accessories go to loose material.</span></div>` : ''}
    </div>`;
  }

  /* ---------- page ---------- */
  const ft = () => (S.ft = S.ft || { ...DB.fineTuning, topology: 'star', ied: '40' });
  function tuning() {
    const f = ft(), open = S.pp.open.tuning, ring = f.topology === 'ring';
    const summary = `${ring ? `Ring of ${f.ringMax}` : 'Star'} · ${f.l1Uplinks} uplink per L1 · ${f.interlink === 'Yes' ? 'A–B interlink' : 'no interlink'} · ${f.portPercent}% ports kept free · ${f.rackU} U kept free`;
    return `<div class="disclosure"><button class="disclosure-head" data-action="pp-tuning" aria-expanded="${open}" aria-controls="ft-body">${icon(open ? 'chevd' : 'chevr')}<b>Network fine tuning</b><span class="muted small">${open ? 'Ring size, uplinks and spares' : esc(summary)}</span></button>
      ${open ? `<div id="ft-body" class="form form--3 disclosure-body">
        ${ring ? field('Switches per ring', input('ft-ring', f.ringMax, { num: true, mono: true }), 'Most L1 switches in one ring.') : ''}
        ${field('L1 uplinks per switch', input('ft-up', f.l1Uplinks, { num: true, mono: true }))}
        ${field('A–B interlink', select('ft-il', ['Yes', 'No'], f.interlink))}
        ${field('L3 uplinks per L2', input('ft-l3', f.l3Uplinks, { num: true, mono: true }))}
        ${field('Ports kept free on each switch', `<div class="input-affix">${input('ft-port', f.portPercent, { num: true, mono: true })}<span class="affix">%</span></div>`)}
        ${field('Spare DC branches per feed', input('ft-dc', f.dcBranches, { num: true, mono: true }))}
        ${field('Spare AC branches', input('ft-ac', f.acBranches, { num: true, mono: true }))}
        ${field('Rack space kept free', `<div class="input-affix">${input('ft-u', f.rackU, { num: true, mono: true })}<span class="affix">U</span></div>`)}
      </div>` : ''}</div>`;
  }
  function setupCard() {
    const r = rows(), picked = r.filter((x) => x.part).length, hasIed = +ft().ied > 0;
    const step = (done, now, title, text) => `<li class="${done ? 'done' : now ? 'now' : ''}">${icon(done ? 'check' : 'info')}<div><b>${title}</b><div class="muted small">${text}</div></div></li>`;
    return `<div class="setup" style="margin-bottom:var(--space-5)"><h3>Set up ${esc(App.curSub().name)}</h3><p class="muted small" style="margin-top:var(--space-1)">Pick a part for each device. The panels are laid out from the picks.</p>
      <ol>${step(hasIed, !hasIed, 'Enter the number of field IEDs', 'It sizes the L1 switches. It is never listed in the BOM.')}
      ${step(picked === r.length, hasIed, 'Pick a part for each device', `${picked} of ${r.length} picked. L1 and L2 can be left to the sizing.`)}
      ${step(false, false, 'Generate the preview', 'Check each device’s panel, position and MCBs, then run Checks.')}</ol></div>`;
  }
  function result() {
    if (isNew()) return `<div class="card"><h3>Result</h3><p class="muted small" style="margin-top:var(--space-2)">Appears when the IED count and the parts are set.</p></div>`;
    const p = DB.networkPlan, A = p.sides.A;
    return `<div class="card"><h3>Result</h3><p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">Worked out by the engine from the picks. Read-only.</p>
      <table class="table table--plain"><thead><tr><th></th><th class="num">Each side</th></tr></thead><tbody>
        <tr><td>L1 switches</td><td class="num"><b>${A.l1}</b></td></tr><tr><td>L2 switches</td><td class="num"><b>${A.l2}</b></td></tr>
        <tr><td>L2 ports in use</td><td class="num">${A.l2Demand} of ${A.l2Usable}</td></tr><tr><td>L1 to L2 links</td><td class="num">${A.links}</td></tr></tbody></table>
      <p class="small" style="margin-top:var(--space-3)">${esc(ft().ied)} field IEDs need ${A.l1} L1 switches on each side.</p></div>`;
  }
  const previewBtn = () => {
    const blocked = S.dirty || isNew();
    return `<button class="btn btn--primary" data-action="pp-preview" ${blocked ? 'disabled aria-describedby="pv-why"' : ''}>${icon('preview')}Generate preview</button>${blocked ? `<span id="pv-why" class="muted small">${isNew() ? 'Pick the parts first.' : 'Save your changes first.'}</span>` : ''}`;
  };
  SCREENS.parts = () => {
    const r = rows(), f = ft(), b = DB.partBrands;
    const iedBad = isNew() && !(+f.ied > 0);
    return `<div class="page">${pageHead('Parts', 'Pick a library part for each device. The panels, MCBs, power and heat follow from these picks.', `<div class="pv-act">${previewBtn()}</div>`)}
      ${isNew() ? setupCard() : ''}
      <div class="net-grid">
        <div class="stack" style="gap:var(--space-6)">
          <section aria-labelledby="h-fn"><h3 id="h-fn">Field network</h3>
            <div class="form form--2" style="margin-top:var(--space-3)">
              ${field('Field IEDs', `<div class="input-affix">${input('n-ied', f.ied, { num: true, mono: true, invalid: iedBad, placeholder: 'Required' })}<span class="affix">IEDs</span></div>`, 'Never listed in the BOM. Only used to size the L1 switches.', iedBad ? 'Enter the number of field IEDs, for example 40.' : '')}
              <div class="field"><span class="label" id="topo-l">Topology</span><div class="segmented" role="radiogroup" aria-labelledby="topo-l"><label><input type="radio" name="pp-topo" value="star" data-action="pp-topo" ${f.topology === 'star' ? 'checked' : ''}><span>Star</span></label><label><input type="radio" name="pp-topo" value="ring" data-action="pp-topo" ${f.topology === 'ring' ? 'checked' : ''}><span>Ring</span></label></div>
                <span class="help">${f.topology === 'star' ? 'Each L1 switch has one uplink to its L2 switch plus an A–B interlink.' : 'L1 switches are joined in rings. Two ports close each ring.'}</span></div>
            </div>
            ${tuning()}</section>
          <section aria-labelledby="h-dev"><h3 id="h-dev">Devices</h3>
            <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">The layout fills the panels in this order. The part number is printed on the BOM; leave it empty to print the library model. Click a value under a part to change it for this design only.</p>
            <div class="prow-head" aria-hidden="true"><span>Library part</span><span>Part number on the BOM</span><span class="num">Qty</span></div>
            <div class="prows">${r.map(partRow).join('')}</div>
            <div class="popwrap prow-add"><button class="btn btn--secondary btn--sm" data-action="pp-add" aria-haspopup="menu" aria-expanded="${!!S.pp.addOpen}">${icon('plus')}Add a device</button>
              ${S.pp.addOpen ? `<div class="menu" role="menu" style="left:0;top:34px">${DB.partCategories.map(([c, t]) => `<button role="menuitem" data-action="pp-add-cat" data-c="${c}" data-t="${esc(t)}">${esc(t)}</button>`).join('')}</div>` : ''}</div>
          </section>
          <section aria-labelledby="h-br"><h3 id="h-br">Catalogue brands</h3>
            <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">The engine sizes each MCB and terminal strip and takes the ordering codes from these brands.</p>
            <div class="form form--3">
              ${field('MCB make and series, AC', select('br-ac', ['Schneider Acti9 iC60N', 'ABB S200', 'Siemens 5SY5'], b.mcbAc))}
              ${field('MCB make and series, DC', select('br-dc', ['Schneider Acti9 C60H-DC', 'ABB S200M-UC', 'Siemens 5SY5'], b.mcbDc))}
              ${field('Terminal blocks', select('br-tb', ['Phoenix Contact UT', 'Weidmüller W', 'WAGO TOPJOB S'], b.tb))}
            </div></section>
          <p class="muted small">${illus()}</p>
        </div>
        <aside class="net-result" aria-live="polite">${result()}</aside>
      </div></div>`;
  };

  /* ---------- actions ---------- */
  const mark = (id) => { S.dirty = true; S.changed.add(id); };
  const keep = (fn) => { const y = $('#main').scrollTop; fn(); App.render(); $('#main').scrollTop = y; };
  ACTIONS['pp-tuning'] = () => keep(() => { S.pp.open.tuning = !S.pp.open.tuning; });
  ACTIONS['pp-topo'] = (el) => keep(() => { ft().topology = el.value; mark('pp-topo'); });
  ACTIONS['pp-expand'] = (el) => keep(() => { S.pp.expanded.add(+el.dataset.i); });
  ACTIONS['pp-edit'] = (el) => { keep(() => { S.pp.editing = `${el.dataset.i}:${el.dataset.k}`; }); const c = $(`[data-dv="${el.dataset.i}:${el.dataset.k}"]`); if (c) { c.focus(); if (c.select) c.select(); } };
  ACTIONS['pp-reset'] = (el) => keep(() => { const r = rows()[+el.dataset.i]; delete r.ov[el.dataset.k]; const id = `ov-${r.key}-${el.dataset.k}`; S.invalid.delete(id); mark(id); });
  ACTIONS['pp-reset-all'] = (el) => keep(() => { const r = rows()[+el.dataset.i]; Object.keys(r.ov).forEach((k) => { S.invalid.delete(`ov-${r.key}-${k}`); mark(`ov-${r.key}-${k}`); }); r.ov = {}; });
  ACTIONS['pp-menu'] = (el) => keep(() => { S.pp.menu = S.pp.menu === +el.dataset.i ? -1 : +el.dataset.i; S.pp.addOpen = false; });
  ACTIONS['pp-move'] = (el) => keep(() => { const r = rows(), i = +el.dataset.i, j = i + +el.dataset.d; [r[i], r[j]] = [r[j], r[i]]; S.pp.menu = -1; mark('pp-row-' + r[j].key); });
  ACTIONS['pp-remove'] = (el) => { const r = rows(), i = +el.dataset.i, gone = r[i]; keep(() => { r.splice(i, 1); S.pp.menu = -1; mark('pp-remove-' + gone.key); }); toast(`Removed ${gone.label}`, 'trash', () => keep(() => { r.splice(i, 0, gone); })); };
  ACTIONS['pp-add'] = () => keep(() => { S.pp.addOpen = !S.pp.addOpen; S.pp.menu = -1; });
  ACTIONS['pp-add-cat'] = (el) => {
    const key = 'new' + Date.now();
    keep(() => { rows().push({ key, label: el.dataset.t, cat: el.dataset.c, part: '', pn: '', qty: 1, ab: false, ov: {}, added: true }); S.pp.addOpen = false; mark('pp-row-' + key); });
    const s = $(`#pp-part-${key}`); if (s) { s.scrollIntoView({ block: 'center' }); s.focus(); }
  };
  ACTIONS['pp-acc-add'] = () => keep(() => { rows()[0].acc.push({ part: 'PTF-SURGE', qty: 1 }); mark('pp-acc'); });
  ACTIONS['pp-acc-remove'] = (el) => keep(() => { rows()[0].acc.splice(+el.dataset.j, 1); mark('pp-acc'); });
  ACTIONS['pp-preview'] = () => go('#/device-preview');

  /* A detail value being edited: Enter or leaving keeps it, Esc cancels. Equal to the library is not an override. */
  function commit(c, cancel) {
    const [i, k] = c.dataset.dv.split(':'), r = rows()[+i], p = lib(r.cat, r.part), id = `ov-${r.key}-${k}`;
    S.pp.editing = '';
    if (!cancel) {
      const raw = c.value.trim(), num = ['h', 'w', 'v', 'ps', 'inrush'].includes(k), v = num && /^\d+(\.\d+)?$/.test(raw) ? +raw : raw;
      if (String(v) === String(p[k])) delete r.ov[k]; else r.ov[k] = v;
      num && badNumber(r.ov[k]) ? S.invalid.add(id) : S.invalid.delete(id);
      mark(id);
    }
    keep(() => {});
    const b = $(`[data-action="pp-edit"][data-i="${i}"][data-k="${k}"]`); if (b) b.focus();
  }
  document.addEventListener('keydown', (e) => {
    const c = e.target.closest && e.target.closest('[data-dv]');
    if (c && (e.key === 'Enter' || e.key === 'Escape')) { e.preventDefault(); e.stopPropagation(); commit(c, e.key === 'Escape'); }
    if (e.key === 'Escape' && S.pp && (S.pp.menu >= 0 || S.pp.addOpen)) { S.pp.menu = -1; S.pp.addOpen = false; App.render(); }
  }, true);
  document.addEventListener('focusout', (e) => { const c = e.target.closest && e.target.closest('[data-dv]'); if (c && S.pp && S.pp.editing === c.dataset.dv) setTimeout(() => { if (S.pp.editing === c.dataset.dv) commit(c, false); }, 0); });
  document.addEventListener('change', (e) => {
    const s = e.target.closest && e.target.closest('select[data-pp]'); if (!s) return;
    const r = rows()[+s.dataset.pp]; r.part = s.value; r.ov = {}; mark('pp-row-' + r.key); keep(() => {});
  });
  document.addEventListener('input', (e) => { if (e.target.id === 'n-ied' && route().a === 'parts') ft().ied = e.target.value; });
  const route = App.route;
})();
