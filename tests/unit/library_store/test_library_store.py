"""Per-user installed-library store: import, preview, list, rollback (ADR 0008, plan M8)."""

import os
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.package import pack
from bomgen.library_store.store import (
    LibraryRef,
    LibraryStore,
    default_library_home,
    library_mismatch,
)

MakePackage = Callable[..., Path]

V1 = "devices:\n  - part_id: SW\n    unit_power_w: 77\n  - part_id: FW\ncatalogues: {}\n"
V2 = "devices:\n  - part_id: SW\n    unit_power_w: 80\n  - part_id: GW\ncatalogues: {}\n"


@pytest.fixture
def store(tmp_path: Path) -> LibraryStore:
    return LibraryStore(tmp_path / "libraries")


@pytest.fixture
def make_package(tmp_path: Path) -> MakePackage:
    def _make(version: str, library: str = V1, name: str = "psa-devices") -> Path:
        source = tmp_path / "src" / version / "library.yaml"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(library)
        out = tmp_path / f"{name}-{version}.bomlib"
        pack(source, out, name=name, version=version)
        return out

    return _make


def _snapshot(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_import_installs_and_activates(store: LibraryStore, make_package: MakePackage) -> None:
    result = store.import_package(make_package("1.0.0"))

    assert result.manifest.version == "1.0.0"
    assert result.previous is None
    assert result.diff.added == ["FW", "SW"]
    assert store.active_version("psa-devices") == "1.0.0"
    assert store.library_file("psa-devices").read_text() == V1
    assert (store.root / "psa-devices" / "1.0.0" / "manifest.json").is_file()


def test_import_reports_diff_against_active(store: LibraryStore, make_package: MakePackage) -> None:
    store.import_package(make_package("1.0.0"))

    result = store.import_package(make_package("1.1.0", V2))

    assert result.previous == "1.0.0"
    assert result.diff.added == ["GW"]
    assert result.diff.removed == ["FW"]
    assert result.diff.changed == {"SW": ["unit_power_w"]}
    assert store.active_version("psa-devices") == "1.1.0"


def test_import_refuses_downgrade_unless_forced(
    store: LibraryStore, make_package: MakePackage
) -> None:
    store.import_package(make_package("1.10.0", V2))
    older = make_package("1.9.0")

    with pytest.raises(LibraryPackageError, match=r"1\.9\.0 is older than the active 1\.10\.0"):
        store.import_package(older)
    assert store.active_version("psa-devices") == "1.10.0"

    store.import_package(older, force=True)
    assert store.active_version("psa-devices") == "1.9.0"


def test_import_refuses_reinstall_unless_forced(
    store: LibraryStore, make_package: MakePackage
) -> None:
    package = make_package("1.0.0")
    store.import_package(package)

    with pytest.raises(LibraryPackageError, match=r"1\.0\.0 is already installed"):
        store.import_package(package)

    result = store.import_package(package, force=True)
    assert result.diff.is_empty
    assert store.library_file("psa-devices").read_text() == V1


def test_reimport_of_inactive_version_points_to_rollback(
    store: LibraryStore, make_package: MakePackage
) -> None:
    first = make_package("1.0.0")
    store.import_package(first)
    store.import_package(make_package("1.1.0", V2))

    with pytest.raises(LibraryPackageError, match="installed but not active") as caught:
        store.import_package(first)

    assert "rollback" not in str(caught.value)
    assert caught.value.hint == "run: bomgen library rollback psa-devices --to 1.0.0"


def test_failed_validation_leaves_store_unchanged(
    store: LibraryStore, make_package: MakePackage
) -> None:
    store.import_package(make_package("1.0.0"))
    before = _snapshot(store.root)
    seen: list[str] = []

    def reject(library_file: Path) -> None:
        seen.append(library_file.read_text())
        raise ValueError("schema says no")

    with pytest.raises(ValueError, match="schema says no"):
        store.import_package(make_package("1.1.0", V2), validate=reject)

    assert seen == [V2]
    assert _snapshot(store.root) == before
    assert sorted(p.name for p in (store.root / "psa-devices").iterdir()) == ["1.0.0", "active"]


def test_preview_import_changes_nothing(store: LibraryStore, make_package: MakePackage) -> None:
    store.import_package(make_package("1.0.0"))
    before = _snapshot(store.root)

    result = store.preview_import(make_package("1.1.0", V2))

    assert result.previous == "1.0.0"
    assert result.diff.added == ["GW"]
    assert _snapshot(store.root) == before


def test_preview_import_applies_the_same_refusals(
    store: LibraryStore, make_package: MakePackage
) -> None:
    store.import_package(make_package("2.0.0"))

    with pytest.raises(LibraryPackageError, match="older"):
        store.preview_import(make_package("1.0.0"))


def test_list_shows_installed_versions_and_active(
    store: LibraryStore, make_package: MakePackage
) -> None:
    store.import_package(make_package("1.0.0"))
    store.import_package(make_package("1.10.0", V2))
    store.import_package(make_package("1.2.0"), force=True)
    store.import_package(make_package("0.1.0", name="other"))

    listing = store.list()

    assert [(lib.name, lib.versions, lib.active) for lib in listing] == [
        ("other", ["0.1.0"], "0.1.0"),
        ("psa-devices", ["1.0.0", "1.2.0", "1.10.0"], "1.2.0"),
    ]


def test_list_of_empty_store(store: LibraryStore) -> None:
    assert store.list() == []


def test_rollback_activates_previous_version(
    store: LibraryStore, make_package: MakePackage
) -> None:
    store.import_package(make_package("1.0.0"))
    store.import_package(make_package("1.1.0", V2))

    assert store.rollback("psa-devices") == "1.0.0"
    assert store.active_version("psa-devices") == "1.0.0"
    assert store.library_file("psa-devices").read_text() == V1
    assert (store.root / "psa-devices" / "1.1.0").is_dir()


def test_rollback_to_named_version(store: LibraryStore, make_package: MakePackage) -> None:
    for version in ("1.0.0", "1.1.0", "1.2.0"):
        store.import_package(make_package(version))
    store.rollback("psa-devices", to="1.0.0")

    assert store.rollback("psa-devices", to="1.2.0") == "1.2.0"
    assert store.active_version("psa-devices") == "1.2.0"


def test_rollback_to_missing_version_fails(store: LibraryStore, make_package: MakePackage) -> None:
    store.import_package(make_package("1.0.0"))

    with pytest.raises(LibraryPackageError, match=r"0\.9\.0 is not installed"):
        store.rollback("psa-devices", to="0.9.0")


def test_rollback_without_older_version_fails(
    store: LibraryStore, make_package: MakePackage
) -> None:
    store.import_package(make_package("1.0.0"))

    with pytest.raises(LibraryPackageError, match="no older version"):
        store.rollback("psa-devices")


def test_rollback_of_unknown_library_fails(store: LibraryStore) -> None:
    with pytest.raises(LibraryPackageError, match="not installed"):
        store.rollback("nothing")


@pytest.mark.parametrize("pointer", ["9.9.9", "garbage", ""])
def test_corrupt_active_pointer_is_reported(
    store: LibraryStore,
    make_package: MakePackage,
    pointer: str,
) -> None:
    store.import_package(make_package("1.0.0"))
    (store.root / "psa-devices" / "active").write_text(pointer)

    with pytest.raises(LibraryPackageError, match="active version"):
        store.active_version("psa-devices")
    [listed] = store.list()
    assert listed.active is None
    assert listed.problem is not None


def test_import_repairs_corrupt_active_pointer(
    store: LibraryStore, make_package: MakePackage
) -> None:
    store.import_package(make_package("1.0.0"))
    (store.root / "psa-devices" / "active").write_text("garbage")

    store.import_package(make_package("1.1.0", V2))

    assert store.active_version("psa-devices") == "1.1.0"


def test_library_file_without_install_fails(store: LibraryStore) -> None:
    with pytest.raises(LibraryPackageError, match="not installed"):
        store.library_file("psa-devices")


def test_default_home_is_localappdata_on_windows() -> None:
    env = {"LOCALAPPDATA": r"C:\Users\ali\AppData\Local"}

    home = default_library_home(env, platform="win32")

    assert home == Path(r"C:\Users\ali\AppData\Local") / "bomgen" / "libraries"


def test_default_home_follows_xdg_elsewhere() -> None:
    home = default_library_home({"XDG_DATA_HOME": "/data"}, platform="linux")

    assert home == Path("/data/bomgen/libraries")


def test_default_home_env_override() -> None:
    env = {"BOMGEN_LIBRARY_HOME": "/custom", "LOCALAPPDATA": "C:/x"}

    assert default_library_home(env, platform="win32") == Path("/custom")


def test_library_mismatch_message() -> None:
    built = LibraryRef("psa-devices", "1.0.0")

    assert library_mismatch(built, LibraryRef("psa-devices", "1.0.0")) is None
    assert library_mismatch(built, LibraryRef("psa-devices", "1.1.0")) == (
        "project was built with library psa-devices 1.0.0; the active version is 1.1.0"
    )
    assert library_mismatch(built, None) == (
        "project was built with library psa-devices 1.0.0, which is not installed"
    )


def test_failed_force_reinstall_keeps_the_installed_version(
    store: LibraryStore, make_package: MakePackage, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = make_package("1.0.0")
    store.import_package(package)
    before = _snapshot(store.root)
    real_replace = os.replace

    def locked(src: str | Path, dst: str | Path) -> None:
        if Path(src).name.startswith(".incoming-"):
            raise PermissionError("locked by antivirus")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", locked)
    with pytest.raises(PermissionError):
        store.import_package(package, force=True)
    monkeypatch.undo()

    assert _snapshot(store.root) == before
    assert store.active_version("psa-devices") == "1.0.0"


def test_interrupted_force_reinstall_keeps_the_installed_version(
    store: LibraryStore, make_package: MakePackage, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = make_package("1.0.0")
    store.import_package(package)
    before = _snapshot(store.root)
    real_replace = os.replace

    def interrupted(src: str | Path, dst: str | Path) -> None:
        if Path(src).name.startswith(".incoming-"):
            raise KeyboardInterrupt
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", interrupted)
    with pytest.raises(KeyboardInterrupt):
        store.import_package(package, force=True)
    monkeypatch.undo()

    assert _snapshot(store.root) == before


def _active_write_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(path: Path, text: str) -> None:
        raise PermissionError("active is locked")

    monkeypatch.setattr("bomgen.library_store.store._write_text_atomic", refuse)


def test_a_failed_active_write_on_a_force_reinstall_restores_the_installed_version(
    store: LibraryStore, make_package: MakePackage, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = make_package("1.0.0")
    store.import_package(package)
    before = _snapshot(store.root)
    _active_write_fails(monkeypatch)

    with pytest.raises(PermissionError):
        store.import_package(package, force=True)
    monkeypatch.undo()

    assert _snapshot(store.root) == before
    assert not [p for p in (store.root / "psa-devices").iterdir() if p.name.startswith(".")]
    assert store.active_version("psa-devices") == "1.0.0"


def test_a_failed_active_write_on_a_new_version_leaves_no_trace_of_it(
    store: LibraryStore, make_package: MakePackage, monkeypatch: pytest.MonkeyPatch
) -> None:
    store.import_package(make_package("1.0.0"))
    before = _snapshot(store.root)
    _active_write_fails(monkeypatch)

    with pytest.raises(PermissionError):
        store.import_package(make_package("1.1.0"))
    monkeypatch.undo()

    assert _snapshot(store.root) == before
    assert store.versions("psa-devices") == ["1.0.0"]
    assert store.active_version("psa-devices") == "1.0.0"


def test_failed_validation_of_a_new_library_leaves_no_trace(
    store: LibraryStore, make_package: MakePackage
) -> None:
    def reject(library_file: Path) -> None:
        raise ValueError("no")

    with pytest.raises(ValueError, match="no"):
        store.import_package(make_package("1.0.0"), validate=reject)

    assert list(store.root.iterdir()) == []


def test_non_utf8_active_pointer_is_reported(
    store: LibraryStore, make_package: MakePackage
) -> None:
    store.import_package(make_package("1.0.0"))
    (store.root / "psa-devices" / "active").write_bytes(b"\xff\xfe1")

    with pytest.raises(LibraryPackageError, match="active version"):
        store.active_version("psa-devices")
    [listed] = store.list()
    assert listed.problem is not None
    store.import_package(make_package("1.1.0", V2))
    assert store.active_version("psa-devices") == "1.1.0"


@pytest.mark.parametrize("damage", ["manifest", "library"])
def test_import_replaces_a_damaged_active_version(
    store: LibraryStore, make_package: MakePackage, damage: str
) -> None:
    package = make_package("1.0.0")
    store.import_package(package)
    version_dir = store.root / "psa-devices" / "1.0.0"
    if damage == "manifest":
        (version_dir / "manifest.json").write_text("{broken")
    else:
        (version_dir / "library.yaml").unlink()

    result = store.import_package(package, force=True)

    assert result.previous is None
    assert store.library_file("psa-devices").read_text() == V1


def test_library_mismatch_ignores_a_different_library() -> None:
    built = LibraryRef("psa-devices", "1.0.0")

    assert library_mismatch(built, LibraryRef("other", "1.0.0")) == (
        "project was built with library psa-devices 1.0.0, which is not installed"
    )


def _kind_of(action: Callable[[], object]) -> RefusalKind:
    with pytest.raises(LibraryPackageError) as caught:
        action()
    return caught.value.kind


def test_refusals_carry_a_machine_readable_kind(
    store: LibraryStore, make_package: MakePackage, tmp_path: Path
) -> None:
    newer = make_package("2.0.0")
    older = make_package("1.0.0")
    store.import_package(newer)
    junk = tmp_path / "junk.bomlib"
    junk.write_text("no")

    assert _kind_of(lambda: store.preview_import(older)) is RefusalKind.DOWNGRADE
    assert _kind_of(lambda: store.preview_import(newer)) is RefusalKind.ALREADY_INSTALLED
    assert _kind_of(lambda: store.preview_import(junk)) is RefusalKind.INVALID_PACKAGE
    assert _kind_of(lambda: store.rollback("psa-devices", to="0.1.0")) is RefusalKind.NOT_INSTALLED
    assert _kind_of(lambda: store.rollback("psa-devices")) is RefusalKind.NOT_INSTALLED


def test_incompatible_packages_have_their_own_kind(
    store: LibraryStore, make_package: MakePackage, tmp_path: Path
) -> None:
    package = make_package("1.0.0")
    newer_schema = tmp_path / "s.bomlib"
    with zipfile.ZipFile(package) as old, zipfile.ZipFile(newer_schema, "w") as new:
        for name in old.namelist():
            data = old.read(name)
            if name == "manifest.json":
                data = data.replace(b'"schema_version": 1', b'"schema_version": 2')
            new.writestr(name, data)

    assert _kind_of(lambda: store.preview_import(newer_schema)) is RefusalKind.INCOMPATIBLE


def test_a_failing_validator_is_not_wrapped(store: LibraryStore, make_package: MakePackage) -> None:
    def reject(library_file: Path) -> None:
        raise LibraryPackageError("schema says no", kind=RefusalKind.VALIDATION_FAILED)

    assert (
        _kind_of(lambda: store.import_package(make_package("1.0.0"), validate=reject))
        is RefusalKind.VALIDATION_FAILED
    )


def test_preview_runs_the_validator_too(store: LibraryStore, make_package: MakePackage) -> None:
    seen: list[str] = []

    def record(library_file: Path) -> None:
        seen.append(library_file.read_text())

    store.preview_import(make_package("1.0.0"), validate=record)

    assert seen == [V1]
    assert not store.root.exists() or list(store.root.iterdir()) == []
