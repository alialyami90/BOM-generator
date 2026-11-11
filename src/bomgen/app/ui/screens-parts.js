/* Screen: Parts (plan M23; docs/ui/screens.md "Parts", components.md "Parts and Device preview").
   Replaces Network. One row per equipment entry with its library part, the part number printed on
   the BOM and this design's overrides; the network inputs and the catalogue brands. Every value comes
   from parts_page; the writers decide what an override is (equal to the library is none). */
(function () {
  const { esc, S, ACTIONS, SCREENS, banner, field, input, select, pageHead, toast } = App;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;
  const sub = () => App.sub;

  /* ---------- the draft form: every field is saved together with the save bar ---------- */
  const NET = { ied_count: 'int', topology: 'choice', ring_max_switches: 'int', l1_uplinks_per_switch: 'int', l1_interlink: 'bool', l3_uplinks_per_l2: 'int', l1_per_side: 'int', l2_per_side: 'int' };
  const SPARES = { port_fraction: ['Ports kept free on each switch', '%', 'pct'], sfp_per_l1: ['Spare SFPs on each L1', '', 'int'], dc_branches_per_feed: ['Spare DC branches per feed', '', 'int'], ac_branches: ['Spare AC branches', '', 'int'], rack_u_reserved: ['Rack space kept free', 'U', 'int'], terminals_fraction: ['Spare terminals on each wiring strip', '%', 'pct'] };
  const VALUES = [['height_u', 'Height', 'int'], ['unit_power_w', 'Power', 'num'], ['supply_type', 'Supply', 'choice'], ['voltage_v', 'Voltage', 'int'], ['power_supplies', 'Supplies', 'int'], ['inrush_a', 'Inrush', 'num'], ['load_type', 'Load', 'choice']];
  const EQ = { part_id: 'choice', ordering_code: 'text', qty: 'int', redundant: 'bool', cable_manager: 'bool', alarm_on_branch_mcb: 'bool', purpose: 'text', tag: 'text', tag_type: 'text', first_nn: 'int', hwio_points: 'int', panel_hint: 'int', priority: 'int', note: 'text' };
  /* M59: the row's BOM text, [field, label, placeholder when unset] */
  const BOM_TEXT = [['purpose', 'Purpose', () => 'None'], ['tag', 'Tag', (r) => r.tags.join(', ') || 'Generated'], ['tag_type', 'Type code', () => 'From the library'], ['first_nn', 'First number', () => 'Automatic'], ['hwio_points', 'HWIO points', () => 'From the library'], ['note', 'Note (not printed)', () => 'None']];  // note: plan M71
  /* M60: one IED schedule row (ADR 0034); ports is text such as "2x100M MM + 1x1G RJ45" */
  const IED = { bay: 'text', name: 'text', qty: 'int', ports: 'text', attachment: 'choice', lands_on: 'choice', notes: 'text' };
  const ATTACH = [['dual', 'Both'], ['single_a', 'A only'], ['single_b', 'B only']], LANDS = [['l1', 'L1'], ['l2', 'L2']];
  /* M61: one external link (control centre, PCC, third party) */
  const XL = { name: 'text', count: 'int', speed: 'choice', media: 'choice', lands_on: 'choice', through_firewall: 'bool', redundant: 'bool', cable_length_m: 'num' };
  const LINK = { l2_ports: 'int', l2_speed: 'choice', l2_media: 'choice' };  // the row's link to the L2 switch
  const BRANDS = [['mcb', 'MCB make and series, AC'], ['mcb_dc', 'MCB make and series, DC'], ['terminal_blocks', 'Terminal blocks']];
  const pct = (v) => Math.round(v * 1000) / 10;
  function spec(key) {  // [path, kind]; keys are n.<field>, s.<spare>, b.<brand>, e.<row>.<field>, l.<row>.<link field>, c.<row> (COM ports), o.<row>.<value>, f.<row>.<speed>.<media>[.total|.extra]
    const [kind, a, b, c, d] = key.split('.');
    if (kind === 'n') return [['network', a], NET[a]];
    if (kind === 's') return [['spares', a], SPARES[a][2]];
    if (kind === 'y') return [['layout', a], 'int'];  // M62: y.max_panels
    if (kind === 'i') return [['network', 'ied_schedule', Number(a), b], IED[b]];  // M60: i.<row>.<field>
    if (kind === 'x') return [['network', 'external_links', Number(a), b], XL[b]];  // M61: x.<row>.<field>
    if (kind === 'b') return [['catalogue_choice', a], 'choice'];
    if (kind === 'e') return [['equipment', Number(a), b], EQ[b]];
    if (kind === 'l') return [['equipment', Number(a), b], LINK[b]];
    if (kind === 'c') return [['equipment', Number(a), 'port_plan', 'serial_ports'], 'int'];
    if (kind === 'o') return [['equipment', Number(a), 'overrides', b], VALUES.find((v) => v[0] === b)[2]];
    if (kind === 'f' && d) return [['equipment', Number(a), 'sfp', b, c, d], 'int'];  // M49: extra; M87: total
    if (kind === 'f') return [['equipment', Number(a), 'sfp', b, c], 'choice'];
    return null;
  }
  const rowAt = (i) => sub().page().parts.rows[i];
  function saved(key) {
    const p = sub().page(); if (!p || !p.parts) return '';
    const [kind, a, b, c, d] = key.split('.');
    if (kind === 'n') { const v = p.network[a]; return a === 'ied_count' && !v ? '' : typeof v === 'boolean' ? String(v) : v; }
    if (kind === 's') { const r = p.spares.find((x) => x.key === a); return r ? (SPARES[a][2] === 'pct' ? pct(r.value) : r.value) : ''; }
    if (kind === 'b') return p.catalogue_choice[a] || '';
    if (kind === 'y') return p[a] == null ? '' : p[a];
    if (kind === 'x') { const r = p.parts.links[Number(a)]; if (!r) return ''; const v = r[b]; return v == null ? '' : typeof v === 'boolean' ? String(v) : v; }
    if (kind === 'i') { const r = p.parts.ieds[Number(a)]; if (!r) return ''; const v = b === 'ports' ? r.ports_text : r[b]; return v == null ? '' : v; }
    const r = rowAt(Number(a)); if (!r) return '';
    if (kind === 'e' && b === 'cable_manager') return r.cable_manager ? String(r.cable_manager.on) : '';
    if (kind === 'e' && b === 'alarm_on_branch_mcb') return r.alarm ? String(r.alarm.on) : '';  // M58
    if (kind === 'e' && (b === 'panel_hint' || b === 'priority')) return r.placement[b] == null ? '' : String(r.placement[b]);  // M74, M76
    if (kind === 'e' && r.bom_text && b in r.bom_text) { const v = r.bom_text[b]; return v == null ? '' : v; }
    if (kind === 'e') { const v = r[b]; return v == null ? '' : typeof v === 'boolean' ? String(v) : v; }
    if (kind === 'l') return r.link ? r.link[b] : '';
    if (kind === 'c') return r.serial_ports == null ? '' : r.serial_ports;
    if (kind === 'o') { const v = b in r.overrides ? r.overrides[b] : r.library ? r.library[b] : null; return v == null ? '' : v; }
    if (kind === 'f') {
      const f = r.sfp.find((x) => x.speed === b && x.media === c); if (!f) return '';
      if (d === 'total') return f.quantity.override == null ? '' : f.quantity.override;  /* M87: empty: the automatic spare */
      return d === 'extra' ? f.extra : f.choice || '';
    }
    return '';
  }
  let cleared = '';  // what a part change cleared, said once the save is done
  /* M87: the extra a typed SFP total keeps: the drafted one, which the same save writes in either order; null is the file's */
  const draftExtra = (path) => { const k = `f.${path[1]}.${path[3]}.${path[4]}.extra`; return k in PF.draft ? Number(PF.draft[k] || 0) : null; };
  function write(path, value) {
    const f = S.project.file, sid = S.sub;
    if (path[0] === 'equipment' && path[2] === 'sfp' && path[5] === 'total') return Bridge.call('set_sfp_total', f, sid, path[1], path[3], path[4], value, draftExtra(path));
    if (path[1] === 'ied_schedule') return Bridge.call('set_ied_field', f, sid, path[2], path[3], value);
    if (path[1] === 'external_links') return Bridge.call('set_external_link_field', f, sid, path[2], path[3], value);
    if (path[0] === 'equipment' && path[2] === 'overrides') return Bridge.call('set_part_override', f, sid, path[1], path[3], value);
    if (path[0] === 'equipment' && path[2] === 'cable_manager') return Bridge.call('set_cable_manager', f, sid, path[1], value === true);  // written only when it differs from the default
    if (path[0] === 'equipment' && path[2] === 'sfp' && path[5]) return Bridge.call('set_sfp_count', f, sid, path[1], path[3], path[4], path[5], value);
    if (path[0] === 'equipment' && path[2] === 'sfp') return Bridge.call('set_sfp_choice', f, sid, path[1], path[3], path[4], value || null);
    if (path[0] === 'equipment' && path[2] === 'part_id' && value) {
      return Bridge.call('set_equipment_part', f, sid, path[1], value).then((r) => {
        if (r.cleared.length) cleared = `Changed to ${value}. Its ${r.cleared.map((k) => ({ overrides: 'overrides', sfp: 'SFP choices', ordering_code: 'part number' })[k]).join(', ').replace(/, ([^,]*)$/, ' and $1')} ${r.cleared.length === 1 ? 'was' : 'were'} cleared, so the BOM prints the library's code.`;
        return r.page;
      });
    }
    if (path[0] === 'equipment' && path[2] === 'alarm_on_branch_mcb') {  // M58: the library's value is no choice
      const r = rowAt(path[1]);
      return Bridge.call('set_substation_field', f, sid, path, r && r.alarm && value === r.alarm.default ? null : value);
    }
    return Bridge.call('set_substation_field', f, sid, path, value);
  }
  const PF = App.draftForm({
    prefix: 'p-', screen: 'parts', file: 'substation.yaml', label: 'Save parts', spec, saved,
    check: (path, value) => (path[2] === 'sfp' && path[5] === 'total' ? Bridge.call('check_sfp_total', S.project.file, S.sub, path[1], path[3], path[4], value, draftExtra(path))
      : path[1] === 'ied_schedule' || path[1] === 'external_links' || path[2] === 'sfp' || path[2] === 'cable_manager' || path[2] === 'alarm_on_branch_mcb' ? Promise.resolve(null) : Bridge.call('check_substation_field', S.project.file, S.sub, path, value)),
    write,
    done: (page) => {
      if (page && page.parts) sub().set(page); else sub().reload();
      App.network.reload(); App.devicePreview.reload(); App.panelEditor.reload();
      if (cleared) { toast(cleared, 'info'); cleared = ''; }
    }
  });
  const UI = { tuning: null, editing: '', menu: -1, addOpen: false, fresh: null, expanded: new Set(), bomText: new Set(), iedMode: null };  // fresh: a new substation's rows before the first save
  sub().resets.push(() => { PF.reset(); Object.assign(UI, { tuning: null, editing: '', menu: -1, addOpen: false, fresh: null, expanded: new Set(), bomText: new Set(), iedMode: null }); });
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
  /* ADR 0037: a figure the library assumes; the title says what it rests on. */
  const ASSUMED = { unit_power_w: 'Assumed power', inrush_a: 'Assumed inrush' };
  const assumedChips = (r) => (r.assumed || []).map((a) => `<span title="${esc(`The library assumes this: ${a.ref}. Override it here or confirm it in the library.`)}">${App.badge('warn', ASSUMED[a.field], 'warn')}</span>`).join('');
  /* Plan M53: a part outside the design basis's vendor list builds, with this chip. */
  const offList = () => { const n = sub().page().parts.vendor_list; return `<span title="${esc(`${n} does not list this part. It still builds; Checks warns.`)}">${App.badge('warn', 'Not on the vendor list', 'warn')}</span>`; };
  const libValue = (r, f) => (r.library[f] == null ? '' : String(r.library[f]));
  function strip(r) {
    if (!r.part_id) return `<div class="prow-strip"><span class="muted small">${r.sized ? 'Pick the switch to change its data.' : 'Pick a part to see its data.'}</span></div>`;
    if (!r.library) return '<div class="prow-strip"></div>';
    if (!r.library.supply_type && !r.library.height_u) return '<div class="prow-strip"><span class="muted small">Passive part: no rack space, no power.</span></div>';
    const fields = r.library.supply_type ? VALUES : VALUES.filter(([f]) => f === 'height_u');  // an unpowered part has only a height
    const open = UI.expanded.has(r.index) || fields.some(([f]) => UI.editing === `o.${r.index}.${f}` || PF.errors[`o.${r.index}.${f}`]);
    if (sub().page().parts.rows.length >= 20 && !open) {  // 20 or more rows: one line per row; clicking it opens the strip
      const at = (f) => shown(`o.${r.index}.${f}`), n = fields.filter(([f]) => at(f) !== libValue(r, f)).length;
      const line = [FMT.height_u(at('height_u')), ...(r.library.supply_type ? [FMT.unit_power_w(at('unit_power_w')), at('voltage_v') ? `${at('voltage_v')} ${at('supply_type')}` : FMT.supply_type(at('supply_type'))] : [])].join(' · ');
      return `<div class="prow-strip"><button class="link-btn small prow-summary" data-action="pp-expand" data-i="${r.index}" aria-label="Show the data of ${esc(r.label)}: ${esc(line)}${n ? `, ${plural(n, 'override')}` : ''}">${esc(line)}${n ? ` · <i class="ov-dot" aria-hidden="true"></i>${n} override${n === 1 ? '' : 's'}` : ''}</button>${r.on_list === false ? offList() : ''}</div>`;
    }
    let overridden = 0;
    const vals = fields.map(([f, label, kind]) => {
      const key = `o.${r.index}.${f}`, id = `p-${key}`, v = shown(key), lib = libValue(r, f), ov = v !== lib, changed = key in PF.draft;
      if (ov) overridden += 1;
      if (UI.editing === key) {
        const ctl = f === 'supply_type' ? select(id, [['VDC', 'DC'], ['VAC', 'AC']], v, { cls: 'dv-input' })
          : f === 'load_type' ? select(id, [['CONTINUOUS', 'Continuous'], ['INTERMITTENT', 'Intermittent']], v, { cls: 'dv-input' })
          : input(id, v, { mono: true, num: true }).replace('class="input', 'class="dv-input input');
        return App.derived(key, { editing: true, id, label, control: ctl.replace('<input ', `<input data-dv="${key}" `).replace('<select ', `<select data-dv="${key}" `) });
      }
      return App.derived(key, { label, shown: FMT[f](v), auto: FMT[f](lib), autoLabel: 'Library', overridden: ov, changed, bad: !!PF.errors[key], edit: 'pp-edit', reset: 'pp-reset',
        resetLabel: `Reset ${label.toLowerCase()} to the library's ${esc(FMT[f](lib))}`, resetTitle: 'Reset to the library value', ...(PF.errors[key] ? { shown: v } : {}) });
    }).join('');
    const errs = fields.map(([f]) => err(`o.${r.index}.${f}`)).join('');
    return `<div class="prow-strip">${vals}${assumedChips(r)}${r.on_list === false ? offList() : ''}${overridden ? `<button class="btn btn--ghost btn--sm" data-action="pp-reset-all" data-i="${r.index}">Reset all</button>` : ''}${proposeButton(r)}</div>${errs ? `<div class="prow-err">${errs}</div>` : ''}`;
  }

  /* ---------- one device row ---------- */
  /* M83, Q82: a part is named by its make and model, never by its library id; an alternative also says
     which part it replaces. The id is only the value written to the file. */
  const TIER = { low: 'Low', mid: 'Mid', high: 'High' };
  const nameOf = (o) => [o.make, o.model].filter(Boolean).join(' ') || o.part_id;
  const altLine = (o) => (o.tier && o.replaces ? `${TIER[o.tier]}-tier alternative to ${nameOf(o.replaces)}` : '');
  const partText = (o) => [nameOf(o), altLine(o)].filter(Boolean).join(' · ');
  const rowPart = (p, r) => { const o = (p.parts.options[r.category] || []).find((x) => x.part_id === r.part_id); return o ? nameOf(o) : r.part_id; };
  /* The row offers its own choices (the API's rule); the Device picker, with Search all parts, opens
     whenever the category is long or holds parts the row does not offer. */
  const usePicker = (opts, own) => opts.length > 12 || own.length < opts.length;
  const emptyLine = (p, category, label) => `<div class="prow-empty muted small">The library has no ${esc(label)} parts yet.</div>`;
  function partSelect(p, r) {
    const key = `e.${r.index}.part_id`, id = `p-${key}`, v = shown(key), opts = p.parts.options[r.category] || [], own = r.choices;
    if (!opts.length && !r.part_id) return emptyLine(p, r.category, r.label);
    const missing = r.part_id && !r.known && v === r.part_id, picked = opts.find((o) => o.part_id === v);
    const first = r.sized && r.role === 'l1_switch' ? `<option value="" ${!v ? 'selected' : ''}>The sizing picks the switch</option>` : '';
    if (usePicker(opts, own)) {
      const text = picked ? partText(picked) : v || (first ? 'The sizing picks the switch' : 'Pick a part');
      return `<div class="prow-partwrap">${mark(key, pickButton(id, r.category, r.label, v, text, { first: !!first, missing, title: picked ? partText(picked) : '', unset: !v, row: r.index }))}
        ${missing ? `<span class="err small" id="${id}-missing">${icon('error')}<span>Not in ${esc(p.project.library.name)} ${esc(p.project.library.version)}. Pick another part.</span></span>` : ''}${err(key)}</div>`;
    }
    return `<div class="prow-partwrap">${mark(key, `<select class="select prow-part${missing ? ' is-missing' : ''}" id="${id}" data-dirty="1" aria-label="Part for ${esc(r.label)}" ${picked ? `title="${esc(partText(picked))}"` : ''} ${missing ? `aria-invalid="true" aria-describedby="${id}-missing"` : ''}>
        ${first}${missing ? `<option value="${esc(r.part_id)}" selected>${esc(r.part_id)}</option>` : ''}${own.map((o) => `<option value="${esc(o.part_id)}" ${o.part_id === v ? 'selected' : ''}>${esc(partText(o))}</option>`).join('')}</select>`)}
      ${missing ? `<span class="err small" id="${id}-missing">${icon('error')}<span>Not in ${esc(p.project.library.name)} ${esc(p.project.library.version)}. Pick another part.</span></span>` : ''}${err(key)}</div>`;
  }
  /* M46: a link the library has no SFP for stops the build; say so on the row first. */
  const noSfp = (speed, media) => `<span class="err small">${icon('warn')}<span>No ${esc(speed)} ${esc(media)} SFP in the library: pick another speed or media, or add the SFP to the library.</span></span>`;
  /* M86: an SFP part is named by its make and model like every other part (Q82); the automatic choice
     names the part the engine takes without one. */
  const sfpOpt = (id) => (sub().page().parts.options.sfp || []).find((o) => o.part_id === id) || { part_id: id };
  const autoText = (f) => (f.auto ? `Automatic: ${nameOf(sfpOpt(f.auto))}` : 'Automatic');
  /* M86, Q76 (a): an L1 row left to the sizing shows the SFPs of the switch the sizing picked, read-only;
     pinning that switch to the row makes them the editable rows below, with the same numbers. */
  /* M87: when one entry's BOM rows differ by cabinet, each cabinet's row with what it prints, read-only */
  const cabinetRows = (r, f) => (f.agree ? '' : f.rows.map((x) => `<div class="prow-strip prow-sfp" role="group" aria-label="${esc(`${f.speed} ${f.media} SFPs in ${x.cabinet}, ${r.label}`)}">
      <span class="dv"><span class="dv-label">${esc(x.cabinet)}</span><span class="dv-val">${x.quantity}</span></span><span class="dv-rule">${esc(x.rule)} = ${x.quantity}</span></div>`).join(''));
  function sizedSfpRows(r) {
    if (!r.sfp.length) return '';
    const dirty = PF.dirty(), help = `pp-pinhelp-${r.index}`;
    const rows = r.sfp.map((f) => `<div class="prow-sub"><span class="prow-sub-what">${esc(f.speed)} · ${esc(f.media)} SFP</span><span class="small">${esc(autoText(f))}</span></div>
      ${f.agree ? `<div class="prow-strip prow-sfp" role="group" aria-label="${esc(`${f.speed} ${f.media} SFPs, ${r.label}`)}">
        <span class="dv" title="From the switch sizing"><span class="dv-label">Links</span><span class="dv-val">${f.used}</span></span>
        <span class="dv"><span class="dv-label">Spare</span><span class="dv-val">${f.spare.value}</span></span>
        <span class="dv" title="${esc(f.rule)}"><span class="dv-label">Each BOM row</span><span class="dv-val">${f.total}</span></span>
        <span class="dv-rule">${esc(f.rule)}. Automatic spare ${esc(f.spare.rule)}.</span>
      </div>` : cabinetRows(r, f)}${f.candidates.length ? '' : `<div class="prow-err">${noSfp(f.speed, f.media)}</div>`}`).join('');
    /* M87: on hand-written panels the BOM takes the files' port plans: the same read-only rows, no pin */
    if (r.sfp_hand) return `${rows}<div class="prow-sub prow-sub--foot"><span class="muted small">${esc(r.sfp_hand)}</span></div>`;
    return `${rows}<div class="prow-sub prow-sub--foot"><button class="btn btn--secondary btn--sm" data-action="pp-pin" data-i="${r.index}" aria-describedby="${help}" ${dirty ? 'disabled title="Save or discard the changes first"' : ''}>Pin this switch to change its SFPs</button>
      <span class="muted small" id="${help}">The sizing picked ${esc(nameOf(r.pin))}. Pinning writes it to this row: the row then keeps this switch when the IED count changes.</span></div>`;
  }
  function sfpRows(r) {
    if (r.sfp_reason) return `<div class="prow-err"><span class="err small">${icon('warn')}<span>${esc(r.sfp_reason)}</span></span></div>`;
    if (r.sfp_hand) return sizedSfpRows(r);  /* M87: read-only, from the hand-written panel files */
    if (r.pin) return sizedSfpRows(r);
    return r.sfp.map((f) => {
      const key = `f.${r.index}.${f.speed}.${f.media}`;
      return `<div class="prow-sub"><span class="prow-sub-what">${esc(f.speed)} · ${esc(f.media)} SFP</span>
        ${mark(key, select(`p-${key}`, [['', autoText(f)], ...f.candidates.map((c) => [c, partText(sfpOpt(c))])], shown(key)).replace('<select ', `<select aria-label="SFP for ${esc(f.speed)} ${esc(f.media)}, ${esc(r.label)}" `))}</div>${sfpCounts(r, f, key)}${f.candidates.length ? '' : `<div class="prow-err">${noSfp(f.speed, f.media)}</div>`}`;
    }).join('');
  }
  /* M49: the SFPs on each BOM row of the switch: links (the sizing's), the total and the extra (derived values).
     M87, Q77 (a): the total is typed; it is stored as the spare it implies, so the spare has no editor of its own. */
  function sfpCounts(r, f, base) {
    const what = `${f.speed} ${f.media} SFPs, ${r.label}`, tk = `${base}.total`, xk = `${base}.extra`;
    const dv = (key, label, auto, o = {}) => {
      const v = shown(key), id = `p-${key}`;
      /* M86: the editor opens on the automatic value, as the switch-count editor does */
      if (UI.editing === key) return App.derived(key, { editing: true, id, label, control: input(id, v === '' ? String(auto) : v, { mono: true, num: true, invalid: !!PF.errors[key] }).replace('class="input', 'class="dv-input input').replace('<input ', `<input data-dv="${key}" aria-label="${label}, ${esc(what)}" `) });
      return App.derived(key, { label, shown: v === '' ? String(auto) : v, auto: String(auto), overridden: v !== '' && (o.always || v !== String(auto)), changed: key in PF.draft, bad: !!PF.errors[key], edit: 'pp-edit', reset: 'pp-reset', ...o.more });
    };
    /* a typed total is marked even when it equals the automatic one: it no longer follows the project's spare */
    const waiting = xk in PF.draft && !(tk in PF.draft), errs = [tk, xk].map(err).join('');
    /* M87: when the cabinets' rows differ, the total is typed for the row it is computed on, named by its cabinet */
    const label = f.agree ? 'Each BOM row' : `Row in ${esc(f.on)}`;
    const total = dv(tk, label, f.quantity.value, { always: true, more: waiting ? { shown: '…' } : {} });
    const leaves = `the spare is what your total leaves after the ${f.used} links${f.extra || xk in PF.draft ? ' and the extra' : ''}.`;
    const why = waiting ? 'Save to update the total.'
      : tk in PF.draft ? (PF.draft[tk] === '' ? 'Save to go back to the automatic total.' : `${f.agree ? 'Each BOM row' : `The row in ${esc(f.on)}`} carries the total you type; ${leaves}`)
        : !f.agree ? `The rows differ by cabinet: you set the total of the row in ${esc(f.on)}, which has the most links, and the spare it implies is added to every cabinet's row.`
          : f.quantity.override != null ? `${esc(f.rule)}: ${leaves}`
            : `${esc(f.quantity.rule)}.`;
    return `<div class="prow-strip prow-sfp" role="group" aria-label="${esc(what)}">
      <span class="dv" title="From the switch sizing"><span class="dv-label">Links</span><span class="dv-val">${f.used}</span></span>
      ${total}${dv(xk, 'Extra', 0)}
      <span class="dv-rule">${why} Extra SFPs add to the BOM, not to the port budget.</span>
    </div>${errs ? `<div class="prow-err">${errs}</div>` : ''}${cabinetRows(r, f)}`;
  }
  function linkRow(r) {  // M31: how the device reaches the L2 switch, and an RTAC's COM ports
    if (!r.link || !r.part_id) return '';
    const k = (f) => `l.${r.index}.${f}`, com = `c.${r.index}`, id = (key) => `p-${key}`;
    const ports = input(id(k('l2_ports')), shown(k('l2_ports')), { num: true, mono: true, invalid: !!PF.errors[k('l2_ports')] }).replace('<input ', `<input aria-label="Ports linked to the L2 switch, ${esc(r.label)}" `);
    const speed = select(id(k('l2_speed')), ['10M', '100M', '1G', '10G'], String(shown(k('l2_speed')))).replace('<select ', `<select aria-label="Link speed, ${esc(r.label)}" `);
    const media = select(id(k('l2_media')), ['MM', 'SM', 'RJ45'], String(shown(k('l2_media')))).replace('<select ', `<select aria-label="Link media, ${esc(r.label)}" `);
    const serial = r.serial_ports == null ? '' : `<span class="prow-link-com"><label class="prow-sub-what" for="${id(com)}">COM ports used</label>${mark(com, input(id(com), shown(com), { num: true, mono: true, invalid: !!PF.errors[com] }))}</span>`;
    const errs = [...Object.keys(LINK).map(k), com].map(err).join('') + (r.link.no_sfp ? noSfp(r.link.l2_speed, r.link.l2_media) : '');
    return `<div class="prow-sub prow-link"><span class="prow-sub-what">Link to the L2 switch</span>${mark(k('l2_ports'), ports)}<span class="muted" aria-hidden="true">×</span>${mark(k('l2_speed'), speed)}${mark(k('l2_media'), media)}${serial}</div>${errs ? `<div class="prow-err">${errs}</div>` : ''}`;
  }
  function accessories(p, r) {
    const a = r.accessories; if (!a) return '';
    const own = a.library.length ? `<div class="prow-sub prow-sub--foot"><span class="muted small">Comes with ${esc(rowPart(p, r))}: ${a.library.map((x) => `<span class="mono">${esc(x.part_id)}</span> × ${x.qty}`).join(', ')}. They go to loose material.</span></div>` : '';
    const added = a.added.map((x) => `<div class="prow-sub"><span class="prow-sub-what">Accessory <span class="mono">${esc(x.part_id)}</span></span><span></span>
        <div class="prow-qty"><input class="input input--num input--mono" id="pp-accq-${x.index}" data-acc="${x.index}" value="${esc(x.item.qty)}" aria-label="Quantity of ${esc(x.part_id)}"></div>
        <button class="btn btn--ghost btn--icon btn--sm btn--del" data-action="pp-acc-remove" data-index="${x.index}" aria-label="Remove ${esc(x.part_id)}">${icon('trash')}</button></div>`).join('');
    const foot = !a.parts.length ? '' : a.host_panel == null
      ? `<div class="prow-sub prow-sub--foot"><span class="muted small">To add accessories, set the loose material's host panel first.</span><a class="btn btn--ghost btn--sm" href="#/loose">Open Loose material</a></div>`
      : `<div class="prow-sub prow-sub--foot"><label class="sr-only" for="pp-acc-part">Accessory to add</label><select class="select" id="pp-acc-part">${a.parts.map((x) => `<option value="${esc(x)}">${esc(x)}</option>`).join('')}</select><button class="btn btn--ghost btn--sm" data-action="pp-acc-add" ${PF.dirty() ? 'disabled title="Save or discard the changes first"' : ''}>${icon('plus')}Add accessory</button><span class="muted small">Accessories go to loose material.</span></div>`;
    return own + added + foot;
  }
  /* M59: purpose, tag, type code, first number and HWIO points the layout copies onto the row; the
     placeholders are what the engine generates. The duplicate-tag check shows on the row. */
  function bomText(r) {
    if (!r.part_id || !r.bom_text) return '';  /* M90: none of it reaches an annunciator's loose item */
    const k = (f) => `e.${r.index}.${f}`, open = UI.bomText.has(r.index) || BOM_TEXT.some(([f]) => PF.errors[k(f)]);
    const set = BOM_TEXT.filter(([f]) => shown(k(f)) !== '');
    const summary = set.length ? set.map(([f, label]) => `${label} ${shown(k(f))}`).join(' · ') : r.tags[0] || 'As generated';
    const dup = r.duplicate ? `<div class="prow-err"><span class="err small">${icon('error')}<span>${esc(r.duplicate)}</span></span></div>` : '';
    const body = open ? `<div class="form form--3 prow-bomtext" id="pp-bt-${r.index}">${BOM_TEXT.map(([f, label, ph]) => mark(k(f), field(label, input(`p-${k(f)}`, shown(k(f)), { mono: f !== 'purpose' && f !== 'note', num: EQ[f] === 'int', placeholder: ph(r), invalid: !!PF.errors[k(f)] }), '', PF.err(k(f))))).join('')}</div>` : '';
    return `<div class="prow-sub prow-sub--foot"><button class="link-btn small" data-action="pp-bomtext" data-i="${r.index}" aria-expanded="${open}" aria-controls="pp-bt-${r.index}">${icon(open ? 'chevd' : 'chevr')}BOM text</button><span class="muted small prow-bt-sum">${esc(summary)}</span></div>${body}${dup}`;
  }
  /* M74: steer a common row's units to a panel without pinning them; the layout says when they do not fit.
     M76: the row's rack priority, the category's when Automatic (spec "Where in the panel"). */
  const PRIORITIES = [['1', '1 Top, with the time server'], ['2', '2 With the network devices'], ['3', '3 With the servers and workstations'], ['4', '4 With the rest']];
  function placeRow(p, r) {
    if (!r.part_id || !r.placement) return '';  /* M90: an annunciator is loose material, never racked */
    const pk = `e.${r.index}.priority`, auto = PRIORITIES[r.placement.default_priority - 1][1].replace(/^\d /, '');
    const prio = `<span class="prow-sub-what">Rack priority</span>${mark(pk, select(`p-${pk}`, [['', `Automatic: ${auto.toLowerCase()}`], ...PRIORITIES], shown(pk)).replace('<select ', `<select aria-label="Rack priority of ${esc(r.label)}" `))}`;
    const line = `<div class="prow-sub prow-link prow-place">${prio}</div>${err(pk)}`;
    if (r.sized || !r.placement.steerable) return line;
    const key = `e.${r.index}.panel_hint`, v = shown(key), n = Math.max(App.panelCount() || p.panels || 0, +v || 0);
    const opts = [['', 'Automatic: most free space'], ...Array.from({ length: n }, (_, i) => [String(i + 1), `Panel ${i + 1}`])];
    return `<div class="prow-sub prow-link prow-place"><span class="prow-sub-what">Panel</span>${mark(key, select(`p-${key}`, opts, v).replace('<select ', `<select aria-label="Panel for ${esc(r.label)}" aria-describedby="pp-pin-${r.index}" `))}<span class="muted small" id="pp-pin-${r.index}">Not a pin: if it does not fit there, it goes where there is room.</span></div>${err(key)}${line}`;
  }
  function partRow(p, r, last) {
    const changed = Object.keys(PF.draft).some((k) => k.split('.')[1] === String(r.index) && 'eofcl'.includes(k[0]));
    const opts = p.parts.options[r.category] || [], empty = !opts.length && !r.part_id;
    const fixed = r.sized, dirty = PF.dirty();
    const pn = `e.${r.index}.ordering_code`, qty = `e.${r.index}.qty`, ab = `e.${r.index}.redundant`, cm = `e.${r.index}.cable_manager`, al = `e.${r.index}.alarm_on_branch_mcb`;
    return `<div class="prow" role="group" aria-label="${esc(r.label)}${r.part_id ? ', ' + esc(rowPart(p, r)) : ', no part yet'}">
      <div class="prow-top">
        <span class="prow-role">${changed ? '<span class="chg-dot" aria-hidden="true"></span><span class="sr-only">changed, </span>' : ''}${esc(r.label)} <span class="muted small mono">${esc(r.id)}</span></span>
        <span class="sp"></span>
        ${r.cable_manager ? `<label class="switch prow-cm" title="${r.cable_manager.zero_u ? 'This part is 0 U, so the BOM has no cable manager for it.' : r.cable_manager.default ? 'On by default for this part' : 'Off by default for this part'}"><input type="checkbox" id="p-${cm}" ${shown(cm) === 'true' ? 'checked' : ''} data-dirty="1">Cable manager</label>${r.cable_manager.zero_u ? '<span class="muted small">0 U: none in the BOM</span>' : ''}` : ''}
        ${r.alarm ? `<label class="switch prow-cm" title="The library says ${r.alarm.default ? 'on' : 'off'}. An alarm adds an auxiliary contact on the device's branch MCBs; on an AC branch it is also one HWIO point."><input type="checkbox" id="p-${al}" ${shown(al) === 'true' ? 'checked' : ''} data-dirty="1">Alarm on branch MCB trip</label>` : ''}
        ${empty || !r.ab ? '' : `<label class="check prow-ab"><input type="checkbox" id="p-${ab}" ${shown(ab) === 'true' ? 'checked' : ''} data-dirty="1"> A and B</label>`}
        <div class="prow-menu-wrap"><button class="btn btn--ghost btn--icon btn--sm" data-action="pp-menu" data-i="${r.index}" aria-haspopup="menu" aria-expanded="${UI.menu === r.index}" aria-label="More for ${esc(r.label)}" ${dirty ? 'disabled title="Save or discard the changes first"' : ''}>${icon('dots')}</button>
          ${UI.menu === r.index ? `<div class="menu" role="menu" style="right:0;top:34px"><button role="menuitem" data-action="pp-move" data-i="${r.index}" data-d="-1" ${r.index === 0 ? 'disabled' : ''}>Move up</button><button role="menuitem" data-action="pp-move" data-i="${r.index}" data-d="1" ${last ? 'disabled' : ''}>Move down</button>${fixed ? '' : `<hr><button role="menuitem" class="danger" data-action="pp-remove" data-i="${r.index}">${icon('trash')}Remove</button>`}</div>` : ''}</div>
      </div>
      <div class="prow-fields">
        ${partSelect(p, r)}
        ${empty ? '' : `<div class="prow-pn">${mark(pn, `<input class="input input--mono" id="p-${pn}" value="${esc(shown(pn))}" placeholder="${r.part_id ? 'Prints the library code' : 'Part number'}" aria-label="Part number on the BOM for ${esc(r.label)}" data-dirty="1" ${!r.part_id ? 'disabled' : ''}>`)}${err(pn)}</div>
        <div class="prow-qty">${r.sized ? '<span class="muted small" title="The sizing sets the quantity">Sized</span>' : `${input('p-' + qty, shown(qty), { num: true, mono: true, invalid: !!PF.errors[qty] }).replace('<input ', `<input aria-label="Quantity of ${esc(r.label)}" `)}`}</div>`}
      </div>
      ${empty ? '' : strip(r)}${placeRow(p, r)}${linkRow(r)}${sfpRows(r)}${bomText(r)}${accessories(p, r)}
    </div>`;
  }

  /* ---------- the Device picker (components.md "Device picker (combobox)") ----------
     A button in the select's place; the pick is set as its value and sent as a change, so the draft form
     and the part-change handlers below treat it as the select it replaces. */
  function pickButton(id, category, label, value, text, o) {
    return `<button type="button" class="select prow-part prow-pick${o.missing ? ' is-missing' : ''}${o.unset ? ' is-unset' : ''}" id="${id}" value="${esc(value || '')}" data-action="pp-pick" data-cat="${esc(category)}" data-label="${esc(label)}" ${o.first ? 'data-first="1"' : ''} ${o.row != null ? `data-row="${o.row}"` : ''} ${o.fresh != null ? `data-fresh="${o.fresh}"` : 'data-dirty="1"'}
      aria-haspopup="listbox" aria-expanded="false" aria-label="Part for ${esc(label)}: ${esc(text)}" ${o.title ? `title="${esc(o.title)}"` : ''} ${o.missing ? `aria-invalid="true" aria-describedby="${id}-missing"` : ''}>${esc(text)}</button>`;
  }
  let pk = null;  // the open picker: { btn, pop }
  function closePicker(focus) {
    if (!pk) return;
    const { btn, pop } = pk; pk = null;
    pop.remove(); btn.setAttribute('aria-expanded', 'false');
    if (focus && btn.isConnected) btn.focus();
  }
  function openPicker(btn) {
    const p = sub().page(), lib = p.project.library, all = p.parts.options[btn.dataset.cat] || [], label = btn.dataset.label;
    const own = btn.dataset.fresh != null ? p.parts.default_rows[+btn.dataset.fresh].choices : p.parts.rows[+btn.dataset.row].choices;
    let wide = false;  // "Search all parts": the whole category instead of the row's own choices
    const pop = document.createElement('div');
    pop.className = 'popover pk';
    pop.innerHTML = `<div class="input-wrap">${icon('search')}<input class="input" id="pk-q" role="combobox" aria-expanded="true" aria-controls="pk-list" aria-autocomplete="list" aria-label="Search the ${esc(label)} parts" placeholder="Search part, make, model or tag" autocomplete="off"></div>
      <div class="listbox" id="pk-list" role="listbox" aria-label="${esc(label)} parts in ${esc(lib.name)} ${esc(lib.version)}"></div>
      <div class="pk-hint small muted" id="pk-hint"></div>`;
    btn.after(pop); btn.setAttribute('aria-expanded', 'true');
    pk = { btn, pop };
    const q = pop.querySelector('#pk-q'), list = pop.querySelector('#pk-list'), hint = pop.querySelector('#pk-hint');
    let active = 0;
    const draw = () => {
      const t = q.value.trim().toLowerCase(), base = wide ? all : own;
      const cur = all.find((o) => o.part_id === btn.value), opts = cur && !base.some((o) => o.part_id === cur.part_id) ? [cur, ...base] : base;  // a pick made in the whole list stays shown
      const found = t ? opts.filter((o) => [o.part_id, o.make, o.model, altLine(o), ...(o.tags || [])].join(' ').toLowerCase().includes(t))
        : [...opts.filter((o) => o.part_id === btn.value), ...opts.filter((o) => o.part_id !== btn.value)];  // the current part first
      const shown = found.slice(0, 8), first = !t && btn.dataset.first ? [{ part_id: '', sizing: true }] : [];
      const toggle = own.length < all.length ? [{ part_id: '', all: true }] : [];
      const items = [...first, ...shown, ...toggle];
      list.innerHTML = (shown.length || first.length ? '' : '<div class="pk-none muted small">No device matches. Check the spelling, or install a library that has it.</div>')
        + items.map((o, i) => o.sizing
          ? `<div role="option" id="pk-${i}" data-v="" aria-selected="false"><span>The sizing picks the switch</span><span class="sub">The engine picks the L1 switch from the IED count.</span></div>`
          : o.all
          ? `<div role="option" id="pk-${i}" data-all="1" aria-selected="false"><span>${wide ? 'Show the parts for this row' : 'Search all parts'}</span><span class="sub">${wide ? `${own.length} for this row.` : `All ${all.length}, not only the ${own.length} for this row.`}</span></div>`
          : `<div role="option" id="pk-${i}" data-v="${esc(o.part_id)}" aria-selected="false"><span>${esc(nameOf(o))}${o.part_id === btn.value ? ` <span class="muted small">current</span>` : ''}</span>
          <span class="sub">${esc([wide ? o.level : '', altLine(o), FMT.supply_type(o.supply_type), o.unit_power_w != null ? `${o.unit_power_w} W` : ''].filter((x) => x && x !== '—').join(' · '))}</span><span class="right">${o.on_list === false ? App.badge('warn', 'Not on the list', 'warn') : ''}${App.verified(o.data_quality) || ''}</span></div>`).join('');
      hint.innerHTML = `${found.length > shown.length ? `Showing ${shown.length} of ${found.length}. Type to narrow the list. ` : ''}From ${esc(lib.name)} ${esc(lib.version)}. <kbd class="kbd">↑</kbd> <kbd class="kbd">↓</kbd> to move, <kbd class="kbd">Enter</kbd> to pick, <kbd class="kbd">Esc</kbd> to close.`;
      active = 0; markActive();
    };
    const options = () => [...list.querySelectorAll('[role="option"]')];
    const markActive = () => options().forEach((o, i) => {
      o.setAttribute('aria-selected', String(i === active));
      if (i === active) { q.setAttribute('aria-activedescendant', o.id); o.scrollIntoView({ block: 'nearest' }); }
    });
    const pick = (v) => {
      closePicker(false);
      btn.value = v;
      btn.dispatchEvent(new Event('change', { bubbles: true }));
      queueMicrotask(() => { const b = document.getElementById(btn.id); if (b) b.focus(); });  // after the re-render
    };
    const choose = (o) => { if (o.dataset.all) { wide = !wide; draw(); q.focus(); } else pick(o.dataset.v); };  // Search all parts switches the list
    q.addEventListener('input', draw);
    q.addEventListener('keydown', (e) => {
      const n = options().length;
      if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, n - 1); markActive(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); markActive(); }
      else if (e.key === 'Enter') { e.preventDefault(); if (n) choose(options()[active]); }
      else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closePicker(true); }
      else if (e.key === 'Tab') closePicker(false);
    });
    list.addEventListener('mousedown', (e) => e.preventDefault());  // keep the focus in the search
    list.addEventListener('click', (e) => { const o = e.target.closest('[role="option"]'); if (o) choose(o); });
    draw(); q.focus();
  }
  ACTIONS['pp-pick'] = (el) => { const again = pk && pk.btn === el; closePicker(false); if (!again) openPicker(el); };
  document.addEventListener('mousedown', (e) => { if (pk && !pk.pop.contains(e.target) && e.target !== pk.btn) closePicker(false); });

  /* ---------- a new substation: the default rows, saved together with the sized L1 switch ---------- */
  function freshRows(p) {
    if (!UI.fresh) UI.fresh = p.parts.default_rows.map((d) => ({ ...d, part_id: '', redundant: ['l1_switch', 'l2_switch'].includes(d.role) }));
    return UI.fresh;
  }
  function freshRow(p, d, j) {
    const opts = p.parts.options[d.category] || [], own = d.choices;
    const l1 = d.role === 'l1_switch';
    const picked = opts.find((o) => o.part_id === d.part_id);
    const ctl = !opts.length ? emptyLine(p, d.category, d.label)
      : usePicker(opts, own) ? `<div class="prow-partwrap">${pickButton(`pn-part-${j}`, d.category, d.label, d.part_id, picked ? partText(picked) : l1 ? 'The sizing picks the switch' : 'Pick a part', { first: l1, title: picked ? partText(picked) : '', unset: !d.part_id, fresh: j })}</div>`
      : `<select class="select prow-part" id="pn-part-${j}" data-fresh="${j}" aria-label="Part for ${esc(d.label)}">${l1 ? `<option value="" ${!d.part_id ? 'selected' : ''}>The sizing picks the switch</option>` : `<option value="" ${!d.part_id ? 'selected' : ''}>Pick a part</option>`}${own.map((o) => `<option value="${esc(o.part_id)}" ${o.part_id === d.part_id ? 'selected' : ''}>${esc(partText(o))}</option>`).join('')}</select>`;
    return `<div class="prow" role="group" aria-label="${esc(d.label)}"><div class="prow-top"><span class="prow-role">${esc(d.label)}</span><span class="sp"></span>
        ${opts.length && d.ab ? `<label class="check prow-ab"><input type="checkbox" data-fresh-ab="${j}" ${d.redundant ? 'checked' : ''}> A and B</label>` : ''}</div>
      <div class="prow-fields">${ctl}</div></div>`;
  }
  function setupCard(p, rows) {
    const hasIed = !!((+shown('n.ied_count') && !PF.errors['n.ied_count']) || p.parts.ieds.length), picked = rows.filter((d) => d.part_id).length;
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
    const summary = `${ring ? `Rings of up to ${shown('n.ring_max_switches')}` : 'Star'} · ${plural(+shown('n.l1_uplinks_per_switch'), 'uplink')} per L1 · ${shown('n.l1_interlink') === 'true' ? 'A–B interlink' : 'no interlink'} · ${shown('s.port_fraction')}% ports kept free · ${shown('s.rack_u_reserved')} U kept free${shown('y.max_panels') ? ` · at most ${plural(+shown('y.max_panels'), 'panel')}` : ''}`;
    const changedSpare = (k) => { const r = sp(k); if (!r || !r.changed) return 'Project default.'; const d = SPARES[k][2] === 'pct' ? pct(r.default) : r.default; return `Changed from ${d}${SPARES[k][1] && SPARES[k][1] !== '%' ? ' ' + SPARES[k][1] : SPARES[k][1]}.`; };
    return `<div class="disclosure"><button class="disclosure-head" data-action="pp-tuning" aria-expanded="${open}" aria-controls="ft-body">${icon(open ? 'chevd' : 'chevr')}<b>Network fine tuning</b><span class="muted small">${open ? 'Ring size, uplinks and spares' : esc(summary)}</span></button>
      ${open ? `<div id="ft-body" class="form form--3 disclosure-body">
        ${ring ? numField('n.ring_max_switches', 'Switches per ring', '', 'Most L1 switches in one ring.') : ''}
        ${numField('n.l1_uplinks_per_switch', 'L1 uplinks per switch', '')}
        ${mark('n.l1_interlink', field('A–B interlink', select('p-n.l1_interlink', [['true', 'Yes'], ['false', 'No']], shown('n.l1_interlink'))))}
        ${numField('n.l3_uplinks_per_l2', 'L3 uplinks per L2', '')}
        ${Object.entries(SPARES).map(([k, [label, unit]]) => numField(`s.${k}`, label, unit, changedSpare(k))).join('')}
        ${numField('y.max_panels', 'Most panels', '', 'Empty: as many as the devices need. A device that does not fit is listed on Panels.')}
      </div>` : ''}</div>`;
  }
  /* ---------- the IED schedule (M60, ADR 0034) ---------- */
  function iedMode(p, schedule) {
    const rows = p.parts.ieds.length, dirty = PF.dirty();
    const why = rows ? `Remove the ${plural(rows, 'row')} of the schedule to size from a count again.` : '';
    return `<div class="row" style="margin-top:var(--space-3);gap:var(--space-3)"><div class="segmented" role="radiogroup" aria-label="How the L1 switches are sized">
        <button role="radio" data-action="pp-ied-mode" data-m="count" aria-checked="${!schedule}" aria-pressed="${!schedule}" ${rows || dirty ? `disabled title="${esc(why || 'Save or discard the changes first')}"` : ''}>Quick count</button>
        <button role="radio" data-action="pp-ied-mode" data-m="schedule" aria-checked="${schedule}" aria-pressed="${schedule}" ${dirty && !schedule ? 'disabled title="Save or discard the changes first"' : ''}>IED schedule</button></div>
      <span class="muted small">${schedule ? 'Each IED row sizes the L1 switches by port speed and media.' : 'One number: every IED port of an L1 switch counts.'}</span></div>`;
  }
  function iedTable(p) {
    const rows = p.parts.ieds, dirty = PF.dirty();
    const cell = (i, f, opts) => { const key = `i.${i}.${f}`, id = `p-${key}`, v = shown(key);
      const ctl = f === 'attachment' ? select(id, ATTACH, v) : f === 'lands_on' ? select(id, LANDS, v)
        : input(id, v, { mono: f === 'qty' || f === 'ports', num: f === 'qty', invalid: !!PF.errors[key], ...(opts || {}) });
      return `<td>${mark(key, ctl.replace(/<(input|select) /, `<$1 aria-label="${esc(IED_LABEL[f])}, row ${i + 1}" `))}${err(key)}</td>`; };
    const body = rows.map((r, i) => `<tr>${cell(i, 'bay')}${cell(i, 'name')}${cell(i, 'qty')}${cell(i, 'ports', { placeholder: '1x100M MM' })}${cell(i, 'attachment')}${cell(i, 'lands_on')}${cell(i, 'notes')}
        <td><button class="btn btn--ghost btn--sm btn--icon" data-action="pp-ied-rm" data-i="${i}" aria-label="Remove ${esc(r.bay)} ${esc(r.name)}" ${dirty ? 'disabled title="Save or discard the changes first"' : ''}>${icon('trash')}</button></td></tr>`).join('');
    return `<div style="margin-top:var(--space-4)"><h4 id="h-ied">IED schedule</h4>
      <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">Ports are per side: write count x speed media, for example <span class="mono">2x100M MM + 1x1G RJ45</span>. A row landing on L2 adds to the L2 ports. Never listed in the BOM.</p>
      ${rows.length ? `<div class="table-wrap"><table class="table ied-table" aria-labelledby="h-ied"><thead><tr><th>Bay</th><th>IED</th><th class="num">Qty</th><th>Ports per side</th><th>Attached to</th><th>Lands on</th><th>Notes</th><th><span class="sr-only">Remove</span></th></tr></thead><tbody>${body}</tbody></table></div>`
        : '<div class="empty small"><b>No IED rows yet.</b> Add the IEDs by bay, or import the protection design\'s CSV.</div>'}
      <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary btn--sm" data-action="pp-ied-add" ${dirty ? 'disabled title="Save or discard the changes first"' : ''}>${icon('plus')}Add a row</button>
        <button class="btn btn--secondary btn--sm" data-action="pp-ied-csv" ${dirty ? 'disabled title="Save or discard the changes first"' : ''}>Import CSV…</button></div></div>`;
  }
  /* ---------- external links (M61) ---------- */
  const XL_LABEL = { name: 'Name', count: 'Links', speed: 'Speed', media: 'Media', lands_on: 'Lands on', through_firewall: 'Through the firewall', redundant: 'Sides', cable_length_m: 'Cable length' };
  function linksTable(p) {
    const rows = p.parts.links, dirty = PF.dirty();
    const cell = (i, f) => { const key = `x.${i}.${f}`, id = `p-${key}`, v = shown(key);
      const ctl = f === 'speed' ? select(id, ['10M', '100M', '1G', '10G'], v) : f === 'media' ? select(id, ['SM', 'MM', 'RJ45'], v)
        : f === 'lands_on' ? select(id, [['l2', 'L2'], ['ext', 'EXT']], v) : f === 'through_firewall' ? select(id, [['false', 'No'], ['true', 'Yes']], v)
        : f === 'redundant' ? select(id, [['true', 'Both'], ['false', 'A only']], v)
        : input(id, v, { mono: f !== 'name', num: f === 'count' || f === 'cable_length_m', invalid: !!PF.errors[key], placeholder: f === 'cable_length_m' ? '—' : '' });
      return `<td>${mark(key, ctl.replace(/<(input|select) /, `<$1 aria-label="${esc(XL_LABEL[f])}, link ${i + 1}" `))}${err(key)}</td>`; };
    const body = rows.map((r, i) => `<tr>${Object.keys(XL).map((f) => cell(i, f)).join('')}
        <td><button class="btn btn--ghost btn--sm btn--icon" data-action="pp-xl-rm" data-i="${i}" aria-label="Remove ${esc(r.name)}" ${dirty ? 'disabled title="Save or discard the changes first"' : ''}>${icon('trash')}</button></td></tr>`).join('');
    return `<div style="margin-top:var(--space-4)"><h4 id="h-xl">External links</h4>
      <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">Links that leave the substation, to the control centre, a PCC or a third party. Each takes a port and an SFP of its speed and media on the L2 or external switch, on each side it is on.</p>
      ${rows.length ? `<div class="table-wrap"><table class="table ied-table xl-table" aria-labelledby="h-xl"><thead><tr><th>Name</th><th class="num">Links</th><th>Speed</th><th>Media</th><th>Lands on</th><th>Firewall</th><th>Sides</th><th class="num">Cable m</th><th><span class="sr-only">Remove</span></th></tr></thead><tbody>${body}</tbody></table></div>`
        : '<p class="muted small">No external links. Devices in the cabinets keep their own link to the L2 switch on their row.</p>'}
      <div class="row" style="margin-top:var(--space-3)"><button class="btn btn--secondary btn--sm" data-action="pp-xl-add" ${dirty ? 'disabled title="Save or discard the changes first"' : ''}>${icon('plus')}Add a link</button></div></div>`;
  }
  const IED_LABEL = { bay: 'Bay', name: 'IED', qty: 'Quantity', ports: 'Ports per side', attachment: 'Attached to', lands_on: 'Lands on', notes: 'Notes' };
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
    const schedule = !fresh && (UI.iedMode || (p.parts.ieds.length ? 'schedule' : 'count')) === 'schedule';
    const unset = !schedule && !shown('n.ied_count');
    const gen = fresh ? '' : PF.dirty() ? `<button class="btn btn--secondary" disabled title="Save your changes first." aria-describedby="pp-gen-why">${icon('elevation')}Generate preview</button><span id="pp-gen-why" class="sr-only">Save your changes first.</span>` : `<a class="btn btn--secondary" href="#/device-preview">${icon('elevation')}Generate preview</a>`;
    return `<div class="page">${pageHead('Parts', 'Pick a library part for each device. The panels, MCBs, power and heat follow from these picks.', gen)}
      ${sub().problems(p)}${fresh ? setupCard(p, rows) : ''}
      <div class="net-grid">
        <div class="stack" style="gap:var(--space-6)">
          <section aria-labelledby="h-fn"><h3 id="h-fn">Field network</h3>
            ${fresh ? '' : iedMode(p, schedule)}
            <div class="form form--2" style="margin-top:var(--space-3)">
              ${schedule ? field('Field IEDs', `<p class="small" style="margin:6px 0 0">${plural(p.parts.ieds.reduce((n, r) => n + r.qty, 0), 'IED')} in the schedule below.</p>`, 'Counted from the schedule. Never listed in the BOM.') : mark('n.ied_count', field('Field IEDs', `<div class="input-affix">${input('p-n.ied_count', shown('n.ied_count'), { num: true, mono: true, invalid: !!PF.errors['n.ied_count'] || unset, placeholder: unset ? 'Required' : '' })}<span class="affix">IEDs</span></div>`, 'Never listed in the BOM. Only used to size the L1 switches. Every IED port of an L1 switch counts.', PF.errors['n.ied_count'] ? PF.err('n.ied_count') : unset ? 'Enter the number of field IEDs, for example 40.' : ''))}
              ${mark('n.topology', field('Topology', select('p-n.topology', [['star', 'Star'], ['ring', 'Ring']], topo), topo === 'ring' ? 'L1 switches are joined in rings. Two ports close each ring.' : 'Each L1 switch has one uplink to its L2 switch plus an A–B interlink.'))}
            </div>
            ${schedule ? iedTable(p) : ''}
            ${fresh ? '' : linksTable(p)}
            ${tuning(p)}</section>
          <section aria-labelledby="h-dev"><h3 id="h-dev">Devices</h3>
            <p class="muted small" style="margin:var(--space-1) 0 var(--space-3)">The layout fills the panels in this order. The part number is printed on the BOM; leave it empty to print the library's code. Click a value under a part to change it for this design only.</p>
            <div class="prow-head" aria-hidden="true"><span>Library part</span><span>${fresh ? '' : 'Part number on the BOM'}</span><span class="num">${fresh ? '' : 'Qty'}</span></div>
            <div class="prows">${fresh ? rows.map((d, j) => freshRow(p, d, j)).join('') : rows.map((r, i) => partRow(p, r, i === rows.length - 1)).join('')}</div>
            ${fresh ? `<div class="row" style="margin-top:var(--space-3)"><button class="btn btn--primary" data-action="pp-start" ${rows.some((d) => d.role === 'l2_switch' && d.part_id) ? '' : 'disabled aria-describedby="pp-start-why"'}>${icon('save')}Save the parts</button>${rows.some((d) => d.role === 'l2_switch' && d.part_id) ? '' : '<span id="pp-start-why" class="muted small">Pick the L2 switch first: the network is sized from it.</span>'}</div>` : addDevice(p)}
          </section>
          ${brands(p)}
        </div>
        <aside class="net-result" aria-live="polite">${App.network.resultCard({ count: switchCount, held: heldCounts })}</aside>
      </div>${PF.bar()}</div>`;
  };
  /* M72: a switch count per side as a derived value; empty is the sizing's count. */
  function switchCount(key, label, d) {
    const v = shown(key), id = `p-${key}`, auto = String(d.value);
    if (UI.editing === key) return App.derived(key, { editing: true, id, label, rule: d.rule, control: input(id, v === '' ? auto : v, { mono: true, num: true, invalid: !!PF.errors[key] }).replace('class="input', 'class="dv-input input').replace('<input ', `<input data-dv="${key}" aria-label="${label} on each side" `) });
    return App.derived(key, { label, shown: v === '' ? auto : v, auto, overridden: v !== '', changed: key in PF.draft, bad: !!PF.errors[key], rule: d.rule, edit: 'pp-edit', reset: 'pp-reset' });
  }
  /* The saved counts the sizing refuses, each with its way back to the automatic count. */
  function heldCounts() {
    const set = [['n.l1_per_side', 'L1'], ['n.l2_per_side', 'L2']].filter(([k]) => shown(k) !== '');
    return set.length ? `<div class="row" style="margin-top:var(--space-2);gap:var(--space-2)">${set.map(([k, l]) => `<button class="btn btn--secondary btn--sm" data-action="pp-reset" data-key="${k}">${icon('undo')}Use the automatic ${l} count</button>`).join('')}</div>` : '';
  }
  function addDevice(p) {
    const dirty = PF.dirty();
    return `<div class="popwrap prow-add"><button class="btn btn--secondary btn--sm" data-action="pp-add" aria-haspopup="menu" aria-expanded="${UI.addOpen}" ${dirty ? 'disabled title="Save or discard the changes first"' : ''}>${icon('plus')}Add a device</button>
      ${UI.addOpen ? `<div class="menu" role="menu" style="left:0;top:34px">${p.parts.add_categories.map((c) => { const n = c.choices.length; return `<button role="menuitem" data-action="pp-add-cat" data-c="${c.category}" ${n ? '' : `disabled title="The library has no ${esc(c.label)} parts yet."`}>${esc(c.label)}${n ? '' : `<span class="muted small">The library has no ${esc(c.label)} parts yet.</span>`}</button>`; }).join('')}</div>` : ''}</div>`;
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
  ACTIONS['pp-bomtext'] = (el) => keep(() => { const i = +el.dataset.i; if (UI.bomText.has(i)) UI.bomText.delete(i); else UI.bomText.add(i); });
  ACTIONS['pp-tuning'] = () => keep(() => { const p = sub().page(); UI.tuning = !(UI.tuning == null ? !p.equipment.length : UI.tuning); });
  ACTIONS['pp-edit'] = (el) => { keep(() => { UI.editing = el.dataset.key; }); const c = document.getElementById('p-' + el.dataset.key); if (c) { c.focus(); if (c.select) c.select(); } };
  const resetTo = (key) => {
    const [kind, i, f] = key.split('.');
    PF.set(key, kind === 'f' ? (key.endsWith('.extra') ? '0' : '') : kind === 'n' ? '' : libValue(rowAt(Number(i)), f)); S.dirty = PF.dirty();  /* f: an SFP total (M87) or extra (M49); n: a switch count (M72) */
  };
  ACTIONS['pp-expand'] = (el) => { const i = +el.dataset.i; keep(() => UI.expanded.add(i)); const b = document.querySelector(`[data-action="pp-edit"][data-key^="o.${i}."]`); if (b) b.focus(); };
  ACTIONS['pp-reset'] = (el) => keep(() => resetTo(el.dataset.key));
  /* M69: a saved override that corrects the library goes there as a pending edit, with where it comes from. */
  const savedOverrides = (r) => Object.keys(r.overrides || {});
  const $ = App.$, plain = (html) => html.replace(' data-dirty="1"', '');  // the dialog's controls are not the page's
  function proposeButton(r) {
    if (!savedOverrides(r).length) return '';
    const dirty = Object.keys(PF.draft).some((k) => k.startsWith(`o.${r.index}.`));
    return `<button class="btn btn--ghost btn--sm" data-action="pp-propose" data-i="${r.index}" ${dirty ? 'disabled title="Save the overrides first"' : ''}>Propose for the library…</button>`;
  }
  ACTIONS['pp-propose'] = (el) => {
    const r = rowAt(+el.dataset.i), fields = savedOverrides(r).map((f) => [f, `${VALUES.find((v) => v[0] === f)[1]}: ${FMT[f](String(r.overrides[f]))}`]);
    App.dialog({ title: `Propose ${esc(r.part_id)}'s value for the library`, body: `<div class="form">
        ${field('Value', plain(select('pp-prop-field', fields, fields[0][0])), `Every project on the library uses ${esc(r.part_id)}; once the library change is applied, they all get this value.`)}
        ${field('Where it comes from', plain(select('pp-prop-kind', [['measured', 'Measured'], ['datasheet', 'Datasheet']], 'measured')), '')}
        ${field('Reference', plain(input('pp-prop-ref', '', { placeholder: 'for example bench test 2026-11-03, or datasheet p. 4' })), 'Kept with the value, so a reviewer can check it.')}
        <label class="check"><input type="checkbox" id="pp-prop-keep"> Keep the part released</label><p class="muted small">Otherwise it goes back to draft and waits in Library › Review.</p>
        <p class="err small" id="pp-prop-err" hidden></p></div>`,
    actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="pp-propose-do" data-i="${r.index}">Add to pending changes</button>` });
  };
  ACTIONS['pp-propose-do'] = (el) => {
    const ref = $('#pp-prop-ref').value.trim(), bad = $('#pp-prop-err');
    const say = (text) => { bad.textContent = text; bad.hidden = false; };
    if (!ref) { say('Give a reference: the test, the datasheet page, or the document.'); $('#pp-prop-ref').setAttribute('aria-invalid', 'true'); $('#pp-prop-ref').focus(); return; }
    const r = rowAt(+el.dataset.i);
    Bridge.call('propose_library_edit', S.project.file, S.sub, r.index, $('#pp-prop-field').value, $('#pp-prop-kind').value, ref, $('#pp-prop-keep').checked)
      .then((pending) => { App.closeDialog(); if (App.setPending) App.setPending(pending); if (App.healthStale) App.healthStale(); toast(`Proposed for ${r.part_id}, pending in the library`, 'check'); })
      .catch((e) => say(e.message.replace(/^The library cannot take this change: /, '')));
  };
  ACTIONS['pp-reset-all'] = (el) => keep(() => VALUES.forEach(([f]) => { const key = `o.${el.dataset.i}.${f}`, r = rowAt(Number(el.dataset.i)); if (r.library && shown(key) !== libValue(r, f)) resetTo(key); }));
  ACTIONS['pp-menu'] = (el) => keep(() => { UI.menu = UI.menu === +el.dataset.i ? -1 : +el.dataset.i; UI.addOpen = false; });
  ACTIONS['pp-move'] = (el) => {
    const i = +el.dataset.i, to = i + +el.dataset.d; UI.menu = -1;
    Bridge.call('move_equipment', S.project.file, S.sub, i, to).then((page) => {
      reloaded(page);
      toast(`Moved ${page.parts.rows[to].label} ${to < i ? 'up' : 'down'}`, 'check', () => Bridge.call('move_equipment', S.project.file, S.sub, to, i).then(reloaded).catch(fail));
    }).catch(fail);
  };
  /* M86: pin the switch the sizing picked, through the part writer, so its SFP rows can be edited. */
  ACTIONS['pp-pin'] = (el) => {
    const r = rowAt(+el.dataset.i), name = nameOf(r.pin);
    el.disabled = true;
    Bridge.call('set_equipment_part', S.project.file, S.sub, r.index, r.pin.part_id)
      .then((d) => { reloaded(d.page); toast(`Pinned ${name} to the ${r.label} row. Its SFPs can be changed now.`, 'check'); })
      .catch((e) => { el.disabled = false; fail(e); });
  };
  ACTIONS['pp-remove'] = (el) => {
    const i = +el.dataset.i, file = S.project.file, sid = S.sub, label = rowAt(i).label; UI.menu = -1;
    Bridge.call('remove_equipment', file, sid, i).then((r) => {
      sub().reload(); App.network.reload(); App.devicePreview.reload(); App.render();
      toast(`Removed ${label}`, 'trash', () => Bridge.call('add_equipment', file, sid, r.row, i).then(() => { sub().reload(); App.render(); }).catch(fail));
    }).catch(fail);
  };
  ACTIONS['pp-ied-mode'] = (el) => keep(() => { UI.iedMode = el.dataset.m; });
  ACTIONS['pp-ied-add'] = () => {
    const rows = sub().page().parts.ieds, last = rows[rows.length - 1];
    Bridge.call('add_ied_row', S.project.file, S.sub, { bay: last ? last.bay : 'E01', name: 'IED' }, null).then((page) => {
      UI.iedMode = 'schedule'; reloaded(page);
      const el = document.getElementById(`p-i.${rows.length}.name`); if (el) { el.focus(); el.select(); }
    }).catch(fail);
  };
  ACTIONS['pp-ied-rm'] = (el) => {
    const i = +el.dataset.i, file = S.project.file, sid = S.sub, r = sub().page().parts.ieds[i];
    Bridge.call('remove_ied_row', file, sid, i).then((d) => {
      reloaded(d.page);
      toast(`Removed ${r.bay} ${r.name}`, 'trash', () => Bridge.call('add_ied_row', file, sid, d.row, i).then(reloaded).catch(fail));
    }).catch(fail);
  };
  ACTIONS['pp-xl-add'] = () => {
    const n = sub().page().parts.links.length;
    Bridge.call('add_external_link', S.project.file, S.sub, { name: n ? `Link ${n + 1}` : 'Control centre' }, null).then((page) => {
      reloaded(page); const el = document.getElementById(`p-x.${n}.name`); if (el) { el.focus(); el.select(); }
    }).catch(fail);
  };
  ACTIONS['pp-xl-rm'] = (el) => {
    const i = +el.dataset.i, file = S.project.file, sid = S.sub, r = sub().page().parts.links[i];
    Bridge.call('remove_external_link', file, sid, i).then((d) => {
      reloaded(d.page);
      toast(`Removed ${r.name}`, 'trash', () => Bridge.call('add_external_link', file, sid, d.row, i).then(reloaded).catch(fail));
    }).catch(fail);
  };
  ACTIONS['pp-ied-csv'] = () => Bridge.call('choose_file', 'csv').then((path) => {
    if (!path) return;
    return Bridge.call('import_ied_csv', S.project.file, S.sub, path, true).then((d) => {
      const probs = d.problems.length ? `<p class="small" style="margin-top:var(--space-3)">${plural(d.problems.length, 'row')} with a problem ${d.problems.length === 1 ? 'is' : 'are'} skipped:</p><ul class="small" style="margin:4px 0 0;padding-left:18px">${d.problems.slice(0, 8).map((x) => `<li>Row ${x.row}${x.column ? `, <span class="mono">${esc(x.column)}</span>` : ''}: ${esc(x.message)}</li>`).join('')}</ul>` : '';
      const refused = d.refused.length ? banner('bad', `<b>The schedule cannot be saved.</b> ${esc(d.refused.join('; '))}`) : '';
      const list = d.rows.length ? `<div class="table-wrap" style="margin-top:var(--space-3);max-height:240px"><table class="table table--plain"><thead><tr><th>Bay</th><th>IED</th><th class="num">Qty</th><th>Ports per side</th><th>Attached to</th><th>Lands on</th></tr></thead><tbody>${d.rows.map((r) => `<tr><td>${esc(r.bay)}</td><td>${esc(r.name)}</td><td class="num">${r.qty}</td><td class="mono">${esc(r.ports_text)}</td><td>${esc((ATTACH.find((a) => a[0] === r.attachment) || [, r.attachment])[1])}</td><td>${r.lands_on.toUpperCase()}</td></tr>`).join('')}</tbody></table></div>` : '';
      App.dialog({ title: `Import ${esc(d.file)}`, body: `${refused}<p>${plural(d.rows.length, 'IED row')} to import.${d.replaces ? ` ${d.replaces === 1 ? 'It replaces the row' : `They replace the ${d.replaces} rows`} of the schedule.` : ' They replace the IED count.'}</p>${list}${probs}`,
        actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="pp-ied-import" data-path="${esc(path)}" ${d.can_import ? '' : 'disabled'}>Import ${plural(d.rows.length, 'row')}</button>` });
    });
  }).catch(fail);
  ACTIONS['pp-ied-import'] = (el) => {
    el.disabled = true;
    Bridge.call('import_ied_csv', S.project.file, S.sub, el.dataset.path, false).then((page) => {
      App.closeDialog(); UI.iedMode = 'schedule'; reloaded(page); toast(`Imported ${plural(page.parts.ieds.length, 'IED row')}`, 'check');
    }).catch((e) => { el.disabled = false; fail(e); });
  };
  ACTIONS['pp-add'] = () => keep(() => { UI.addOpen = !UI.addOpen; UI.menu = -1; });
  /* Add a device: the model takes no row without a part, so the part is picked first. The API gives each
     category the role of the row it makes and the parts that row offers (a Switch makes an EXT switch). */
  const aName = (label) => {  // "an RTAC", "a KVM", "an I/O rack", "a fibre patch panel"
    const s = label.split(' ').map((w) => (/^[A-Z/]{2,}$/.test(w) ? w : w.toLowerCase())).join(' ');
    return `${/^[aeiou]/.test(s) || /^[AEFHILMNORSX][A-Z/]/.test(s) ? 'an' : 'a'} ${s}`;
  };
  const freeId = (base, taken) => { let id = base, n = 2; while (taken.includes(id)) id = `${base}-${n++}`; return id; };
  ACTIONS['pp-add-cat'] = (el) => {
    const p = sub().page(), c = p.parts.add_categories.find((x) => x.category === el.dataset.c), opts = c.choices;
    UI.addOpen = false;
    App.dialog({ title: `Add ${esc(aName(c.label))}`, body: `<div class="form">
      ${field('Part', `<select class="select" id="pa-part">${opts.map((o) => `<option value="${esc(o.part_id)}">${esc(partText(o))}</option>`).join('')}</select>`, 'From the active library.')}
      <label class="check"><input type="checkbox" id="pa-red">A and B units (redundant)</label>
      <div id="pa-err" class="err small" role="alert"></div></div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="pp-add-do" data-c="${c.category}">Add</button>` });
  };
  ACTIONS['pp-add-do'] = (el) => {
    const p = sub().page(), v = (id) => document.getElementById(id), part = v('pa-part').value;
    const base = part.toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^[^a-z0-9]+|-+$/g, '') || 'device';
    const row = { id: freeId(base, p.equipment.map((e) => e.id)), part_id: part, role: p.parts.add_categories.find((x) => x.category === el.dataset.c).role };
    if (v('pa-red').checked) row.redundant = true;
    Bridge.call('add_equipment', S.project.file, S.sub, row, null, true).then(() => { App.closeDialog(); sub().reload(); App.network.reload(); App.devicePreview.reload(); App.render(); toast(`Added ${row.id}`, 'check'); })
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
    Bridge.call('start_parts', S.project.file, S.sub, rows).then((page) => {
      UI.fresh = null; reloaded(page); toast(`Saved ${plural(rows.length, 'device row')}`, 'check');
      return PF.save();  // the IED count and the other network inputs typed on the set-up card
    }).catch(fail);
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
  document.addEventListener('change', (e) => { if (e.target.closest && e.target.closest('[data-dv]')) UI.editing = ''; }, true);  // before the form's render
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
