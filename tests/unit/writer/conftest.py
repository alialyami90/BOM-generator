"""Writer test fixtures: write a model to tmp_path and reopen it with openpyxl."""

from pathlib import Path

import openpyxl
import pytest
from openpyxl.workbook.workbook import Workbook
from writer_helpers import WriteAndOpen

from bomgen.models.sheet import SheetModel, WorkbookModel
from bomgen.writer import write_workbook


@pytest.fixture
def out_path(tmp_path: Path) -> Path:
    return tmp_path / "out" / "book.xlsx"


@pytest.fixture
def write_and_open(out_path: Path) -> WriteAndOpen:
    """Write sheets (or a whole workbook model) and reopen the file with openpyxl."""

    def _write(*sheets: SheetModel | WorkbookModel, data_only: bool = False) -> Workbook:
        model = sheets[0] if isinstance(sheets[0], WorkbookModel) else None
        if model is None:
            model = WorkbookModel(sheets=tuple(s for s in sheets if isinstance(s, SheetModel)))
        write_workbook(model, out_path)
        return openpyxl.load_workbook(out_path, data_only=data_only)

    return _write
