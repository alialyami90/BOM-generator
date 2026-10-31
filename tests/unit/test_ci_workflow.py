"""The CI workflow's docs-only gating (ADR 0006)."""

from pathlib import Path
from typing import Any

import yaml

CI_FILE = Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml"


def ci_workflow() -> dict[Any, Any]:
    loaded: dict[Any, Any] = yaml.safe_load(CI_FILE.read_text(encoding="utf-8"))
    return loaded


def test_docs_the_tests_or_the_library_read_still_run_ci() -> None:
    # docs/ui holds the design tokens, fonts and editing.md the app tests read; data/ holds
    # the library and device-db, whose markdown ships in the default .bomlib.
    changes = ci_workflow()["jobs"]["changes"]
    filters = yaml.safe_load(changes["steps"][-1]["with"]["filters"])
    assert filters["read_by_code"] == ["{docs/ui,data}/**"]
    code = changes["outputs"]["code"]
    assert "steps.filter.outputs.code == 'true'" in code
    assert "steps.filter.outputs.read_by_code == 'true'" in code


def test_every_ci_job_gates_ci_status() -> None:
    jobs = ci_workflow()["jobs"]
    assert set(jobs["ci-status"]["needs"]) == set(jobs) - {"ci-status"}
    assert jobs["ci-status"]["if"] == "always()"
