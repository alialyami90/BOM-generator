"""Generated workbooks are never committed (CLAUDE.md)."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_no_xlsx_tracked_in_git() -> None:
    result = subprocess.run(
        ["git", "ls-files", "--", "*.xlsx", "*.xlsm"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip("not a git checkout")
    assert result.stdout.split() == []
