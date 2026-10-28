"""Writer: a workbook replaces the file at the target path only once it is complete."""

from pathlib import Path

import openpyxl
import pytest
from xlsxwriter import Workbook
from xlsxwriter.exceptions import XlsxWriterException

from bomgen.models.sheet import SheetModel, WorkbookModel
from bomgen.writer import WriterError, write_workbook


def book(name: str) -> WorkbookModel:
    return WorkbookModel(sheets=(SheetModel(name=name),))


@pytest.fixture
def issued(out_path: Path) -> bytes:
    """A workbook already issued at the target path."""
    write_workbook(book("Issued"), out_path)
    return out_path.read_bytes()


def test_replaces_an_existing_workbook(out_path: Path, issued: bytes) -> None:
    assert write_workbook(book("New"), out_path) == out_path
    assert openpyxl.load_workbook(out_path).sheetnames == ["New"]
    assert [p.name for p in out_path.parent.iterdir()] == [out_path.name]


def test_failed_replace_keeps_the_issued_workbook(
    out_path: Path, issued: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The target is open in Excel or read-only: Windows refuses the replace.
    def refuse(src: object, dst: object) -> None:
        raise PermissionError(13, "Permission denied", str(dst))

    monkeypatch.setattr("bomgen.writer.xlsx.os.replace", refuse)
    with pytest.raises(WriterError, match="could not write") as error:
        write_workbook(book("New"), out_path)
    assert isinstance(error.value.__cause__, PermissionError)
    assert out_path.read_bytes() == issued
    assert [p.name for p in out_path.parent.iterdir()] == [out_path.name]


def test_failed_write_keeps_the_issued_workbook(
    out_path: Path, issued: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    # XlsxWriter fails while saving, after part of the file is on disk.
    close = Workbook.close

    def fail_after_writing(self: Workbook) -> None:
        close(self)
        raise XlsxWriterException("disk full")

    monkeypatch.setattr(Workbook, "close", fail_after_writing)
    with pytest.raises(WriterError, match="disk full"):
        write_workbook(book("New"), out_path)
    assert out_path.read_bytes() == issued
    assert [p.name for p in out_path.parent.iterdir()] == [out_path.name]
