/* Screen: Parts (plan M23; docs/ui/screens.md "Parts", components.md "Parts and Device preview").
   Replaces Network. One row per equipment entry with its library part, the part number printed on
   the BOM and this design's overrides; the network inputs and the catalogue brands. Every value comes
   from parts_page; the writers decide what an override is (equal to the library is none). */
(function () {
  const { esc, S, ACTIONS, SCREENS, banner, field, input, select, pageHead, toast } = App;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;
  const sub = () => App.sub;

  /* ---------- the draft form: every field is saved together with the save bar ---------- */
  const NET = { ied_count: 'int', topology: 'choice', ring_max_switches: 'int', l1_uplinks_per_switch: 'int', l1_interlink: 'bool', l3_uplinks_per_l2: 'int' };
  const SPARES = { port_fraction: ['Ports kept free on each switch', '%', 'pct'], sfp_per_l1: ['Spare SFPs on each L1', '', 'int'], dc_branches_per_feed: ['Spare DC branches per feed', '', 'int'], ac_branches: ['Spare AC branches', '', 'int'], rack_u_reserved: ['Rack space kept free', 'U', 'int'] };
  const VALUES = [['height_u', 'Height', 'int'], ['unit_power_w', 'Power', 'num'], ['supply_type', 'Supply', 'choice'], ['voltage_v', 'Voltage', 'int'], ['power_supplies', 'Supplies', 'int'], ['inrush_a', 'Inrush', 'num'], ['load_type', 'Load', 'choice']];
  const EQ = { part_id: 'choice', ordering_code: 'text', qty: 'int', redundant: 'bool', cable_manager: 'bool' };
  const BRANDS = [['mcb', 'MCB make and series, AC'], ['mcb_dc', 'MCB make and series, DC'], ['terminal_blocks', 'Terminal blocks']];
  const pct = (v) => Math.round(v * 1000) / 10;
  function spec(key) {  // [path, kind]; keys are n.<field>, s.<spare>, b.<brand>, e.<row>.<field>, o.<row>.<value>, f.<row>.<speed>.<media>
    const [kind, a, b, c] = key.split('.');
    if (kind === 'n') return [['network', a], NET[a]];
    if (kind === 's') return [['spares', a], SPARES[a][2]];
    if (kind === 'b') return [['catalogue_choice', a], 'choice'];
    if (kind === 'e') return [['equipment', Number(a), b], EQ[b]];
    if (kind === 'o') return [['equipment', Number(a), 'overrides', b], VALUES.find((v) => v[0] === b)[2]];
    if (kind === 'f') return [['equipment', Number(a), 'sfp', b, c], 'choice'];
    return null;
  }
  const rowAt = (i) => sub().page().parts.rows[i];
  function saved(key) {
    const p = sub().page(); if (!p || !p.parts) return '';
    const [kind, a, b, c] = key.split('.');
    if (kind === 'n') { const v = p.network[a]; return a === 'ied_count' && !v ? '' : typeof v === 'boolean' ? String(v) : v; }
    if (kind === 's') { const r = p.spares.find((x) => x.key === a); return r ? (a === 'port_fraction' ? pct(r.value) : r.value) : ''; }
    if (kind === 'b') return p.catalogue_choice[a] || '';
    const r = rowAt(Number(a)); if (!r) return '';
    if (kind === 'e' && b === 'cable_manager') return r.cable_manager ? String(r.cable_manager.on) : '';
    if (kind === 'e') { const v = r[b]; return v == null ? '' : typeof v === 'boolean' ? String(v) : v; }
    if (kind === 'o') { const v = b in r.overrides ? r.overrides[b] : r.library ? r.library[b] : null; return v == null ? '' : v; }
    if (kind === 'f') { const f = r.sfp.find((x) => x.speed === b && x.media === c); return (f && f.choice) || ''; }
    return '';
  }
  let cleared = '';  // what a part change cleared, said once the save is done
  function write(path, value) {
    const f = S.project.file, sid = S.sub;
    if (path[0] === 'equipment' && path[2] === 'overrides') return Bridge.call('set_part_override', f, sid, path[1], path[3], value);
    if (path[0] === 'equipment' && path[2] === 'cable_manager') return Bridge.call('set_cable_manager', f, sid, path[1], value === true);  // written only when it differs from the default
    if (path[0] === 'equipment' && path[2] === 'sfp') return Bridge.call('set_sfp_choice', f, sid, path[1], path[3], path[4], value || null);
    if (path[0] === 'equipment' && path[2] === 'part_id' && value) {
      return Bridge.call('set_equipment_part', f, sid, path[1], value).then((r) => {
        if (r.cleared.length) cleared = `Changed to ${value}. Its ${r.cleared.map((k) => ({ overrides: 'overrides', sfp: 'SFP choices', ordering_code: 'part number' })[k]).join(', ').replace(/, ([^,]*)$/, ' and $1')} ${r.cleared.length === 1 ? 'was' : 'were'} cleared, so the BOM prints the library's code.`;
        return r.page;
      });
    }
    return Bridge.call('set_substation_field', f, sid, path, value);
  }
  const PF = App.draftForm({
    prefix: 'p-', screen: 'parts', file: 'substation.yaml', label: 'Save parts', spec, saved,
    check: (path, value) => (path[2] === 'sfp' || path[2] === 'cable_manager' ? Promise.resolve(null) : Bridge.call('check_substation_field', S.project.file, S.sub, path, value)),
    write,
    done: (page) => {
      if (page && page.parts) sub().set(page); else sub().reload();
      App.network.reload(); App.devicePreview.reload();
      if (cleared) { toast(cleared, 'info'); cleared = ''; }
    }
  });
  const UI = { tuning: null, editing: '', menu: -1, addOpen: false, fresh: null };  // fresh: a new substation's rows before the first save
  sub().resets.push(() => { PF.reset(); Object.assign(UI, { tuning: null, editing: '', menu: -1, addOpen: false, fresh: null }); });
  const shown = (key) => { const v = PF.shown(key); return v == null ? '' : String(v); };
  const mark = (key, html) => PF.mark(key, html);
  const err = (key) => (PF.errors[key] ? `<span class="err small" id="p-${key}-err">${icon('error')}<span>${PF.err(key)}</span></span>` : '');
  /* A change that reloads the page from an immediate write (move, remove, accessories). */
  const reloaded = (page) => { if (page && page.parts) sub().set(page); else sub().reload(); App.network.reload(); App.devicePreview.reload(); App.render(); };
  const fail = (e) => toast(e.message, 'error');

  /* ---------- the details strip: the library values, each overridable for this design ---------- */
  const FMT = {
    height_u: (v) => (+v ? `${v} U` : 'DIN rail'), unit_power_w: (v) => `${v} W`, supply_type: (v) => ({ VDC: 'DC', VAC: 'AC' })[v] || v || '—',
    voltage_v: (v) => (v === '' ? '—' : `${v} V`), power_supplies: (v) => `${v}`, inrush_a: (v) => (v === '' ? '—' : `${v} A`),
    load_type: (v) => ({ CONTINUOUS: 'Continuous', INTERMITTENT: 'Intermittent' })[v] || '—'
  };
  const libValue = (r, f) => (r.library[f] == null ? '' : String(r.library[f]));
  function strip(r) {
    if (!r.part_id) return `<div class="prow-strip"><span class="muted small">${r.sized ? 'Pick the switch to change its data.' : 'Pick a part to see its data.'}</span></div>`;
    if (!r.library) return '<div class="prow-strip"></div>';
    if (!r.library.supply_type && !r.library.height_u) return '<div class="prow-strip"><span class="muted small">Passive part: no rack space, no power.</span></div>';
    const fields = r.library.supply_type ? VALUES : VALUES.filter(([f]) => f === 'height_u');  // an unpowered part has only a height
    let overridden = 0;
    const vals = fields.map(([f, label, kind]) => {
      const key = `o.${r.index}.${f}`, id = `p-${key}`, v = shown(key), lib = libValue(r, f), ov = v !== lib, changed = key in PF.draft;
      if (ov) overridden += 1;
      if (UI.editing === key) {
        const ctl = f === 'supply_type' ? select(id, [['VDC', 'DC'], ['VAC', 'AC']], v, { cls: 'dv-input' })
          : f === 'load_type' ? select(id, [['CONTINUOUS', 'Continuous'], ['INTERMITTENT', 'Intermittent']], v, { cls: 'dv-input' })
          : input(id, v, { mono: true, num: true }).replace('class="input', 'class="dv-input input');
        return `<span class="dv is-editing"><label class="dv-label" for="${id}">${label}</label>${ctl.replace('<input ', `<input data-dv="${key}" `).replace('<select ', `<select data-dv="${key}" `)}</span>`;
      }
      const bad = !!PF.errors[key];
      return `<span class="dv${ov ? ' is-ov' : ''}${bad ? ' is-bad' : ''}"><button class="dv-btn" data-action="pp-edit" data-key="${key}" aria-label="${label} ${esc(FMT[f](v))}${ov ? `, overridden; library ${esc(FMT[f](lib))}` : ''}${changed ? ', not saved' : ''}. Change">
          <span class="dv-label">${changed ? '<span class="chg" aria-hidden="true"></span>' : ''}${label}</span><span class="dv-val">${ov ? '<i class="ov-dot" aria-hidden="true"></i>' : ''}${esc(bad ? v : FMT[f](v))}</span></button>${ov ? `<span class="dv-lib">Library ${esc(FMT[f](lib))}</span><button class="btn btn--ghost btn--icon btn--xs" data-action="pp-reset" data-key="${key}" aria-label="Reset ${label.toLowerCase()} to the library's ${esc(FMT[f](lib))}" title="Reset to the library value">${icon('undo')}</button>` : ''}</span>`;
    }).join('');
    const errs = fields.map(([f]) => err(`o.${r.index}.${f}`)).join('');
    return `<div class="prow-strip">${vals}${overridden ? `<button class="btn btn--ghost btn--sm" data-action="pp-reset-all" data-i="${r.index}">Reset all</button>` : ''}</div>${errs ? `<div class="prow-err">${errs}</div>` : ''}`;
  }

  /* ---------- one device row ---------- */
  const partText = (o) => `${o.part_id}${o.make || o.model ? ' · ' + [o.make, o.model].filter(Boolean).join(' ') : ''}`;
  const emptyLine = (p, category, label) => `<div class="prow-empty muted small">The library has no ${esc(label)} parts yet.</div>`;
  function partSelect(p, r) {
    const key = `e.${r.index}.part_id`, id = `p-${key}`, v = shown(key), opts = p.parts.options[r.category] || [];
    if (!opts.length && !r.part_id) return emptyLine(p, r.category, r.label);
    const missing = r.part_id && !r.known && v === r.part_id, picked = opts.find((o) => o.part_id === v);
    const first = r.sized && r.role === 'l1_switch' ? `<option value="" ${!v ? 'selected' : ''}>The sizing picks the switch</option>` : '';
    return `<div class="prow-partwrap">${mark(key, `<select class="select prow-part${missing ? ' is-missing' : ''}" id="${id}" data-dirty="1" aria-label="Part for ${esc(r.label)}" ${picked ? `title="${esc(partText(picked))}"` : ''} ${missing ? `aria-invalid="true" aria-describedby="${id}-missing"` : ''}>
        ${first}${missing ? `<option value="${esc(r.part_id)}" selected>${esc(r.part_id)}</option>` : ''}${opts.map((o) => `<option value="${esc(o.part_id)}" ${o.part_id === v ? 'selected' : ''}>${esc(partText(o))}</option>`).join('')}</select>`)}
      ${missing ? `<span class="err small" id="${id}-missing">${icon('error')}<span>Not in ${esc(p.project.library.name)} ${esc(p.project.library.version)}. Pick another part.</span></span>` : ''}${err(key)}</div>`;
  }
  function sfpRows(r) {
    return r.sfp.map((f) => {
      const key = `f.${r.index}.${f.speed}.${f.media}`;
      return `<div class="prow-sub"><span class="prow-sub-what">${esc(f.speed)} · ${esc(f.media)} SFP</span>
        ${mark(key, select(`p-${key}`, [['', 'Automatic: same make first'], ...f.candidates.map((c) => [c, c])], shown(key)).replace('<select ', `<select aria-label="SFP for ${esc(f.speed)} ${esc(f.media)}, ${esc(r.label)}" `))}</div>`;
    }).join('');
  }
  function accessories(p, r) {
    const a = r.accessories; if (!a) return '';
    const own = a.library.length ? `<div class="prow-sub prow-sub--foot"><span class="muted small">Comes with ${esc(r.part_id)}: ${a.library.map((x) => `<span class="mono">${esc(x.part_id)}</span> × ${x.qty}`).join(', ')}. They go to loose material.</span></div>` : '';
    const added = a.added.map((x) => `<div class="prow-sub"><span class="prow-sub-what">Accessory <span class="mono">${esc(x.part_id)}</span></span><span></span>
        <div class="prow-qty"><input class="input input--num input--mono" id="pp-accq-${x.index}" data-acc="${x.index}" value="${esc(x.item.qty)}" aria-label="Quantity of ${esc(x.part_id)}"></div>
        <button class="btn btn--ghost btn--icon btn--sm btn--del" data-action="pp-acc-remove" data-index="${x.index}" aria-label="Remove ${esc(x.part_id)}">${icon('trash')}</button></div>`).join('');
    const foot = !a.parts.length ? '' : a.host_panel == null
      ? `<div class="prow-sub prow-sub--foot"><span class="muted small">To add accessories, set the loose material's host panel first.</span><a class="btn btn--ghost btn--sm" href="#/loose">Open Loose material</a></div>`
      : `<div class="prow-sub prow-sub--foot"><label class="sr-only" for="pp-acc-part">Accessory to add</label><select class="select" id="pp-acc-part">${a.parts.map((x) => `<option value="${esc(x)}">${esc(x)}</option>`).join('')}</select><button class="btn btn--ghost btn--sm" data-action="pp-acc-add" ${PF.dirty() ? 'disabled title="Save or discard the changes first"' : ''}>${icon('plus')}Add accessory</button><span class="muted small">Accessories go to loose material.</span></div>`;
    return own + added + foot;
  }
  function partRow(p, r, last) {
    const changed = Object.keys(PF.draft).some((k) => k.split('.')[1] === String(r.index) && 'eof'.includes(k[0]));
    const opts = p.parts.options[r.category] || [], empty = !opts.length && !r.part_id;
    const fixed = r.sized, dirty = PF.dirty();
    const pn = `e.${r.index}.ordering_code`, qty = `e.${r.index}.qty`, ab = `e.${r.index}.redundant`, cm = `e.${r.index}.cable_manager`;
    return `<div class="prow" role="group" aria-label="${esc(r.label)}${r.part_id ? ', ' + esc(r.part_id) : ', no part yet'}">
      <div class="prow-top">
        <span class="prow-role">${changed ? '<span class="chg-dot" aria-hidden="true"></span><span class="sr-only">changed, </span>' : ''}${esc(r.label)} <span class="muted small mono">${esc(r.id)}</span></span>
        <span class="sp"></span>
        ${r.cable_manager ? `<label class="switch prow-cm" title="${r.cable_manager.default ? 'On by default for this part' : 'Off by default for this part'}"><input type="checkbox" id="p-${cm}" ${shown(cm) === 'true' ? 'checked' : ''} data-dirty="1">Cable manager</label>` : ''}
        ${empty ? '' : `<label class="check prow-ab"><input type="checkbox" id="p-${ab}" ${shown(ab) === 'true' ? 'checked' : ''} data-dirty="1"> A and B</label>`}
        <div class="prow-menu-wrap"><button class="btn btn--ghost btn--icon btn--sm" data-action="pp-menu" data-i="${r.index}" aria-haspopup="menu" aria-expanded="${UI.menu === r.index}" aria-label="More for ${esc(r.label)}" ${dirty ? 'disabled title="Save or discard the changes first"' : ''}>${icon('dots')}</button>
          ${UI.menu === r.index ? `<div class="menu" role="menu" style="right:0;top:34px"><button role="menuitem" data-action="pp-move" data-i="${r.index}" data-d="-1" ${r.index === 0 ? 'disabled' : ''}>Move up</button><button role="menuitem" data-action="pp-move" data-i="${r.index}" data-d="1" ${last ? 'disabled' : ''}>Move down</button>${fixed ? '' : `<hr><button role="menuitem" class="danger" data-action="pp-remove" data-i="${r.index}">${icon('trash')}Remove</button>`}</div>` : ''}</div>
      </div>
      <div class="prow-fields">
        ${partSelect(p, r)}
        ${empty ? '' : `<div class="prow-pn">${mark(pn, `<input class="input input--mono" id="p-${pn}" value="${esc(shown(pn))}" placeholder="${r.part_id ? 'Prints the library code' : 'Part number'}" aria-label="Part number on the BOM for ${esc(r.label)}" data-dirty="1" ${!r.part_id ? 'disabled' : ''}>`)}${err(pn)}</div>
        <div class="prow-qty">${r.sized ? '<span class="muted small" title="The sizing sets the quantity">Sized</span>' : `${input('p-' + qty, shown(qty), { num: true, mono: true, invalid: !!PF.errors[qty] }).replace('<input ', `<input aria-label="Quantity of ${esc(r.label)}" `)}`}</div>`}
      </div>
      ${empty ? '' : strip(r)}${sfpRows(r)}${accessories(p, r)}
    </div>`;
  }

  /* ---------- a new substation: the default rows, saved together with the sized L1 switch ---------- */
  function freshRows(p) {
    if (!UI.fresh) UI.fresh = p.parts.default_rows.map((d) => ({ ...d, part_id: '', redundant: ['l1_switch', 'l2_switch'].includes(d.role) }));
    return UI.fresh;
  }
  function freshRow(p, d, j) {
    const opts = p.parts.options[d.category] || [];
    const l1 = d.role === 'l1_switch';
    const ctl = !opts.length ? emptyLine(p, d.category, d.label)
      : `<select class="select prow-part" id="pn-part-${j}" data-fresh="${j}" aria-label="Part for ${esc(d.label)}">${l1 ? `<option value="" ${!d.part_id ? 'selected' : ''}>The sizing picks the switch</option>` : `<option value="" ${!d.part_id ? 'selected' : ''}>Pick a part</option>`}${opts.map((o) => `<option value="${esc(o.part_id)}" ${o.part_id === d.part_id ? 'selected' : ''}>${esc(partText(o))}</option>`).join('')}</select>`;
    return `<div class="prow" role="group" aria-label="${esc(d.label)}"><div class="prow-top"><span class="prow-role">${esc(d.label)}</span><span class="sp"></span>
        ${opts.length ? `<label class="check prow-ab"><input type="checkbox" data-fresh-ab="${j}" ${d.redundant ? 'checked' : ''}> A and B</label>` : ''}</div>
      <div class="prow-fields">${ctl}</div></div>`;
  }
  function setupCard(p, rows) {
    const hasIed = !!(+shown('n.ied_count') && !PF.errors['n.ied_count']), picked = rows.filter((d) => d.part_id).length;
    const step = (done, now, title, text) => `<li class="${done ? 'done' : now ? 'now' : ''}">${icon(done ? 'check' : 'info')}<div><b>${title}</b><div class="muted small">${text}</div></div></li>`;
    return `<div class="setup" style="margin-bottom:var(--space-5)"><h3>Set up ${esc(p.name)}</h3><p class="muted small" style="margin-top:var(--space-1)">Pick a part for each device. The panels are laid out from the picks.</p>
      <ol>${step(hasIed, !hasIed, 'Enter the number of field IEDs', 'It sizes the L1 switches. It is never listed in the BOM.')}
      ${step(false, hasIed, 'Pick a part for each device', `${picked} of ${rows.length} picked. L1 can be left to the sizing; the L2 switch is needed.`)}
      ${step(false, false, 'Look at the panels', 'Check the layout, then run Checks and build.')}</ol></div>`;
  }

  /* ---------- the network inputs ---------- */
  const numField = (key, label, unit, help) => {
    const id = `p-${key}`, html = input(id, shown(key), { num: true, mono: true, invalid: !!PF.errors[key] });
    return mark(key, field(esc(label), unit ? `<div class="input-affix">${html}<span class="affix">${esc(unit)}</span></div>` : html, help, PF.err(key)));
  };
  function tuning(p) {
    const ring = shown('n.topology') === 'ring', open = UI.tuning == null ? !p.equipment.length : UI.tuning;
    const sp = (k) => p.spares.find((x) => x.key === k);
    const summary = `${ring ? `Rings of up to ${shown('n.ring_max_switches')}` : 'Star'} · ${plural(+shown('n.l1_uplinks_per_switch'), 'uplink')} per L1 · ${shown('n.l1_interlink') === 'true' ? 'A–B interlink' : 'no interlink'} · ${shown('s.port_fraction')}% ports kept free · ${shown('s.rack_u_reserved')} U kept free`;
    const changedSpare = (k) => { const r = sp(k); if (!r || !r.changed) return 'Project default.'; const d = k === 'port_fraction' ? pct(r.default) : r.default; return `Changed from ${d}${SPARES[k][1] && SPARES[k][1] !== '%' ? ' ' + SPARES[k][1] : SPARES[k][1]}.`; };
    return `<div class="disclosure"><button class="disclosure-head" data-action="pp-tuning" aria-expanded="${open}" aria-controls="ft-body">${icon(open ? 'chevd' : 'chevr')}<b>Network fine tuning</b><span class="muted small">${open ? 'Ring size, uplinks and spares' : esc(summary)}</span></button>
      ${open ? `<div id="ft-body" class="form form--3 disclosure-body">
        ${ring ? numField('n.ring_max_switches', 'Switches per ring', '', 'Most L1 switches in one ring.') : ''}
        ${numField('n.l1_uplinks_per_switch', 'L1 uplinks per switch', '')}
        ${mark('n.l1_interlink', field('A–B interlink', select('p-n.l1_interlink', [['true', 'Yes'], ['false', 'No']], shown('n.l1_interlink'))))}
        ${numField('n.l3_uplinks_per_l2', 'L3 uplinks per L2', '')}
        ${Object.entries(SPARES).map(([k, [label, unit]]) => numField(`s.${k}`, label, unit, changedSpare(k))).join('')}
      </div>` : ''}</div>`;
  }
  function brands(p) {
    if (!Object.keys(p.brands).length) return '';
    const name = (kind, id) => ((p.brands[kind] || []).find((b) => b.id === id) || { name: id }).name;
    return `<section aria-labelledby="h-br"><h3 id="h-br">Catalogue brands</h3>
      <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">The engine sizes each MCB and terminal strip and takes the ordering codes from these brands. The other catalogues are on Settings.</p>
      <div class="form form--3">${BRANDS.map(([kind, label]) => {
        const own = p.project_choice[kind], lib = (p.brands[kind] || [])[0] || {};
        const same = !own && kind === 'mcb_dc' ? 'Same as AC branches' : `Same as the project (${own ? name(kind, own) : lib.product || 'Library default'})`;
        return mark(`b.${kind}`, field(esc(label), select(`p-b.${kind}`, [['', same], ...(p.brands[kind] || []).map((b) => [b.id, b.name])], shown(`b.${kind}`)), '', PF.err(`b.${kind}`)));
      }).join('')}</div></section>`;
  }

  /* ---------- the page ---------- */
  SCREENS.parts = () => {
    if (!sub().real()) return `<div class="page">${pageHead('Parts')}<div class="empty"><b>Open a substation first.</b></div></div>`;
    const p = sub().page(); if (!p) return sub().waiting('Parts');
    if (!p.parts) { if (p.network) sub().reload(); return `<div class="page">${pageHead('Parts', 'Pick a library part for each device.')}${sub().problems(p)}</div>`; }
    const fresh = !p.equipment.length, rows = fresh ? freshRows(p) : p.parts.rows, topo = shown('n.topology');
    const unset = !shown('n.ied_count');
    const gen = fresh ? '' : PF.dirty() ? `<button class="btn btn--secondary" disabled title="Save your changes first." aria-describedby="pp-gen-why">${icon('elevation')}Generate preview</button><span id="pp-gen-why" class="sr-only">Save your changes first.</span>` : `<a class="btn btn--secondary" href="#/device-preview">${icon('elevation')}Generate preview</a>`;
    return `<div class="page">${pageHead('Parts', 'Pick a library part for each device. The panels, MCBs, power and heat follow from these picks.', gen)}
      ${sub().problems(p)}${fresh ? setupCard(p, rows) : ''}
      <div class="net-grid">
        <div class="stack" style="gap:var(--space-6)">
          <section aria-labelledby="h-fn"><h3 id="h-fn">Field network</h3>
            <div class="form form--2" style="margin-top:var(--space-3)">
              ${mark('n.ied_count', field('Field IEDs', `<div class="input-affix">${input('p-n.ied_count', shown('n.ied_count'), { num: true, mono: true, invalid: !!PF.errors['n.ied_count'] || unset, placeholder: unset ? 'Required' : '' })}<span class="affix">IEDs</span></div>`, 'Never listed in the BOM. Only used to size the L1 switches.', PF.errors['n.ied_count'] ? PF.err('n.ied_count') : unset ? 'Enter the number of field IEDs, for example 40.' : ''))}
              ${mark('n.topology', field('Topology', select('p-n.topology', [['star', 'Star'], ['ring', 'Ring']], topo), topo === 'ring' ? 'L1 switches are joined in rings. Two ports close each ring.' : 'Each L1 switch has one uplink to its L2 switch plus an A–B interlink.'))}
            </div>
            ${tuning(p)}</section>
          <section aria-labelledby="h-dev"><h3 id="h-dev">Devices</h3>
            <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">The layout fills the panels in this order. The part number is printed on the BOM; leave it empty to print the library's code. Click a value under a part to change it for this design only.</p>
            <div class="prow-head" aria-hidden="true"><span>Library part</span><span>${fresh ? '' : 'Part number on the BOM'}</span><span class="num">${fresh ? '' : 'Qty'}</span></div>
            <div class="prows">${fresh ? rows.map((d, j) => freshRow(p, d, j)).join('') : rows.map((r, i) => partRow(p, r, i === rows.length - 1)).join('')}</div>
            ${fresh ? `<div class="row" style="margin-top:var(--space-3)"><button class="btn btn--primary" data-action="pp-start" ${rows.some((d) => d.role === 'l2_switch' && d.part_id) ? '' : 'disabled aria-describedby="pp-start-why"'}>${icon('save')}Save the parts</button>${rows.some((d) => d.role === 'l2_switch' && d.part_id) ? '' : '<span id="pp-start-why" class="muted small">Pick the L2 switch first: the network is sized from it.</span>'}</div>` : addDevice(p)}
          </section>
          ${brands(p)}
        </div>
        <aside class="net-result" aria-live="polite">${App.network.resultCard()}</aside>
      </div>${PF.bar()}</div>`;
  };
  function addDevice(p) {
    const dirty = PF.dirty();
    return `<div class="popwrap prow-add"><button class="btn btn--secondary btn--sm" data-action="pp-add" aria-haspopup="menu" aria-expanded="${UI.addOpen}" ${dirty ? 'disabled title="Save or discard the changes first"' : ''}>${icon('plus')}Add a device</button>
      ${UI.addOpen ? `<div class="menu" role="menu" style="left:0;top:34px">${p.parts.add_categories.map((c) => { const n = (p.parts.options[c.category] || []).length; return `<button role="menuitem" data-action="pp-add-cat" data-c="${c.category}" ${n ? '' : `disabled title="The library has no ${esc(c.label)} parts yet."`}>${esc(c.label)}${n ? '' : `<span class="muted small">The library has no ${esc(c.label)} parts yet.</span>`}</button>`; }).join('')}</div>` : ''}</div>`;
  }

  /* "Go to the row" from Device preview: #/parts/<device> scrolls to the row and focuses its part. The page
     re-renders as its parts load (the Result card), so the focus is put back on the row for a few seconds. */
  let goRow = null;  // { id, until, scrolled }
  SCREENS.partsAfter = () => {
    const want = decodeURIComponent(App.route().b || '');
    if (want) { goRow = { id: want, until: Date.now() + 3000, scrolled: false }; history.replaceState(null, '', '#/parts'); }
    const p = goRow && Date.now() < goRow.until && sub().page(); if (!p || !p.parts) return;
    const r = p.parts.rows.find((x) => x.id === goRow.id), el = r && document.getElementById(`p-e.${r.index}.part_id`);
    if (!el) return;
    if (!goRow.scrolled) { el.closest('.prow').scrollIntoView({ block: 'center' }); goRow.scrolled = true; }
    if (document.activeElement === document.body) el.focus({ preventScroll: true });
  };

  /* ---------- actions ---------- */
  const keep = (fn) => { const m = document.getElementById('main'), y = m ? m.scrollTop : 0; fn(); App.render(); if (m) m.scrollTop = y; };
  ACTIONS['pp-tuning'] = () => keep(() => { const p = sub().page(); UI.tuning = !(UI.tuning == null ? !p.equipment.length : UI.tuning); });
  ACTIONS['pp-edit'] = (el) => { keep(() => { UI.editing = el.dataset.key; }); const c = document.getElementById('p-' + el.dataset.key); if (c) { c.focus(); if (c.select) c.select(); } };
  const resetTo = (key) => { const r = rowAt(Number(key.split('.')[1])); PF.set(key, libValue(r, key.split('.')[2])); S.dirty = PF.dirty(); };
  ACTIONS['pp-reset'] = (el) => keep(() => resetTo(el.dataset.key));
  ACTIONS['pp-reset-all'] = (el) => keep(() => VALUES.forEach(([f]) => { const key = `o.${el.dataset.i}.${f}`, r = rowAt(Number(el.dataset.i)); if (r.library && shown(key) !== libValue(r, f)) resetTo(key); }));
  ACTIONS['pp-menu'] = (el) => keep(() => { UI.menu = UI.menu === +el.dataset.i ? -1 : +el.dataset.i; UI.addOpen = false; });
  ACTIONS['pp-move'] = (el) => {
    const i = +el.dataset.i, to = i + +el.dataset.d; UI.menu = -1;
    Bridge.call('move_equipment', S.project.file, S.sub, i, to).then((page) => {
      reloaded(page);
      toast(`Moved ${page.parts.rows[to].label} ${to < i ? 'up' : 'down'}`, 'check', () => Bridge.call('move_equipment', S.project.file, S.sub, to, i).then(reloaded).catch(fail));
    }).catch(fail);
  };
  ACTIONS['pp-remove'] = (el) => {
    const i = +el.dataset.i, file = S.project.file, sid = S.sub, label = rowAt(i).label; UI.menu = -1;
    Bridge.call('remove_equipment', file, sid, i).then((r) => {
      sub().reload(); App.network.reload(); App.devicePreview.reload(); App.render();
      toast(`Removed ${label}`, 'trash', () => Bridge.call('add_equipment', file, sid, r.row, i).then(() => { sub().reload(); App.render(); }).catch(fail));
    }).catch(fail);
  };
  ACTIONS['pp-add'] = () => keep(() => { UI.addOpen = !UI.addOpen; UI.menu = -1; });
  /* Add a device: the model takes no row without a part, so the part is picked first. */
  const ROLE_OF = { patch_panel: 'fopp', firewall: 'firewall', network_switch: 'ext_switch', kvm: 'kvm', console: 'console' };
  const freeId = (base, taken) => { let id = base, n = 2; while (taken.includes(id)) id = `${base}-${n++}`; return id; };
  ACTIONS['pp-add-cat'] = (el) => {
    const p = sub().page(), c = p.parts.add_categories.find((x) => x.category === el.dataset.c), opts = p.parts.options[c.category];
    UI.addOpen = false;
    App.dialog({ title: `Add a ${esc(c.label.toLowerCase())}`, body: `<div class="form">
      ${field('Part', `<select class="select" id="pa-part">${opts.map((o) => `<option value="${esc(o.part_id)}">${esc(partText(o))}</option>`).join('')}</select>`, 'From the active library.')}
      <label class="check"><input type="checkbox" id="pa-red">A and B units (redundant)</label>
      <div id="pa-err" class="err small" role="alert"></div></div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="pp-add-do" data-c="${c.category}">Add</button>` });
  };
  ACTIONS['pp-add-do'] = (el) => {
    const p = sub().page(), v = (id) => document.getElementById(id), part = v('pa-part').value;
    const base = part.toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^[^a-z0-9]+|-+$/g, '') || 'device';
    const row = { id: freeId(base, p.equipment.map((e) => e.id)), part_id: part, role: ROLE_OF[el.dataset.c] || 'other' };
    if (v('pa-red').checked) row.redundant = true;
    Bridge.call('add_equipment', S.project.file, S.sub, row, null).then(() => { App.closeDialog(); sub().reload(); App.network.reload(); App.devicePreview.reload(); App.render(); toast(`Added ${row.id}`, 'check'); })
      .catch((e) => { v('pa-err').innerHTML = `${icon('error')}<span>${esc(e.message)}</span>`; });
  };
  /* Accessories are loose material items, written at once (decision 2 of the M23 plan). */
  const looseReply = (r) => { if (!r.written) throw new Error(r.issues.map((x) => x.message).join('; ') || 'Not written.'); sub().reload(); App.render(); return r; };
  ACTIONS['pp-acc-add'] = () => {
    const part = document.getElementById('pp-acc-part').value;
    Bridge.call('add_loose_item', S.project.file, S.sub, { part_id: part, qty: 1 }, null, null).then(looseReply).then(() => toast(`Added ${part} to loose material`, 'check')).catch(fail);
  };
  ACTIONS['pp-acc-remove'] = (el) => {
    const index = +el.dataset.index, gps = sub().page().parts.rows.find((r) => r.accessories), item = gps.accessories.added.find((x) => x.index === index).item;
    Bridge.call('remove_loose_item', S.project.file, S.sub, index).then(looseReply)
      .then(() => toast(`Removed ${item.part_id}`, 'trash', () => Bridge.call('add_loose_item', S.project.file, S.sub, item, index, null).then(looseReply).catch(fail))).catch(fail);
  };
  document.addEventListener('change', (e) => {
    const t = e.target;
    if (t.dataset && t.dataset.acc != null) {  // an accessory's quantity, written at once
      const index = +t.dataset.acc, gps = sub().page().parts.rows.find((r) => r.accessories), item = gps.accessories.added.find((x) => x.index === index).item;
      const qty = Number(t.value);
      if (!Number.isInteger(qty) || qty < 1) { toast('Enter a whole number, 1 or more.', 'error'); return; }
      Bridge.call('set_loose_item', S.project.file, S.sub, index, { ...item, qty }).then(looseReply).catch(fail);
      return;
    }
    if (t.dataset && t.dataset.fresh != null) { UI.fresh[+t.dataset.fresh].part_id = t.value; App.render(); return; }
    if (t.dataset && t.dataset.freshAb != null) { UI.fresh[+t.dataset.freshAb].redundant = t.checked; return; }
    /* A new part drops this row's unsaved overrides, SFP choices and part number: they described the old part. */
    const m = /^p-e\.(\d+)\.part_id$/.exec(t.id || '');
    if (m) Object.keys(PF.draft).filter((k) => k.split('.')[1] === m[1] && (k[0] === 'o' || k[0] === 'f' || k.endsWith('.ordering_code'))).forEach((k) => { delete PF.draft[k]; delete PF.errors[k]; });
  });
  ACTIONS['pp-start'] = () => {
    const rows = UI.fresh.filter((d) => d.part_id || d.role === 'l1_switch').map((d) => ({ role: d.role, part_id: d.part_id || null, redundant: d.redundant || undefined }));
    Bridge.call('start_parts', S.project.file, S.sub, rows).then((page) => { UI.fresh = null; reloaded(page); toast(`Saved ${plural(rows.length, 'device row')}`, 'check'); }).catch(fail);
  };
  /* A detail value being edited: the draft form keeps it on change; Enter keeps it, Esc puts the shown value back. */
  document.addEventListener('keydown', (e) => {
    const c = e.target.closest && e.target.closest('[data-dv]');
    if (c && (e.key === 'Enter' || e.key === 'Escape')) {
      e.preventDefault(); e.stopPropagation();
      const key = c.dataset.dv;
      if (e.key === 'Escape') c.value = shown(key);
      UI.editing = ''; c.blur(); App.render();
      const b = document.querySelector(`[data-action="pp-edit"][data-key="${key}"]`); if (b) b.focus();
    }
    if (e.key === 'Escape' && (UI.menu >= 0 || UI.addOpen)) { UI.menu = -1; UI.addOpen = false; App.render(); }
  }, true);
  document.addEventListener('focusout', (e) => {
    const c = e.target.closest && e.target.closest('[data-dv]');
    if (c && UI.editing === c.dataset.dv) setTimeout(() => { if (UI.editing === c.dataset.dv) { UI.editing = ''; App.render(); } }, 0);
  });
  /* Use this instead (docs/ui/editing.md, Alternatives): the chosen rows get the other part as an unsaved edit. */
  App.holdParts = (indices, part) => {
    sub().page();  // the open substation's draft; a different substation's would be dropped on load
    indices.forEach((i) => { PF.draft[`e.${i}.part_id`] = part; delete PF.errors[`e.${i}.part_id`]; });
    S.dirty = true; App.go('#/parts');
  };
})();
