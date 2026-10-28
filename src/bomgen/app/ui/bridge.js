/* The only code that talks to Python (bomgen.app.api, ADR 0015).
   Bridge.call(name, ...args) resolves with the endpoint's data, or rejects with { kind, message }.
   Opened in a plain browser (design review) there is no backend: calls reject with kind "no_backend". */
(function () {
  const WAIT_MS = 5000;
  let settle;
  const ready = new Promise((resolve) => { settle = resolve; });
  const api = () => (window.pywebview && window.pywebview.api) || null;
  if (api()) settle(true);
  else {
    window.addEventListener('pywebviewready', () => settle(true));
    setTimeout(() => settle(!!api()), WAIT_MS);
  }

  async function call(name, ...args) {
    await ready;
    if (!api()) throw { kind: 'no_backend', message: 'Not running inside the app.' };  // checked per call: a slow start may answer after WAIT_MS
    const method = api()[name];
    if (typeof method !== 'function') throw { kind: 'internal', message: `The app has no endpoint "${name}".` };
    let reply;
    try { reply = await method(...args); } catch (e) { throw { kind: 'internal', message: String((e && e.message) || e) }; }
    if (reply && reply.ok === true) return reply.data;
    throw (reply && reply.error) || { kind: 'internal', message: `No answer from "${name}".` };
  }

  window.Bridge = { ready, call };
})();
