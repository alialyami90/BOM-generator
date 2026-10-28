"""Library and app versions: MAJOR.MINOR.PATCH, compared numerically."""

from __future__ import annotations

import re
from dataclasses import dataclass

_VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> Version:
        match = _VERSION.fullmatch(text)
        if match is None:
            raise ValueError(f"invalid version {text!r}: expected MAJOR.MINOR.PATCH, e.g. 1.4.0")
        major, minor, patch = (int(part) for part in match.groups())
        return cls(major, minor, patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
