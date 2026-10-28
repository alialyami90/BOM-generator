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
  assets/logo.png       company logo for the page header
```

Schemas: `docs/plan.md` → "Input file schemas".
