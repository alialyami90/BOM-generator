"""Errors raised by the package code (`.bomlib` libraries and `.bomproj` projects).

Every refusal is a `LibraryPackageError` whose `kind` says why, so a caller
(the CLI today, the desktop app's import screen in M10) can choose its wording
or offer a remedy without parsing the message:

- `INVALID_PACKAGE`: not a usable `.bomlib` (bad zip, tampered, unsafe paths).
- `INCOMPATIBLE`: a valid package this bomgen cannot read (newer schema,
  format or `min_app_version`).
- `VALIDATION_FAILED`: the library inside fails schema validation.
- `DOWNGRADE`, `ALREADY_INSTALLED`: refused unless forced.
- `NOT_INSTALLED`: the named library or version is not in the store.
- `STORE_DAMAGED`: the installed store is unreadable (for example a corrupt
  `active` file).
"""

from __future__ import annotations

from enum import StrEnum


class RefusalKind(StrEnum):
    INVALID_PACKAGE = "invalid_package"
    INCOMPATIBLE = "incompatible"
    VALIDATION_FAILED = "validation_failed"
    DOWNGRADE = "downgrade"
    ALREADY_INSTALLED = "already_installed"
    NOT_INSTALLED = "not_installed"
    STORE_DAMAGED = "store_damaged"


class LibraryPackageError(Exception):
    """A package or installed library is invalid, or an operation on it was refused."""

    def __init__(self, message: str, kind: RefusalKind = RefusalKind.INVALID_PACKAGE) -> None:
        super().__init__(message)
        self.kind = kind
