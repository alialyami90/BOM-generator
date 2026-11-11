"""A pytest plugin, loaded by ``addopts`` in pyproject.toml, with a fixture for every test."""

import pytest


@pytest.fixture(autouse=True)
def per_user_folders_are_the_tests_own(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """No test reads or writes the per-user folders of the PC it runs on (plan M95).

    Without this a test that names no store sees the libraries installed on the PC: on a PC
    with the app installed, ``test_a_taken_folder_gets_a_number`` found psa-devices there.
    """
    home = tmp_path_factory.mktemp("per-user")
    monkeypatch.setenv("BOMGEN_LIBRARY_HOME", str(home / "libraries"))
    monkeypatch.setenv("BOMGEN_WORKSPACE", str(home / "workspace"))
    monkeypatch.setenv("BOMGEN_APP_HOME", str(home / "app"))
