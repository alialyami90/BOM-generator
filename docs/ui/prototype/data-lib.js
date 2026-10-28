/* Illustrative data for the v0.2 library editors: catalogues with brands, alternatives as library parts, pending changes.
   Shapes follow the plan for M13 (alternatives as parts linked by a group key; catalogue brands). Values are for judging layout. */
(function () {
  const hash = (s) => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);

  /* Alternatives are library parts. One group key links a device and its alternatives. */
  DB.altGroup = (d) => (d.alt ? 'ALT-' + d.id.replace(/[^A-Z0-9]/gi, '').slice(0, 8).toUpperCase() : '');
  DB.altList = (d) => {
    if (!d.alt) return [];
    const base = { id: d.id, tier: '—', make: d.make, model: d.model, w: d.w, inrush: d.inrush || Math.round(d.w * 0.35), ports: d.ds ? d.ds.ports.split(',')[0] : '', h: 1, verified: d.verified, self: true };
    const rows = [];
    d.alt.forEach((b) => b.rows.forEach((r) => {
      const h = hash(r.model);
      rows.push({ id: r.model, tier: r.tier, make: b.brand, model: r.model.replace(/^[A-Z]{3}-/, ''), w: Math.max(4, Math.round(d.w * (0.72 + (h % 7) * 0.07))), inrush: Math.round(d.w * (0.25 + (h % 5) * 0.06)), ports: base.ports, h: 1 + (h % 11 === 0 ? 1 : 0), verified: r.verified, self: false });
    }));
    const order = { Low: 0, Mid: 1, High: 2 };
    rows.sort((a, b) => order[a.tier] - order[b.tier] || a.make.localeCompare(b.make));
    return [base, ...rows];
  };

  DB.catalogues = {
    mcb: { title: 'Miniature circuit breakers', blurb: 'The engine sizes each MCB from the equipment it feeds and takes the ordering code for that rating from the brand chosen here.', kind: 'rating',
      cols: [['rating', 'Rating', 'A'], ['code', 'Ordering code']], active: 'schneider',
      brands: [
        { id: 'schneider', name: 'Schneider Acti9', detail: '2-pole, C curve', rows: [['1', 'A9F74201'], ['2', 'A9F74202'], ['6', 'A9F74206'], ['10', 'A9F74210'], ['16', 'A9F74216']] },
        { id: 'abb', name: 'ABB S200', detail: '2-pole, C curve', rows: [['1', '2CDS252001R0014'], ['2', '2CDS252001R0024'], ['6', '2CDS252001R0064'], ['10', '2CDS252001R0104'], ['16', '2CDS252001R0164']] },
        { id: 'siemens', name: 'Siemens 5SL6', detail: '2-pole, C curve', rows: [['1', '5SL62017RC'], ['2', '5SL62027RC'], ['6', '5SL62067RC'], ['10', '5SL62107RC'], ['16', '5SL62167RC']] }] },
    aux: { title: 'Auxiliary alarm contact', blurb: 'Fitted beside an MCB whose alarm is wired to the panel.', kind: 'aux',
      cols: [['model', 'Model'], ['code', 'Ordering code']], active: 'schneider',
      brands: [
        { id: 'schneider', name: 'Schneider', detail: 'for Acti9', rows: [['A9A26924', 'A9A26924']] },
        { id: 'abb', name: 'ABB', detail: 'for S200', rows: [['S2C-H6R', '2CDS200912R0001']] },
        { id: 'siemens', name: 'Siemens', detail: 'for 5SL', rows: [['5ST3010', '5ST3010']] }] },
    tb: { title: 'Terminal blocks', blurb: 'The block types the terminal strips use.', kind: 'block',
      cols: [['type', 'Type'], ['code', 'Ordering code']], active: 'phoenix',
      brands: [
        { id: 'phoenix', name: 'Phoenix Contact', detail: 'UT series', rows: [['UT-16', '3044199'], ['UT-2.5-MTD', '3064085'], ['UT-2.5-MT', '3046362']] },
        { id: 'weidmuller', name: 'Weidmüller', detail: 'W series', rows: [['WDU 16', '1020300000'], ['WDK 2.5', '1020500000'], ['WDU 2.5', '1020000000']] }] },
    bus: { title: 'Busbars', blurb: 'The grounding busbars a panel can carry.', kind: 'busbar',
      cols: [['description', 'Description'], ['tag', 'Tag']], active: 'rittal',
      brands: [{ id: 'rittal', name: 'Rittal', detail: 'SZ series', rows: [['AC safety ground busbar', 'AC-GND'], ['Instrument ground busbar', 'INST-GND']] }] },
    hk: { title: 'Housekeeping parts', blurb: 'The lamp, fan, filter, thermostat and the other small parts every cabinet carries. Each role points to a library part.', kind: 'role',
      cols: [['role', 'Role'], ['part', 'Part']], active: '', brands: [],
      roles: [['Lamp', 'SZ2500-LAMP'], ['Door switch', 'SZ4127-DOOR'], ['Fan', 'SK3243-FAN'], ['Vent filter', 'SK3238-FILTER'], ['Thermostat', 'SK3110-TH'], ['IPR kit', 'IPR-2903685'], ['Change-over diodes', 'DIODE-PAIR'], ['Socket', 'SK-SOCKET-10A']] }
  };

  /* A diff to review before it is applied. Each is { area, label, kind: added|changed|removed, from, to }. */
  DB.pending = [];
  DB.csvScenario = {
    file: 'psa-devices-2026-10-28.csv', size: '41 KB', tables: [['devices', 52, 'new part_id column present'], ['alternatives', 18, 'linked by alt_group']],
    checks: [['ok', 'All required columns are present'], ['ok', 'Every part_id is unique in the file'], ['ok', 'Every alt_group has at least two members'], ['bad', '2 rows have a problem and will be skipped (see below)']],
    errors: [['devices', 14, 'part_id', 'SEL-2730M-EXT is listed twice (rows 14 and 40). Keep one row.'], ['devices', 22, 'unit_power_w', '"approx 25" is not a number. Enter a number of watts, for example 25.']],
    added: [['SEL-2730M-EXT-B', 'New device']], changed: [['RST2228-L1-24MM', 'unit_power_w 77 → 79'], ['SEL-3555-GW', 'inrush_a empty → 18'], ['FGR-60F', 'ordering_code FGR-60F → FGR-60F-BDL'], ['SEL-2488', 'height_u empty → 1'], ['SK3243-FAN', 'unit_power_w 87 → 85']],
    removed: []
  };
})();
