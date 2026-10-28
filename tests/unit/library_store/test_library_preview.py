"""The library import dry-run: every check listed, nothing written (plan M8c)."""

import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from bomgen.bundle.checks import Check, CheckStatus
from bomgen.bundle.errors import RefusalKind
from bomgen.library_store import LibraryImportPreview, preview_library_import
from bomgen.library_store.package import pack
from bomgen.library_store.store import LibraryStore

MakePackage = Callable[..., Path]

EXAMPLE_LIBRARY = Path(__file__).parents[3] / "examples" / "library.yaml"
SCHEMA_INVALID = "devices:\n  - part_id: X\n    bogus: 1\n"
IDS = [
    "package",
    "paths",
    "size",
    "manifest",
    "files",
    "checksums",
    "library",
    "validation",
    "version",
    "signature",
]


@pytest.fixture
def store(tmp_path: Path) -> LibraryStore:
    return LibraryStore(tmp_path / "libraries")


@pytest.fixture
def make_package(tmp_path: Path) -> MakePackage:
    def _make(version: str, library: str | None = None, **options: object) -> Path:
        source = tmp_path / "src" / version / "library.yaml"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(library if library is not None else EXAMPLE_LIBRARY.read_text())
        out = tmp_path / f"psa-{version}.bomlib"
        pack(source, out, name="psa", version=version, **options)  # type: ignore[arg-type]
        return out

    return _make


def _by_id(preview: LibraryImportPreview) -> dict[str, Check]:
    return {check.id: check for check in preview.checks}


def test_a_good_package_passes_every_check(store: LibraryStore, make_package: MakePackage) -> None:
    preview = preview_library_import(make_package("1.0.0", release_notes="first"), store=store)

    assert [c.id for c in preview.checks] == IDS
    checks = _by_id(preview)
    assert all(checks[i].status is CheckStatus.OK for i in IDS if i not in ("signature", "version"))
    assert checks["version"].status is CheckStatus.OK
    assert checks["signature"].status is CheckStatus.SKIPPED
    assert "checksums only" in checks["signature"].detail
    assert preview.can_import
    assert preview.manifest is not None
    assert preview.manifest.version == "1.0.0"
    assert preview.manifest.release_notes == "first"
    assert preview.previous is None
    assert preview.diff is not None
    assert preview.diff.added
    assert preview.files[0].name == "library.yaml"


def test_the_preview_writes_nothing(
    tmp_path: Path, store: LibraryStore, make_package: MakePackage
) -> None:
    preview_library_import(make_package("1.0.0"), store=store)

    assert not store.root.exists()


def test_a_newer_version_is_compared_with_the_active_one(
    store: LibraryStore, make_package: MakePackage
) -> None:
    store.import_package(make_package("1.0.0"))
    preview = preview_library_import(make_package("1.1.0"), store=store)

    check = _by_id(preview)["version"]
    assert check.status is CheckStatus.OK
    assert "1.0.0" in check.detail
    assert preview.previous == "1.0.0"


def test_a_downgrade_fails_with_its_kind_unless_forced(
    store: LibraryStore, make_package: MakePackage
) -> None:
    store.import_package(make_package("1.1.0"))
    older = make_package("1.0.0")

    refused = preview_library_import(older, store=store)
    forced = preview_library_import(older, force=True, store=store)

    check = _by_id(refused)["version"]
    assert (check.status, check.kind) == (CheckStatus.FAILED, RefusalKind.DOWNGRADE)
    assert not refused.can_import
    assert _by_id(forced)["version"].status is CheckStatus.WARNING
    assert forced.can_import


def test_the_same_version_fails_with_its_kind(
    store: LibraryStore, make_package: MakePackage
) -> None:
    package = make_package("1.0.0")
    store.import_package(package)

    check = _by_id(preview_library_import(package, store=store))["version"]

    assert (check.status, check.kind) == (CheckStatus.FAILED, RefusalKind.ALREADY_INSTALLED)


def test_a_schema_invalid_library_fails_validation(
    store: LibraryStore, make_package: MakePackage
) -> None:
    package = make_package("1.0.0", library=SCHEMA_INVALID)

    preview = preview_library_import(package, store=store)

    check = _by_id(preview)["validation"]
    assert (check.status, check.kind) == (CheckStatus.FAILED, RefusalKind.VALIDATION_FAILED)
    assert "devices[0].bogus: unknown key" in check.detail
    assert _by_id(preview)["library"].status is CheckStatus.OK
    assert not preview.can_import


def test_a_tampered_package_fails_checksums_and_skips_the_rest(
    tmp_path: Path, store: LibraryStore, make_package: MakePackage
) -> None:
    good = make_package("1.0.0")
    bad = tmp_path / "tampered.bomlib"
    with zipfile.ZipFile(good) as source, zipfile.ZipFile(bad, "w") as out:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "library.yaml":
                data += b"# edited\n"
            out.writestr(item.filename, data)

    preview = preview_library_import(bad, store=store)

    checks = _by_id(preview)
    assert checks["checksums"].status is CheckStatus.FAILED
    for later in ("library", "validation", "version"):
        assert checks[later].status is CheckStatus.SKIPPED
    assert preview.files == []
    assert preview.diff is None
    assert not preview.can_import


def test_a_package_needing_a_newer_app_fails_the_manifest_check(
    store: LibraryStore, make_package: MakePackage
) -> None:
    package = make_package("1.0.0", min_app_version="99.0.0")

    preview = preview_library_import(package, store=store)

    check = _by_id(preview)["manifest"]
    assert (check.status, check.kind) == (CheckStatus.FAILED, RefusalKind.INCOMPATIBLE)
    assert "99.0.0" in check.detail
    assert preview.manifest is None


def test_a_file_that_is_not_a_package_fails_the_first_check(
    tmp_path: Path, store: LibraryStore
) -> None:
    junk = tmp_path / "junk.bomlib"
    junk.write_text("not a zip")

    preview = preview_library_import(junk, store=store)

    assert _by_id(preview)["package"].status is CheckStatus.FAILED
    assert not preview.can_import
