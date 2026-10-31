CONSOLIDATED DEVICE LIBRARY
31 October 2026

START HERE
Consolidated-library.xlsx is the review workbook. devices.csv is the canonical
device table. device_ports.csv contains the canonical port inventory. Join all
technical tables by part_id. sources.csv is the full field-level evidence ledger.

MERGE RESULT
993 input device rows -> 991 unique devices.
Two repeated records removed: FGR-60F and FGR-70F.
81 input port rows -> 77 unique port groups.
22334 input evidence rows -> 18998 distinct references.
3336 byte-for-byte equivalent evidence rows (after PDF path rebasing)
are stored once. Every original occurrence remains mapped in source_lineage.csv.
82 unique PDFs, including both original project bundles, are in pdfs/.
All 25 technical tables and 28 original CSV templates are retained.

IDENTITY AND MERGE RULES
Exact part_id duplicates are matched against manufacturer and full ordering code.
Blank cells never overwrite populated values. Zero remains zero. Full ordering
codes preserve punctuation: Cisco spare SKUs ending in = remain distinct.
Configured assemblies remain separate from base catalogue SKUs. related_records.csv
explains the identified relationships; family matches alone are not duplicates.

The SEL-2730M device row was restored to SEL-2730M-EXT, the key already used by its
ports, evidence and original worklist for ordering code 2730M#2CF9. identity_aliases.csv
and device_lineage.csv preserve the old key and original row. No engineering values
were changed for this repair.

Four nonblank wording differences were resolved for the two FGR records: the more
detailed vendor model names and configuration descriptions are retained. All
alternative wording and its evidence remain in merge_conflicts.csv and sources.csv.
There are no unresolved conflicts between populated device values in this merge.
This does not resolve the engineering/configuration questions in the original notes.

SOURCE REFERENCES
All active pdf_file, source_pdf and pdf_path values resolve relative to this folder.
Original source pages, titles, document numbers, revisions, dates, URLs, evidence
bases, exact-part flags and notes are preserved. PDF page numbers are viewer pages
within the cited PDF; original bundle page numbers remain in their separate fields.
pdf_manifest.csv records SHA-256 hashes and page counts. pdf_aliases.csv maps original
filenames/paths to the deduplicated PDFs. No PDF content or page order was changed.
Source column names retain the source conventions (ports.N and device_ports[N].field).

TRACEABILITY
device_lineage.csv maps each original device row to its canonical identity.
field_lineage.csv identifies the selected input for each populated device value.
source_lineage.csv maps every original evidence row to its consolidated CSV row.
Row numbers are one-based including the header. Multiple original rows can map to
one retained evidence row. port_lineage.csv preserves repeated port row origins.
merge_duplicates.csv lists the removed device repetitions.

WORKLIST AND HISTORICAL CONTEXT
worklist-updated.csv is a separate tracking list, reconciled to canonical identities.
The SEL identity alias is collapsed; current nonblank library identity fields are
used, and already-populated requested fields are removed from matching missing lists.
The missing list is not a complete import checklist. worklist_coverage.csv identifies
127 tracking records outside the researched library. These are not added to devices.csv.
worklist_lineage.csv and documentation/delivery-2026-10-31-bundles/worklist-original.csv
preserve the original tracking entries. existing_matches.csv includes family and
external-worklist references; these are relationships, not additional device rows.
datasheet_manifest.csv and page_coverage.csv retain the original bundle section/page
accounting. Original notes, schemas and validation reports in documentation/ are
historical context. Their old file paths can be resolved using pdf_aliases.csv.
The current schema.json and VALIDATION.json describe this consolidated package.

IMPORT AND ORIGINAL LIMITATIONS
The original common CSV headers are unchanged. Technical tables and faster port
rates (2.5G, 5G and 25G) require importer support. Catalogue alternatives are not
project quantities or selected configurations. Manufacturer-configured order codes,
inrush data, supply choices and fitted optics still require the reviews described
in the original notes. The actual BOM application/importer was not available for
an import dry run. The review workbook mirrors the core and technical tables;
large evidence/provenance ledgers and the tracking worklist remain separate CSVs.

VALIDATION
Saved CSVs checked against prepared values and original headers; every input
source occurrence retained; all PDF hashes and page pointers verified; device,
port and evidence joins checked; all original populated device values either
retained or explicitly recorded in the wording audit; exported workbook values
checked against CSVs. See VALIDATION.json for counts and verification status.
