"""Names that are safe to store in a package and to extract on Windows."""

from __future__ import annotations

import re
from collections.abc import Iterable

from bomgen.bundle.errors import LibraryPackageError

_WINDOWS_DEVICE = re.compile(r"(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?", re.IGNORECASE)


def is_safe_member(path: str) -> bool:
    """True if `path` is a plain relative POSIX path that is safe to extract on Windows too.

    Rejects anything that escapes the directory, and names Windows cannot create
    as ordinary files: device names, `:` (alternate data streams), trailing dots
    or spaces.
    """
    if not path or "\\" in path or path.startswith("/") or ":" in path:
        return False
    return all(is_safe_name(part) for part in path.split("/"))


def is_safe_name(part: str) -> bool:
    """True if `part` is one safe path component."""
    if part in ("", ".", "..") or "/" in part or part != part.rstrip(". "):
        return False
    return _WINDOWS_DEVICE.fullmatch(part) is None


def check_case_collisions(members: Iterable[str]) -> None:
    """Refuse names that differ only by case: Windows would merge them."""
    seen: dict[str, str] = {}
    for member in members:
        other = seen.setdefault(member.casefold(), member)
        if other != member:
            raise LibraryPackageError(
                f"{other!r} and {member!r} differ only by case; Windows would merge them"
            )
