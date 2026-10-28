"""Entry points shared by the CLI, the launcher and the desktop app.

Both raise `LibraryPackageError`; its `kind` says why (see `errors.py`).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from bomgen.io.errors import InputError
from bomgen.io.loader import load_library
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.manifest import LIBRARY_FILE
from bomgen.library_store.store import ImportResult, LibraryStore, default_library_home


def validate_library(library_file: Path) -> None:
    """Check a library with the same loader the build uses."""
    try:
        load_library(library_file)
    except InputError as error:
        problems = "\n".join(
            f"  {replace(issue, file=Path(LIBRARY_FILE))}" for issue in error.issues
        )
        raise LibraryPackageError(
            f"{LIBRARY_FILE} fails validation:\n{problems}", RefusalKind.VALIDATION_FAILED
        ) from None


def import_library(
    package: Path, *, force: bool = False, dry_run: bool = False, store: LibraryStore | None = None
) -> ImportResult:
    """Verify, validate and install a `.bomlib` package into the user's store.

    With `dry_run` nothing is installed; the result shows what would change.
    """
    store = store or LibraryStore(default_library_home())
    if dry_run:
        return store.preview_import(package, force=force, validate=validate_library)
    return store.import_package(package, force=force, validate=validate_library)
