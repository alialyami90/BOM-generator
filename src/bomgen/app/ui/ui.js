/* App state, shared components, shell rendering and routing. */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (v) => String(v).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  const S = {
    theme: 'light',            // light | dark | system
    firstRun: false,           // true: nothing installed yet, no projects
    launch: 'normal',          // normal | bomproj (app was started by double-clicking a .bomproj file)
    proj: 'ep132',             // open project id, or null
    sub: 'gis01',              // open substation id, or null
    checks: 'errors',          // errors | clean
    dirty: false,
    libTab: 'import',
    build: 'ready',            // ready | building | success | locked
    buildStep: 0,
    tab: { project: 'info', settings: 'general', panel: 'devices', panels: 'board', lib: 'overview', preview: 'psa1', libdetail: 'overview', panelsel: 'psa1' },
    layout: { overrides: [], removed: [], history: [], selected: '', openOverrides: false },
    selectedDevice: 'RST2228-L1-24MM',
    yamlError: true,
    density: 'default',
    backend: 'unknown',        // unknown | yes | no (opened in a plain browser: the prototype's illustrative data)
    project: null,             // the open project's page from open_project, shaped for the screens
    app: null,                 // app_info from Python: version, project_file, workspace, libraries
    library: null,             // the active library { name, version }, or null
    launchFile: ''             // file name of the .bomproj the app was started with
  };
  const ACTIONS = {};
  const SCREENS = {};
  /* Real state from bomgen.app.api.app_info; screens not connected yet still read the illustrative DB. */
  function setAppInfo(info) {
    if (S.backend !== 'yes') { S.backend = 'yes'; S.proj = null; S.sub = null; }  // real projects replace the example
    S.app = info;
    const active = info.libraries.find((l) => l.active);
    S.library = active ? { name: active.name, version: active.active } : null;
    S.firstRun = info.libraries.length === 0;  // installed but broken is not a first run
    S.launch = info.project_file ? 'bomproj' : 'normal';
    S.launchFile = info.project_file ? info.project_file.split(/[\\/]/).pop() : '';
    render();
    info.libraries.filter((l) => l.problem).forEach((l) => toast(`Library ${l.name} needs attention: ${l.problem}`, 'warn'));
  }
  const lib = () => S.library || { name: DB.library.name, version: DB.library.version };
  const noActive = () => !!S.app && !S.library;  // libraries installed, none usable (see the toast)
  const counts = () => ({ errors: S.checks === 'errors' ? DB.problems.filter((p) => p.sev === 'error').length : 0, warnings: DB.problems.filter((p) => p.sev === 'warning').length });

  /* ---------- components ---------- */
  const badge = (kind, text, ic) => `<span class="badge badge--${kind}">${ic ? icon(ic) : ''}${esc(text)}</span>`;
  const verified = (v) => ({ confirmed: badge('ok', 'Confirmed', 'check'), partial: badge('warn', 'Partial', 'info'), unverified: badge('plain', 'Unverified', 'info') }[v]);
  const banner = (kind, body, actions = '') => `<div class="banner banner--${kind}" role="${kind === 'bad' ? 'alert' : 'status'}">${icon({ bad: 'error', warn: 'warn', ok: 'check', info: 'info' }[kind])}<div class="grow">${body}</div>${actions}</div>`;
  const tabs = (group, items, active, label) =>
    `<div class="tabs" role="tablist" aria-label="${esc(label)}">${items.map(([id, text, extra]) =>
      `<button role="tab" id="tab-${group}-${id}" aria-selected="${id === active}" tabindex="${id === active ? 0 : -1}" data-action="tab" data-group="${group}" data-value="${id}">${esc(text)}${extra || ''}</button>`).join('')}</div>`;
  const field = (label, control, help = '', err = '') => {
    const id = (control.match(/\sid="([^"]+)"/) || [])[1];
    const desc = [help && id ? `${id}-help` : '', err && id ? `${id}-err` : ''].filter(Boolean).join(' ');
    const ctl = desc && !/aria-describedby=/.test(control) ? control.replace(/<(input|select|textarea)\b/, `<$1 aria-describedby="${desc}"`) : control;
    return `<div class="field"><label${id ? ` for="${id}"` : ''}>${label}</label>${ctl}${help ? `<span class="help"${id ? ` id="${id}-help"` : ''}>${help}</span>` : ''}${err ? `<span class="err"${id ? ` id="${id}-err"` : ''}>${icon('error')}<span>${err}</span></span>` : ''}</div>`;
  };
  const input = (id, value, o = {}) => `<input class="input ${o.mono ? 'input--mono' : ''} ${o.num ? 'input--num' : ''}" id="${id}" value="${esc(value)}" ${o.readonly ? 'readonly' : ''} ${o.invalid ? 'aria-invalid="true"' : ''} ${o.placeholder ? `placeholder="${esc(o.placeholder)}"` : ''} data-dirty="1">`;
  const select = (id, opts, value, o = {}) => `<select class="select ${o.cls || ''}" id="${id}" ${o.invalid ? 'aria-invalid="true"' : ''} data-dirty="1">${opts.map((x) => { const [v, t] = Array.isArray(x) ? x : [x, x]; return `<option value="${esc(v)}" ${v === value ? 'selected' : ''}>${esc(t)}</option>`; }).join('')}</select>`;
  const pageHead = (title, lede = '', actions = '', crumbs = '') => `<div class="page-head"><div>${crumbs ? `<div class="crumbs">${crumbs}</div>` : ''}<h1>${title}</h1>${lede ? `<p class="lede">${lede}</p>` : ''}</div>${actions ? `<div class="actions">${actions}</div>` : ''}</div>`;
  const illus = () => `<span class="illus">${icon('info')}Illustrative data: not connected yet</span>`;

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
  const curProject = () => (S.backend === 'no' ? DB.projects.find((p) => p.id === S.proj) || null : S.project);
  const curSub = () => { const p = curProject(); return p ? p.substations.find((s) => s.id === S.sub) || null : null; };
  const hasProject = () => !S.firstRun && !!curProject();
  const hasSub = () => hasProject() && !!curSub();

  function renderBar() {
    const p = curProject(), s = curSub();
    $('#bar').innerHTML = `
      <div class="brand"><span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span>BOM Generator</div>
      ${hasProject() ? `<span class="bar-divider"></span><div class="bar-project"><b>${esc(p.name)}</b><span>${s ? esc(s.name) : 'No substation open'}</span></div>` : ''}
      <div class="bar-spacer"></div>
      <a class="bar-btn" href="#/library" style="text-decoration:none" aria-label="Device library ${S.firstRun ? 'not installed' : noActive() ? 'needs attention' : esc(lib().name + ' ' + lib().version)}">
        <span class="dot ${S.firstRun || noActive() ? 'dot--bad' : 'dot--ok'}" aria-hidden="true"></span>${S.firstRun ? 'No library installed' : noActive() ? 'No active library' : `${esc(lib().name)} ${esc(lib().version)}`}</a>
      <button class="bar-btn bar-btn--icon" data-action="theme" aria-label="Theme: ${S.theme}. Change theme" title="Theme: ${S.theme}">${icon(S.theme === 'dark' ? 'moon' : 'sun')}</button>
      <button class="bar-btn bar-btn--icon" data-action="help" aria-label="Help" title="Help">${icon('help')}</button>`;
  }
  function navItem(href, ic, label, tail = '', tailCls = '', disabled = false, cur = false) {
    return `<a href="${disabled ? '#' : href}" ${cur ? 'aria-current="page"' : ''} ${disabled ? 'aria-disabled="true" tabindex="-1" style="opacity:.45;pointer-events:none"' : ''}>${icon(ic)}<span>${label}</span>${tail ? `<span class="tail ${tailCls}">${tail}</span>` : ''}</a>`;
  }
  function renderNav() {
    const r = route().a, c = counts(), np = hasProject(), p = curProject();
    const ns = hasSub(), ex = ns && S.backend !== 'yes';  // ex: the example substation's figures (M10c and M10d connect the real ones)
    const v = ns && S.backend === 'yes' && S.verify && S.verify.key === `${S.project.file}#${S.sub}` ? S.verify : null;  // the last checks of a real substation
    const buildTail = v ? (v.errors ? `${icon('error')}Blocked` : `${icon('check')}Ready`) : !ex ? '' : c.errors ? `${icon('error')}Blocked` : `${icon('check')}Ready`;
    const checksTail = v ? (v.errors ? `${icon('error')}${v.errors} ${v.errors === 1 ? 'error' : 'errors'}` : v.failed ? `${icon('error')}Failed` : `${icon('check')}Clear`) : ex ? (c.errors ? `${icon('error')}${c.errors} errors` : `${icon('check')}Clear`) : '';
    const bad = v ? v.errors > 0 || v.failed : c.errors > 0;
    const projTail = !np ? '' : p.status === 'bad' ? `${icon('error')}${p.statusText}` : p.status === 'warn' ? `${icon('warn')}1` : `${icon('check')}`;
    const switcher = np ? `<div class="nav-switch"><label class="sr-only" for="sub-switch">Substation</label><select class="select" id="sub-switch" data-action="sub-switch">${S.sub ? '' : '<option value="">Choose a substation…</option>'}${p.substations.map((x) => `<option value="${x.id}" ${x.id === S.sub ? 'selected' : ''}>${esc(x.name)}</option>`).join('')}</select></div>` : '';
    $('#nav').innerHTML = `
      ${navItem('#/home', 'home', 'Home', '', '', false, r === 'home')}
      ${navItem('#/library', 'library', 'Library', S.firstRun || noActive() ? '' : esc(lib().version), '', false, r === 'library')}
      ${np ? `<div class="nav-group">Project</div>
      ${navItem('#/project', 'project', esc(p.name.replace(' (example)', '')), projTail, p.status === 'bad' ? 'bad' : p.status === 'warn' ? 'warn' : 'ok', false, r === 'project')}
      <div class="nav-group">Substation</div>${switcher}
      ${navItem('#/settings', 'file', 'Settings', ex ? icon('check') : '', 'ok', !ns, r === 'settings')}
      ${navItem('#/network', 'network', 'Network', ex ? (S.sub === 'cb03' ? `${icon('warn')}Not set up` : icon('check')) : '', S.sub === 'cb03' ? 'warn' : 'ok', !ns, r === 'network')}
      ${navItem('#/panels', 'panels', 'Panels', ex ? String(S.sub === 'cb03' ? 0 : DB.panels.length) : ns ? esc(curSub().panels) : '', '', !ns, r === 'panels')}
      <div class="nav-group">Verify and issue</div>
      ${navItem('#/checks', 'checks', 'Checks', checksTail, bad ? 'bad' : 'ok', !ns, r === 'checks')}
      ${navItem('#/preview', 'preview', 'Preview', '', '', !ns, r === 'preview')}
      ${navItem('#/build', 'build', 'Build', buildTail, (v ? v.errors : c.errors) ? 'bad' : 'ok', !ns, r === 'build')}` : ''}
      <div class="nav-foot">App ${S.app ? esc(S.app.version) : ''}<br>Works offline. Nothing leaves this PC.</div>`;
  }
  function renderStatus() {
    const c = counts(), ns = hasSub(), np = hasProject(), p = curProject();
    $('#status').innerHTML = ns && S.backend === 'yes' ? `<span class="mono" style="font-size:12px">${esc(curSub().file)}</span><span class="sp"></span>`
      : ns ? `
      <span>${S.dirty ? `<b style="color:var(--color-warning)">Unsaved changes</b>` : `Substation saved ${esc(DB.sub.savedAt)}`}</span>
      <span class="mono" style="font-size:12px">${esc(DB.sub.path)}</span>
      <span class="sp"></span>
      <button data-action="goto" data-to="#/checks" aria-label="${c.errors} errors, ${c.warnings} warnings in ${esc(curSub().name)}. Open checks">
        ${c.errors ? `<span class="bad">${icon('error')} ${c.errors} errors</span>` : `<span class="ok">${icon('check')} No errors</span>`}
        <span>${icon('warn')} ${c.warnings} warnings</span></button>`
      : np ? `<span>${esc(p.path)}</span><span class="sp"></span><span>${p.substations.length} ${p.substations.length === 1 ? 'substation' : 'substations'}</span>`
      : `<span>No project open</span><span class="sp"></span><span>${S.firstRun ? 'Library: none installed' : ''}</span>`;
  }
  function renderMain() {
    const { a } = route();
    const key = ({ home: 'home', project: 'project', settings: 'settings', network: 'network', panels: 'panels', library: 'library', checks: 'checks', preview: 'preview', build: 'build' })[a] || 'home';
    const needsProject = key === 'project', needsSub = ['settings', 'network', 'panels', 'checks', 'preview', 'build'].includes(key);
    const m = $('#main');
    m.innerHTML = (needsProject && !hasProject()) || (needsSub && !hasSub()) ? SCREENS.home() : SCREENS[key]();
    if (needsSub && hasSub() && S.backend === 'yes' && !['settings', 'network', 'checks', 'preview', 'build'].includes(key)) {  // M10c part 2 connects the panels
      m.insertAdjacentHTML('afterbegin', `<div class="not-connected"><div class="page" style="padding-bottom:var(--space-3)">${banner('info', '<b>Not connected yet.</b> This screen still shows the example substation from the design, not your project.')}</div></div>`);
    }
    if (SCREENS[key + 'After']) SCREENS[key + 'After']();
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
  document.addEventListener('change', (e) => { const g = e.target.closest('select[data-action="grp"]'); if (g) ACTIONS.grp(g); const sw = e.target.closest('select[data-action="sub-switch"]'); if (sw) ACTIONS['sub-switch'](sw); });
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
  ACTIONS['sub-switch'] = (el) => { S.sub = el.value || null; S.dirty = false; S.layout = { overrides: [], removed: [], history: [], selected: '', openOverrides: false }; const { a } = route(); go(['settings', 'network', 'panels', 'checks', 'preview', 'build'].includes(a) ? '#/' + a : '#/panels'); };
  ACTIONS.theme = () => { S.theme = { light: 'dark', dark: 'system', system: 'light' }[S.theme]; render(); toast(`Theme: ${S.theme}`, 'info'); };
  ACTIONS.help = () => dialog({ title: 'Help', body: '<p>The user guide is not written yet.</p>', actions: '<button class="btn btn--primary" data-action="close">Close</button>' });
  ACTIONS.close = () => closeDialog();
  ACTIONS.scrim = () => closeDialog();
  window.addEventListener('hashchange', () => { render(); $('#main').scrollTop = 0; });

  window.App = { $, $$, esc, S, ACTIONS, SCREENS, counts, badge, verified, banner, tabs, field, input, select, pageHead, illus, dialog, closeDialog, toast, go, render, setAppInfo, checkList, route, hasProject, hasSub, curProject, curSub, renderStatus };
})();
