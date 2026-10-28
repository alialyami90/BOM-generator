"""Writer test helpers; a unique module name so other test areas' helpers never clash."""

import struct
import zlib
from collections.abc import Callable
from pathlib import Path

from openpyxl.workbook.workbook import Workbook

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
