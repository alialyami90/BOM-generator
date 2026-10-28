"""``bomgen build`` on the example project (plan M7): one workbook per substation."""

from pathlib import Path

import openpyxl
import pytest
from typer.testing import CliRunner

from bomgen.cli import app

pytestmark = pytest.mark.golden

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
# Output requirements (OUT-2): '<project doc no.>_PSA_BOM_Rev<rev>.xlsx'; the register's
# gis01-bom entry is VD-EL0009-861GISPSA-001 rev 02.
FILE_NAME = "VD-EL0009-861GISPSA-001_PSA_BOM_Rev02.xlsx"
SHEETS = ["1", "2", "3", "4", "Power Consumption", "Heat Dissipation", "Heat Calculations"]

runner = CliRunner()


@pytest.mark.parametrize(
    "args",
    [
        ["build", str(EXAMPLES / "project.yaml")],
        ["build", str(EXAMPLES / "project.yaml"), "--substation", "gis01"],
        ["build", str(EXAMPLES / "substations" / "gis01" / "substation.yaml")],
    ],
)
def test_build_writes_the_example_workbook(tmp_path: Path, args: list[str]) -> None:
    result = runner.invoke(app, [*args, "--out", str(tmp_path / "out")])
    assert result.exit_code == 0, result.output
    written = tmp_path / "out" / FILE_NAME
    assert result.stdout.strip() == str(written)
    assert openpyxl.load_workbook(written).sheetnames == SHEETS
