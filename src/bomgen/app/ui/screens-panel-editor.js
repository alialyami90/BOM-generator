/* Screen: the panel editor on bomgen.app.api (plan M32a; docs/ui/screens.md "Panel editor").
   panel_page gives one panel. A generated panel's enclosure, document, options and the port plans
   of its devices live in substation.yaml, so the form tabs draft and save there through the shared
   save bar (draftForm); adding or removing a port allocation writes at once. Devices and YAML are
   read-only: Parts and Device preview place the devices. Hand-written panels are edited in M32b. */
(function () {
  const { esc, S, ACTIONS, badge, banner, tabs, field, input, select, pageHead, toast } = App;
  const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;
  const str = (v) => (v == null ? '' : String(v));

  /* ---------- data: one page per (project file, substation id, panel id) ---------- */
  const PE = { key: '', state: 'idle', page: null, error: null, dv: '' };
  function load(id) {
    const key = `${S.project.file}#${S.sub}#${id}`;
    if (PE.key !== key) Object.assign(PE, { key, state: 'idle', page: null, error: null });
    if (PE.state === 'idle') {
      PE.state = 'loading';
      const current = () => PE.key === key;
      Bridge.call('panel_page', S.project.file, S.sub, id)
        .then((p) => { if (current()) PE.page = p; }).catch((err) => { if (current()) PE.error = err; })
        .then(() => { if (current()) { PE.state = 'loaded'; App.render(); } });
    }
    return PE.state === 'loaded' ? PE : null;
  }
  const reload = () => { PE.state = 'idle'; };
  App.onDiskChange(reload);
  /* A write changes the board, Device preview and Parts too. */
  const changed = () => { reload(); App.network.reload(); App.devicePreview.reload(); App.sub.reload(); };

  /* ---------- the form: keys e.<enclosure field>, doc, o.<all|panel>.<option>, p.<row>.… ---------- */
  const ENC = { make: 'text', model: 'text', ordering_code: 'text', h_mm: 'int', d_mm: 'int', w_mm: 'int', cable_entry: 'choice', ip_rating: 'text', colour: 'text', 'base_frame.h_mm': 'int', 'base_frame.d_mm': 'int', 'base_frame.w_mm': 'int' };
  const OPT = { dc_spare_branches_per_feed: 'int', ac_spare_branches: 'int', ventilation: 'choice', change_over_diodes: 'choice', main_mcb_override_a: 'int', ac_spare_rating_a: 'int', dc_spare_rating_a: 'int', aux_socket_a: 'int', inter_panel_terminals: 'int', smoke_detector: 'choice' };
  const PORT = { count: 'int', speed: 'choice', media: 'choice', spare: 'int' };
  const TERM = { t: 'terminal_overrides', tb: 'terminal_block_overrides' };  // t.<all|panel>.<strip>, tb.… (ADR 0033)
  /* hk.<all|panel>.<field>[.<load>]: the housekeeping kit (ADR 0032); a panel's own kit replaces the shared one. */
  const HK = { lamps: 'int', fans: 'int', thermostats_forced: 'int', thermostats_natural: 'int', filters: 'int', heater: 'choice', hygrostat: 'choice', branch_ratings: 'int' };
  const dig = (o, path) => path.reduce((x, k) => (x == null ? x : x[k]), o);
  function spec(key) {  // [path in substation.yaml, kind]
    const [k, a, ...r] = key.split('.');
    if (k === 'e') { const f = [a, ...r].join('.'); return ENC[f] ? [['generated_panels', 'enclosure', ...f.split('.')], ENC[f]] : null; }
    if (k === 'eo') { const f = r.join('.'); return ENC[f] ? [['generated_panels', 'enclosure_by_panel', Number(a), ...r], ENC[f]] : null; }  // plan M50
    if (k === 'kind') return [a === 'all' ? ['generated_panels', 'kind'] : ['generated_panels', 'kind_by_panel', Number(a)], 'choice'];
    if (k === 'doc') return [['generated_panels', 'document'], 'choice'];
    if (k === 'nt') return [['generated_panels', 'notes_by_panel', Number(a)], 'text'];  // plan M70
    if (k === 'mi') return [a === 'all' ? ['generated_panels', 'options', 'misc_items'] : ['generated_panels', 'options_by_panel', Number(a), 'misc_items'], 'lines'];
    if (k === 'g') return [['generated_panels', a], 'text'];  // a numbering pattern every generated panel shares
    if (k === 'o') return OPT[r[0]] ? [a === 'all' ? ['generated_panels', 'options', r[0]] : ['generated_panels', 'options_by_panel', Number(a), r[0]], OPT[r[0]]] : null;
    if (k === 't' || k === 'tb') return [[...(a === 'all' ? ['generated_panels', 'options'] : ['generated_panels', 'options_by_panel', Number(a)]), TERM[k], r.join('.')], k === 't' ? 'int' : 'choice'];  // ADR 0033
    if (k === 'hk') return [[...(a === 'all' ? ['generated_panels', 'options'] : ['generated_panels', 'options_by_panel', Number(a)]), 'housekeeping', ...r], HK[r[0]]];  // ADR 0032
    if (k === 'p' && r[0] === 'serial_ports') return [['equipment', Number(a), 'port_plan', 'serial_ports'], 'int'];
    if (k === 'p' && PORT[r[2]]) return [['equipment', Number(a), 'port_plan', r[0], Number(r[1]), r[2]], PORT[r[2]]];
    return null;
  }
  function saved(key) {
    const p = PE.page; if (!p || !p.panel) return '';
    const [k, a, ...r] = key.split('.');
    if (k === 'e') return str([a, ...r].reduce((o, x) => (o == null ? o : o[x]), p.shared ? p.shared.enclosure : p.enclosure));
    if (k === 'eo') return p.shared && p.shared.own_enclosure ? str(r.reduce((o, x) => (o == null ? o : o[x]), p.enclosure)) : '';
    if (k === 'kind') return a === 'all' ? str(p.shared && p.shared.kind) : p.shared && p.shared.own_kind ? p.panel.kind : '';
    if (k === 'doc') return p.document;
    if (k === 'nt') return str(p.panel.notes);
    if (k === 'mi') { const o = p.options.find((x) => x.key === 'misc_items'); return (a === 'all' ? o.shared : o.own && Number(a) === p.panel.number ? o.value : []).join('\n'); }
    if (k === 'g') return p.template ? str(p.template[a]) : '';
    if (k === 'o') {
      const o = p.options.find((x) => x.key === r[0]); if (!o) return '';
      return a === 'all' ? str(o.shared) : o.own && Number(a) === p.panel.number ? str(o.value) : '';
    }
    if (k === 'hk') {
      const o = p.options.find((x) => x.key === 'housekeeping');
      return a === 'all' ? str(dig(o.shared, r)) : o.own && Number(a) === p.panel.number ? str(dig(o.value, r)) : '';
    }
    if (k === 't' || k === 'tb') {
      const o = p.options.find((x) => x.key === TERM[k]), code = r.join('.');
      return a === 'all' ? str(o.shared[code]) : o.own && Number(a) === p.panel.number ? str(o.value[code]) : '';
    }
    if (k === 'p') {
      const row = p.ports.find((x) => x.equipment === Number(a)), own = row && row.own;
      if (!own) return '';
      if (r[0] === 'serial_ports') return str(own.serial_ports);
      const al = (own[r[0]] || [])[Number(r[1])];
      return al ? str(al[r[2]]) : '';
    }
    return '';
  }
  /* change_over_diodes is auto, true or false; the select gives text. */
  const typed = (path, value) => (['change_over_diodes', 'alarm_on_branch_mcb', 'heater', 'hygrostat'].includes(path[path.length - 1]) && (value === 'true' || value === 'false') ? value === 'true' : value);
  const PD = App.draftForm({
    prefix: 'pe-', screen: 'panels', file: 'substation.yaml', label: 'Save the panel', spec, saved,
    check: (path, value) => Bridge.call('check_substation_field', S.project.file, S.sub, path, typed(path, value)),
    write: (path, value) => Bridge.call('set_substation_field', S.project.file, S.sub, path, typed(path, value)),
    done: changed
  });

  /* A hand-written panel's own file (M32b): keys c.<identity field>, e.…, doc, o.<option>, d.<row>.<field>. */
  const CAB = { cabinet_name: 'text', cabinet_number: 'text', tag_prefix: 'text', sheet_name: 'text', kind: 'choice', lan: 'choice' };
  const DEV = { qty: 'int', purpose: 'text', hwio_points: 'int', alarm_on_branch_mcb: 'choice', tag: 'text', tag_type: 'text', first_nn: 'int', note: 'text' };
  function hSpec(key) {
    const [k, a, ...r] = key.split('.');
    if (k === 'c') return CAB[a] ? [[a], CAB[a]] : null;
    if (k === 'e') { const f = [a, ...r].join('.'); return ENC[f] ? [['enclosure', ...f.split('.')], ENC[f]] : null; }
    if (k === 'doc') return [['document'], 'choice'];
    if (k === 'nt') return [['notes'], 'text'];  // plan M70
    if (k === 'mi') return [['options', 'misc_items'], 'lines'];
    if (k === 'o') return OPT[a] ? [['options', a], OPT[a]] : null;
    if (k === 'd') return DEV[r[0]] ? [['devices', Number(a), r[0]], DEV[r[0]]] : null;
    if (k === 't' || k === 'tb') return [['options', TERM[k], [a, ...r].join('.')], k === 't' ? 'int' : 'choice'];
    if (k === 'hk') return HK[a] ? [['options', 'housekeeping', a, ...r], HK[a]] : null;
    return null;
  }
  function hSaved(key) {
    const p = PE.page; if (!p || !p.panel) return '';
    const [k, a, ...r] = key.split('.');
    if (k === 'c') return str(p.panel[a === 'sheet_name' ? 'sheet' : a]);
    if (k === 'e') return str([a, ...r].reduce((o, x) => (o == null ? o : o[x]), p.enclosure));
    if (k === 'doc') return p.document;
    if (k === 'nt') return str(p.panel.notes);
    if (k === 'mi') { const o = p.options.find((x) => x.key === 'misc_items'); return o.own ? o.value.join('\n') : ''; }
    if (k === 'o') { const o = p.options.find((x) => x.key === a); return o && o.own ? str(o.value) : ''; }
    if (k === 'd') { const d = p.devices[Number(a)]; return d ? str(d[r[0]]) : ''; }
    if (k === 't' || k === 'tb') { const o = p.options.find((x) => x.key === TERM[k]); return o && o.own ? str(o.value[[a, ...r].join('.')]) : ''; }
    if (k === 'hk') { const o = p.options.find((x) => x.key === 'housekeeping'); return o && o.own ? str(dig(o.value, [a, ...r])) : ''; }
    return '';
  }
  let hPanel = '';  // the hand-written panel the draft belongs to
  const HD = App.draftForm({
    prefix: 'ph-', screen: 'panels', file: 'the panel file', label: 'Save the panel', spec: hSpec, saved: hSaved,
    check: (path, value) => Bridge.call('check_panel_field', S.project.file, S.sub, hPanel, path, typed(path, value)),
    write: (path, value) => Bridge.call('set_panel_field', S.project.file, S.sub, hPanel, path, typed(path, value)),
    done: changed
  });
  App.sub.resets.push(() => { PD.reset(); HD.reset(); });
  /* The form of the panel on screen: the generated panels' (PD, pe-) or a hand-written one's (HD, ph-). */
  let F = PD, PFX = 'pe-';
  const err = (key) => F.err(key);
  const edit = (key, label, html, help) => F.mark(key, field(label, html, help, err(key)));
  const text = (key, o = {}) => input(PFX + key, str(F.shown(key)), { invalid: !!F.errors[key], ...o });
  const num = (key, unit, o = {}) => `<div class="input-affix">${text(key, { num: true, mono: true, ...o })}${unit ? `<span class="affix">${esc(unit)}</span>` : ''}</div>`;
  const area = (key, o = {}) => `<textarea class="input" id="${PFX}${key}" rows="${o.rows || 3}" style="height:auto;padding:8px 10px"${o.placeholder ? ` placeholder="${esc(o.placeholder)}"` : ''}${F.errors[key] ? ' aria-invalid="true"' : ''}>${esc(str(F.shown(key)))}</textarea>`;
  const choice = (key, opts) => select(PFX + key, opts, str(F.shown(key)), { invalid: !!F.errors[key] });
  /* A rating as a derived value (plan M48): the engine's rating and its rule; a typed rating overrides it.
     `inherited` is the shared override a panel-only key falls back to. The main MCB, and the spares (M58). */
  /* A value the engine derives and nobody overrides here (ADR 0040): the value and its rule, nothing to click. */
  const shownRule = (label, d, unit = '') => (!d ? '' : `<span class="dv"><span class="dv-label">${esc(label)}</span><span class="dv-val">${esc(String(d.value))}${unit}</span><span class="dv-rule">${esc(d.rule)}</span></span>`);
  /* Why an override weakens a check (ADR 0040): shown under a derived value typed below its automatic value, kept with Reason…. */
  const reasonLine = (p, subject, shown, auto) => {
    const below = Number(String(shown).replace(/[^\d.]/g, '')) < Number(String(auto).replace(/[^\d.]/g, ''));
    const reason = (p.override_reasons || {})[subject];
    if (!below && !reason) return '';
    return `<span class="dv-reason ${reason ? '' : 'is-missing'}">${reason ? `Reason: ${esc(reason)}` : 'Below the automatic value: give a reason'} <button class="btn btn--ghost btn--sm" data-action="pe-reason" data-subject="${esc(subject)}" ${F.dirty() ? 'disabled title="Save or discard the changes first"' : ''}>${reason ? 'Edit…' : 'Reason…'}</button></span>`;
  };
  ACTIONS['pe-reason'] = (el) => {
    const p = PE.page, subject = el.dataset.subject, reason = (p.override_reasons || {})[subject] || '';
    App.dialog({ title: 'Why this override?', body: `<div class="form"><p>${esc(p.panel.cabinet_name)} · ${esc(subject)}</p>${App.field('Reason', App.input('pe-or-reason', reason, { placeholder: 'For example, the client feeds this panel at 6 A' }).replace('data-dirty="1"', 'data-dirty="0"'), 'Saved beside the override and printed on the Revision History sheet of the next issue. Empty removes it.')}<div id="pe-or-err"></div></div>`,
      actions: `<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--primary" data-action="pe-reason-do" data-subject="${esc(subject)}">Save reason</button>` });
    setTimeout(() => { const n = document.getElementById('pe-or-reason'); if (n) n.focus(); }, 0);
  };
  ACTIONS['pe-reason-do'] = (el) => {
    const p = PE.page;
    Bridge.call('set_override_reason', S.project.file, S.sub, p.panel.id, el.dataset.subject, document.getElementById('pe-or-reason').value)
      .then(() => { App.closeDialog(); changed(); App.render(); toast('Reason saved'); })
      .catch((e) => { const n = document.getElementById('pe-or-err'); if (n) n.innerHTML = App.banner('bad', esc(e.message)); });
  };
  const DV = { main_mcb_override_a: ['main_mcb_a', 'Main MCB'], ac_spare_rating_a: ['ac_spare_a', 'AC spare rating'], dc_spare_rating_a: ['dc_spare_a', 'DC spare rating'] };
  function mainMcb(p, key, inherited, name = 'main_mcb_a') {
    const d = p.derived[name];
    if (PE.dv === key) return App.derived(key, { editing: true, id: PFX + key, label: 'Rating', rule: d.rule, control: num(key, 'A').replace('<input ', `<input data-pdv="${key}" `) });
    const eff = str(F.shown(key)) || str(inherited);
    return App.derived(key, { label: 'Rating', shown: `${eff || d.value} A`, auto: `${d.value} A`, overridden: !!eff, bad: !!F.errors[key], rule: d.rule, edit: 'pe-dv-edit', reset: 'pe-dv-reset' })
      + (eff ? reasonLine(p, SUBJECT[name], eff, d.value) : '');
  }
  const SUBJECT = { main_mcb_a: 'main_mcb', ac_spare_a: 'ac_spare', dc_spare_a: 'dc_spare' };
  ACTIONS['pe-dv-edit'] = (el) => { PE.dv = el.dataset.key; App.render(); const c = document.getElementById(PFX + el.dataset.key); if (c) { c.focus(); c.select(); } };
  ACTIONS['pe-dv-reset'] = (el) => { F.set(el.dataset.key, ''); S.dirty = true; App.render(); };
  /* Enter keeps the typed rating, Esc puts the shown one back; leaving the field keeps it as a change does. */
  document.addEventListener('keydown', (e) => {
    const c = e.target.closest && e.target.closest('[data-pdv]');
    if (!c || (e.key !== 'Enter' && e.key !== 'Escape')) return;
    e.preventDefault(); e.stopPropagation();
    const key = c.dataset.pdv;
    if (e.key === 'Escape') c.value = str(F.shown(key)); else F.apply(key, c.value);
    PE.dv = ''; c.blur(); App.render();
    const b = document.querySelector(`[data-action="pe-dv-edit"][data-key="${key}"]`); if (b) b.focus();
  }, true);
  document.addEventListener('change', (e) => { if (e.target.closest && e.target.closest('[data-pdv]')) PE.dv = ''; }, true);  // before the form's render
  document.addEventListener('focusout', (e) => {
    const c = e.target.closest && e.target.closest('[data-pdv]');
    if (c && PE.dv === c.dataset.pdv) setTimeout(() => { if (PE.dv === c.dataset.pdv) { PE.dv = ''; App.render(); } }, 0);
  });

  /* ---------- the page ---------- */
  const TABS = [['enclosure', 'Enclosure'], ['devices', 'Devices'], ['ports', 'Port plans'], ['options', 'Options'], ['terminals', 'Terminals'], ['document', 'Document'], ['yaml', 'YAML']];
  const KIND = { network: 'Network', control: 'Control', console: 'Console' };
  const TAB_OF = (key) => ({ c: 'enclosure', e: 'enclosure', eo: 'enclosure', kind: 'enclosure', g: 'enclosure', doc: 'document', nt: 'document', o: 'options', hk: 'options', mi: 'options', t: 'terminals', tb: 'terminals', p: 'ports', d: 'devices' })[key.split('.')[0]];
  function tabMark(tab) {
    const bad = Object.keys(F.errors).filter((k) => TAB_OF(k) === tab).length, n = Object.keys(F.draft).filter((k) => TAB_OF(k) === tab).length;
    if (bad) return ` <span class="dot dot--bad" aria-hidden="true"></span><span class="sr-only">(${bad} to fix)</span>`;
    return n ? ` <span class="dot dot--warn" aria-hidden="true"></span><span class="sr-only">(${n} unsaved)</span>` : '';
  }
  App.panelEditor = (id) => {
    const crumbs = (name) => `<a href="#/panels">Panels</a>${icon('chevr')}<span>${esc(name)}</span>`;
    const l = load(id);
    if (!l) return `<div class="page">${pageHead(esc(id), 'Reading the panel…', '', crumbs(id))}</div>`;
    if (!l.page) return `<div class="page">${pageHead(esc(id), '', '', crumbs(id))}${banner('bad', `<b>This panel cannot be opened.</b> ${esc(l.error ? l.error.message : '')}`, '<a class="btn btn--secondary btn--sm" href="#/panels">Back to the panels</a>')}</div>`;
    const p = l.page;
    if (!p.panel) return `<div class="page">${pageHead(esc(id), '', '', crumbs(id))}${banner('bad', `<b>The panel cannot be read.</b> ${esc(p.reason)}.`, App.fixButtons(p.problems))}</div>`;
    const h = p.panel, gen = h.generated, mirror = !!h.mirror_of;
    if (gen) { F = PD; PFX = 'pe-'; } else { F = HD; PFX = 'ph-'; if (!HD.dirty()) hPanel = h.id; }
    const rc = App.route().c; if (TABS.some(([k]) => k === rc)) S.tab.panel = rc;
    const t = TABS.some(([k]) => k === S.tab.panel) ? S.tab.panel : 'enclosure';
    const meta = `<span class="mono" style="font-size:13px">${esc(h.cabinet_number)}</span> · ${KIND[h.kind] || esc(h.kind)}${gen ? ` · Side ${esc(h.side)}, pair ${h.pair} (panels ${2 * h.pair - 1} and ${2 * h.pair})` : ` · hand-written${h.manual ? ' (manual)' : ''}`}`;
    const intro = gen
      ? banner('info', '<b>Written by the layout.</b> Its devices come from Parts and where you place them on Device preview or the board. Numbering, enclosure, port plans, options and the document are yours to set.',
        '<a class="btn btn--secondary btn--sm" href="#/parts">Open Parts</a><a class="btn btn--secondary btn--sm" href="#/device-preview">Open Device preview</a>')
      : mirror ? banner('info', `<b>Mirror of ${esc(h.mirror_of)}.</b> It takes its devices, enclosure and options from that panel, so they are shown here as they are. Change them on ${esc(h.mirror_of)}.`, `<a class="btn btn--secondary btn--sm" href="#/panels/${esc(h.mirror_of)}">Open ${esc(h.mirror_of)}</a>`)
      : banner('info', '<b>Hand-written panel.</b> The layout does not touch it. Everything on it is yours to set here.');
    const other = !gen && HD.dirty() && hPanel !== h.id ? `<div style="margin-bottom:var(--space-4)">${banner('warn', `<b>Unsaved changes on ${esc(hPanel)}.</b> Save or discard them before you change this panel.`, `<a class="btn btn--secondary btn--sm" href="#/panels/${esc(hPanel)}">Open ${esc(hPanel)}</a>`)}</div>` : '';
    const engine = p.engine_error ? `<div style="margin-bottom:var(--space-4)">${banner('warn', `<b>The engine stopped on this substation.</b> ${esc(p.engine_error)}`, '<a class="btn btn--secondary btn--sm" href="#/checks">Open checks</a>')}</div>` : '';
    const body = gen ? { enclosure, devices, ports, options, terminals, document: docTab, yaml }[t](p)
      : t === 'yaml' ? yaml(p) : mirror || other || t === 'ports' ? readOnly(p, t)
        : { enclosure: handEnclosure, devices: handDevices, options: handOptions, terminals, document: docTab }[t](p);
    const del = gen ? '' : `<button class="btn btn--danger" data-action="pe-delete">${icon('trash')}Delete panel…</button>`;
    return `<div class="page">${pageHead(esc(h.cabinet_name), meta, `<a class="btn btn--secondary" href="#/preview/${esc(h.id)}">${icon('preview')}Preview BOM</a>${del}`, crumbs(h.cabinet_name))}
      <div style="margin-bottom:var(--space-4)">${intro}</div>${other}${engine}
      ${tabs('panel', TABS.map(([k, x]) => [k, x, mirror ? '' : tabMark(k)]), t, 'Panel sections')}
      <div role="tabpanel" aria-labelledby="tab-panel-${t}" style="margin-top:var(--space-4)">${body}</div>${F.bar()}</div>`;
  };

  App.panelEditor.reload = reload;  // Parts and Project › Overview write the spare terminals (M57)

  /* ---------- Enclosure: shared by every generated panel, or this panel's own (plan M50) ---------- */
  const KINDS = [['network', 'Network cabinet'], ['control', 'Control'], ['console', 'Console']];
  function enclosure(p) {
    const own = S.encScope === 'own', n = p.panel.number, sh = p.shared, busy = PD.dirty() ? 'disabled title="Save or discard the changes first"' : '';
    const scope = `<div class="field" style="margin-bottom:var(--space-4)"><span class="label" id="pe-escope-l">Apply to</span><div class="segmented" role="radiogroup" aria-labelledby="pe-escope-l">
        <label><input type="radio" name="pe-escope" value="all" data-action="pe-escope" ${own ? '' : 'checked'}><span>All generated panels</span></label><label><input type="radio" name="pe-escope" value="own" data-action="pe-escope" ${own ? 'checked' : ''}><span>This panel only</span></label></div>
      <span class="help">${own ? `The kind and enclosure you set here are kept for ${esc(p.panel.cabinet_name)} only.` : 'The numbering, kind and enclosure apply to every generated panel that has none of its own.'}</span></div>`;
    const kindHelp = own ? (sh.own_kind ? badge('info', `Own value · shared ${KINDS.find(([k]) => k === sh.kind)[1]}`) : '') : sh.own_kind ? `<span class="muted small">This panel has its own kind.</span>` : '';
    const kind = `<div class="form form--3" style="margin-bottom:var(--space-5)">${edit(own ? `kind.${n}` : 'kind.all', 'Kind', choice(own ? `kind.${n}` : 'kind.all', own ? [['', `Shared: ${KINDS.find(([k]) => k === sh.kind)[1]}`], ...KINDS] : KINDS), kindHelp)}</div>`;
    if (!own) return `${scope}${numbering()}${kind}<h3 style="margin-bottom:var(--space-3)">Enclosure</h3>${sh.own_enclosure ? `<p class="muted small" style="margin:0 0 var(--space-3)">This panel has its own enclosure, so a change here does not reach it.</p>` : ''}${encFields('e')}`;
    const head = `<div style="display:flex;align-items:center;gap:var(--space-3);margin-bottom:var(--space-3)"><h3 style="margin:0">Enclosure</h3>`;
    if (!sh.own_enclosure) return `${scope}${kind}${head}</div><p class="muted" style="margin:0 0 var(--space-3)">This panel uses the shared enclosure, H${sh.enclosure.h_mm} × D${sh.enclosure.d_mm} × W${sh.enclosure.w_mm} mm.</p>
      <button class="btn btn--secondary btn--sm" data-action="pe-enc-own" ${busy}>Give this panel its own enclosure</button>`;
    return `${scope}${kind}${head}${badge('info', 'Own value')}<span class="sp"></span><button class="btn btn--ghost btn--sm" data-action="pe-enc-shared" ${busy}>Use the shared enclosure</button></div>${encFields(`eo.${n}`)}`;
  }
  ACTIONS['pe-escope'] = (el) => { S.encScope = el.value; App.render(); };
  /* Taking or dropping an own enclosure writes at once: a copy of the shared one, or none. */
  function writeEnclosure(call, said) {
    call.then((r) => {
      if (r && r.written === false) { toast(`Not changed. ${(r.issues[0] && r.issues[0].message) || 'The enclosure was refused.'}`, 'error'); return; }
      changed(); toast(said); App.render();
    }).catch((e) => toast(`Not changed. ${e.message}`, 'error'));
  }
  ACTIONS['pe-enc-own'] = () => { const p = PE.page; writeEnclosure(Bridge.call('set_enclosure', S.project.file, S.sub, p.shared.enclosure, p.panel.number), `${p.panel.cabinet_name} has its own enclosure`); };
  ACTIONS['pe-enc-shared'] = () => { const p = PE.page; writeEnclosure(Bridge.call('set_substation_field', S.project.file, S.sub, ['generated_panels', 'enclosure_by_panel', p.panel.number], null), `${p.panel.cabinet_name} uses the shared enclosure`); };
  /* ALI-5, ALI-13: the generated panels' numbering, written as patterns where {n} is the panel number. */
  const numbering = () => `<section class="section" style="margin:0 0 var(--space-5)"><h3>Numbering</h3>
    <p class="muted small" style="margin:2px 0 var(--space-3)">{n} is the panel number; {n:04d} pads it to four digits. This panel reads ${esc(PE.page.panel.cabinet_number)}.</p>
    <div class="form form--2">${edit('g.cabinet_name', 'Cabinet name', text('g.cabinet_name', { mono: true }), 'Printed in the sheet header.')}${edit('g.cabinet_number', 'Cabinet number', text('g.cabinet_number', { mono: true }))}
    ${edit('g.tag_prefix', 'Tag prefix', text('g.tag_prefix', { mono: true }), 'Starts every tag in the panel.')}${edit('g.sheet_name', 'Sheet name', text('g.sheet_name', { mono: true }), 'The workbook tab.')}</div></section>`;
  const encFields = (e = 'e') => `<div class="form form--3">
    ${edit(`${e}.make`, 'Make', text(`${e}.make`))}${edit(`${e}.model`, 'Model', text(`${e}.model`))}${edit(`${e}.ordering_code`, 'Ordering code', text(`${e}.ordering_code`, { mono: true, placeholder: 'Optional' }))}
    ${edit(`${e}.h_mm`, 'Height', num(`${e}.h_mm`, 'mm'))}${edit(`${e}.d_mm`, 'Depth', num(`${e}.d_mm`, 'mm'))}${edit(`${e}.w_mm`, 'Width', num(`${e}.w_mm`, 'mm'))}
    ${edit(`${e}.base_frame.h_mm`, 'Base frame height', num(`${e}.base_frame.h_mm`, 'mm'))}${edit(`${e}.base_frame.d_mm`, 'Base frame depth', num(`${e}.base_frame.d_mm`, 'mm'))}${edit(`${e}.base_frame.w_mm`, 'Base frame width', num(`${e}.base_frame.w_mm`, 'mm'))}
    ${edit(`${e}.cable_entry`, 'Cable entry', choice(`${e}.cable_entry`, [['top', 'Top'], ['side', 'Side'], ['bottom', 'Bottom']]))}
    ${edit(`${e}.ip_rating`, 'IP rating', text(`${e}.ip_rating`, { mono: true, placeholder: 'e.g. IP54' }), 'Printed on the PANEL row when given.')}${edit(`${e}.colour`, 'Colour', text(`${e}.colour`, { placeholder: 'e.g. RAL 7035' }), 'Printed on the PANEL row when given.')}</div>`;

  /* ---------- Devices: what the layout placed, read-only ---------- */
  const ROLES = { fopp: 'Fibre patch panel', l2_switch: 'L2 switch', l1_switch: 'L1 switch', ext_switch: 'External switch', firewall: 'Firewall' };
  const devName = (d) => ROLES[d.role] || d.label;
  function devices(p) {
    return `<div class="toolbar"><span class="muted small">Add or remove devices on Parts. Move or pin them on Device preview or the board.</span><span class="sp"></span><a class="btn btn--secondary btn--sm" href="#/parts">${icon('parts')}Open Parts</a></div>
      <div class="table-wrap"><table class="table"><thead><tr><th>Device</th><th>Part</th><th class="num" style="width:80px">Height</th><th style="width:90px">Side</th><th style="width:110px">Origin</th><th style="width:190px"><span class="sr-only">Action</span></th></tr></thead>
      <tbody>${p.devices.map((d, i) => `<tr><td>${esc(devName(d))}${d.label !== devName(d) ? `<span class="cell-sub">${esc(d.label)}</span>` : ''}</td><td class="mono">${esc(d.part_id)}</td><td class="num">${d.height_u ? d.height_u + ' U' : 'DIN rail'}</td><td>${d.side ? 'Side ' + esc(d.side) : 'Common'}</td>
        <td>${d.origin === 'pinned' ? badge('info', 'Pinned', 'pin') : '<span class="muted small">Layout</span>'}</td>
        <td><button class="btn btn--ghost btn--sm" data-action="pe-show" data-i="${i}">${icon('elevation')}Show on Device preview</button></td></tr>`).join('')}</tbody></table>
      <div class="table-foot"><span>${plural(p.devices.length, 'unit')} in this panel</span></div></div>`;
  }
  ACTIONS['pe-show'] = (el) => {
    const p = PE.page, d = p.devices[+el.dataset.i];
    const id = `${p.panel.number}:${d.device}#${d.n}:${(d.side || '').toLowerCase()}`;  // Device preview's uid
    App.devicePreview.select(id);
    App.fix({ file: '', location: '' }, { label: '', hash: '#/device-preview', focus: `.eu[data-uid="${id}"]` });
  };
  /* ---------- a hand-written panel: identity and enclosure, devices, options ---------- */
  const handEnclosure = (p) => `<section class="section" style="margin:0 0 var(--space-5)"><h3>Cabinet</h3>
    <div class="form form--3" style="margin-top:var(--space-3)">
    ${edit('c.cabinet_name', 'Name', text('c.cabinet_name'), 'Printed in the sheet header.')}${edit('c.cabinet_number', 'Cabinet number', text('c.cabinet_number', { mono: true }))}${edit('c.sheet_name', 'Sheet name', text('c.sheet_name', { mono: true }), 'The workbook tab.')}
    ${edit('c.tag_prefix', 'Tag prefix', text('c.tag_prefix', { mono: true }), `Starts every tag in this panel, for example ${esc(p.panel.tag_prefix)}-Q1.`)}${edit('c.kind', 'Kind', choice('c.kind', [['console', 'Console'], ['network', 'Network cabinet'], ['control', 'Control']]))}${edit('c.lan', 'LAN side', choice('c.lan', [['', 'Both (common)'], ['A', 'Side A'], ['B', 'Side B']]))}</div></section>
    <h3 style="margin-bottom:var(--space-3)">Enclosure</h3>${encFields()}`;
  const blocked = () => (HD.dirty() ? 'disabled title="Save or discard the changes first"' : '');
  function handDevices(p) {
    const n = p.devices.length, cats = [...new Set(p.parts.map((x) => x.category))];
    const cell = (i, f, label, o) => `<label class="sr-only" for="ph-d.${i}.${f}">${label}</label>${text(`d.${i}.${f}`, o).replace('class="input', 'class="ctl input')}`;
    return `<div class="toolbar"><label class="sr-only" for="ph-add-part">Device to add</label><select class="select" id="ph-add-part" style="width:auto;max-width:420px">${cats.map((c) => `<optgroup label="${esc(c)}">${p.parts.filter((x) => x.category === c).map((x) => `<option value="${esc(x.part_id)}">${esc(x.part_id)} · ${esc(x.label)}</option>`).join('')}</optgroup>`).join('')}</select>
      <button class="btn btn--primary btn--sm" data-action="ph-dev-add" ${blocked()}>${icon('plus')}Add device</button><span class="sp"></span><span class="muted small">The BOM lists them in this order. Tags are generated by the engine.</span></div>
      <div class="table-wrap"><table class="table"><thead><tr><th style="width:76px"><span class="sr-only">Order</span></th><th>Device</th><th class="num" style="width:80px">Qty</th><th>Purpose (printed in the description)</th><th class="num" style="width:96px">HWIO</th><th style="width:170px">Alarm on breaker trip</th><th style="width:44px"><span class="sr-only">Remove</span></th></tr></thead>
      <tbody>${p.devices.map((d, i) => { const bad = Object.keys(DEV).map((f) => HD.errors[`d.${i}.${f}`]).filter(Boolean), chg = Object.keys(DEV).some((f) => `d.${i}.${f}` in HD.draft);
        return `<tr${chg ? ' class="is-changed"' : ''}><td><button class="btn btn--ghost btn--icon btn--xs" data-action="ph-dev-move" data-i="${i}" data-by="-1" aria-label="Move ${esc(d.part_id)} up" ${i === 0 || HD.dirty() ? 'disabled' : ''}>${icon('chevu')}</button><button class="btn btn--ghost btn--icon btn--xs" data-action="ph-dev-move" data-i="${i}" data-by="1" aria-label="Move ${esc(d.part_id)} down" ${i === n - 1 || HD.dirty() ? 'disabled' : ''}>${icon('chevd')}</button></td>
        <td><span class="mono">${esc(d.part_id)}</span><span class="cell-sub">${esc(d.label)}</span>${bad.length ? `<span class="err small">${icon('error')}<span>${esc(bad[0])}</span></span>` : ''}</td>
        <td>${cell(i, 'qty', `Quantity of ${esc(d.part_id)}`, { num: true, mono: true })}</td><td>${cell(i, 'purpose', `Purpose of ${esc(d.part_id)}`, { placeholder: 'Optional' })}</td><td>${cell(i, 'hwio_points', `HWIO points of ${esc(d.part_id)}`, { num: true, mono: true, placeholder: 'Auto' })}</td>
        <td>${d.branch_mcb ? `<label class="sr-only" for="ph-d.${i}.alarm_on_branch_mcb">Alarm on the breaker trip of ${esc(d.part_id)}</label>${choice(`d.${i}.alarm_on_branch_mcb`, [['', `Library: ${d.alarm_default ? 'on' : 'off'}`], ['true', 'On'], ['false', 'Off']]).replace('class="select', 'class="ctl select')}` : '<span class="muted small">No branch MCB</span>'}</td>
        <td><button class="btn btn--ghost btn--icon btn--sm" data-action="ph-dev-remove" data-i="${i}" aria-label="Remove ${esc(d.part_id)}" ${n === 1 ? 'disabled title="A panel lists at least one device. Delete the panel instead."' : blocked()}>${icon('trash')}</button></td></tr>
        <tr class="row-sub${chg ? ' is-changed' : ''}"><td></td><td colspan="5"><div style="display:flex;gap:var(--space-4);align-items:center;flex-wrap:wrap">${tagCell(i, 'tag', 'Tag', d.tags.join(', ') || 'Generated', 220)}${tagCell(i, 'tag_type', 'Type code', 'From the library', 150)}${tagCell(i, 'first_nn', 'First number', 'Automatic', 110, true)}${noteCell(i)}
          ${d.duplicate ? `<span class="err small">${icon('error')}<span>${esc(d.duplicate)}</span></span>` : ''}</div></td><td></td></tr>`; }).join('')}</tbody></table>
      <div class="table-foot"><span>${plural(n, 'row')}</span><span>HWIO comes from the device unless you set it. An alarm on breaker trip adds an auxiliary contact on the device's branch MCBs; on an AC branch it is also one HWIO point.</span></div></div>`;
  }
  /* A row's note (plan M71): shown in Preview and on the optional Notes sheet, never on the BOM. */
  const noteCell = (i) => `<label class="small muted" for="ph-d.${i}.note" style="display:flex;gap:var(--space-2);align-items:center">Note${text(`d.${i}.note`, { placeholder: 'Not printed' }).replace('class="input', 'style="width:260px" class="ctl input')}</label>`;
  /* Tag, type code and first number of a hand-written row (plan M59); the placeholders are what the engine generates. */
  const tagCell = (i, f, label, ph, w, numeric) => `<label class="small muted" for="ph-d.${i}.${f}" style="display:flex;gap:var(--space-2);align-items:center">${label}${text(`d.${i}.${f}`, { mono: true, num: !!numeric, placeholder: ph }).replace('class="input', `style="width:${w}px" class="ctl input`)}</label>`;
  /* Adding, moving or removing a device writes the whole list at once, without what the page adds to a row. */
  const rows = () => PE.page.devices.map(({ label, branch_mcb, alarm_default, tags, duplicate, ...d }) => { if (d.qty === 1) delete d.qty; return d; });  // qty 1 is the default
  function writeDevices(list, said) {
    Bridge.call('set_panel_field', S.project.file, S.sub, PE.page.panel.id, ['devices'], list)
      .then((page) => { PE.page = page; App.network.reload(); App.devicePreview.reload(); toast(said); App.render(); })
      .catch((e) => toast(`Not changed. ${e.message}`, 'error'));
  }
  ACTIONS['ph-dev-add'] = () => { const part = document.getElementById('ph-add-part').value; writeDevices([...rows(), { part_id: part }], `Added ${part}`); };
  ACTIONS['ph-dev-remove'] = (el) => { const list = rows(), [gone] = list.splice(+el.dataset.i, 1); writeDevices(list, `Removed ${gone.part_id}`); };
  ACTIONS['ph-dev-move'] = (el) => {
    const list = rows(), i = +el.dataset.i, j = i + Number(el.dataset.by);
    [list[i], list[j]] = [list[j], list[i]];
    writeDevices(list, `Moved ${list[j].part_id} ${j < i ? 'up' : 'down'}`);
  };
  function handOptions(p) {
    return `<p class="muted" style="max-width:68ch;margin-bottom:var(--space-4)">Empty a value to use the default.</p><div class="form form--2">${OPTIONS.map(([k, label, kind, help]) => {
      const o = p.options.find((x) => x.key === k), key = `o.${k}`;
      if (DV[k] && p.derived[DV[k][0]]) return edit(key, DV[k][1], mainMcb(p, key, '', DV[k][0]), 'Click the rating to type your own.');
      const ctl = Array.isArray(kind) ? choice(key, [['', `Default: ${shownValue(o.shared, kind)}`], ...kind]) : num(key, kind, { placeholder: `Default: ${str(o.shared) || 'none'}` });
      const note = o.own ? `${badge('info', `Own value · default ${shownValue(o.shared, kind)}`)} <button class="btn btn--ghost btn--sm" data-action="ph-use-default" data-key="${key}">Use the default</button>` : '';
      return edit(key, esc(label), ctl, [help || '', note].filter(Boolean).join(' '));
    }).join('')}</div>${busbars(p, false)}${kitSection(p, '', false)}${miscSection(p, 'mi', false)}`;
  }
  ACTIONS['ph-use-default'] = (el) => { HD.set(el.dataset.key, ''); S.dirty = true; App.render(); };
  /* Delete panel…: the writer refuses while something still names the panel; Undo writes the copy back. */
  ACTIONS['pe-delete'] = () => {
    const h = PE.page.panel;
    App.dialog({ title: `Delete ${esc(h.cabinet_name)}?`, body: `<p>This deletes <span class="mono">${esc(h.file.split(/[\\/]/).slice(-2).join('/'))}</span> and its sheet in the workbook. You can undo it.</p>`,
      actions: '<button class="btn btn--secondary" data-action="close">Cancel</button><button class="btn btn--danger" data-action="pe-delete-go">Delete panel</button>' });
  };
  ACTIONS['pe-delete-go'] = () => {
    const h = PE.page.panel;
    Bridge.call('delete_panel', S.project.file, S.sub, h.id).then((r) => {
      if (!r.written) {
        App.dialog({ title: `${esc(h.cabinet_name)} is still in use`, body: `<p>Change these first, then delete the panel:</p><ul style="padding-left:18px">${r.issues.map((i) => `<li>${i.location ? `<span class="mono small">${esc(i.location)}</span> ` : ''}${esc(i.message)}</li>`).join('')}</ul>`,
          actions: '<button class="btn btn--primary" data-action="close">OK</button>' });
        return;
      }
      App.closeDialog(); reload(); App.network.reload(); App.devicePreview.reload(); HD.reset();
      const sub = App.curSub(); if (sub && sub.panels) sub.panels -= 1;
      App.go('#/panels');
      toast(`Deleted ${h.cabinet_name}`, 'trash', () => Bridge.call('restore_panel', S.project.file, S.sub, r.panel)
        .then((x) => { if (!x.written) { toast(`Not restored. ${(x.issues[0] || {}).message || ''}`, 'error'); return; } App.network.reload(); App.devicePreview.reload(); if (App.curSub()) App.curSub().panels += 1; App.go(`#/panels/${x.id}`); })
        .catch((e) => toast(e.message, 'error')));
    }).catch((e) => toast(e.message, 'error'));
  };
  const readOnly = (p, t) => (t === 'devices' ? `<div class="table-wrap"><table class="table"><thead><tr><th>Part</th><th class="num" style="width:70px">Qty</th><th>Purpose</th></tr></thead>
    <tbody>${p.devices.map((d) => `<tr><td><span class="mono">${esc(d.part_id)}</span><span class="cell-sub">${esc(d.label)}</span></td><td class="num">${d.qty}</td><td>${esc(d.purpose || '')}</td></tr>`).join('')}</tbody></table></div>`
    : t === 'document' ? `<dl class="kv"><dt>Register document</dt><dd class="mono">${esc(p.document)}</dd></dl>`
    : t === 'enclosure' ? `<dl class="kv">${Object.entries(p.enclosure).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(typeof v === 'object' ? JSON.stringify(v) : v)}</dd>`).join('')}</dl>`
    : t === 'terminals' ? stripTable(p, (s) => `${esc(s.block_override || s.block)}`, (s) => `<span class="mono">${s.qty.override ?? s.qty.value}</span><span class="cell-sub">${esc(s.qty.rule)}</span>`)
    : t === 'options' ? `<dl class="kv">${p.options.map((o) => `<dt>${esc(o.key)}</dt><dd>${esc(JSON.stringify(o.value))}</dd>`).join('')}</dl>`
    : '<p class="muted">Port plans of a hand-written panel are in its file.</p>');

  /* ---------- Port plans: each device's own; the sized switches' are computed ---------- */
  const GROUPS = [['uplinks_l3', 'Uplink to L3'], ['uplinks', 'Uplink'], ['downlinks', 'Downlink']];
  const SPEEDS = ['10M', '100M', '1G', '2.5G', '5G', '10G', '25G'], MEDIA = ['MM', 'SM', 'RJ45'];
  const cellSel = (key, opts, label) => `<label class="sr-only" for="pe-${key}">${label}</label>${select('pe-' + key, opts, str(PD.shown(key)), { cls: 'ctl', invalid: !!PD.errors[key] })}`;
  const cellNum = (key, label) => `<label class="sr-only" for="pe-${key}">${label}</label>${text(key, { num: true, mono: true }).replace('class="input', 'class="ctl input')}`;
  const allocs = (plan) => GROUPS.flatMap(([g, use]) => ((plan && plan[g]) || []).map((a, i) => ({ g, use, i, a })));
  const result = (r) => `<div class="table-foot"><span>Engine result</span><span>${r.lines.length ? r.lines.map((x) => `<span class="mono" style="color:var(--color-text)">${esc(x.qty)} × ${esc(x.part_id || '')}</span> <span class="muted">${esc(x.description)}</span>`).join('<br>') : '<span class="muted">No SFPs or cables for this device</span>'}</span></div>`;
  /* r.l2 is null for a device with no link to the L2 switch (plan M89): nothing to change on Parts */
  const l2Line = (r) => `<p class="small" style="margin:var(--space-2) 0">${r.l2 && r.l2.ports ? `Linked to the L2 switch: ${r.l2.ports} × ${esc(r.l2.speed)} ${esc(r.l2.media)}.` : 'Not linked to the L2 switch.'}${r.l2 ? ` <a href="#/parts" data-action="pe-parts" data-i="${r.equipment}">Change on Parts</a>` : ''}</p>`;
  function portSection(r, p) {
    const d = p.devices.find((x) => x.device === r.device) || { role: r.role, label: r.device }, head = `<h3>${esc(devName(d))} <span class="muted mono" style="font-weight:400;font-size:13px">${esc(r.part_id)}</span></h3>`;
    if (!r.editable) {
      const rows = allocs(r.used);
      return `<section class="section" style="padding-top:var(--space-4)">${head}<p class="muted small" style="margin:var(--space-1) 0 var(--space-2)">Worked out by the switch sizing from Parts. Read-only.</p>
        <div class="table-wrap" style="max-width:820px"><table class="table"><thead><tr><th>Use</th><th class="num" style="width:90px">Ports</th><th style="width:100px">Speed</th><th style="width:100px">Media</th><th class="num" style="width:90px">Spare</th></tr></thead>
        <tbody>${rows.map(({ use, a }) => `<tr><td>${use}</td><td class="num">${a.count}</td><td class="mono">${esc(a.speed)}</td><td class="mono">${esc(a.media)}</td><td class="num">${a.spare}</td></tr>`).join('') || '<tr class="empty-row"><td colspan="5">No ports in use.</td></tr>'}</tbody></table>${result(r)}</div></section>`;
    }
    /* a monitor or a plain KVM: no link and no plan written, so nothing to allocate (plan M89) */
    if (!r.offered) return `<section class="section" style="padding-top:var(--space-4)">${head}<p class="muted small" style="margin:var(--space-1) 0 var(--space-2)">Not on the network, so it has no port plan.</p></section>`;
    const rows = allocs(r.own), k = (x, f) => `p.${r.equipment}.${x.g}.${x.i}.${f}`;
    return `<section class="section" style="padding-top:var(--space-4)"><div class="row" style="justify-content:space-between">${head}
        <span class="row" style="gap:var(--space-2)"><label class="sr-only" for="pa-g-${r.equipment}">Use of the new allocation</label><select class="select" id="pa-g-${r.equipment}" style="width:auto">${GROUPS.map(([g, u]) => `<option value="${g}" ${g === 'downlinks' ? 'selected' : ''}>${u}</option>`).join('')}</select>
        <button class="btn btn--ghost btn--sm" data-action="pe-alloc-add" data-i="${r.equipment}" ${PD.dirty() ? 'disabled title="Save or discard the changes first"' : ''}>${icon('plus')}Add allocation</button></span></div>
      ${l2Line(r)}
      <div class="table-wrap" style="max-width:820px"><table class="table"><thead><tr><th>Use</th><th class="num" style="width:90px">Ports</th><th style="width:110px">Speed</th><th style="width:100px">Media</th><th class="num" style="width:90px">Spare</th><th style="width:44px"><span class="sr-only">Remove</span></th></tr></thead>
      <tbody>${rows.map((x) => { const bad = ['count', 'speed', 'media', 'spare'].map((f) => PD.errors[k(x, f)]).filter(Boolean); const chg = ['count', 'speed', 'media', 'spare'].some((f) => k(x, f) in PD.draft);
        return `<tr${chg ? ' class="is-changed"' : ''}><td>${x.use}${bad.length ? `<span class="err small">${icon('error')}<span>${esc(bad[0])}</span></span>` : ''}</td><td>${cellNum(k(x, 'count'), `${x.use} ports`)}</td><td>${cellSel(k(x, 'speed'), SPEEDS, `${x.use} speed`)}</td><td>${cellSel(k(x, 'media'), MEDIA, `${x.use} media`)}</td><td>${cellNum(k(x, 'spare'), `${x.use} spare ports`)}</td>
        <td><button class="btn btn--ghost btn--icon btn--sm" data-action="pe-alloc-remove" data-i="${r.equipment}" data-g="${x.g}" data-n="${x.i}" aria-label="Remove ${x.use.toLowerCase()} ${x.a.count} × ${esc(x.a.speed)}" ${PD.dirty() ? 'disabled title="Save or discard the changes first"' : ''}>${icon('trash')}</button></td></tr>`; }).join('')
        || '<tr class="empty-row"><td colspan="6">No ports beyond its L2 link. Add an allocation for the ports it uses.</td></tr>'}</tbody></table>${result(r)}</div>
      <div class="form form--3" style="margin-top:var(--space-3);max-width:820px">${edit(`p.${r.equipment}.serial_ports`, 'Serial ports', num(`p.${r.equipment}.serial_ports`, '', { placeholder: '0' }), 'Each one adds a serial cable to the BOM.')}</div></section>`;
  }
  const ports = (p) => `<p class="muted" style="max-width:68ch">A port plan belongs to the device on Parts, so a change here also applies to the other panels with that device, on both sides. The engine works out the SFPs and cables and shows them under each table.</p>
    ${p.ports.map((r) => portSection(r, p)).join('') || '<p class="muted">No devices in this panel.</p>'}`;
  /* Adding or removing an allocation writes the device's whole port plan at once. */
  function writePlan(row, plan) {
    const empty = GROUPS.every(([g]) => !(plan[g] || []).length) && !plan.serial_ports;
    Bridge.call('set_port_plan', S.project.file, S.sub, row.device, empty ? null : plan).then((r) => {
      if (!r.written) { toast(`Not changed. ${(r.issues[0] && r.issues[0].message) || 'The plan was refused.'}`, 'error'); return; }
      changed(); App.render();
    }).catch((e) => toast(e.message, 'error'));
  }
  const rowOf = (i) => PE.page.ports.find((x) => x.equipment === +i);
  const planOf = (row) => JSON.parse(JSON.stringify(row.own || { uplinks_l3: [], uplinks: [], downlinks: [], serial_ports: 0 }));
  ACTIONS['pe-alloc-add'] = (el) => {
    const row = rowOf(el.dataset.i), plan = planOf(row), g = document.getElementById('pa-g-' + el.dataset.i).value;
    const link = row.l2 || {};
    plan[g] = [...(plan[g] || []), { count: 1, speed: link.speed || '1G', media: link.media || 'MM', spare: 0 }];
    writePlan(row, plan);
  };
  ACTIONS['pe-alloc-remove'] = (el) => {
    const row = rowOf(el.dataset.i), plan = planOf(row);
    plan[el.dataset.g] = plan[el.dataset.g].filter((_, i) => i !== +el.dataset.n);
    writePlan(row, plan);
  };
  ACTIONS['pe-parts'] = (el, e) => { e.preventDefault(); App.fix({ file: 'substation.yaml', location: `equipment[${el.dataset.i}]` }); };

  /* ---------- Options: for every generated panel, or this one only ---------- */
  const OPTIONS = [
    ['dc_spare_branches_per_feed', 'DC spare branches per feed', '', 'Spare MCBs on each of feed 1 and feed 2.'],
    ['ac_spare_branches', 'AC spare branches', ''],
    ['dc_spare_rating_a', 'DC spare rating', 'A', 'Empty uses the largest device branch.'],
    ['ac_spare_rating_a', 'AC spare rating', 'A', 'Empty uses the largest housekeeping branch.'],
    ['ventilation', 'Ventilation', [['auto', 'Automatic (from the heat calculation)'], ['forced', 'Fans'], ['natural', 'Filters']]],
    ['change_over_diodes', 'Change-over diodes', [['auto', 'Automatic'], ['true', 'Yes'], ['false', 'No']]],
    ['main_mcb_override_a', 'Main MCB override', 'A', 'Empty uses the sizing rule.'],
    ['aux_socket_a', 'Auxiliary socket', 'A', 'Empty means no socket.'],
    ['inter_panel_terminals', 'Inter-panel terminals', ''],
    ['smoke_detector', 'Smoke detector', [['terminals', 'Terminals only, detector by others'], ['supplied', 'Supplied with the panel'], ['none', 'None']]]];  // ADR 0032
  const shownValue = (o, opts) => { const v = str(o); const hit = Array.isArray(opts) && opts.find(([x]) => x === v); return hit ? hit[1] : v || 'None'; };
  function options(p) {
    const own = S.optScope === 'own', n = p.panel.number, scope = own ? String(n) : 'all';
    const owned = p.options.filter((o) => o.own);
    const rows = OPTIONS.map(([k, label, kind, help]) => {
      const o = p.options.find((x) => x.key === k), key = `o.${scope}.${k}`;
      if (DV[k] && p.derived[DV[k][0]]) return edit(key, DV[k][1], mainMcb(p, key, own ? o.shared : '', DV[k][0]), `Click the rating to type your own${own ? ' for this panel' : ' for every generated panel'}.`);
      const opts = Array.isArray(kind) ? (own ? [['', `Shared: ${shownValue(o.shared, kind)}`], ...kind] : kind) : null;
      const ctl = opts ? choice(key, opts) : num(key, kind, own ? { placeholder: `Shared: ${str(o.shared) || 'none'}` } : {});
      const note = own && o.own ? `${badge('info', `Own value · shared ${shownValue(o.shared, kind)}`)} <button class="btn btn--ghost btn--sm" data-action="pe-use-shared" data-key="${key}">Use the shared value</button>`
        : !own && o.own ? `<span class="muted small">This panel has its own value, ${esc(shownValue(o.value, kind))}.</span>` : '';
      return edit(key, esc(label), ctl, [help || '', note].filter(Boolean).join(' '));
    }).join('');
    return `${scopeField(own, `${own ? `Values you set are kept for ${esc(p.panel.cabinet_name)} only and marked Own value.` : 'Values you set apply to every generated panel that has no value of its own.'}${owned.length ? ` This panel has ${plural(owned.length, 'own value')}.` : ''}`)}
      <div class="form form--2">${rows}</div>${derivedRules(p)}${busbars(p, own)}${kitSection(p, `${own ? p.panel.number : 'all'}.`, own)}${miscSection(p, `mi.${own ? p.panel.number : 'all'}`, own)}`;
  }
  /* ADR 0040: what the engine chose for this panel and why; read here, changed through the inputs above. */
  const derivedRules = (p) => (!p.derived.fan && !p.derived.cable_managers ? '' : `<div class="form form--2" style="margin-top:var(--space-3)">${p.derived.fan ? field('Fan', shownRule('Fitted', p.derived.fan), 'From the heat calculation and the library\'s fans; the ventilation option above decides whether fans are fitted.') : ''}${p.derived.cable_managers ? field('Cable managers', shownRule('Quantity', p.derived.cable_managers), 'Switched per device on Parts.') : ''}</div>`);
  const scopeField = (own, help) => `<div class="field" style="margin-bottom:var(--space-4)"><span class="label" id="pe-scope-l">Apply to</span><div class="segmented" role="radiogroup" aria-labelledby="pe-scope-l">
        <label><input type="radio" name="pe-scope" value="all" data-action="pe-scope" ${own ? '' : 'checked'}><span>All generated panels</span></label><label><input type="radio" name="pe-scope" value="own" data-action="pe-scope" ${own ? 'checked' : ''}><span>This panel only</span></label></div>
      <span class="help">${help}</span></div>`;
  /* Grounding busbars (M58): one checkbox per busbar in the library's catalogue; a tick writes at once. */
  function busbars(p, own) {
    const o = p.options.find((x) => x.key === 'grounding_busbars'), on = own || !p.panel.generated ? o.value : o.shared;
    const busy = F.dirty() ? 'disabled title="Save or discard the changes first"' : '';
    const note = p.panel.generated && own && o.own ? `${badge('info', 'Own value')} <button class="btn btn--ghost btn--sm" data-action="pe-bus-shared" ${busy}>Use the shared busbars</button>`
      : p.panel.generated && !own && o.own ? '<span class="muted small">This panel has its own busbars.</span>' : '';
    return `<fieldset class="section" style="margin-top:var(--space-5);border:0;padding:0"><legend style="padding:0"><h3 style="margin:0">Grounding busbars</h3></legend>
      <p class="lede">Each one ticked is a group H row.${note ? ' ' + note : ''}</p>${p.derived.grounding ? `<span class="dv-rule">${esc(p.derived.grounding.rule)}</span>` : ''}
      ${p.busbars.map((b) => `<label class="check" style="display:flex;gap:var(--space-2);align-items:center;margin-top:var(--space-2)"><input type="checkbox" data-action="pe-busbar" data-key="${esc(b.key)}" ${on.includes(b.key) ? 'checked' : ''} ${busy}><span>${esc(b.description)} <span class="muted small mono">${esc(b.tag)}</span></span></label>`).join('')}</fieldset>`;
  }
  function writeBusbars(list) {
    const p = PE.page, own = S.optScope === 'own';
    const call = !p.panel.generated ? Bridge.call('set_panel_field', S.project.file, S.sub, p.panel.id, ['options', 'grounding_busbars'], list)
      : list === null ? Bridge.call('remove_panel_option', S.project.file, S.sub, 'grounding_busbars', p.panel.number)
        : Bridge.call('set_panel_option', S.project.file, S.sub, 'grounding_busbars', list, own ? p.panel.number : null);
    call.then((r) => {
      if (r && r.written === false) { toast(`Not changed. ${(r.issues[0] && r.issues[0].message) || 'The busbars were refused.'}`, 'error'); return; }
      changed(); App.render();
    }).catch((e) => toast(`Not changed. ${e.message}`, 'error'));
  }
  ACTIONS['pe-busbar'] = (el) => {
    const p = PE.page, ticked = new Set([...document.querySelectorAll('[data-action="pe-busbar"]:checked')].map((x) => x.dataset.key));
    writeBusbars(p.busbars.map((b) => b.key).filter((k) => ticked.has(k)));
  };
  ACTIONS['pe-bus-shared'] = () => writeBusbars(null);
  ACTIONS['pe-scope'] = (el) => { S.optScope = el.value; App.render(); };
  ACTIONS['pe-use-shared'] = (el) => { PD.set(el.dataset.key, ''); S.dirty = true; App.render(); };

  /* ---------- Terminals (ADR 0033): each strip's quantity from its rule, which the panel may override, and its block type ---------- */
  const stripTable = (p, block, qty, changed = () => false) => `<div class="table-wrap"><table class="table"><thead><tr><th>Strip</th><th style="width:220px">Block type</th><th>Quantity</th></tr></thead>
    <tbody>${p.terminals.map((s) => `<tr${changed(s) ? ' class="is-changed"' : ''}><td><span class="mono">${esc(s.code)}</span><span class="cell-sub">${esc(s.description)}</span></td><td>${block(s)}</td><td>${qty(s)}</td></tr>`).join('')}</tbody></table>
    <div class="table-foot"><span>${plural(p.terminals.length, 'strip')}</span><span>The spare terminals of Project settings are added to the wiring strips. Strips a device brings stay as its part gives them.</span></div></div>`;
  function stripQty(key, d, inherited, label = 'Quantity', unit = '', subject = '') {
    if (PE.dv === key) return App.derived(key, { editing: true, id: PFX + key, label, rule: d.rule, control: num(key, unit).replace('<input ', `<input data-pdv="${key}" `) });
    const eff = str(F.shown(key)) || str(inherited), u = unit ? ` ${unit}` : '';
    return App.derived(key, { label, shown: `${eff || d.value}${u}`, auto: `${d.value}${u}`, overridden: !!eff, changed: key in F.draft, bad: !!F.errors[key], rule: d.rule, edit: 'pe-dv-edit', reset: 'pe-dv-reset' })
      + (eff && subject ? reasonLine(PE.page, subject, eff, d.value) : '');
  }
  function terminals(p) {
    if (!p.terminals.length) return `<p class="muted">${p.engine_error ? 'The strips show once the engine runs on this substation.' : 'This panel has no terminal strips.'}</p>`;
    const gen = p.panel.generated, own = gen && S.optScope === 'own', pre = gen ? `${own ? p.panel.number : 'all'}.` : '';
    const ov = p.options.find((x) => x.key === 'terminal_overrides'), bo = p.options.find((x) => x.key === 'terminal_block_overrides');
    const inherited = (o, code) => (own && !o.own ? str(o.shared[code]) : '');  // this panel's own list replaces the shared one
    const head = gen ? scopeField(own, own ? `Overrides you set are kept for ${esc(p.panel.cabinet_name)} only; once it has its own, the shared ones no longer reach it.` : `Overrides you set apply to every generated panel that has none of its own.${ov.own || bo.own ? ' This panel has its own.' : ''}`)
      : '<p class="muted" style="max-width:68ch;margin-bottom:var(--space-4)">Click a quantity to type your own. Empty it to use the rule.</p>';
    return head + stripTable(p, (s) => { const key = `tb.${pre}${s.code}`, inh = inherited(bo, s.code);
      return `<label class="sr-only" for="${PFX}${key}">Block type of ${esc(s.code)}</label>${choice(key, [['', inh ? `Shared: ${inh}` : `Rule: ${s.block}`], ...p.terminal_blocks]).replace('class="select', 'class="ctl select')}`;
    }, (s) => { const key = `t.${pre}${s.code}`, bad = err(key) || err(`tb.${pre}${s.code}`);
      return stripQty(key, s.qty, inherited(ov, s.code), 'Quantity', '', `terminals.${s.code}`) + (bad ? `<span class="err small">${icon('error')}<span>${esc(bad)}</span></span>` : '');
    }, (s) => `t.${pre}${s.code}` in F.draft || `tb.${pre}${s.code}` in F.draft);
  }

  /* ---------- Cabinet housekeeping (ADR 0032): the kit's counts, heater and hygrostat, each load's breaker ---------- */
  const KIT = [['lamps', 'Lamps'], ['fans', 'Fans', 'With fans'], ['thermostats_forced', 'Thermostats with fans'], ['thermostats_natural', 'Thermostats with filters'], ['filters', 'Vent filters', 'With filters']];
  const LOADS = { lamp: 'Lamp breaker', fan: 'Fan and thermostat breaker', thermostat: 'Thermostat breaker', heater: 'Heater breaker' };
  function kitSection(p, pre, own) {
    const hk = p.housekeeping, o = p.options.find((x) => x.key === 'housekeeping'), inh = (path) => (own && !o.own ? str(dig(o.shared, path)) : '');
    const shownBool = (v) => (v === true || v === 'true' ? 'Yes' : 'No');
    const counts = KIT.map(([f, label]) => { const key = `hk.${pre}${f}`, i = inh([f]);
      return edit(key, esc(label), num(key, '', { placeholder: i ? `Shared: ${i}` : `Spec: ${hk.defaults[f]}` })); }).join('');
    const extras = [['heater', 'Heater'], ['hygrostat', 'Hygrostat']].map(([f, label]) => { const key = `hk.${pre}${f}`;
      if (!hk.roles[f]) return field(esc(label), `<span class="muted small">The library has no ${f} part. Add one under Library › Catalogues › Housekeeping.</span>`);
      return edit(key, esc(label), choice(key, [['', `${own && !o.own ? 'Shared' : 'Default'}: ${shownBool(inh([f]) || false)}`], ['true', 'Yes'], ['false', 'No']]), f === 'heater' ? 'Adds its row, its own breaker and its strips.' : ''); }).join('');
    const ratings = Object.keys(LOADS).filter((k) => hk.ratings[k]).map((k) => { const key = `hk.${pre}branch_ratings.${k}`;
      return edit(key, LOADS[k], stripQty(key, hk.ratings[k], inh(['branch_ratings', k]), 'Rating', 'A', `housekeeping.${k}`), 'Click the rating to type your own.'); }).join('');
    const note = !p.panel.generated ? '' : own && o.own ? ` ${badge('info', 'Own value')} Once this panel has its own kit, the shared one no longer reaches it.` : !own && o.own ? ' <span class="muted small">This panel has its own kit.</span>' : '';
    return `<section class="section" style="margin-top:var(--space-5)"><h3>Cabinet housekeeping</h3>
      <p class="lede">Empty counts use the spec's kit. Fans or filters follow the ventilation.${note}</p>
      <div class="form form--3">${counts}${extras}</div><div class="form form--2" style="margin-top:var(--space-3)">${ratings}</div></section>`;
  }

  /* ---------- Miscellaneous rows (plan M70): free text, each printed last in group H as 1 Lot ---------- */
  function miscSection(p, key, own) {
    const o = p.options.find((x) => x.key === 'misc_items'), inh = own && !o.own ? o.shared.join(', ') : '';
    const note = !p.panel.generated ? '' : own && o.own ? ` ${badge('info', 'Own value')} Once this panel has its own rows, the shared ones no longer reach it.` : !own && o.own ? ' <span class="muted small">This panel has its own rows.</span>' : '';
    return `<section class="section" style="margin-top:var(--space-5)"><h3>Miscellaneous rows</h3>
      <p class="lede">Each line is a group H row, printed last with a quantity of 1 Lot.${note}</p>
      <div class="form">${edit(key, 'Rows', area(key, { placeholder: inh ? `Shared: ${inh}` : 'e.g. Miscellaneous: cable ties, labels' }), 'One row per line. Empty uses none.')}</div></section>`;
  }

  /* ---------- Document ---------- */
  function docTab(p) {
    const e = p.documents.find((x) => x.key === str(F.shown('doc'))), nt = p.panel.generated ? `nt.${p.panel.number}` : 'nt';
    return `<div class="form form--3">${edit('doc', 'Register document', choice('doc', p.documents.map((x) => [x.key, x.key])), `${p.panel.generated ? 'Shared by every generated panel. ' : ''}Chosen from the project's document register.`)}
      ${field('Document number', input('pe-dn', e ? e.doc_no : '', { mono: true, readonly: true }), 'Printed in the page header and footer.')}${field('Revision', input('pe-dr', e ? e.rev : '', { mono: true, readonly: true }))}</div>
      <div class="row" style="margin-top:var(--space-3)"><a class="btn btn--secondary btn--sm" href="#/project/documents">Edit in the register</a></div>
      <div class="form" style="margin-top:var(--space-5)">${edit(nt, 'Notes', area(nt, { rows: 4 }), `Your own notes on ${esc(p.panel.cabinet_name)}. Never printed in the workbook.`)}</div>`;
  }

  /* ---------- YAML: read-only ---------- */
  const hl = (line) => esc(line).replace(/^(\s*)(- )?([A-Za-z_][\w]*)(:)/, '$1$2<span class="k">$3</span>$4').replace(/(#.*)$/, '<span class="c">$1</span>');
  function yaml(p) {
    const lines = p.yaml.replace(/\n$/, '').split('\n'), name = p.panel.file.split(/[\\/]/).slice(-2).join('/');
    return `<div class="toolbar"><span class="mono" style="font-size:12.5px">${esc(name)}</span>${p.panel.generated ? badge('info', 'Generated') : ''}<span class="sp"></span><span class="muted small">${icon('lock')} ${p.panel.generated ? 'Written by the layout. Read-only.' : 'Read-only in the app for now'}</span></div>
      <div class="code" role="textbox" aria-readonly="true" aria-multiline="true" aria-label="${esc(name)} source" tabindex="0">
        <div class="gut" aria-hidden="true">${lines.map((_, i) => `<div>${i + 1}</div>`).join('')}</div>
        <div class="src">${lines.map((x) => `<div>${hl(x) || ' '}</div>`).join('')}</div></div>`;
  }
})();
