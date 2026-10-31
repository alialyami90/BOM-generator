/* One pointer drag for the Panels board and Device preview (plan M24; part picking design §6).
   Pointer events, not HTML5 drag-and-drop, which never reaches the page in the installed app (WebView2).
   A press on a handle becomes a drag after 4 px, so a click without movement still selects. Esc,
   pointercancel and a lost pointer capture cancel; the click that follows a drag is swallowed.
   App.pointerDrag({ handle, enabled(), start(el, e) -> false to refuse, move(e), drop(), cancel() }) */
(function () {
  const views = [];
  let press = null, drag = null, swallowClick = false;  // press: { o, el, x, y, pointer }; drag: { o, el, pointer }
  App.pointerDrag = (o) => { views.push(o); };
  function end(cancelled) {
    const d = drag; drag = null; press = null; swallowClick = true;
    try { if (d.el.hasPointerCapture(d.pointer)) d.el.releasePointerCapture(d.pointer); } catch (_) { /* already released */ }
    if (cancelled) d.o.cancel(); else d.o.drop();
  }
  document.addEventListener('pointerdown', (e) => {
    swallowClick = false;
    if (drag || e.button !== 0 || !e.isPrimary || !e.target.closest) return;
    for (const o of views) {
      const el = e.target.closest(o.handle);
      if (el && (!o.enabled || o.enabled())) { press = { o, el, x: e.clientX, y: e.clientY, pointer: e.pointerId }; return; }
    }
  });
  document.addEventListener('pointermove', (e) => {
    if (drag) { if (e.pointerId === drag.pointer) drag.o.move(e); return; }
    if (!press || e.pointerId !== press.pointer || Math.hypot(e.clientX - press.x, e.clientY - press.y) < 4) return;
    const p = press; press = null;
    if (!document.body.contains(p.el) || p.o.start(p.el, e) === false) return;
    drag = { o: p.o, el: p.el, pointer: p.pointer };
    try { p.el.setPointerCapture(p.pointer); } catch (_) { /* the pointer is already gone */ }
    p.o.move(e);
  });
  document.addEventListener('pointerup', (e) => { press = null; if (drag && e.pointerId === drag.pointer) end(false); });
  document.addEventListener('pointercancel', (e) => { press = null; if (drag && e.pointerId === drag.pointer) end(true); });
  document.addEventListener('lostpointercapture', (e) => { if (drag && e.pointerId === drag.pointer) end(true); });
  document.addEventListener('keydown', (e) => { if (drag && e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); end(true); } }, true);
  document.addEventListener('click', (e) => { if (swallowClick) { swallowClick = false; e.stopPropagation(); e.preventDefault(); } }, true);
})();
