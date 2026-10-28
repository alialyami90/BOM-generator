"""Save an edited library as a local version of an installed one (ADR 0018).

A local version is `<base>+local.<n>`. It carries the base version's other files unchanged
(for example `device-db/`), keeps the base installed for rollback, and becomes the active
version. The edits come from the edit operations or a CSV import; this module only saves.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import yaml

from bomgen.bundle.container import sha256
from bomgen.io.errors import InputError
from bomgen.io.loader import load_library
from bomgen.library_store.diff import LibraryDiff, diff_libraries, parse_library
from bomgen.library_store.edit import Insert, Remove, SetValue, apply_edits
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.manifest import FORMAT_VERSION, LIBRARY_FILE, Manifest
from bomgen.library_store.package import PackageContents
from bomgen.library_store.service import validate_library
from bomgen.library_store.store import LibraryStore
from bomgen.library_store.versions import Version
from bomgen.models.library import Library


@dataclass(frozen=True)
class LocalSave:
    """The version written, the version it started from, and what changed against it."""

    manifest: Manifest
    previous: str
    diff: LibraryDiff


def dump_library(library: Library) -> bytes:
    """The `library.yaml` bytes of a library; loading them again gives an equal library."""
    data = library.model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).encode("utf-8")


def save_local_version(
    store: LibraryStore,
    name: str,
    library: Library,
    *,
    base: str | None = None,
    note: str = "",
) -> LocalSave:
    """Install `library` as the next local version of `name` and make it active.

    `base` is the installed version the edits started from (default: the active one). Raises
    `LibraryPackageError` with `NO_CHANGES` when `library` equals the base, and with
    `VALIDATION_FAILED` when it fails the loader's checks; the store is untouched either way.
    """
    base = base or store.active_version(name)
    if base is None:
        raise LibraryPackageError(f"library {name} is not installed", RefusalKind.NOT_INSTALLED)
    base_contents = store.read_version(name, base)
    try:
        base_library = load_library(store.library_file(name, base))
    except InputError as exc:
        raise LibraryPackageError(
            f"library {name} {base}: the installed library is damaged", RefusalKind.STORE_DAMAGED
        ) from exc

    # Compare dumps of both, so defaults the base file leaves out do not show as edits.
    old_bytes = dump_library(base_library)
    new_bytes = dump_library(library)
    old_files = {**base_contents.manifest.files, LIBRARY_FILE: sha256(old_bytes)}
    files = {**base_contents.files, LIBRARY_FILE: new_bytes}
    digests = {member: sha256(data) for member, data in sorted(files.items())}
    new_library = parse_library(new_bytes)
    diff = diff_libraries(parse_library(old_bytes), new_library, old_files, digests)
    if diff.is_empty:
        raise LibraryPackageError(
            f"library {name}: nothing differs from {base}", RefusalKind.NO_CHANGES
        )

    manifest = Manifest(
        format_version=FORMAT_VERSION,
        name=name,
        version=str(_next_local(store, name, Version.parse(base))),
        schema_version=base_contents.manifest.schema_version,
        min_app_version=base_contents.manifest.min_app_version,
        release_notes=_release_notes(base, diff, note),
        created=datetime.now(UTC).replace(microsecond=0),
        files=digests,
    )
    store.install(PackageContents(manifest, files, new_library), validate=validate_library)
    return LocalSave(manifest, base, diff)


def save_edits(
    store: LibraryStore,
    name: str,
    edits: Sequence[SetValue | Insert | Remove],
    *,
    base: str | None = None,
    note: str = "",
) -> LocalSave:
    """Apply `edits` to the installed version `base` (default: the active one) and save the result.

    Problems with the edits come back as one `VALIDATION_FAILED` refusal listing each; the
    store is untouched.
    """
    base = base or store.active_version(name)
    if base is None:
        raise LibraryPackageError(f"library {name} is not installed", RefusalKind.NOT_INSTALLED)
    try:
        current = load_library(store.library_file(name, base))
    except InputError as exc:
        raise LibraryPackageError(
            f"library {name} {base}: the installed library is damaged", RefusalKind.STORE_DAMAGED
        ) from exc
    result = apply_edits(current, edits)
    if result.library is None:
        listed = "\n".join(f"  {p.location}: {p.message}" for p in result.problems)
        raise LibraryPackageError(
            f"the edits leave {LIBRARY_FILE} invalid:\n{listed}", RefusalKind.VALIDATION_FAILED
        )
    return save_local_version(store, name, result.library, base=base, note=note)


def _next_local(store: LibraryStore, name: str, base: Version) -> Version:
    release = base.base
    used = [
        parsed.local
        for parsed in map(Version.parse, store.versions(name))
        if parsed.base == release
    ]
    return release.with_local(max(used, default=0) + 1)


def _release_notes(base: str, diff: LibraryDiff, note: str) -> str:
    counts = [
        (len(diff.added), "part", "added"),
        (len(diff.changed), "part", "changed"),
        (len(diff.removed), "part", "removed"),
        (len(diff.catalogues_changed), "catalogue", "changed"),
    ]
    parts = [f"{n} {noun}{'s' if n != 1 else ''} {verb}" for n, noun, verb in counts if n]
    text = f"Local edit from {base}: {', '.join(parts)}."
    return f"{text}\n{note.strip()}" if note.strip() else text
