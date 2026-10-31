PROJECT BUNDLE DEVICE LIBRARY - 31 OCTOBER 2026

958 device/component/catalogue-variant records have been prepared from the two supplied bundles. Six match the supplied worklist; 952 are absent from the supplied worklist and previous delivery. These are library choices, not 958 selected project requirements or BOM quantities. The complete current library was not present, so "new" means new to the supplied lists only.

40 datasheet sections are filed under ../Datasheets/<manufacturer>/. Both original bundles are preserved under ../Datasheets/Project Bundles/. All 485 pages are accounted for in page_coverage.csv: 479 extracted pages, 3 project cover/index pages, and 3 repeated trailing clock pages. The extracted pages retain their original content and dimensions. Older revisions are preserved as evidence and do not replace the previously researched 2026 documents.

FILES TO USE
worklist-updated.csv: supplied worklist plus prior delivery identities and the new records, deduplicated by part_id (1,111 rows). Original worklist identifiers are retained. Resolved requested fields are removed from the matching row's missing list. That list is not a complete import-validation checklist.
devices.csv: 958 records from THIS task, using the exact original 27-column contractor template. This is an incremental library dataset, not a replacement for the full existing library.
device_ports.csv: exact original template, with 30 port groups for the eight Fortinet models. The network_interfaces.csv extension preserves management/HA/data roles and shared-port notes.
sources.csv: exact original source template, with 21,617 field-level evidence records. Extension fields use table_name.column names. Alternative rating/variant rows may legitimately have more than one source for the same part and column.
templates/: 25 new technical CSV templates plus the three original common templates. All are header-only and have matching populated CSV files in this folder.
Device-library-review.xlsx: a readable copy of the common and technical tables. CSVs are the machine-readable delivery. The field-level evidence ledger, worklist and matching audit remain separate CSVs.
schema.json: column types, units, row counts and relationship cardinality. Blanks mean unknown, unselected or not applicable; never convert them automatically to zero.
device_review.csv: existing/new matches, catalogue-vs-device scope, ordering-code status and unresolved configuration notes.
existing_matches.csv: 12 further links to previously known devices/assemblies without overwriting newer or configuration-specific records.
datasheet_manifest.csv and validation.json: file/page inventory, checksums and validation results.

BOM INTEGRATION
1. Match on part_id first, then review normalized manufacturer plus ordering_code against the full library before creating a new identity. For existing identities, merge populated researched values only; do not replace unrelated fields with blanks or overwrite engineering decisions.
2. Join each technical table to devices by part_id. Most tables have one row per part. mcb_ratings, io_power_variants and network_interfaces are one-to-many. Their rows represent conditional ratings or interface groups, not additional physical devices.
3. Add the new category/column mappings to the BOM importer using schema.json. The original common headers are unchanged, but new categories and extension files are not automatically supported by an older importer. No BOM application or importer was available for an actual import run.
4. Select the required orderable configuration and project quantity. Catalogue alternatives, spare modules, pack quantities and references are not automatically selected for a project. Preserve the existing engineering columns: branch-MCB choices, alarm policy, tags, Purdue level and excluded_from_power remain blank in this research dataset.
5. Keep the package folder structure: source_pdf/pdf_file paths resolve relative to this delivery folder. sources.page is the page within the extracted datasheet; notes also state the original bundle and its PDF-viewer page.

TECHNICAL POINTS
- Fans: SK 3243.100 is 230 VAC with separate 50 Hz (70 W) and 60 Hz (87 W) data. Choose frequency before filling a common unit_power_w. Airflow depends on the filter/outlet arrangement. The 4 A pre-fuse is a manufacturer recommendation, not an assigned project branch breaker.
- Thermostats and passive components: contact ratings, terminal losses at rated current, and socket capacity are not independent continuous electrical loads.
- MCBs: 420 unique Hager references and 225 Schneider iC60N combinations. Hager ordering pages do not establish voltage, applicable breaking-capacity standard or DC applicability. Schneider AC Icn and voltage-dependent AC/DC Icu are kept separate. 1P+N is not treated as two protected poles. Actual DC pole wiring and application still require the manufacturer's installation instructions.
- Relay 2903685: coil is 230 VAC (179.4-317.4 VAC), not 125 VDC. The 16 A / 20 ms figure is contact-load inrush after the gold contact layer is destroyed; it is not coil/supply inrush. It is kept out of devices.inrush_a/inrush_ms.
- SZ2500-LAMP: the bundle contains SZ 2500.470 door-switch data, not SZ 2500.210 lamp data. A separate switch component was added without replacing the lamp assembly.
- NAP-F23: appears only in the UltraView family listing, with no F23-specific technical sheet. K55 ratings were not applied to it.
- SEL-2240: component burdens and channel counts are tabulated. A complete node requires a selected chassis, RTAC, coupler count/media and I/O mix. Sum module burdens once through the power coupler; account for its stated quiescent behavior. The family record has no invented total consumption or configured order code.
- SEL-2440: DC power and inrush are published as upper bounds (<20 W and <20 A). The bound operators are retained in the technical table. Interruption/ride-through times are not inrush durations.
- Servers and storage: PSU wattage is capacity, not consumption. Dell/HPE configuration-specific loads and ordering codes remain blank where absent. HPE SN3600B 8-port SKUs do not become 24 licensed ports; the 24-port/32G power condition is separate. Conflicting HPE printed metric dimensions were not imported.
- AEC CD-S-E-001: the image-only source specifies 130-360 VDC or 100-255 VAC and 330 W. Three independent inlets are not redundant PSUs. The 125 VDC nominal point is outside the published DC range. CD-H-F-001 is only an interface-level mention and has no borrowed mechanical/power ratings.
- Fortinet: shared RJ45/SFP ports are counted once in a fiber-selected planning layout. Cages do not imply fitted transceivers. Management and HA roles are preserved in the extension. AC PSU counts are stored in the technical table to preserve the earlier DC-only convention for devices.power_supplies.
- Cisco: explicit hardware SKU rows and separately ordered modules are catalogued. PSU/uplink/optics/licensing configurations and their consumption are not invented. Incidental software subscriptions, vendor comparison-table products and general advertising family mentions are retained in the source PDFs rather than treated as selected project devices.
- CyberView: the actual panel diagonal is 18.5 inches despite the 19-inch product label. Console-only maximum is 14 W; the KVM adds a separately specified maximum of 45 W. Configured power/keyboard options must be selected.
- Nozomi: virtual sensors are software records, without fabricated hardware power. Embedded-platform power is not an extra load if already included in the host chassis. Source maximum throughput is a published upper limit.

VALIDATION
Checked all saved CSV rows against the prepared data, exact original common headers, unique device/worklist IDs, foreign keys, blank engineering fields, evidence for every populated common/technical field, source page bounds, PDF hashes, and complete page accounting. Checked every Hager ordering line, all 225 Schneider matrix combinations, KVM SKU boundaries, and shared-port counts. Visually reviewed the extracted section starts and review-workbook sheets. The complete original library and actual BOM importer were unavailable, so full-library collision checking and application-level import validation remain open.
