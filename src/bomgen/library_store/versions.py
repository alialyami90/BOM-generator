"""Library and app versions: MAJOR.MINOR.PATCH, with an optional ``+local.N`` (ADR 0018).

A local version is a library edited on this machine. It orders after its base and before
the next release: 1.0.0 < 1.0.0+local.1 < 1.0.1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

_VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\+local\.([1-9]\d*))?")


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int
    local: int = 0  # 0 for a release, else the N of ``+local.N``

    @classmethod
    def parse(cls, text: str) -> Version:
        match = _VERSION.fullmatch(text)
        if match is None:
            raise ValueError(
                f"invalid version {text!r}: expected MAJOR.MINOR.PATCH, e.g. 1.4.0,"
                " or 1.4.0+local.1 for a library edited here"
            )
        major, minor, patch, local = match.groups()
        return cls(int(major), int(minor), int(patch), int(local or 0))

    @property
    def is_local(self) -> bool:
        return self.local > 0

    @property
    def base(self) -> Version:
        """The release this version starts from (itself, for a release)."""
        return replace(self, local=0)

    def with_local(self, number: int) -> Version:
        return replace(self, local=number)

    def __str__(self) -> str:
        text = f"{self.major}.{self.minor}.{self.patch}"
        return f"{text}+local.{self.local}" if self.local else text
