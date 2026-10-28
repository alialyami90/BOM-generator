# 0003. Write .xlsx with XlsxWriter, read back with openpyxl

- Status: Proposed (deviation from the brief; needs Ali's approval)
- Date: 2026-10-28
- Spec sections: Output requirements (page header, OUT-1, OUT-5, OUT-7); Formatting

## Context

The brief names `openpyxl` for writing, including "headers/footers incl. logo
image". The spec's page header puts the company logo in the left zone as an
`&G` picture on every printed sheet.

openpyxl cannot write header/footer pictures: it has no API for them and does
not emit the `legacyDrawingHF` VML part Excel needs (checked in openpyxl 3.1.5:
no reference to `legacyDrawingHF` anywhere in the package). Everything else the
spec needs (live formulas, styles, merges, hidden columns, print setup,
page-break preview, full recalculation on load) works in openpyxl.

XlsxWriter 3.x supports all of the above *and* header images
(`set_header('&L&G…', {'image_left': logo})`), page-break preview
(`set_page_view(2)`), repeat rows, fit-to-page, and `fullCalcOnLoad`. It is
write-only.

## Options

1. **XlsxWriter for writing, openpyxl for reading in tests** (recommended).
2. openpyxl for writing, then post-process the zip to inject the VML header
   drawing and image relationship by hand. Keeps one library but we own a fragile
   piece of OOXML plumbing that is exactly where "opens without a repair prompt"
   (OUT-1) breaks.
3. openpyxl without a logo. Fails the spec.

## Decision (proposed)

Option 1. The writer module is the only place that imports XlsxWriter; it
consumes library-agnostic sheet models (ADR 0005). Writer tests reopen the file
with openpyxl to assert formulas, styles, merges, print settings and
header/footer strings, and inspect the zip for the header image part.

## Consequences

- One extra runtime dependency (`XlsxWriter`, pure Python, BSD).
- openpyxl stays as a test/readback dependency (and for the OUT-8 revision
  comparison, which reads the previous issue).
- Swapping the writer later only touches `bomgen.writer`.
