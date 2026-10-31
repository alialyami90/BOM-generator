/* Illustrative data for the Parts page and Device preview (M22, part picking design).
   Shapes follow the M20 plan (equipment ordering_code, overrides, sfp; new roles and categories).
   Values are for judging layout only; the engine supplies the real ones. */
(function () {
  /* Library parts by category. h: height U, w: watts, supply, v: volts, ps: power supplies, inrush: A, load. */
  const P = (id, make, model, h, w, supply, v, ps, inrush, load) => ({ id, make, model, h, w, supply, v, ps, inrush, load });
  DB.partLib = {
    gps_clock: [P('SEL-2488', 'SEL', 'SEL-2488 satellite clock', 1, 15, 'DC', 125, 2, 20, 'continuous'), P('MBG-M3000', 'Meinberg', 'LANTIME M3000', 1, 30, 'DC', 125, 2, 8, 'continuous')],
    l2_switch: [P('RST2228-L2', 'Siemens', 'Ruggedcom RST2228', 1, 77, 'DC', 125, 2, 3, 'continuous'), P('SEL-2730M-L2', 'SEL', 'SEL-2730M', 1, 50, 'DC', 125, 2, 8, 'continuous')],
    l1_switch: [P('RST2228-L1-24MM', 'Siemens', 'Ruggedcom RST2228, 24 MM', 1, 77, 'DC', 125, 2, 3, 'continuous'), P('SEL-2730M-24', 'SEL', 'SEL-2730M, 24 ports', 1, 50, 'DC', 125, 2, 8, 'continuous')],
    workstation: [P('SEL-3355', 'SEL', 'SEL-3355 computer', 2, 150, 'DC', 125, 2, 17, 'continuous'), P('DELL-R250', 'Dell', 'PowerEdge R250', 1, 250, 'AC', 230, 1, 30, 'continuous')],
    kvm: [P('ATEN-CL5708', 'ATEN', 'CL5708 LCD KVM, 8 ports', 1, 25, 'AC', 230, 1, 3, 'continuous')],
    console: [P('ATEN-CL3000', 'ATEN', 'CL3000 LCD console', 1, 20, 'AC', 230, 1, 3, 'continuous')],
    annunciator: [P('NAP-K55', 'Ronan', 'X55 annunciator, 24 windows', 0, 12, 'DC', 125, 1, 2, 'continuous')],
    time_accessory: [P('SEL-9524-ANT', 'SEL', 'GPS antenna kit', 0, 0, null, null, 0, 0, null), P('RG6-30M', 'Belden', 'RG-6 antenna cable, 30 m', 0, 0, null, null, 0, 0, null), P('PTF-SURGE', 'PolyPhaser', 'Antenna surge arrester', 0, 0, null, null, 0, 0, null)],
    sfp: [P('SFP-1G-MM', 'Siemens', 'SFP991-1, 1G multi-mode', 0, 0, null, null, 0, 0, null), P('SFP-1G-SM', 'Siemens', 'SFP992-1, 1G single-mode', 0, 0, null, null, 0, 0, null), P('FS-SFP-1G-MM', 'FS', 'SFP-1G-SX-85, 1G multi-mode', 0, 0, null, null, 0, 0, null)],
    fibre_patch_panel: [P('FOPP-96SM', 'Corning', 'FOPP 96-core SM', 4, 0, null, null, 0, 0, null)],
    firewall: [P('FGR-60F', 'Fortinet', 'FortiGate Rugged 60F', 1, 24, 'DC', 125, 2, 10, 'continuous')],
    ext_switch: [P('SEL-2730M-EXT', 'SEL', 'SEL-2730M, external', 1, 50, 'DC', 125, 2, 8, 'continuous')],
    gateway: [P('SEL-3555-GW', 'SEL', 'SEL-3555 gateway', 3, 150, 'DC', 125, 2, 20, 'continuous')],
    rtac: [P('SEL-3555-RTAC', 'SEL', 'SEL-3555 RTAC', 3, 150, 'DC', 125, 2, 20, 'continuous')],
    io_rack: [P('AXION-IO-RACK', 'SEL', 'Axion I/O rack', 5, 40, 'DC', 125, 1, 5, 'continuous')],
    other: [P('SEL-2240', 'SEL', 'SEL-2240 Axion', 5, 40, 'DC', 125, 1, 5, 'continuous')]
  };
  DB.partCategories = [['fibre_patch_panel', 'Fibre patch panel'], ['firewall', 'Firewall'], ['ext_switch', 'External switch'], ['gateway', 'Gateway'], ['rtac', 'RTAC'], ['io_rack', 'I/O rack'], ['other', 'Other']];

  /* The Parts rows of GIS Substation 01, in equipment order. ov: overrides; pn: the BOM part number. */
  DB.partRows = () => [
    { key: 'gps', label: 'Time server clock', cat: 'gps_clock', part: 'SEL-2488', pn: 'SEL-2488-R1A1', qty: 1, ab: false, ov: {},
      acc: [{ part: 'SEL-9524-ANT', qty: 1 }, { part: 'RG6-30M', qty: 1 }] },
    { key: 'l2', label: 'L2 switch', cat: 'l2_switch', part: 'RST2228-L2', pn: '6GK6222-8AB00-5CC0', qty: 'sized', ab: true, ov: {},
      sfp: [{ speed: '1G', media: 'Multi-mode', need: 4, part: '' }] },
    { key: 'l1', label: 'L1 switch', cat: 'l1_switch', part: 'RST2228-L1-24MM', pn: '6GK6222-6AB00-5CC0', qty: 'sized', ab: true, ov: {},
      sfp: [{ speed: '1G', media: 'Multi-mode', need: 6, part: 'FS-SFP-1G-MM' }, { speed: '1G', media: 'Single-mode', need: 2, part: '' }] },
    { key: 'ows', label: 'Operator workstation', cat: 'workstation', part: 'SEL-3355', pn: 'SEL-3355-OWS-2026', qty: 1, ab: false, ov: { w: 180 } },
    { key: 'ews', label: 'Engineering workstation', cat: 'workstation', part: 'SEL-3355', pn: '', qty: 1, ab: false, ov: {} },
    { key: 'da', label: 'DA server', cat: 'workstation', part: 'DELL-R250', pn: 'R250-PSA-01', qty: 1, ab: true, ov: { h: 2, inrush: 45 } },
    { key: 'kvm', label: 'KVM', cat: 'kvm', part: 'ATEN-CL5708', pn: 'CL5708M-ATA-AG', qty: 1, ab: false, ov: {} },
    { key: 'console', label: 'Console', cat: 'console', part: 'ATEN-CL3000', pn: 'CL3000N-ATA-AG', qty: 1, ab: false, ov: {} },
    { key: 'ann', label: 'Annunciator', cat: 'annunciator', part: 'NAP-K55', pn: 'X55-24-125DC', qty: 1, ab: false, ov: {} },
    { key: 'fopp', label: 'Fibre patch panel', cat: 'fibre_patch_panel', part: 'FOPP-96SM', pn: 'FOPP-96SM', qty: 1, ab: true, ov: {}, added: true },
    { key: 'fw', label: 'Firewall', cat: 'firewall', part: 'FGR-60F', pn: 'FGR-60F-BDL-950-12', qty: 1, ab: true, ov: {}, added: true },
    { key: 'gw', label: 'Gateway', cat: 'gateway', part: 'SEL-3555-GW', pn: '', qty: 1, ab: true, ov: {}, added: true }
  ];
  DB.partBrands = { mcbAc: 'Schneider Acti9 iC60N', mcbDc: 'Schneider Acti9 C60H-DC', tb: 'Phoenix Contact UT' };
  DB.fineTuning = { ringMax: '6', l1Uplinks: '1', interlink: 'Yes', l3Uplinks: '2', portPercent: '20', dcBranches: '2', acBranches: '2', rackU: '4' };

  /* Device preview: one unit per row, as the engine would place it (top U counted from the bottom of the rack space). */
  const U = (tag, row, part, pn, top, h, w, supply, mcb1, mcb2, strip, extra = {}) => ({ tag, row, part, pn, top, h, w, supply, mcb1, mcb2, strip, ...extra });
  DB.preview = {
    waistMm: 1000, rackStartMm: 200, baseMm: 100, usableU: 32, rackU: 42,
    panels: [
      { n: 1, id: 'psa1', name: 'PSA Cabinet - 001', side: 'A', units: [
        U('PSA1-GPS-01', 'gps', 'SEL-2488', 'SEL-2488-R1A1', 32, 1, 15, '125 VDC', ['PSA1-F11', 2, 'min'], ['PSA1-F12', 2, 'min'], 'X1'),
        U('PSA1-L2-ESW-A01', 'l2', 'RST2228-L2', '6GK6222-8AB00-5CC0', 31, 2, 77, '125 VDC', ['PSA1-F13', 2], ['PSA1-F14', 2], 'X1', { cm: 1 }),
        U('PSA1-L1-ESW-A11', 'l1', 'RST2228-L1-24MM', '6GK6222-6AB00-5CC0', 29, 2, 77, '125 VDC', ['PSA1-F15', 2], ['PSA1-F16', 2], 'X1', { cm: 1 }),
        U('PSA1-L1-ESW-A12', 'l1', 'RST2228-L1-24MM', '6GK6222-6AB00-5CC0', 27, 2, 77, '125 VDC', ['PSA1-F17', 2], ['PSA1-F18', 2], 'X1', { cm: 1 }),
        U('PSA1-FW-A01', 'fw', 'FGR-60F', 'FGR-60F-BDL-950-12', 25, 2, 24, '125 VDC', ['PSA1-F19', 2, 'min'], ['PSA1-F20', 2, 'min'], 'X2', { cm: 1 }),
        U('PSA1-DA-A01', 'da', 'DELL-R250', 'R250-PSA-01', 23, 2, 250, '230 VAC', ['PSA1-Q31', 6], null, 'X3', { ov: ['h', 'inrush'] }),
        U('PSA1-KVM-01', 'kvm', 'ATEN-CL5708', 'CL5708M-ATA-AG', 19, 1, 25, '230 VAC', ['PSA1-Q32', 2, 'min'], null, 'X3', { kvm: true }),
        U('PSA1-OWS-01', 'ows', 'SEL-3355', 'SEL-3355-OWS-2026', 17, 2, 180, '125 VDC', ['PSA1-F21', 6], ['PSA1-F22', 6], 'X2', { ov: ['w'] }),
        U('PSA1-GW-A01', 'gw', 'SEL-3555-GW', 'SEL-3555-GW', 14, 3, 150, '125 VDC', ['PSA1-F23', 6], ['PSA1-F24', 6], 'X2', { nopn: true })] },
      { n: 2, id: 'psa2', name: 'PSA Cabinet - 002', side: 'B', units: [
        U('PSA2-L2-ESW-B01', 'l2', 'RST2228-L2', '6GK6222-8AB00-5CC0', 32, 2, 77, '125 VDC', ['PSA2-F13', 2], ['PSA2-F14', 2], 'X1', { cm: 1 }),
        U('PSA2-L1-ESW-B11', 'l1', 'RST2228-L1-24MM', '6GK6222-6AB00-5CC0', 30, 2, 77, '125 VDC', ['PSA2-F15', 2], ['PSA2-F16', 2], 'X1', { cm: 1 }),
        U('PSA2-L1-ESW-B12', 'l1', 'RST2228-L1-24MM', '6GK6222-6AB00-5CC0', 28, 2, 77, '125 VDC', ['PSA2-F17', 2], ['PSA2-F18', 2], 'X1', { cm: 1 }),
        U('PSA2-FW-B01', 'fw', 'FGR-60F', 'FGR-60F-BDL-950-12', 26, 2, 24, '125 VDC', ['PSA2-F19', 2, 'min'], ['PSA2-F20', 2, 'min'], 'X2', { cm: 1 }),
        U('PSA2-DA-B01', 'da', 'DELL-R250', 'R250-PSA-01', 24, 2, 250, '230 VAC', ['PSA2-Q31', 6], null, 'X3', { ov: ['h', 'inrush'] }),
        U('PSA2-CON-01', 'console', 'ATEN-CL3000', 'CL3000N-ATA-AG', 19, 1, 20, '230 VAC', ['PSA2-Q32', 2, 'min'], null, 'X3', { kvm: true }),
        U('PSA2-EWS-01', 'ews', 'SEL-3355', '', 17, 2, 150, '125 VDC', ['PSA2-F21', 6], ['PSA2-F22', 6], 'X2', { nopn: true }),
        U('PSA2-GW-B01', 'gw', 'SEL-3555-GW', 'SEL-3555-GW', 14, 3, 150, '125 VDC', ['PSA2-F23', 6], ['PSA2-F24', 6], 'X2', { nopn: true }),
        U('PSA2-ANN-01', 'ann', 'NAP-K55', 'X55-24-125DC', 0, 0, 0, '125 VDC', ['PSA2-F25', 2, 'min'], null, 'X4', { din: true, zero: false })] }
    ],
    issues: [
      { sev: 'warning', msg: 'Engineering workstation has no part number, so the BOM prints the library model SEL-3355.', row: 'ews' },
      { sev: 'warning', msg: 'Gateway has no part number, so the BOM prints the library model SEL-3555-GW.', row: 'gw' }
    ]
  };
})();
