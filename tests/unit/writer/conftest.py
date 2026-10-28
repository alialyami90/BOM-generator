"""Shared helpers for writer tests: write a model to tmp_path and reopen it with openpyxl."""

import struct
import zlib
from collections.abc import Callable
from pathlib import Path

import openpyxl
import pytest
from openpyxl.workbook.workbook import Workbook

from bomgen.models.sheet import SheetModel, WorkbookModel
from bomgen.writer import write_workbook

WriteAndOpen = Callable[..., Workbook]


def tiny_png(path: Path) -> Path:
    """Write a valid 1 x 1 pixel PNG to ``path``."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixels = zlib.compress(b"\x00\xff\x00\x00")
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")
    )
    return path


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
