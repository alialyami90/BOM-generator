# Example project

YAML inputs that reproduce the example project in the spec (PSA Cabinets 001–003,
WS Console 0010 and the loose-material list). They arrive with milestone M1:

```
examples/
  project.yaml          project settings, documents, design constants, loose extras
  library.yaml          device library + commodity catalogues
  panels/
    psa1.yaml           PSA Cabinet 001 (LAN-A)
    psa2.yaml           PSA Cabinet 002 (LAN-B, mirrors psa1)
    psa3.yaml           PSA Cabinet 003 (GPS, RTAC, Axion IO)
    ws.yaml             WS Console 0010
  assets/logo.png       company logo for the page header (not committed yet; add the PNG)
```

Schemas: `docs/plan.md` → "Input file schemas".

## Provenance

The files are transcribed from the example workbook the spec was written from (plan
Q1, ADR 0010 item 10). The workbook itself is not committed (`.xlsx` files are
git-ignored). BOM rows come from the hidden master sheets `Panel 1`, `Panel 2`,
`Panel 3` and `Aux`, unit watts from `Power Consumption` column I, and project and
document data from the page headers and footers. Comments next to values name the
workbook row or cell, and each panel device carries its workbook tag as a comment.

A trailing `# ASSUMED` marks a value the workbook does not give: the issue dates, the
logo (`assets/logo.png` is not committed yet: binary files are added separately) and the MCB family name. A `# NOTE:`
marks a workbook value the input models cannot hold exactly; the note gives the
workbook's text.

Workbook mistakes the generator corrects (plan Q22). The inputs describe the intended
cabinets; the generator writes the corrected values and the golden tests expect them:

- `Power Consumption`'s cabinet-1 AC rows reference cabinet 1's own BOM (the workbook
  points at `Panel 3` cells).
- The External Equipment DC row (the annunciator) divides by 125 V (the workbook
  divides by 230 V).
- `PSA2-XPS` uses UT-2.5-MTD code 3064085 (the workbook has 3064086).
- Panel 3's title reads 003 (the workbook's master says "PSA CABINET-001").
- The XRTAC-C1...C6 strips sit with the other group G strips before grounding (the
  workbook puts C3...C6 after the grounding rows).
- The WS console's QCOD branch MCBs are 2 A, code A9F74202 (the workbook text says 2A
  but uses the 1 A code A9F74201).

Open question (plan Q23): the issued sheets `1` and `2` differ from their masters in
three rows. The EXT switch is a Ruggedcom RST-2228 (`...E01+F00+G00`) instead of the
SEL-2730M, and the L2 switch's 1G and 100M MM SFPs are 18 and 6 instead of 15 and 2.
The examples follow the masters, which the Power Consumption sheet reads, until Ali
decides.
