"""Python API the desktop app's UI calls (plan M10, ADR 0015)."""

import inspect
from pathlib import Path

import pytest

import bomgen
from bomgen.app import api
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.package import pack
from bomgen.library_store.service import import_library
from bomgen.library_store.store import LibraryStore

EXAMPLE_LIBRARY = Path(__file__).parents[3] / "examples" / "library.yaml"


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    return {
        "BOMGEN_LIBRARY_HOME": str(tmp_path / "libraries"),
        "BOMGEN_WORKSPACE": str(tmp_path / "workspace"),
    }


def install_example(tmp_path: Path, env: dict[str, str], version: str = "1.0.0") -> None:
    package = tmp_path / f"psa-{version}.bomlib"
    pack(EXAMPLE_LIBRARY, package, name="psa", version=version)
    import_library(package, store=LibraryStore(Path(env["BOMGEN_LIBRARY_HOME"])))


def data(envelope: dict[str, object]) -> dict[str, object]:
    assert envelope["ok"] is True, envelope
    payload = envelope["data"]
    assert isinstance(payload, dict)
    return payload


def test_app_info_reports_version_and_title(env: dict[str, str]) -> None:
    info = data(api.Api(env=env).app_info())

    assert info["title"] == "BOM Generator"
    assert info["version"] == bomgen.__version__
    assert info["workspace"] == env["BOMGEN_WORKSPACE"]


def test_app_info_reports_the_bomproj_the_app_was_opened_with(
    env: dict[str, str], tmp_path: Path
) -> None:
    opened = tmp_path / "eastern-province.bomproj"

    assert data(api.Api(opened, env=env).app_info())["project_file"] == str(opened)
    assert data(api.Api(env=env).app_info())["project_file"] is None


def test_app_info_with_no_library_is_first_run(env: dict[str, str]) -> None:
    assert data(api.Api(env=env).app_info())["libraries"] == []


def test_app_info_lists_installed_libraries(env: dict[str, str], tmp_path: Path) -> None:
    install_example(tmp_path, env, "1.0.0")
    install_example(tmp_path, env, "1.1.0")

    assert data(api.Api(env=env).app_info())["libraries"] == [
        {"name": "psa", "active": "1.1.0", "versions": ["1.0.0", "1.1.0"], "problem": None}
    ]


def test_app_info_reports_a_damaged_store_instead_of_failing(
    env: dict[str, str], tmp_path: Path
) -> None:
    install_example(tmp_path, env)
    (Path(env["BOMGEN_LIBRARY_HOME"]) / "psa" / "active").write_text("9.9.9")

    libraries = data(api.Api(env=env).app_info())["libraries"]

    assert isinstance(libraries, list)
    (library,) = libraries

    assert library["active"] is None
    assert "9.9.9" in library["problem"]


def test_endpoint_turns_a_refusal_into_an_error_envelope() -> None:
    @api.endpoint
    def refuse() -> object:
        raise LibraryPackageError("psa 1.0.0 is already installed", RefusalKind.ALREADY_INSTALLED)

    assert refuse() == {
        "ok": False,
        "error": {"kind": "already_installed", "message": "psa 1.0.0 is already installed"},
    }


def test_endpoint_turns_a_file_error_into_an_io_error() -> None:
    @api.endpoint
    def locked() -> object:
        raise PermissionError(13, "Permission denied", "out.xlsx")

    result = locked()

    assert result["ok"] is False
    assert result["error"]["kind"] == "io"  # type: ignore[index]
    assert "out.xlsx" in result["error"]["message"]  # type: ignore[index]


def test_endpoint_turns_an_unexpected_exception_into_an_internal_error() -> None:
    @api.endpoint
    def broken() -> object:
        raise KeyError("panels")

    result = broken()

    assert result["ok"] is False
    assert result["error"]["kind"] == "internal"  # type: ignore[index]
    assert "panels" in result["error"]["message"]  # type: ignore[index]


def test_endpoint_makes_results_json_ready(tmp_path: Path) -> None:
    @api.endpoint
    def paths() -> object:
        return {"file": tmp_path / "a.bomproj", "items": (1, 2)}

    assert paths() == {"ok": True, "data": {"file": str(tmp_path / "a.bomproj"), "items": [1, 2]}}


def test_only_endpoints_are_public(env: dict[str, str]) -> None:
    # pywebview exposes every public attribute of js_api to the page.
    instance = api.Api(env=env)
    public = [name for name in dir(instance) if not name.startswith("_")]

    assert public
    for name in public:
        member = getattr(instance, name)
        assert inspect.ismethod(member), name
        assert getattr(member, "__wrapped__", None) is not None, f"{name} is not an endpoint"
