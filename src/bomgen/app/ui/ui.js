/* App state, shared components, shell rendering and routing. */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (v) => String(v).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  const S = {
    theme: 'light',            // light | dark | system
    firstRun: false,           // true: nothing installed yet, no projects
    launch: 'normal',          // normal | bomproj (app was started by double-clicking a .bomproj file)
    proj: null,                // open project id, or null
    sub: null,                 // open substation id, or null
    dirty: false,
    libTab: 'import',
    tab: { project: 'info', settings: 'general', panel: 'devices', panels: 'board', lib: 'overview', preview: 'psa1', libdetail: 'overview', panelsel: 'psa1' },
    selectedDevice: '',
    density: 'default',
    backend: 'unknown',        // unknown | yes | no (no bridge: the app says so, see noBackend)
    project: null,             // the open project's page from open_project, shaped for the screens
    app: null,                 // app_info from Python: version, project_file, workspace, libraries
    library: null,             // the active library { name, version }, or null
    launchFile: ''             // file name of the .bomproj the app was started with
  };
  const ACTIONS = {};
  const SCREENS = {};
  /* Real state from bomgen.app.api.app_info. */
  function setAppInfo(info) {
    S.backend = 'yes';
    S.app = info;
    const active = info.libraries.find((l) => l.active);
    S.library = active ? { name: active.name, version: active.active } : null;
    S.firstRun = info.libraries.length === 0;  // installed but broken is not a first run
    S.launch = info.project_file ? 'bomproj' : 'normal';
    S.launchFile = info.project_file ? info.project_file.split(/[\\/]/).pop() : '';
    render();
    info.libraries.filter((l) => l.problem).forEach((l) => toast(`Library ${l.name} needs attention: ${l.problem}`, 'warn'));
  }
  const lib = () => S.library || { name: '', version: '' };
  const noActive = () => !!S.app && !S.library;  // libraries installed, none usable (see the toast)

  /* ---------- components ---------- */
  const badge = (kind, text, ic) => `<span class="badge badge--${kind}">${ic ? icon(ic) : ''}${esc(text)}</span>`;
  const verified = (v) => ({ confirmed: badge('ok', 'Confirmed', 'check'), partial: badge('plain', 'Partial', 'info'), unverified: badge('plain', 'Unverified', 'info') }[v]);
  const banner = (kind, body, actions = '') => `<div class="banner banner--${kind}" role="${kind === 'bad' ? 'alert' : 'status'}">${icon({ bad: 'error', warn: 'warn', ok: 'check', info: 'info' }[kind])}<div class="grow">${body}</div>${actions}</div>`;
  const tabs = (group, items, active, label) =>
    `<div class="tabs" role="tablist" aria-label="${esc(label)}">${items.map(([id, text, extra, tip]) =>
      `<button role="tab" id="tab-${group}-${id}"${tip ? ` title="${esc(tip)}"` : ''} aria-selected="${id === active}" tabindex="${id === active ? 0 : -1}" data-action="tab" data-group="${group}" data-value="${id}">${esc(text)}${extra || ''}</button>`).join('')}</div>`;
  const field = (label, control, help = '', err = '') => {
    const id = (control.match(/\sid="([^"]+)"/) || [])[1];
    const desc = [help && id ? `${id}-help` : '', err && id ? `${id}-err` : ''].filter(Boolean).join(' ');
    const ctl = desc && !/aria-describedby=/.test(control) ? control.replace(/<(input|select|textarea)\b/, `<$1 aria-describedby="${desc}"`) : control;
    return `<div class="field"><label${id ? ` for="${id}"` : ''}>${label}</label>${ctl}${help ? `<span class="help"${id ? ` id="${id}-help"` : ''}>${help}</span>` : ''}${err ? `<span class="err"${id ? ` id="${id}-err"` : ''}>${icon('error')}<span>${err}</span></span>` : ''}</div>`;
  };
  /* Changed marker (components.md): a warning dot before the label, or at the start of an edited cell, never the revision yellow. */
  const CHG = '<span class="chg" aria-hidden="true"></span><span class="sr-only">changed</span>';
  const changedField = (html) => html.replace(/^<div class="field">(<label[^>]*>)/, `<div class="field is-changed">$1${CHG}`);
  const changedCell = (on) => (on ? [' class="is-changed"', CHG] : ['', '']);
  /* The save bar's invalid line: one control that moves focus to the first invalid field (components.md "Save bar"). */
  const fixLine = (action, bad) => `<button class="savebar-fix" data-action="${action}">${icon('error')}<span><b>${bad} ${bad === 1 ? 'field needs' : 'fields need'} fixing</b> before you can save.</span></button>`;
  const input = (id, value, o = {}) => `<input class="input ${o.mono ? 'input--mono' : ''} ${o.num ? 'input--num' : ''}" id="${id}" value="${esc(value)}" ${o.readonly ? 'readonly' : ''} ${o.invalid ? 'aria-invalid="true"' : ''} ${o.placeholder ? `placeholder="${esc(o.placeholder)}"` : ''} data-dirty="1">`;
  const select = (id, opts, value, o = {}) => `<select class="select ${o.cls || ''}" id="${id}" ${o.invalid ? 'aria-invalid="true"' : ''} data-dirty="1">${opts.map((x) => { const [v, t] = Array.isArray(x) ? x : [x, x]; return `<option value="${esc(v)}" ${v === value ? 'selected' : ''}>${esc(t)}</option>`; }).join('')}</select>`;
  /* `note`: one muted line under the lede, the same place on every page (what the app cannot do yet). */
  const pageHead = (title, lede = '', actions = '', crumbs = '', note = '') => `<div class="page-head"><div class="page-head-main">${crumbs ? `<div class="crumbs">${crumbs}</div>` : ''}<h1>${title}</h1>${lede ? `<p class="lede">${lede}</p>` : ''}${note ? `<p class="page-note" title="${esc(note)}">${icon('info')}<span>${esc(note)}</span></p>` : ''}</div>${actions ? `<div class="actions">${actions}</div>` : ''}</div>`;

  /* Import reviews (library and project): every check; after a failure the later ones collapse to one line. */
  const CHECK = { ok: ['ok', 'check'], warning: ['warn', 'warn'], failed: ['bad', 'error'], skipped: ['info', 'info'] };
  function checkList(checks) {
    const failed = checks.some((c) => c.status === 'failed');
    const item = (cls, ic, label, detail) => `<li class="${cls}">${icon(ic)}<span style="color:var(--color-text)">${esc(label)}${detail ? `<span class="cell-sub">${esc(detail)}</span>` : ''}</span></li>`;
    const shown = failed ? checks.filter((c) => c.status !== 'skipped') : checks;
    const skipped = checks.length - shown.length;
    return shown.map((c) => {
      if (c.id === 'signature' && c.status === 'skipped') return item('info', 'info', 'Not signed (not used)', c.detail);
      const [cls, ic] = CHECK[c.status];
      return item(cls, ic, c.label, c.detail);
    }).join('') + (skipped ? `<li class="info">${icon('info')}<span>${skipped} later ${skipped === 1 ? 'check was' : 'checks were'} not run</span></li>` : '');
  }

  /* ---------- overlay: dialog, toast ---------- */
  let lastFocus = null;
  function dialog({ title, body, actions }) {
    lastFocus = document.activeElement;
    const ov = $('#overlay');
    ov.innerHTML = `<div class="scrim" data-action="scrim"><div class="dialog" role="dialog" aria-modal="true" aria-labelledby="dlg-title"><h2 id="dlg-title">${title}</h2><div class="body">${body}</div><div class="foot">${actions}</div></div></div>`;
    const first = $('.dialog .btn--primary, .dialog .btn', ov);
    first && first.focus();
  }
  function closeDialog() { $('#overlay').innerHTML = ''; if (lastFocus && lastFocus.focus) lastFocus.focus(); }
  function toast(text, ic = 'check', undo = null) {
    const t = document.createElement('div'); t.className = 'toast'; t.innerHTML = `${icon(ic)}<span>${esc(text)}</span>${undo ? '<button class="toast-btn" data-toast-undo>Undo</button>' : ''}`;
    if (undo) t.querySelector('[data-toast-undo]').addEventListener('click', () => { undo(); t.remove(); });
    $('#toasts').appendChild(t); setTimeout(() => t.remove(), undo ? 8000 : 3600);
  }

  /* ---------- shell ---------- */
  const route = () => {
    const [, a = 'home', b = '', c = ''] = location.hash.split('/');
    return { a, b, c };
  };
  const go = (hash) => { if (location.hash === hash) render(); else location.hash = hash; };
  const curProject = () => S.project;
  const curSub = () => { const p = curProject(); return p ? p.substations.find((s) => s.id === S.sub) || null : null; };
  const hasProject = () => !S.firstRun && !!curProject();
  const hasSub = () => hasProject() && !!curSub();

  function renderBar() {
    const p = curProject(), s = curSub();
    $('#bar').innerHTML = `
      <div class="brand"><span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span>BOM Generator</div>
      ${hasProject() ? `<span class="bar-divider"></span><div class="bar-project"><b title="${esc(p.name)}">${esc(p.name)}</b><span>${s ? esc(s.name) : 'No substation open'}</span></div>` : ''}
      <div class="bar-spacer"></div>
      <a class="bar-btn" href="#/library" style="text-decoration:none" aria-label="Device library ${S.backend !== 'yes' ? 'unknown' : S.firstRun ? 'not installed' : noActive() ? 'needs attention' : esc(lib().name + ' ' + lib().version)}">
        <span class="dot ${S.backend !== 'yes' || S.firstRun || noActive() ? 'dot--bad' : 'dot--ok'}" aria-hidden="true"></span>${S.backend !== 'yes' ? 'Library unknown' : S.firstRun ? 'No library installed' : noActive() ? 'No active library' : `${esc(lib().name)} ${esc(lib().version)}`}</a>
      <button class="bar-btn bar-btn--icon" data-action="theme" aria-label="Theme: ${S.theme}. Change theme" title="Theme: ${S.theme}">${icon(S.theme === 'dark' ? 'moon' : 'sun')}</button>
      <button class="bar-btn bar-btn--icon" data-action="help" aria-label="Help" title="Help">${icon('help')}</button>`;
  }
  function navItem(href, ic, label, tail = '', tailCls = '', disabled = false, cur = false) {
    return `<a href="${disabled ? '#' : href}" ${cur ? 'aria-current="page"' : ''} ${disabled ? 'aria-disabled="true" tabindex="-1" style="opacity:.45;pointer-events:none"' : ''}>${icon(ic)}<span>${label}</span>${tail ? `<span class="tail ${tailCls}">${tail}</span>` : ''}</a>`;
  }
  function renderNav() {
    const r = route().a, np = hasProject(), p = curProject();
    const ns = hasSub();
    const noParts = () => { const sp = App.sub && App.sub.peek(); return !!sp && !!sp.equipment && !sp.equipment.length; };  // Device preview waits for the first parts
    /* APP-24: "Not set up" until the first parts; else a count of rows whose part the library lacks, as on Checks */
    const unknown = () => { const sp = App.sub && App.sub.peek(); return sp && sp.parts ? sp.parts.rows.filter((x) => x.part_id && !x.known).length : 0; };
    const partsTail = !ns ? '' : noParts() ? `${icon('warn')}Not set up` : unknown() ? `${icon('error')}${unknown()} ${unknown() === 1 ? 'error' : 'errors'}` : '';
    const v = ns && S.verify && S.verify.key === `${S.project.file}#${S.sub}` ? S.verify : null;  // the last checks of the open substation
    const buildTail = v ? (v.errors ? `${icon('error')}Blocked` : `${icon('check')}Ready`) : '';
    const checksTail = v ? (v.errors ? `${icon('error')}${v.errors} ${v.errors === 1 ? 'error' : 'errors'}` : v.failed ? `${icon('error')}Failed` : `${icon('check')}Clear`) : '';
    const bad = !!v && (v.errors > 0 || v.failed);
    const projTail = !np ? '' : p.status === 'bad' ? `${icon('error')}${p.statusText}` : p.status === 'warn' ? `${icon('warn')}1` : `${icon('check')}`;
    const switcher = np ? `<div class="nav-switch"><label class="sr-only" for="sub-switch">Substation</label><select class="select" id="sub-switch" data-action="sub-switch">${S.sub ? '' : '<option value="">Choose a substation…</option>'}${p.substations.map((x) => `<option value="${x.id}" ${x.id === S.sub ? 'selected' : ''}>${esc(x.name)}</option>`).join('')}</select></div>` : '';
    $('#nav').innerHTML = `
      ${navItem('#/home', 'home', 'Home', '', '', false, r === 'home')}
      ${navItem('#/library', 'library', 'Library', S.firstRun || noActive() ? '' : esc(lib().version), '', false, r === 'library')}
      ${np ? `<div class="nav-group">Project</div>
      ${navItem('#/project', 'project', esc(p.name), projTail, p.status === 'bad' ? 'bad' : p.status === 'warn' ? 'warn' : 'ok', false, r === 'project')}
      <div class="nav-group">Substation</div>${switcher}
      ${navItem('#/settings', 'file', 'Settings', '', 'ok', !ns, r === 'settings')}
      ${navItem('#/parts', 'parts', 'Parts', partsTail, partsTail ? (noParts() ? 'warn' : 'bad') : 'ok', !ns, r === 'parts')}
      ${navItem('#/device-preview', 'elevation', 'Device preview', '', '', !ns || noParts(), r === 'device-preview')}
      ${navItem('#/panels', 'panels', 'Panels', ns ? esc(App.panelCount && App.panelCount() != null ? App.panelCount() : curSub().panels) : '', '', !ns, r === 'panels')}
      ${navItem('#/loose', 'pkg', 'Loose material', App.looseCount && App.looseCount() != null ? String(App.looseCount()) : '', '', !ns, r === 'loose')}
      <div class="nav-group">Verify and issue</div>
      ${navItem('#/checks', 'checks', 'Checks', checksTail, bad ? 'bad' : 'ok', !ns, r === 'checks')}
      ${navItem('#/preview', 'preview', 'Preview', '', '', !ns, r === 'preview')}
      ${navItem('#/build', 'build', 'Build', buildTail, v && v.errors ? 'bad' : 'ok', !ns, r === 'build')}` : ''}
      <div class="nav-foot">App ${S.app ? esc(S.app.version) : ''}<br>Works offline. Nothing leaves this PC.</div>`;
  }
  const saveState = () => (unsaved() ? `<span class="warn">${icon('warn')} Unsaved changes</span>` : '');
  function renderStatus() {
    const ns = hasSub(), np = hasProject(), p = curProject();
    $('#status').innerHTML = S.backend === 'no' ? `<span class="bad">${icon('error')} Engine not reachable</span>`
      : ns ? `${saveState()}<span class="mono" style="font-size:12px">${esc(curSub().file)}</span><span class="sp"></span>`
      : np ? `${saveState()}<span>${esc(p.path)}</span><span class="sp"></span><span>${p.substations.length} ${p.substations.length === 1 ? 'substation' : 'substations'}</span>`
      : `<span>No project open</span><span class="sp"></span><span>${S.firstRun ? 'Library: none installed' : ''}</span>`;
  }
  /* No bridge: the UI must never stand in for the engine, so every page says so (audit 2026-10-30, finding 1). */
  const noBackend = () => `<div class="page">${pageHead('BOM Generator could not reach its engine', 'The window opened, but the part of the app that reads projects and builds workbooks did not answer.')}
      <div class="empty"><h3>Nothing can be shown or saved until it does.</h3><p>Close this window and start BOM Generator again from the Start menu. If this keeps happening, run the installer again; the repair keeps your projects and libraries.</p>
      <div class="row"><button class="btn btn--primary" data-action="retry-backend">${icon('refresh')}Try again</button></div></div></div>`;
  function renderMain() {
    const { a } = route();
    if (a === 'network') { location.replace('#/parts'); return; }  // Network became Parts (M23)
    if (S.backend === 'no') { $('#main').innerHTML = noBackend(); document.title = 'BOM Generator'; return; }
    const key = ({ home: 'home', project: 'project', settings: 'settings', parts: 'parts', 'device-preview': 'device-preview', panels: 'panels', loose: 'loose', library: 'library', checks: 'checks', preview: 'preview', build: 'build' })[a] || 'home';
    const needsProject = key === 'project', needsSub = ['settings', 'parts', 'device-preview', 'panels', 'loose', 'checks', 'preview', 'build'].includes(key);
    const m = $('#main');
    m.innerHTML = (needsProject && !hasProject()) || (needsSub && !hasSub()) ? SCREENS.home() : SCREENS[key]();
    if (SCREENS[key + 'After']) SCREENS[key + 'After']();
    if (fixing) {  // the field a problem leads to, once its page has loaded
      if (fixing.screen !== a) fixing = null;
      else { const el = m.querySelector(fixing.focus); if (el) { fixing = null; el.scrollIntoView({ block: 'center' }); el.focus(); } }
    }
    // a strip wider than the page scrolls; keep the selected tab whole
    // (sideways only, so a re-render never moves the page)
    m.querySelectorAll('.tabs [role="tab"][aria-selected="true"]').forEach((t) => {
      const strip = t.parentElement, s = strip.getBoundingClientRect(), r = t.getBoundingClientRect();
      if (r.left < s.left) strip.scrollLeft -= s.left - r.left;
      else if (r.right > s.right) strip.scrollLeft += r.right - s.right;
    });
    document.title = 'BOM Generator';
  }
  function render() {
    document.documentElement.dataset.theme = S.theme === 'system' ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : S.theme;
    document.documentElement.classList.toggle('comfort', S.density === 'comfort');
    renderBar(); renderNav(); renderStatus(); renderMain();
    document.title = 'BOM Generator';
  }

  /* ---------- events ---------- */
  document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action]'); if (!el) return;
    const name = el.dataset.action;
    if (name === 'scrim' && e.target !== el) return;
    if (ACTIONS[name]) { ACTIONS[name](el, e); }
  });
  document.addEventListener('input', (e) => { if (e.target.dataset && e.target.dataset.dirty && !S.dirty) { S.dirty = true; renderStatus(); } });
  document.addEventListener('change', (e) => { const sw = e.target.closest('select[data-action="sub-switch"]'); if (sw) ACTIONS['sub-switch'](sw); });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && $('#overlay').innerHTML) { e.preventDefault(); closeDialog(); }
    if (e.key === 'Tab' && $('#overlay .dialog')) {
      const f = $$('#overlay button, #overlay input, #overlay select, #overlay a[href]').filter((x) => !x.disabled);
      if (!f.length) return; const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
    const t = e.target.closest && e.target.closest('[role="tab"]');
    if (t && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) {
      const list = $$('[role="tab"]', t.parentElement); const i = list.indexOf(t);
      const n = list[(i + (e.key === 'ArrowRight' ? 1 : list.length - 1)) % list.length]; n.click(); setTimeout(() => { const nn = document.getElementById(n.id); nn && nn.focus(); }, 0);
    }
  });

  ACTIONS.tab = (el) => { S.tab[el.dataset.group] = el.dataset.value; if (el.dataset.group === 'project') history.replaceState(null, '', '#/project/' + el.dataset.value); if (el.dataset.group === 'settings') history.replaceState(null, '', '#/settings/' + el.dataset.value); if (el.dataset.group === 'panel') history.replaceState(null, '', '#/panels/' + route().b + '/' + el.dataset.value); const keep = $('#main').scrollTop; renderMain(); $('#main').scrollTop = keep; const nt = document.getElementById(el.id); nt && nt.focus(); };
  ACTIONS.goto = (el) => go(el.dataset.to);

  /* ---------- where to fix a located problem (APP-7; the M32 design brief) ---------- */
  /* One action per problem: its label, the page that holds the value, and the control to focus there. */
  let fixing = null;  // { screen, focus } until that page has drawn the control
  const SETTINGS_TAB = { substation: 'general', output: 'output', document: 'output', calculations: 'documents', constants: 'constants' };
  const PANEL_TAB = { enclosure: 'enclosure', devices: 'devices', port_plans: 'ports', options: 'options', document: 'document' };
  function whereToFix(p) {
    const file = String(p.file || ''), loc = String(p.location || ''), id = (x) => `[id="${x}"]`;
    const line = { label: 'Show the line', hash: '#/settings/yaml', focus: null, line: p.line || null };
    const own = /[\\/]panels[\\/]([^\\/]+)\.yaml$/.exec(file);
    if (own) return { label: 'Open the panel', hash: `#/panels/${own[1]}/${PANEL_TAB[loc.split(/[.[]/)[0]] || 'yaml'}`, focus: null };
    if (!/substation\.yaml$/.test(file)) return { label: 'Open the project', hash: '#/project', focus: null };
    const [head, rest = ''] = loc.split(/\.(.*)/s), key = rest.split(/[.[]/)[0];
    let m;
    if ((m = /^equipment\[(\d+)\]/.exec(loc))) return { label: 'Go to the row', hash: '#/parts', focus: id(`p-e.${m[1]}.part_id`) };
    if (head === 'network') return { label: 'Go to the field', hash: '#/parts', focus: id(`p-n.${key}`) };
    if (head === 'spares') return { label: 'Go to the field', hash: '#/parts', focus: id(`p-s.${key}`) };
    if (head === 'catalogue_choice') return { label: 'Go to the field', hash: '#/parts', focus: id(`p-b.${key}`) };
    if (head === 'generated_panels') {
      const n = (m = /^options_by_panel\[(\d+)\]\.(\w+)/.exec(rest)) ? Number(m[1]) : 1;
      const panel = App.generatedPanelId ? App.generatedPanelId(n) : null, base = `#/panels/${panel}`;
      if (!panel) return line;  // no layout to open while the files have errors
      if (m) return { label: 'Open the panel', hash: `${base}/options`, focus: id(`pe-o.${n}.${m[2]}`), scope: 'own' };
      if (key === 'options') { const k = rest.split('.')[1]; return { label: 'Open the panel', hash: `${base}/options`, focus: k ? id(`pe-o.all.${k}`) : null, scope: 'all' }; }
      if (key === 'enclosure') { const k = rest.split('.').slice(1).join('.'); return { label: 'Open the panel', hash: `${base}/enclosure`, focus: k ? id(`pe-e.${k}`) : null }; }
      if (key === 'document') return { label: 'Open the panel', hash: `${base}/document`, focus: id('pe-doc') };
      if (['cabinet_name', 'cabinet_number', 'tag_prefix', 'sheet_name'].includes(key)) return { label: 'Open the panel', hash: `${base}/enclosure`, focus: id(`pe-g.${key}`) };
      return line;
    }
    if (loc === 'equipment') return { label: 'Open Parts', hash: '#/parts', focus: null };
    if (loc === 'panels') return { label: 'Open Panels', hash: '#/panels', focus: null };
    if (head === 'layout') return { label: 'Open the board', hash: '#/panels', focus: null, changes: true };
    if (head === 'loose_material') return { label: 'Open loose material', hash: '#/loose', focus: null };
    const tab = SETTINGS_TAB[head];
    if (!tab) return line;
    const field = head === 'substation' ? 'st-name' : head === 'document' ? 'st-document' : head === 'output' ? (key === 'sheet_names' ? `st-sheet_${rest.split('.')[1]}` : 'st-file_name')
      : head === 'calculations' ? `st-calc_${key}` : `st-c_${key}`;
    return { label: 'Go to the field', hash: `#/settings/${tab}`, focus: id(field) };
  }
  /* A banner's buttons for a page that cannot show: the first error's fix, and Checks. */
  let fixable = null;
  const fixButtons = (problems) => {
    fixable = (problems || []).find((p) => p.level === 'error') || null;
    return `${fixable ? `<button class="btn btn--primary btn--sm" data-action="fix-first">${esc(whereToFix(fixable).label)}</button>` : ''}<a class="btn btn--secondary btn--sm" href="#/checks">Open checks</a>`;
  };
  ACTIONS['fix-first'] = () => { if (fixable) fix(fixable); };
  /* Opens where a problem is fixed and focuses the control once the page draws it. */
  function fix(p, to) {  // to: a place given directly, instead of the problem's
    const f = to || whereToFix(p);
    if (f.scope) S.optScope = f.scope;
    if (f.changes && App.panelsShowChanges) App.panelsShowChanges();
    fixing = f.focus ? { screen: f.hash.split('/')[1], focus: f.focus } : f.line ? { screen: 'settings', focus: `.code .src > div:nth-child(${f.line})` } : null;
    if (f.hash.startsWith('#/settings/')) S.tab.settings = f.hash.split('/')[2];
    if (location.hash === f.hash) render(); else go(f.hash);
  }
  const switchTo = (id) => { S.sub = id || null; S.dirty = false; const { a } = route(); go(['settings', 'parts', 'device-preview', 'panels', 'loose', 'checks', 'preview', 'build'].includes(a) ? '#/' + a : '#/panels'); };
  ACTIONS['sub-switch'] = (el) => {
    const value = el.value;
    el.value = S.sub || '';  // the switch waits for the dialog's answer
    if (leaving(() => switchTo(value))) return;
    switchTo(value);
  };
  ACTIONS.theme = () => { S.theme = { light: 'dark', dark: 'system', system: 'light' }[S.theme]; render(); toast(`Theme: ${S.theme}`, 'info'); };
  ACTIONS.help = () => dialog({ title: 'Help', body: '<p>The user guide is not written yet.</p>', actions: '<button class="btn btn--primary" data-action="close">Close</button>' });
  ACTIONS.close = () => closeDialog();
  ACTIONS['retry-backend'] = () => { S.backend = 'unknown'; render(); Bridge.call('app_info').then(setAppInfo).catch((err) => { if (err.kind === 'no_backend') { S.backend = 'no'; render(); } else toast(`Could not read the app's state: ${err.message}`, 'error'); }); };
  ACTIONS.scrim = () => closeDialog();
  /* Leaving a form page with unsaved changes asks first (editing.md "Leaving with unsaved changes").
     Each draft form adds a guard; `leaving(then)` opens the first dirty one's dialog and returns true. */
  const GUARDS = [];
  const unsaved = () => GUARDS.some((g) => g.screen === route().a && g.dirty());
  const leaving = (then) => { const g = GUARDS.find((x) => x.screen === route().a && x.dirty()); if (!g) return false; g.ask(then); return true; };
  let here = location.hash;
  window.addEventListener('hashchange', () => {
    const was = here; here = location.hash;
    const to = location.hash, from = was.split('/')[1] || 'home';
    if (from !== route().a && GUARDS.some((g) => g.screen === from && g.dirty())) {
      history.replaceState(null, '', was); here = was;  // stay until the dialog answers
      leaving(() => go(to)); return;
    }
    closeDialog(); render(); $('#main').scrollTop = 0;
  });

  /* ---------- a form drafted on the page and saved together (docs/ui/editing.md) ----------
     Each field is read on change and checked by the model; the draft holds only what differs from the file.
     o: { prefix (control ids are prefix + key), screen (route), file, label, spec(key) -> [path, kind] or null,
          saved(key), check(path, value) -> Promise of a message, write(path, value) -> Promise of the page, done(page, keys) } */
  function toModel(kind, raw) {  // [value for the file, or null to remove the key; a message when it cannot be read]
    const t = String(raw == null ? '' : raw).trim();
    if (!t) return [null, null];
    if (kind === 'text' || kind === 'choice') return [t, null];
    if (kind === 'bool') return [t === 'true', null];
    if (kind === 'int') return /^\d+$/.test(t) ? [Number(t), null] : [null, 'Enter a whole number, for example 2.'];
    if (kind === 'num') return /^-?\d+(\.\d+)?$/.test(t) ? [Number(t), null] : [null, 'Enter a number, for example 1.3.'];
    return /^\d+(\.\d+)?$/.test(t) ? [Math.round(Number(t) * 10) / 1000, null] : [null, 'Enter a percentage, for example 20.'];
  }
  function draftForm(o) {
    const D = { draft: {}, errors: {}, saving: false };
    const n = (x) => Object.keys(x).length;
    D.shown = (key) => (key in D.draft ? D.draft[key] : o.saved(key));
    D.mark = (key, html) => (key in D.draft ? changedField(html) : html);
    D.err = (key) => (D.errors[key] ? esc(D.errors[key]) : '');
    D.dirty = () => n(D.draft) > 0;
    D.reset = () => { D.draft = {}; D.errors = {}; };
    D.set = (key, typed) => {  // a typed value; returns the value for the file, or undefined when it cannot be read
      const sp = o.spec(key), was = o.saved(key);
      if (String(typed).trim() === String(was == null ? '' : was)) { delete D.draft[key]; delete D.errors[key]; return undefined; }
      D.draft[key] = typed;
      const [value, local] = toModel(sp[1], typed);
      if (local) { D.errors[key] = local; return undefined; }
      delete D.errors[key];
      return value;
    };
    D.bar = () => {
      const c = n(D.draft), bad = n(D.errors);
      if (!c && !D.saving) return '';
      return `<div class="savebar${bad ? ' savebar--bad' : ''}" role="region" aria-label="Unsaved changes"><span class="savebar-msg">${D.saving ? '<span class="spinner"></span><b>Saving…</b>' : bad ? fixLine(`${o.prefix}first-bad`, bad) : `<span class="dot dot--warn" aria-hidden="true"></span><b>${c} unsaved change${c === 1 ? '' : 's'}</b> · saved to ${esc(o.file)}`}</span>
        <span class="sp"></span><button class="btn btn--secondary" data-action="${o.prefix}discard" ${D.saving ? 'disabled' : ''}>Discard</button><button class="btn btn--primary" data-action="${o.prefix}save" ${D.saving || bad ? 'disabled' : ''}>${icon('save')}${esc(o.label)} <kbd class="kbd">Ctrl+S</kbd></button></div>`;
    };
    document.addEventListener('change', (e) => {
      const id = e.target.id || '';
      if (!id.startsWith(o.prefix) || route().a !== o.screen) return;
      const key = id.slice(o.prefix.length), sp = o.spec(key);
      if (!sp) return;
      const typed = e.target.type === 'checkbox' ? String(e.target.checked) : e.target.value, value = D.set(key, typed);
      queueMicrotask(render);
      if (value == null) return;  // unchanged, unreadable or emptied (removed on save)
      o.check(sp[0], value).then((msg) => {
        if (D.draft[key] !== typed || (D.errors[key] || null) === (msg || null)) return;  // a render would drop what is being typed elsewhere
        if (msg) D.errors[key] = msg; else delete D.errors[key];
        render();
      }).catch(() => {});
    });
    ACTIONS[o.prefix + 'first-bad'] = () => {  // the first refused field on the page
      const key = Object.keys(D.errors).find((k) => document.getElementById(o.prefix + k)), el = key && document.getElementById(o.prefix + key);
      if (el) { el.scrollIntoView({ block: 'center' }); el.focus(); }
    };
    ACTIONS[o.prefix + 'discard'] = () => { D.reset(); S.dirty = false; render(); toast('Changes discarded', 'undo'); };
    D.save = () => {  // resolves true once every change is written
      const keys = Object.keys(D.draft);
      if (D.saving || !keys.length || n(D.errors)) return Promise.resolve(false);
      D.saving = true; render();
      let page = null;
      const next = (i) => {
        if (i === keys.length) return Promise.resolve();
        const key = keys[i], [path, kind] = o.spec(key);
        return o.write(path, toModel(kind, D.draft[key])[0]).then((r) => { page = r; delete D.draft[key]; return next(i + 1); })
          .catch((err) => { D.errors[key] = err.message; throw err; });
      };
      return next(0).then(() => { toast(`Saved ${keys.length} change${keys.length === 1 ? '' : 's'} to ${o.file}`, 'check'); S.dirty = false; return true; })
        .catch(() => { toast('Not saved: a value was refused. It is marked on the page.', 'error'); return false; })
        .then((ok) => { D.saving = false; if (page) o.done(page, keys); render(); return ok; });
    };
    ACTIONS[o.prefix + 'save'] = () => { D.save(); };
    let then = null;  // where the person was going when the leave dialog opened
    GUARDS.push({ screen: o.screen, dirty: () => D.dirty() && !D.saving, ask: (next) => {
      then = next;
      const c = n(D.draft), bad = n(D.errors), why = bad ? `${bad} ${bad === 1 ? 'field needs' : 'fields need'} fixing before you can save.` : '';
      dialog({ title: 'Save the changes first?', body: `<p>You have ${c} unsaved change${c === 1 ? '' : 's'} on this page. They are saved to ${esc(o.file)}.</p>${bad ? `<p class="small" id="${o.prefix}leave-why" style="color:var(--color-danger-text);display:flex;gap:6px">${icon('error')}${esc(why)}</p>` : ''}`,
        actions: `<button class="btn btn--secondary" data-action="close">Keep editing</button><button class="btn btn--secondary" data-action="${o.prefix}leave-discard">Discard changes</button><button class="btn btn--primary" data-action="${o.prefix}leave-save" ${bad ? `disabled aria-describedby="${o.prefix}leave-why" title="${esc(why)}"` : ''}>${icon('save')}Save and leave</button>` });
    } });
    const leave = () => { const t = then; then = null; if (t) t(); };
    ACTIONS[o.prefix + 'leave-discard'] = () => { closeDialog(); D.reset(); S.dirty = false; leave(); };
    ACTIONS[o.prefix + 'leave-save'] = () => { closeDialog(); D.save().then((ok) => { if (ok) leave(); }); };
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's' && route().a === o.screen && D.dirty()) {
        e.preventDefault(); if (document.activeElement) document.activeElement.blur(); queueMicrotask(ACTIONS[o.prefix + 'save']);
      }
    });
    return D;
  }

  window.App = { $, $$, esc, S, ACTIONS, SCREENS, badge, verified, banner, tabs, field, input, select, pageHead, dialog, closeDialog, toast, go, render, setAppInfo, checkList, route, hasProject, hasSub, curProject, curSub, renderStatus, draftForm, changedField, changedCell, fixLine, whereToFix, fix, fixButtons };
})();
