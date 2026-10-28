"""The example project's step 15 check report (spec: Data model and generation order,
step 15; plan M7, Q3)."""

from pathlib import Path

import pytest

from bomgen.checks import check_report
from bomgen.engine.pipeline import build
from bomgen.io.loader import load_substation
from bomgen.models.report import CheckReport, CheckStatus

pytestmark = pytest.mark.golden

SUBSTATION_FILE = (
    Path(__file__).resolve().parents[2] / "examples" / "substations" / "gis01" / "substation.yaml"
)


@pytest.fixture(scope="module")
def report() -> CheckReport:
    loaded = load_substation(SUBSTATION_FILE)
    return check_report(loaded, build(loaded))


def statuses(report: CheckReport, check: str) -> dict[str | None, CheckStatus]:
    return {item.panel_id: item.status for item in report.items if item.check == check}


def test_the_example_has_no_failed_check(report: CheckReport) -> None:
    assert not report.failed


def test_design_current_per_cabinet(report: CheckReport) -> None:
    # DC distribution: ΣQ ≈ 7.1 A in cabinets 001 and 002, ≈ 1.5 A in 003 and the console.
    current = {
        item.panel_id: item.values["design_current_a"]
        for item in report.items
        if item.check == "dc_main"
    }
    assert current == {
        "psa1": pytest.approx(7.1, abs=0.05),
        "psa2": pytest.approx(7.1, abs=0.05),
        "psa3": pytest.approx(1.5, abs=0.05),
        "ws": pytest.approx(1.5, abs=0.05),
    }


def test_16a_mains_of_001_and_002_differ_from_the_rule(report: CheckReport) -> None:
    # DC distribution: Q1/Q2 are 16 A in the workbook where the rule gives 10 A (Q3).
    mains = {
        i.panel_id: (i.status, i.values["rating_a"]) for i in report.items if i.check == "dc_main"
    }
    assert mains == {
        "psa1": (CheckStatus.WARN, 16),
        "psa2": (CheckStatus.WARN, 16),
        "psa3": (CheckStatus.PASS, 6),
        "ws": (CheckStatus.PASS, 6),
    }


def test_fans_and_natural_convection_pass(report: CheckReport) -> None:
    # Heat Calculations: 391, 391 and 172 m³/h against 716; the console's ΔT 6.96 °C.
    assert statuses(report, "airflow") == dict.fromkeys(("psa1", "psa2", "psa3"), CheckStatus.PASS)
    assert statuses(report, "natural_convection") == {"ws": CheckStatus.PASS}
    assert statuses(report, "line_up") == {None: CheckStatus.PASS}


def test_di_capacity_covers_the_hwio_total(report: CheckReport) -> None:
    # 'Panel 3': four 24 DI cards (SEL-2244-2) for 17 + 17 + 6 HWIO points.
    (item,) = [i for i in report.items if i.check == "di_capacity"]
    assert (item.status, item.values) == (CheckStatus.PASS, {"di_inputs": 96, "hwio": 40})


def test_sfps_fit_the_switch_slots(report: CheckReport) -> None:
    sfp = [(i.panel_id, i.subject, i.status) for i in report.items if i.check == "sfp_slots"]
    assert [s for s in sfp if s[2] is CheckStatus.FAIL] == []
    # The firewall's two SFP slots take its two downlink SFPs ('Panel 1' row 17).
    assert {s[2] for s in sfp if "FW" in (s[1] or "")} == {CheckStatus.PASS}
