/* Illustrative data for the prototype. Shapes follow the input schema work (A2), the library package work (A5)
   and the device-database records (A3). Values are for judging layout and density, not engineering truth. */
(function () {
  /* The open substation: what the first prototype called the project (its panels, constants and workbook). */
  const sub = {
    name: 'GIS Substation 01',
    titleLine: 'GIS Substation',
    path: 'D:\\Projects\\eastern-province\\substations\\gis01\\substation.yaml',
    savedAt: '10:02',
    sheetDocs: [
      { label: 'Power Consumption', key: 'gis01-power' },
      { label: 'Heat Dissipation', key: 'gis01-heat' },
      { label: 'Heat Calculations', key: 'gis01-heatcalc' }
    ],
    mainDoc: 'gis01-bom-1',
    output: { pattern: '{doc_no}_PSA_BOM_Rev{rev}.xlsx', fileName: 'DOC-0001-GIS01-001_PSA_BOM_Rev02.xlsx', sheets: ['Power Consumption', 'Heat Dissipation', 'Heat Calculations'] },
    constants: [
      { key: 'dc_voltage_v', label: 'DC supply voltage', value: '125', def: '125', unit: 'V' },
      { key: 'ac_voltage_v', label: 'AC supply voltage', value: '230', def: '230', unit: 'V' },
      { key: 'power_margin', label: 'Power margin', value: '0.25', def: '0.25', unit: '×' },
      { key: 'current_factor', label: 'Current factor', value: '1.3', def: '1.3', unit: '×' },
      { key: 'btu_per_w', label: 'Heat conversion', value: '3.41', def: '3.41', unit: 'BTU/h per W' },
      { key: 't_max_c', label: 'Maximum ambient', value: '35', def: '35', unit: '°C' },
      { key: 't_int_c', label: 'Internal limit', value: '25', def: '25', unit: '°C' },
      { key: 'air_constant', label: 'Air constant', value: '4.1', def: '4.1', unit: 'm³·K/Wh' },
      { key: 'steel_coefficient', label: 'Sheet-steel heat transfer', value: '5.5', def: '5.5', unit: 'W/m²·°C' },
      { key: 'min_main_mcb_a', label: 'Minimum main MCB', value: '6', def: '6', unit: 'A' }
    ],
    loose: [
      { part: 'NAP-K55', tag: '55" LCD Alarm Annunciator', qty: '1', fed: 'psa3', children: 'LPA37-696' },
      { part: 'ZENON-V12', tag: 'SRV/OAS - HMI Software', qty: '1', fed: '', children: '' },
      { part: 'MS-OFFICE-2021', tag: 'SRV/OAS - MS Office', qty: '1', fed: '', children: '' },
      { part: 'ANN-DISPLAY-CABLE-10M', tag: 'ANN - Display Cable', qty: '1', fed: '', children: '' },
      { part: 'FO-PATCH-CORDS', tag: 'FO', qty: '1 Lot', fed: '', children: '' }
    ]
  };

  /* Network inputs and the engine's NetworkPlan for them (literal values; the engine supplies them in the app). */
  sub.network = {
    iedCount: '40', topology: 'star', ringMax: '6',
    spares: { portPercent: '20', sfpPerL1: '3', dcBranches: '3', acBranches: '1', rackUReserved: '10' }
  };
  const networkPlan = {
    note: 'In a star, each L1 switch has one uplink to its L2 switch plus an A–B interlink.',
    sides: {
      A: { l1: 2, l1Usable: 20, l2: 1, l2Demand: 7, l2Usable: 20, links: 2 },
      B: { l1: 2, l1Usable: 20, l2: 1, l2Demand: 7, l2Usable: 20, links: 2 }
    }
  };
  /* Equipment: what the substation has, before any panel exists (substation.yaml equipment). */
  const equipment = [
    { id: 'fopp', part: 'FOPP-96SM', model: 'FOPP 96-core SM', label: 'FO patch panel', role: 'fopp', redundant: true, l2Ports: '', h: 4, count: 1, stem: 'FOPP-CCR', base: 1 },
    { id: 'l2', part: 'RST2228-L2', model: 'Ruggedcom RST-2228', label: 'L2 switch', role: 'l2_switch', redundant: true, l2Ports: '', h: 1, count: 1, stem: 'L2-ESW', base: 1 },
    { id: 'l1', part: 'RST2228-L1-24MM', model: 'Ruggedcom RST-2228 (24 MM)', label: 'L1 switch', role: 'l1_switch', redundant: true, l2Ports: '', h: 1, count: 2, stem: 'L1-ESW', base: 11 },
    { id: 'ext', part: 'SEL-2730M-EXT', model: 'SEL-2730M', label: 'External switch', role: 'ext_switch', redundant: true, l2Ports: '2', h: 1, count: 1, stem: 'EXT-ESW', base: 1 },
    { id: 'gw', part: 'SEL-3555-GW', model: 'SEL-3555', label: 'Gateway', role: 'other', redundant: true, l2Ports: '1', h: 1, count: 1, stem: 'DHPCC-GW', base: 1 },
    { id: 'fw', part: 'FGR-60F', model: 'FortiGate Rugged 60F', label: 'Firewall', role: 'firewall', redundant: true, l2Ports: '1', h: 1, count: 1, stem: 'EXT-FW', base: 1 },
    { id: 'gps', part: 'SEL-2488', model: 'SEL-2488', label: 'GPS clock', role: 'other', redundant: false, l2Ports: '1', h: 1, count: 1, stem: 'GPS', base: 1 },
    { id: 'rtac', part: 'SEL-3555-RTAC', model: 'SEL-3555 RTAC', label: 'Data concentrator', role: 'other', redundant: false, l2Ports: '2', h: 2, count: 1, stem: 'RTAC', base: 1 },
    { id: 'io1', part: 'AXION-IO-RACK', model: 'SEL Axion I/O rack', label: 'Axion I/O rack 1', role: 'other', redundant: true, l2Ports: '0', h: 12, count: 1, stem: 'HWIO', base: 1 },
    { id: 'io2', part: 'AXION-IO-RACK', model: 'SEL Axion I/O rack', label: 'Axion I/O rack 2', role: 'other', redundant: true, l2Ports: '0', h: 12, count: 1, stem: 'HWIO', base: 2 }
  ];
  const dinParts = { 1: 38, 2: 38, 3: 12, 4: 12 };

  /* Panels of the substation. Panels 1 to 4 are written by the layout engine; WS is hand-written (manual_panels). */
  const panels = [
    { id: 'psa1', n: 1, sheet: '1', cabinet: '861-GIS01-PSA-0001', name: 'PSA Cabinet - 001', prefix: 'PSA1', kind: 'network', side: 'A', pair: 1, generated: true, doc: 'gis01-bom-1', status: 'ok' },
    { id: 'psa2', n: 2, sheet: '2', cabinet: '861-GIS01-PSA-0002', name: 'PSA Cabinet - 002', prefix: 'PSA2', kind: 'network', side: 'B', pair: 1, generated: true, doc: 'gis01-bom-2', status: 'ok' },
    { id: 'psa3', n: 3, sheet: '3', cabinet: '861-GIS01-PSA-0003', name: 'PSA Cabinet - 003', prefix: 'PSA3', kind: 'network', side: 'A', pair: 2, generated: true, doc: 'gis01-bom-3', status: 'ok' },
    { id: 'psa4', n: 4, sheet: '4', cabinet: '861-GIS01-PSA-0004', name: 'PSA Cabinet - 004', prefix: 'PSA4', kind: 'network', side: 'B', pair: 2, generated: true, doc: 'gis01-bom-4', status: 'ok' },
    { id: 'ws', n: 0, sheet: '5', cabinet: '861-GIS01-PSA-0010', name: 'WS Console', prefix: 'WS', kind: 'console', side: '', pair: 0, generated: false, doc: 'gis01-bom-ws', status: 'bad' }
  ];
  const wsDevices = [
    { part: 'WS-HP-Z', model: 'HP Z2 Workstation', qty: 1, purpose: 'Server / operator workstation', hwio: '', tag: 'WS-SRV/OAS-1' },
    { part: 'MON-24', model: 'Dell P2422H', qty: 1, purpose: '', hwio: '', tag: 'WS-MONITOR-1' },
    { part: 'KB-MK120', model: 'Logitech MK120', qty: 1, purpose: '', hwio: '', tag: 'WS-KB-1' }
  ];

  /* Projects on this PC. Only the first substation of the first project carries full example data; the rest show the same screens. */
  const projects = [
    { id: 'ep132', name: 'Eastern Province 132 kV Programme (example)', client: 'Example Utility Co.', path: 'D:\\Projects\\eastern-province', logo: '',
      library: { name: 'psa-devices', builtWith: '1.3.2', active: '1.4.0' }, opened: 'Today 10:02', status: 'bad', statusText: '2 errors',
      substations: [
        { id: 'gis01', name: 'GIS Substation 01', folder: 'substations\\gis01', panels: 5, changed: 'Today 10:02', status: 'bad', statusText: '2 errors', from: '' },
        { id: 'gis02', name: 'GIS Substation 02', folder: 'substations\\gis02', panels: 4, changed: 'Yesterday', status: 'ok', statusText: 'Ready', from: 'GIS Substation 01' },
        { id: 'cb03', name: 'Control Building 03', folder: 'substations\\cb03', panels: 0, changed: '12 Oct', status: 'warn', statusText: 'Network not set up', from: '' }
      ],
      documents: [
        { key: 'gis01-bom-1', sub: 'gis01', label: 'PSA Cabinet - 001 BOM', docNo: 'DOC-0001-GIS01-001', rev: '02', issue: '2026-10-28', assumed: true, usedBy: 'Sheet 1' },
        { key: 'gis01-bom-2', sub: 'gis01', label: 'PSA Cabinet - 002 BOM', docNo: 'DOC-0001-GIS01-002', rev: '02', issue: '2026-10-28', assumed: true, usedBy: 'Sheet 2' },
        { key: 'gis01-bom-3', sub: 'gis01', label: 'PSA Cabinet - 003 BOM', docNo: 'DOC-0001-GIS01-003', rev: '01', issue: '2026-10-14', assumed: false, usedBy: 'Sheet 3' },
        { key: 'gis01-bom-4', sub: 'gis01', label: 'PSA Cabinet - 004 BOM', docNo: 'DOC-0001-GIS01-004', rev: '01', issue: '2026-10-14', assumed: false, usedBy: 'Sheet 4' },
        { key: 'gis01-bom-ws', sub: 'gis01', label: 'WS Console BOM', docNo: 'DOC-0001-GIS01-010', rev: '01', issue: '2026-10-14', assumed: false, usedBy: 'Sheet 5' },
        { key: 'gis01-power', sub: 'gis01', label: 'Power Consumption', docNo: 'DOC-0001-GIS01-020', rev: '00', issue: '2026-10-28', assumed: false, usedBy: 'Power sheet' },
        { key: 'gis01-heat', sub: 'gis01', label: 'Heat Dissipation', docNo: 'DOC-0001-GIS01-021', rev: '00', issue: '2026-10-28', assumed: false, usedBy: 'Heat sheet' },
        { key: 'gis01-heatcalc', sub: 'gis01', label: 'Heat Calculations', docNo: 'DOC-0001-GIS01-022', rev: '00', issue: '2026-10-28', assumed: false, usedBy: 'Heat calculations sheet' },
        { key: 'gis02-bom-1', sub: 'gis02', label: 'PSA Cabinet - 001 BOM', docNo: 'DOC-0001-GIS02-001', rev: '00', issue: '2026-10-21', assumed: false, usedBy: 'Sheet 1' },
        { key: 'gis02-bom-2', sub: 'gis02', label: 'PSA Cabinet - 002 BOM', docNo: 'DOC-0001-GIS02-002', rev: '00', issue: '2026-10-21', assumed: false, usedBy: 'Sheet 2' },
        { key: 'gis02-power', sub: 'gis02', label: 'Power Consumption', docNo: 'DOC-0001-GIS02-020', rev: '00', issue: '2026-10-21', assumed: false, usedBy: 'Power sheet' }
      ],
      defaults: [
        { label: 'Power margin', value: '0.25', unit: '×' },
        { label: 'Spare ports on each switch', value: '20', unit: '%' },
        { label: 'Rack space kept free', value: '10', unit: 'U' },
        { label: 'Spare DC branches per feed', value: '3', unit: 'per feed' },
        { label: 'Spare AC branches', value: '1', unit: '' }
      ],
      backups: [
        { file: 'eastern-province-2026-10-27-1640.bomproj', date: '2026-10-27 16:40', size: '412 KB', lib: 'psa-devices 1.3.2', note: 'Before the 1.4.0 library update' },
        { file: 'eastern-province-2026-10-20-0915.bomproj', date: '2026-10-20 09:15', size: '398 KB', lib: 'psa-devices 1.3.2', note: '' },
        { file: 'eastern-province-2026-10-02-1402.bomproj', date: '2026-10-02 14:02', size: '301 KB', lib: 'psa-devices 1.3.0', note: 'First issue' }
      ] },
    { id: 'sub-b', name: 'Substation B PSA upgrade', client: 'Example Utility Co.', path: 'D:\\Projects\\substation-b', logo: 'logo.png',
      library: { name: 'psa-devices', builtWith: '1.4.0', active: '1.4.0' }, opened: 'Yesterday', status: 'ok', statusText: 'Ready',
      substations: [{ id: 'b01', name: 'Substation B', folder: 'substations\\b01', panels: 3, changed: 'Yesterday', status: 'ok', statusText: 'Ready', from: '' }], documents: [], defaults: [], backups: [] },
    { id: 'training', name: 'Training example', client: 'Internal', path: 'C:\\Users\\Ali\\Documents\\bomgen-example', logo: '',
      library: { name: 'psa-devices', builtWith: '1.3.0', active: '1.4.0' }, opened: '12 Oct', status: 'warn', statusText: 'Library out of date',
      substations: [{ id: 't01', name: 'Training substation', folder: 'substations\\t01', panels: 4, changed: '12 Oct', status: 'warn', statusText: 'Library out of date', from: '' }], documents: [], defaults: [], backups: [] }
  ];

  const library = {
    name: 'psa-devices', version: '1.4.0', schema: 1, installed: '2026-10-20', notes: 'Adds firewall and external switch records; refreshes datasheet wattages.',
    versions: [
      { v: '1.4.0', date: '2026-10-20', active: true, notes: 'Adds firewall and external switch records; refreshes datasheet wattages.', projects: 1 },
      { v: '1.3.2', date: '2026-09-02', active: false, notes: 'Corrects the L1 switch ordering code suffix.', projects: 2 },
      { v: '1.3.0', date: '2026-07-14', active: false, notes: 'First release with alternative brands.', projects: 0 }
    ]
  };

  const alt = (brand, rows) => ({ brand, rows });
  const devices = [
    { id: 'FOPP-96SM', make: 'Corning', model: 'FOPP 96-core SM', cat: 'fibre_patch_panel', supply: '—', w: 0, verified: 'confirmed', alt: null },
    { id: 'RST2228-L2', make: 'Ruggedcom', model: 'RST-2228', cat: 'network_switch', supply: '125 VDC', w: 77, verified: 'confirmed', alt: null },
    { id: 'RST2228-L1-24MM', make: 'Ruggedcom', model: 'RST-2228 (24 MM)', cat: 'network_switch', supply: '125 VDC', w: 77, verified: 'confirmed',
      code: '6GK6222-6AB00-5CC0-Z A05+B05+C05+D05+E05+F05+G05', tagType: 'ESW', level: 'L1', power: 'Dual feed (2 supplies)', mcb: '2 A branch',
      ds: { supply: '88–300 VDC / 85–264 VAC', typical: '62 W', max: '77 W', ports: '24 × 100M MM (fixed), 4 × 1G SFP slots', dims: '483 × 270 × 44 mm (1U)', weight: '4.1 kg', temp: '−40 to +85 °C', certs: 'IEC 61850-3, IEEE 1613', url: 'datasheet link (illustrative)' },
      src: ['Manufacturer datasheet (revision 2026-03)', 'Project workbook'],
      alt: [
        alt('Hirschmann', [
          { tier: 'Low', model: 'HIR-RS20-2400M2', verified: 'confirmed' },
          { tier: 'Mid', model: 'HIR-RSP25-2400M4', verified: 'partial' },
          { tier: 'High', model: 'HIR-RSPE35-2400M4', verified: 'unverified' }]),
        alt('Moxa', [
          { tier: 'Low', model: 'MOX-PT-G7728-LOW', verified: 'confirmed' },
          { tier: 'Mid', model: 'MOX-PT-G7728-MID', verified: 'confirmed' },
          { tier: 'High', model: 'MOX-PT-G7828-HI', verified: 'partial' }])
      ] },
    { id: 'SEL-2730M-EXT', make: 'SEL', model: 'SEL-2730M', cat: 'network_switch', supply: '125 VDC', w: 23, verified: 'partial',
      code: '2730M-16-MM', tagType: 'ESW', level: 'EXT', power: 'Dual feed (2 supplies)', mcb: '2 A branch',
      ds: { supply: '125–250 VDC / 120–240 VAC', typical: '18 W', max: '23 W', ports: '16 × 100M MM, 4 × RJ45', dims: '483 × 215 × 44 mm (1U)', weight: '3.2 kg', temp: '−40 to +75 °C', certs: 'IEC 61850-3, IEEE 1613', url: 'datasheet link (illustrative)' },
      src: ['Manufacturer datasheet', 'Wattage from project workbook, not yet cross-checked'],
      alt: [
        alt('Hirschmann', [
          { tier: 'Low', model: 'HIR-GRS-1640-LOW', verified: 'unverified' },
          { tier: 'Mid', model: 'HIR-GRS-1640-MID', verified: 'confirmed' },
          { tier: 'High', model: 'HIR-GRS-1640-HI', verified: 'confirmed' }]),
        alt('Moxa', [
          { tier: 'Low', model: 'MOX-EDS-516-LOW', verified: 'partial' },
          { tier: 'Mid', model: 'MOX-PT-7520-MID', verified: 'unverified' },
          { tier: 'High', model: 'MOX-PT-7828-HI', verified: 'confirmed' }])
      ] },
    { id: 'SEL-3555-GW', make: 'SEL', model: 'SEL-3555', cat: 'gateway', supply: '125 VDC', w: 45, verified: 'confirmed',
      code: '3555-GW-A', tagType: 'GW', level: 'L2', power: 'Dual feed (2 supplies)', mcb: '2 A branch',
      ds: { supply: '125–250 VDC / 120–240 VAC', typical: '36 W', max: '45 W', ports: '4 × Ethernet, 4 × serial', dims: '483 × 305 × 133 mm (3U)', weight: '7.8 kg', temp: '−40 to +75 °C', certs: 'IEC 60255, IEEE 1613', url: 'datasheet link (illustrative)' },
      src: ['Manufacturer datasheet (revision 2026-05)'],
      alt: [
        alt('Moxa', [
          { tier: 'Low', model: 'MOX-MGate-LOW', verified: 'confirmed' },
          { tier: 'Mid', model: 'MOX-DA-720-MID', verified: 'partial' },
          { tier: 'High', model: 'MOX-DA-820C-HI', verified: 'unverified' }]),
        alt('Hitachi Energy', [
          { tier: 'Low', model: 'HE-COM600-LOW', verified: 'confirmed' },
          { tier: 'Mid', model: 'HE-COM600-MID', verified: 'confirmed' },
          { tier: 'High', model: 'HE-COM600-HI', verified: 'partial' }])
      ] },
    { id: 'FGR-60F', make: 'Fortinet', model: 'FortiGate Rugged 60F', cat: 'firewall', supply: '125 VDC', w: 24, verified: 'confirmed',
      code: 'FGR-60F', tagType: 'FW', level: 'EXT', power: 'Single feed via change-over diodes', mcb: '2 A branch, alarmed',
      ds: { supply: '9.6–60 VDC', typical: '19 W', max: '24 W', ports: '4 × 1G RJ45, 2 × SFP', dims: '216 × 160 × 45 mm', weight: '1.6 kg', temp: '−40 to +75 °C', certs: 'IEC 61850-3, IEEE 1613', url: 'datasheet link (illustrative)' },
      src: ['Manufacturer datasheet'],
      alt: [
        alt('Palo Alto', [
          { tier: 'Low', model: 'PAN-PA-220R-LOW', verified: 'unverified' },
          { tier: 'Mid', model: 'PAN-PA-220R-MID', verified: 'confirmed' },
          { tier: 'High', model: 'PAN-PA-450R-HI', verified: 'confirmed' }]),
        alt('Cisco', [
          { tier: 'Low', model: 'CIS-IR1101-LOW', verified: 'partial' },
          { tier: 'Mid', model: 'CIS-IR1833-MID', verified: 'unverified' },
          { tier: 'High', model: 'CIS-FPR1010E-HI', verified: 'confirmed' }])
      ] },
    { id: 'SEL-2488', make: 'SEL', model: 'SEL-2488', cat: 'time_sync', supply: '125 VDC', w: 12, verified: 'confirmed', alt: null },
    { id: 'SEL-3555-RTAC', make: 'SEL', model: 'SEL-3555 RTAC', cat: 'data_concentrator', supply: '125 VDC', w: 45, verified: 'confirmed', alt: null },
    { id: 'AXION-CHASSIS', make: 'SEL', model: 'SEL-2240 Axion', cat: 'io_chassis', supply: '125 VDC', w: 30, verified: 'partial', alt: null },
    { id: 'AXION-DI-MOD', make: 'SEL', model: 'SEL-2244-2', cat: 'io_module', supply: '—', w: 0, verified: 'partial', alt: null },
    { id: 'WS-HP-Z', make: 'HP', model: 'Z2 Workstation', cat: 'workstation', supply: '230 VAC', w: 160, verified: 'unverified', alt: null },
    { id: 'MON-24', make: 'Dell', model: 'P2422H', cat: 'monitor', supply: '230 VAC', w: 20, verified: 'unverified', alt: null },
    { id: 'FAN-716', make: 'Rittal', model: 'Filter fan 716 m³/h', cat: 'housekeeping', supply: '230 VAC', w: 60, verified: 'confirmed', alt: null },
    { id: 'TH-1', make: 'Rittal', model: 'Thermostat', cat: 'housekeeping', supply: '230 VAC', w: 2, verified: 'confirmed', alt: null }
  ];

  const importScenarios = {
    ok: { label: 'Update available (1.5.0)', file: 'psa-devices-1.5.0.bomlib', size: '184 KB', name: 'psa-devices', version: '1.5.0', active: '1.4.0', schema: '1', minApp: '0.1.0', created: '2026-10-27 16:40', notes: 'Adds the SEL-2740S switch and a 6 mm² terminal block. Updates SEL-3555 ordering code and L1 switch wattage. Removes the retired 48-core FOPP.',
      checks: [['ok', 'Checksums match for all 14 files'], ['ok', 'Library schema version 1 is supported'], ['ok', 'Needs app 0.1.0 or later; this is 0.2.0'], ['info', 'Signatures are not enabled for this install']],
      diff: { added: [['SEL-2740S-L2', 'SEL-2740S managed switch'], ['UT-6-MT', 'Terminal block 6 mm²'], ['FAN-AXIAL-120', 'Axial fan 120 mm']], changed: [['SEL-3555-GW', 'ordering_code, unit_power_w'], ['RST2228-L1-24MM', 'unit_power_w, description_template']], removed: [['FOPP-48SM', '48-core SM patch panel']], catalogues: ['terminal_blocks'], files: { added: ['data/device-db/housekeeping.yaml'], changed: ['data/device-db/network.yaml'], removed: [] } }, impact: 'The current project was built with 1.3.2. After import, rebuilding uses 1.5.0 and the check report will say so.' },
    downgrade: { label: 'Refused: older than installed', file: 'psa-devices-1.3.0.bomlib', size: '171 KB', name: 'psa-devices', version: '1.3.0', active: '1.4.0', schema: '1', minApp: '0.1.0', created: '2026-07-14 09:12', notes: 'First release with alternative brands.',
      checks: [['ok', 'Checksums match for all 12 files'], ['ok', 'Library schema version 1 is supported'], ['bad', 'Version 1.3.0 is older than the active 1.4.0']], refused: { title: 'This package is older than the installed library', body: 'Installing 1.3.0 would replace 1.4.0 and reverse its changes. To go back to an earlier version you already have, use Installed versions → Make active.', force: 'Install anyway (downgrade)' }, diff: { added: [], changed: [['SEL-3555-GW', 'ordering_code']], removed: [['SEL-2730M-EXT', 'External switch']], catalogues: [], files: { added: [], changed: [], removed: [] } } },
    tampered: { label: 'Refused: checksum mismatch', file: 'psa-devices-1.5.0.bomlib', size: '184 KB', name: 'psa-devices', version: '1.5.0', active: '1.4.0', schema: '1', minApp: '0.1.0', created: '2026-10-27 16:40', notes: '',
      checks: [['bad', 'data/device-db/network.yaml does not match its checksum'], ['info', 'Other checks were skipped']], refused: { title: 'The package was changed or damaged after it was built', body: 'The file data/device-db/network.yaml does not match the checksum in the manifest. Nothing was installed. Ask the sender for a new copy, or download it again.', force: null }, diff: null },
    schema: { label: 'Refused: needs a newer app', file: 'psa-devices-2.0.0.bomlib', size: '212 KB', name: 'psa-devices', version: '2.0.0', active: '1.4.0', schema: '2', minApp: '0.4.0', created: '2026-10-28 08:03', notes: 'New library schema with supplier pricing.',
      checks: [['ok', 'Checksums match for all 16 files'], ['bad', 'Library schema version 2 is not supported by this app (supports 1)'], ['bad', 'Needs app 0.4.0 or later; this is 0.2.0']], refused: { title: 'This package needs a newer version of the app', body: 'Install app 0.4.0 or later, then import this package again. Your current library is unchanged.', force: null }, diff: null },
    none: { label: 'No changes', file: 'psa-devices-1.4.0.bomlib', size: '181 KB', name: 'psa-devices', version: '1.4.0', active: '1.4.0', schema: '1', minApp: '0.1.0', created: '2026-10-20 11:30', notes: 'Adds firewall and external switch records; refreshes datasheet wattages.',
      checks: [['ok', 'Checksums match for all 13 files'], ['ok', 'Library schema version 1 is supported'], ['info', 'Same version as the active library']], refused: { title: 'This version is already installed', body: 'Version 1.4.0 is the active library and the package has the same contents. There is nothing to import.', force: 'Reinstall anyway' }, diff: { added: [], changed: [], removed: [], catalogues: [], files: { added: [], changed: [], removed: [] } } }
  };

  const problems = [
    { sev: 'error', file: 'substation.yaml', line: 18, where: 'GIS Substation 01 › Network › Equipment row 4', path: 'equipment[3].part_id', msg: 'SEL-2730M-EXT2 is not in library psa-devices 1.4.0.', fix: 'Did you mean SEL-2730M-EXT? Pick the device from the list or import a library that includes it.', route: '#/network' },
    { sev: 'error', file: 'panels/ws.yaml', line: 22, where: 'WS Console › Options', path: 'options.dc_spare_branches_per_feed', msg: 'Must be a whole number of 0 or more; found "two".', fix: 'Enter a number, for example 1.', route: '#/panels/ws/options' },
    { sev: 'warning', file: 'substation.yaml', line: 6, where: 'GIS Substation 01 › Network', path: 'network.ied_count', msg: 'The field IED count is an assumed value (marked # ASSUMED).', fix: 'Confirm the count from the single-line diagram. It sizes the L1 switches.', route: '#/network' },
    { sev: 'warning', file: 'project.yaml', line: 6, where: 'Project › Overview', path: 'library', msg: 'This project was built with psa-devices 1.3.2; 1.4.0 is active. 2 parts used here changed.', fix: 'Rebuild to use 1.4.0, or make 1.3.2 active under Library → Installed versions.', route: '#/project/info' },
    { sev: 'warning', file: 'project.yaml', line: 9, where: 'Project › Overview', path: 'project.logo', msg: 'No logo is set, so the workbook header will have no picture.', fix: 'Choose a PNG under Project → Overview.', route: '#/project/info' },
    { sev: 'warning', file: 'project.yaml', line: 31, where: 'Project › Documents', path: 'documents[0].issue_date', msg: 'The issue date of 2 documents is assumed (marked # ASSUMED).', fix: 'Confirm the dates before issuing.', route: '#/project/documents' }
  ];
  const engineChecks = [
    { name: 'SFPs match the port plans', detail: 'All 4 generated panels: 7 host switches, 29 SFPs.', result: 'pass' },
    { name: 'Main MCB covers the feed current', detail: 'Panels 1 to 4: 10 A calculated, 16 A set. Within the limit.', result: 'pass' },
    { name: 'Airflow covers the heat load', detail: '391 / 391 / 301 / 301 m³/h required, 716 m³/h per cabinet.', result: 'pass' },
    { name: 'Rack space per panel', detail: 'Panel 1: 22 of 32 U. Panels 3 and 4: 25 of 32 U. 10 U kept free in every panel.', result: 'pass' },
    { name: 'Digital inputs cover the hardwired points', detail: '40 points wired from panels 3 and 4; XDIN provides 40.', result: 'pass' }
  ];

  /* ---------- BOM rows (illustrative) ---------- */
  const mcb = (a) => ({ make: 'Schneider', model: 'Acti9 2P', code: 'A9F742' + String(a).padStart(2, '0') });
  function bomPsa(n, lan) {
    const P = 'PSA' + n, L = lan, rows = [];
    const add = (g, o) => rows.push(Object.assign({ g, tag: '', desc: '', qty: 1, make: '', model: '', code: '', hwio: '', span: 0, sr: rows.length + 1, gapBefore: 'EFGH'.includes(g) && rows.length > 0 && rows[rows.length - 1].g !== g }, o));
    add('A', { tag: 'PANEL', desc: 'Fixed frame, H2100 x D1000 x W800, top cable entry', make: 'Rawabi', model: 'Fixed Frame', code: 'Fixed Frame' });
    add('B', { tag: `${P}-FOPP-CCR-${L}01`, desc: 'FO patch panel 96 core SM (L2-L3 uplink to CCR)', make: 'Corning', model: 'FOPP-96SM', code: 'FOPP-96SM', span: 4 });
    add('B', { desc: 'Cable spool', make: 'Corning', model: 'SPOOL-1', code: 'SPOOL-1' });
    add('B', { desc: 'Splice holder', make: 'Corning', model: 'SH-1', code: 'SH-1' });
    add('B', { desc: 'LC SM pigtail', qty: 96, make: 'Corning', model: 'PIG-LC-SM', code: 'PIG-LC-SM' });
    add('B', { tag: `${P}-L2-ESW-${L}01`, desc: `LAN-${L} Industrial Ethernet switch (Level-2)`, make: 'Ruggedcom', model: 'RST-2228', code: '6GK6222-6AB00-5CC0-Z A05+B05+C05+D05+E05', hwio: 1 });
    add('B', { tag: `${P}-L1-ESW-${L}11 to ${L}12`, desc: `LAN-${L} Industrial Ethernet switch (Level-1) (24 MM FO ports)`, qty: 2, make: 'Ruggedcom', model: 'RST-2228', code: '6GK6222-6AB00-5CC0-Z A05+B05+C05+D05+E05+F05+G05', hwio: 10 });
    if (n === 1) {
      add('B', { tag: `${P}-GPS-1`, desc: 'GPS satellite-synchronised clock', make: 'SEL', model: 'SEL-2488', code: '2488-A', hwio: 1 });
      add('B', { tag: `${P}-RTAC-1`, desc: 'Data concentrator', make: 'SEL', model: 'SEL-3555', code: '3555-RTAC-A' });
    }
    add('B', { tag: `${P}-EXT-ESW-${L}`, desc: 'External-systems switch (16 MM + 4 RJ45)', make: 'SEL', model: 'SEL-2730M', code: '2730M-16-MM', hwio: 1 });
    add('B', { tag: `${P}-DHPCC-GW-${n}`, desc: 'Gateway for Dhahran PCC connection', make: 'SEL', model: 'SEL-3555', code: '3555-GW-A' });
    add('B', { tag: `${P}-EXT-FW-${L}`, desc: 'Firewall for external systems', make: 'Fortinet', model: 'FGR-60F', code: 'FGR-60F' });
    add('C', { tag: `L2-ESW-${L}01 SFP (SM)`, desc: '1000BASE-LX SM SFP', qty: 2, make: 'SEL', model: 'SEL-9524', code: 'SEL-9524' });
    add('C', { tag: `L2-ESW-${L}01 SFP (MM)`, desc: '1000BASE-SX MM SFP', qty: 15, make: 'SEL', model: 'SEL-9523', code: 'SEL-9523' });
    add('C', { tag: `L2-ESW-${L}01 SFP (MM)`, desc: '100BASE-FX MM SFP', qty: 2, make: 'SEL', model: 'SEL-9522', code: 'SEL-9522' });
    add('C', { tag: `L1-ESW-${L}11 to ${L}16 SFP (MM)`, desc: '1000BASE-SX MM SFP', qty: '=24+3', make: 'SEL', model: 'SEL-9523', code: 'SEL-9523' });
    add('C', { tag: `EXT-FW-${L} SFP (MM)`, desc: '1000BASE-SX MM SFP', qty: 2, make: 'SEL', model: 'SEL-9523', code: 'SEL-9523' });
    add('C', { tag: 'Cable Manager', desc: '1U cable manager', qty: 9, make: 'Rittal', model: 'CM-1U', code: 'CM-1U' });
    add('D', { tag: 'IL', desc: 'Cabinet lamp with door switch', make: 'Rittal', model: 'SZ 4100', code: 'SZ 4100' });
    add('D', { tag: 'FAN-1,2', desc: 'Filter fan, 716 m³/h', qty: 2, make: 'Rittal', model: 'FAN-716', code: 'FAN-716' });
    add('D', { tag: 'TH-1,2,3', desc: 'Thermostat', qty: 3, make: 'Rittal', model: 'TH-1', code: 'TH-1' });
    add('D', { tag: 'IPR', desc: 'Interposing relay (high-temperature alarm)', make: 'Phoenix Contact', model: 'REL-IR', code: 'REL-IR', span: 4 });
    add('D', { desc: 'Relay base', make: 'Phoenix Contact', model: 'REL-BASE', code: 'REL-BASE' });
    add('D', { desc: 'Suppression module', make: 'Phoenix Contact', model: 'REL-SUP', code: 'REL-SUP' });
    add('D', { desc: 'Mounting bracket', make: 'Phoenix Contact', model: 'REL-BRK', code: 'REL-BRK' });
    const cinc = n === 2 ? 16 : 6;
    add('E', Object.assign({ tag: `${P}-CINC`, desc: `${cinc}A,2P MCB For Incoming AC` }, mcb(cinc)));
    [['C1', 1, 'Lamp'], ['C2', 2, 'FAN-1 + TH-1'], ['C3', 2, 'FAN-2 + TH-2'], ['C4', 1, 'TH-3']].forEach(([c, a, d]) => add('E', Object.assign({ tag: `${P}-${c}`, desc: `${a}A,2P MCB For ${d}` }, mcb(a))));
    add('E', Object.assign({ tag: `${P}-C5`, desc: '2A,2P MCB (spare)' }, mcb(2)));
    add('E', { tag: 'Aux Contact', desc: 'AC MCB auxiliary contact', qty: 3, make: 'Schneider', model: 'A9A26924', code: 'A9A26924', hwio: 3 });
    ['Q1', 'Q2'].forEach((q, fi) => {
      add('F', Object.assign({ tag: `${P}-${q}`, desc: `16A,2P MCB For DC${fi + 1} Main`, hwio: 1 }, mcb(16)));
      const loads = ['L2_ESW_' + L + '01', ...[11, 12, 13, 14, 15, 16].map((k) => `L1_ESW_${L}${k}`), `EXT_ESW_${L}`, `DHPCC_GW_${n}`, `EXT_FW_${L}`];
      loads.forEach((ld, i) => add('F', Object.assign({ tag: `${P}-${q}.${i + 1}`, desc: `2A,2P MCB For ${ld} PS${fi + 1}` }, mcb(2))));
      for (let s = 11; s <= 13; s++) add('F', Object.assign({ tag: `${P}-${q}.${s}`, desc: '2A,2P MCB (spare)' }, mcb(2)));
    });
    add('F', { tag: 'Aux Contact', desc: 'DC MCB auxiliary contact', qty: 4, make: 'Schneider', model: 'A9A26924', code: 'A9A26924', hwio: 8 });
    [['X-AC', 'AC input', 6, 'UT-16', '3044199'], ['X3-AC', 'AC distribution', 12, 'UT-2.5-MTD', '3064085'], ['TBL', 'lighting', 4, 'UT-2.5-MTD', '3064085'], ['THF', 'fan and thermostat', 12, 'UT-2.5-MTD', '3064085'], ['XSD', 'smoke detector', 4, 'UT-2.5-MTD', '3064085'], ['X-DC1', 'DC1 input', 6, 'UT-16', '3044199'], ['X-DC2', 'DC2 input', 6, 'UT-16', '3044199'], ['X4-DC1', 'DC1 distribution', 32, 'UT-2.5-MTD', '3064085'], ['X4-DC2', 'DC2 distribution', 32, 'UT-2.5-MTD', '3064085'], ['XIP', 'inter-panel wiring', 40, 'UT-2.5-MT', '3046362']]
      .forEach(([t, d, q, m, c]) => add('G', { tag: `${P}-${t}`, desc: `Terminal Blocks For ${d}`, qty: q, make: 'Phoenix Contact', model: m, code: c }));
    add('H', { tag: 'AC SAFETY POWER-GROUND', desc: 'AC safety power-ground busbar' });
    add('H', { tag: 'INSTRUMENT-GROUND', desc: 'Instrument-ground busbar' });
    return rows;
  }
  function bomWs() {
    const rows = [], add = (g, o) => rows.push(Object.assign({ g, tag: '', desc: '', qty: 1, make: '', model: '', code: '', hwio: '', span: 0, sr: rows.length + 1, gapBefore: 'EFGH'.includes(g) && rows.length > 0 && rows[rows.length - 1].g !== g }, o));
    add('A', { tag: 'PANEL', desc: 'Console, H1600 x D636 x W800', make: 'Rittal', model: 'Console', code: 'Console' });
    add('B', { tag: 'WS-SRV/OAS-1', desc: 'Server / operator workstation', make: 'HP', model: 'Z2 Workstation', code: 'Z2-WS' });
    add('B', { tag: 'WS-MONITOR-1', desc: '24" monitor', make: 'Dell', model: 'P2422H', code: 'P2422H' });
    add('B', { tag: 'WS-KB-1', desc: 'Keyboard and mouse', make: 'Logitech', model: 'MK120', code: 'MK120' });
    add('D', { tag: 'IL', desc: 'Console lamp', make: 'Rittal', model: 'SZ 4100', code: 'SZ 4100' });
    add('D', { tag: 'FILTER', desc: 'Ventilation filter', qty: 2, make: 'Rittal', model: 'FILTER-1', code: 'FILTER-1' });
    add('D', { tag: 'TH-1', desc: 'Thermostat', make: 'Rittal', model: 'TH-1', code: 'TH-1' });
    add('E', Object.assign({ tag: 'WS-CINC', desc: '6A,2P MCB For Incoming AC' }, mcb(6)));
    add('E', Object.assign({ tag: 'WS-C1', desc: '1A,2P MCB For Lamp' }, mcb(1)));
    add('E', Object.assign({ tag: 'WS-C2', desc: '1A,2P MCB For TH-1' }, mcb(1)));
    add('E', Object.assign({ tag: 'WS-C3', desc: '1A,2P MCB (spare)' }, mcb(1)));
    add('E', { tag: 'Aux Contact', desc: 'AC MCB auxiliary contact', qty: 1, make: 'Schneider', model: 'A9A26924', code: 'A9A26924', hwio: 1 });
    add('G', { tag: 'WS-X-AC', desc: 'Terminal Blocks For AC input', qty: 4, make: 'Phoenix Contact', model: 'UT-16', code: '3044199' });
    add('G', { tag: 'WS-THF', desc: 'Terminal Blocks For fan and thermostat', qty: 5, make: 'Phoenix Contact', model: 'UT-2.5-MTD', code: '3064085' });
    add('H', { tag: 'INSTRUMENT-GROUND', desc: 'Instrument-ground busbar' });
    return rows;
  }
  /* Panels 3 and 4: the Axion I/O racks that did not fit in panels 1 and 2. */
  function bomIo(n, L) {
    const rows = [], add = (g, o) => rows.push(Object.assign({ g, tag: '', desc: '', qty: 1, make: '', model: '', code: '', hwio: '', span: 0, sr: rows.length + 1, gapBefore: 'EFGH'.includes(g) && rows.length > 0 && rows[rows.length - 1].g !== g }, o));
    const P = 'PSA' + n;
    add('A', { tag: 'PANEL', desc: 'Fixed frame, H2100 x D1000 x W800, top cable entry', make: 'Rawabi', model: 'Fixed Frame', code: 'Fixed Frame' });
    [1, 2].forEach((k) => {
      add('B', { tag: `${P}-HWIO-${k}`, desc: `Axion hardwired IO chassis (side ${L})`, make: 'SEL', model: 'SEL-2240', code: '2240-A', span: 5, hwio: k === 1 ? 1 : '' });
      add('B', { desc: 'Axion chassis', make: 'SEL', model: 'SEL-2241', code: '2241' });
      add('B', { desc: 'Axion CPU', make: 'SEL', model: 'SEL-2242', code: '2242' });
      add('B', { desc: 'Power coupler', qty: 2, make: 'SEL', model: 'SEL-2243', code: '2243' });
      add('B', { desc: 'DI module', qty: 4, make: 'SEL', model: 'SEL-2244-2', code: '2244-2' });
    });
    ['D', 'E', 'F', 'G'].forEach((s) => add('G', { tag: `${P}-XDIP${s}`, desc: `Terminal Blocks For knife-disconnect slot ${s}`, qty: 58, make: 'Phoenix Contact', model: 'UT-2.5-MT', code: '3046362' }));
    add('G', { tag: `${P}-XDIN`, desc: 'Terminal Blocks For DI negative', qty: 40, make: 'Phoenix Contact', model: 'UT-2.5-MT', code: '3046362' });
    add('H', { tag: 'AC SAFETY POWER-GROUND', desc: 'AC safety power-ground busbar' });
    add('H', { tag: 'INSTRUMENT-GROUND', desc: 'Instrument-ground busbar' });
    return rows;
  }

  /* Illustrative engine output for the Power and Heat sheets (Cabinet 1 sample).
     Every figure is a literal value. In M10 the engine supplies them; the UI only renders. */
  const power = {
    dc: { title: 'Power Consumption for Cabinet-1: DC load', volt: 125, type: 'VDC', load: 'CONTINUOUS', totalWithMargin: 403.75, rows: [
      { name: 'L2 switch', make: 'Ruggedcom', model: 'RST-2228', qty: 1, unitW: 77, totalW: 77, unitBtu: 262.57, totalBtu: 262.57 },
      { name: 'L1 switch (24 MM)', make: 'Ruggedcom', model: 'RST-2228', qty: 2, unitW: 77, totalW: 154, unitBtu: 262.57, totalBtu: 525.14 },
      { name: 'External switch', make: 'SEL', model: 'SEL-2730M', qty: 1, unitW: 23, totalW: 23, unitBtu: 78.43, totalBtu: 78.43 },
      { name: 'Gateway', make: 'SEL', model: 'SEL-3555', qty: 1, unitW: 45, totalW: 45, unitBtu: 153.45, totalBtu: 153.45 },
      { name: 'Firewall', make: 'Fortinet', model: 'FGR-60F', qty: 1, unitW: 24, totalW: 24, unitBtu: 81.84, totalBtu: 81.84 }] },
    ac: { title: 'Cabinet-1: AUX AC load', volt: 230, type: 'VAC', load: 'INTERMITTENT', totalWithMargin: 175.0, rows: [
      { name: 'Cabinet lamp', make: 'Rittal', model: 'SZ 4100', qty: 1, unitW: 9, totalW: 9, unitBtu: 30.69, totalBtu: 30.69 },
      { name: 'Fan', make: 'Rittal', model: 'FAN-716', qty: 2, unitW: 60, totalW: 120, unitBtu: 204.6, totalBtu: 409.2 },
      { name: 'Thermostat', make: 'Rittal', model: 'TH-1', qty: 3, unitW: 2, totalW: 6, unitBtu: 6.82, totalBtu: 20.46 },
      { name: 'Interposing relay', make: 'Phoenix Contact', model: 'REL-IR', qty: 1, unitW: 5, totalW: 5, unitBtu: 17.05, totalBtu: 17.05 }] },
    summary: { dcW: 2177.5, acW: 1090.3, totalW: 3267.8 }
  };
  const heat = { cabinet: 'Cabinet-1', totalW: 463, totalBtu: 1578.83, rows: [
      { name: 'L2 switch', make: 'Ruggedcom', model: 'RST-2228', qty: 1, unitW: 77, totalW: 77, unitBtu: 262.57, totalBtu: 262.57 },
      { name: 'L1 switch (24 MM)', make: 'Ruggedcom', model: 'RST-2228', qty: 2, unitW: 77, totalW: 154, unitBtu: 262.57, totalBtu: 525.14 },
      { name: 'External switch', make: 'SEL', model: 'SEL-2730M', qty: 1, unitW: 23, totalW: 23, unitBtu: 78.43, totalBtu: 78.43 },
      { name: 'Gateway', make: 'SEL', model: 'SEL-3555', qty: 1, unitW: 45, totalW: 45, unitBtu: 153.45, totalBtu: 153.45 },
      { name: 'Firewall', make: 'Fortinet', model: 'FGR-60F', qty: 1, unitW: 24, totalW: 24, unitBtu: 81.84, totalBtu: 81.84 },
      { name: 'Cabinet lamp', make: 'Rittal', model: 'SZ 4100', qty: 1, unitW: 9, totalW: 9, unitBtu: 30.69, totalBtu: 30.69 },
      { name: 'Fan', make: 'Rittal', model: 'FAN-716', qty: 2, unitW: 60, totalW: 120, unitBtu: 204.6, totalBtu: 409.2 },
      { name: 'Thermostat', make: 'Rittal', model: 'TH-1', qty: 3, unitW: 2, totalW: 6, unitBtu: 6.82, totalBtu: 20.46 },
      { name: 'Interposing relay', make: 'Phoenix Contact', model: 'REL-IR', qty: 1, unitW: 5, totalW: 5, unitBtu: 17.05, totalBtu: 17.05 }] };
  const hwioTotal = { psa1: 0, psa2: 0, psa3: 0, psa4: 0, ws: 0 };
  const bom = { psa1: bomPsa(1, 'A'), psa2: bomPsa(2, 'B'), psa3: bomIo(3, 'A'), psa4: bomIo(4, 'B'), ws: bomWs() };
  const groupNames = { A: 'Enclosure', B: 'Main equipment', C: 'Network and IO accessories', D: 'Cabinet housekeeping', E: 'AC distribution', F: 'DC distribution', G: 'Terminal blocks', H: 'Grounding' };

  window.DB = { sub, projects, equipment, networkPlan, dinParts, wsDevices, panels, library, devices, importScenarios, problems, engineChecks, bom, hwioTotal, power, heat, groupNames
  };
})();
