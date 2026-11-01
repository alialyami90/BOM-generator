import bomgen


def test_package_exposes_version() -> None:
    assert bomgen.__version__ == "0.3.2"
