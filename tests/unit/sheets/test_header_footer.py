"""Page header and footer (spec: Output requirements → header and footer)."""

from datetime import date
from pathlib import Path

from bomgen.models.panel import DocumentInfo
from bomgen.models.sheet import HFZone, Margins
from bomgen.sheets import styles
from bomgen.sheets.header_footer import (
    BOM_SIZE,
    CALC_MAX_SIZE,
    bom_header_footer,
    calc_header_footer,
    fitting_size,
)

DOC = DocumentInfo(doc_no="VD-EL0009-861GISPSA-001", rev="02", issue_date=date(2026, 10, 28))
LOGO = Path("logo.png")


def texts(zone: HFZone) -> list[str]:
    return ["".join(run.text for run in line) for line in zone.lines]


def test_bom_header_names_project_cabinet_and_document() -> None:
    hf = bom_header_footer("JAFURAH", "861-GIS01-PSA-0001", DOC, LOGO)
    assert hf.header_left.image == LOGO
    assert texts(hf.header_center) == [
        "JAFURAH",
        "Bill of Materials for 861-GIS01-PSA-0001",
        "Supplier Doc # VD-EL0009-861GISPSA-001",
    ]
    assert texts(hf.header_right) == ["Rev : 02"]


def test_footer_has_document_page_count_and_revision_date() -> None:
    hf = bom_header_footer("JAFURAH", "861-GIS01-PSA-0001", DOC, LOGO)
    assert texts(hf.footer_left) == ["VD-EL0009-861GISPSA-001"]
    page = hf.footer_center.lines[0]
    assert [run.field or run.text for run in page] == ["Page ", "page", " of ", "pages"]
    assert texts(hf.footer_right) == ["Rev 02 \N{EN DASH} 2026-10-28"]


def test_only_the_project_name_is_bold_and_every_run_has_the_sheet_size() -> None:
    hf = bom_header_footer("JAFURAH", "861-GIS01-PSA-0001", DOC, LOGO)
    zones = (*hf.header_zones, *hf.footer_zones)
    runs = [run for zone in zones for line in zone.lines for run in line]
    assert {run.size for run in runs} == {BOM_SIZE}
    assert [run.text for run in runs if run.bold] == ["JAFURAH"]


def test_no_logo_means_no_picture() -> None:
    hf = bom_header_footer("JAFURAH", "861-GIS01-PSA-0001", DOC, None)
    assert all(zone.image is None for zone in (*hf.header_zones, *hf.footer_zones))


def test_calc_header_uses_its_title_and_size() -> None:
    hf = calc_header_footer("JAFURAH", "Power Consumption for GIS01", DOC, LOGO, 17)
    assert texts(hf.header_center)[1] == "Power Consumption for GIS01"
    assert {run.size for line in hf.header_center.lines for run in line} == {17}


def test_calc_header_size_fits_three_scaled_lines_in_the_top_margin() -> None:
    # 1.9 cm top, 0.8 cm header: 31.2 pt of room for three lines at 1.2 line spacing.
    assert fitting_size(styles.CALC_MARGINS, 49) == 17
    assert fitting_size(styles.CALC_MARGINS, 50) == 17
    assert fitting_size(styles.CALC_MARGINS, 78) == 11


def test_calc_header_size_is_capped() -> None:
    roomy = Margins(top_cm=5.0)
    assert fitting_size(roomy, 49) == CALC_MAX_SIZE
    assert fitting_size(Margins(top_cm=0.9), 400) == 1
