/* STAND-IN for the engine. Not UI code.
   In the app the Python engine supplies `layout_preview(substation, overrides) -> LayoutResult` (A8, ADR 0013).
   This stub exists only so the Panels board can be tried in the prototype. It places devices the way the
   design describes (32 U usable, one blank plate between neighbours, A units in odd panels, B units in even
   panels, common devices in the first panel with room). The UI renders its result and never re-derives it. */
(function () {
  const CAPACITY = 32, RESERVED = 10;

  function units() {
    const out = [];
    DB.equipment.forEach((it, order) => {
      for (let i = 0; i < it.count; i++) {
        const pair = it.count > 1 ? `${it.id}.${i + 1}` : it.id;
        const name = it.count > 1 ? `${it.label} ${i + 1}` : it.label;
        if (it.redundant) ['A', 'B'].forEach((s) => out.push({ id: `${pair}.${s}`, pair, item: it.id, side: s, name, label: it.label, model: it.model, part: it.part, h: it.h, order: order * 10 + i, stem: it.stem, num: it.base + i, redundant: true }));
        else out.push({ id: pair, pair: '', item: it.id, side: '', name, label: it.label, model: it.model, part: it.part, h: it.h, order: order * 10 + i, stem: it.stem, num: it.base + i, redundant: false });
      }
    });
    return out;
  }

  const cost = (list, extra) => { const all = extra ? list.concat([extra]) : list; return all.reduce((a, u) => a + u.h, 0) + Math.max(0, all.length - 1); };

  /* overrides: [{ pair: 'l1.2', pairIndex: 2 } | { unit: 'l1.2.A', panel: 3 }], removed: [unit or pair ids] */
  function layoutPreview(overrides = [], removed = []) {
    const all = units().filter((u) => !removed.includes(u.id) && !removed.includes(u.pair || u.id));
    const placed = {}; // unit id -> panel n
    const load = {};   // panel n -> unit list
    const errors = [];
    const put = (u, n) => { placed[u.id] = n; (load[n] = load[n] || []).push(u); };
    const moved = new Set();
    all.sort((a, b) => a.order - b.order).forEach((u) => {
      for (let pi = 1; pi < 20; pi++) {
        const a = 2 * pi - 1, b = 2 * pi;
        if (u.redundant) {
          if (u.side === 'B') continue;
          const partner = all.find((x) => x.pair === u.pair && x.side === 'B');
          if (cost(load[a] || [], u) <= CAPACITY && cost(load[b] || [], partner) <= CAPACITY) { put(u, a); put(partner, b); break; }
        } else if (cost(load[a] || [], u) <= CAPACITY) { put(u, a); break; }
      }
    });
    /* Overrides are applied after the automatic fill. A move that does not fit is an error, never a silent reflow. */
    const relocate = (u, n) => { load[placed[u.id]] = load[placed[u.id]].filter((x) => x.id !== u.id); put(u, n); moved.add(u.id); };
    overrides.forEach((o) => {
      if (o.pair) all.filter((u) => u.pair === o.pair).forEach((u) => relocate(u, 2 * o.pairIndex - (u.side === 'A' ? 1 : 0)));
      else if (o.unit) { const u = all.find((x) => x.id === o.unit); if (u) relocate(u, o.panel); }
    });
    const maxN = Math.max(4, ...Object.keys(load).map(Number));
    const count = maxN % 2 ? maxN + 1 : maxN;
    const panels = [];
    for (let n = 1; n <= count; n++) {
      const list = (load[n] || []).sort((a, b) => a.order - b.order || (a.side < b.side ? -1 : 1));
      const used = list.length ? cost(list) : 0;
      if (used > CAPACITY) errors.push(`Panel ${n} needs ${used} U, only ${CAPACITY} U may be used.`);
      const meta = DB.panels.find((p) => p.n === n);
      panels.push({
        n, id: meta ? meta.id : 'psa' + n, name: meta ? meta.name : `PSA Cabinet - ${String(n).padStart(3, '0')}`, prefix: meta ? meta.prefix : 'PSA' + n,
        side: n % 2 ? 'A' : 'B', pair: Math.ceil(n / 2), capacity: CAPACITY, reserved: RESERVED, used, free: CAPACITY - used, plates: Math.max(0, list.length - 1), din: DB.dinParts[n] || 0,
        devices: list.map((u) => ({ id: u.id, pair: u.pair, name: u.name, model: u.model, part: u.part, h: u.h, side: u.side, redundant: u.redundant, moved: moved.has(u.id),
          tag: `${(meta ? meta.prefix : 'PSA' + n)}-${u.stem}${u.redundant ? '-' + u.side : '-'}${String(u.num).padStart(2, '0')}` }))
      });
    }
    return { panels, errors };
  }

  /* Would this move fit? Returns { ok, reason } without changing anything. */
  function canMove(move, overrides, removed) {
    const trial = overrides.filter((o) => !(move.pair ? o.pair === move.pair : o.unit === move.unit)).concat([move]);
    const r = layoutPreview(trial, removed);
    return { ok: r.errors.length === 0, reason: r.errors[0] || '', result: r, overrides: trial };
  }

  window.Engine = { layoutPreview, canMove, units, CAPACITY, RESERVED };
})();
