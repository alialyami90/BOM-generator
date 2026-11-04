"""The previous issue from the substation's recorded issues (ADR 0036, plan M66)."""

import hashlib
import shutil
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from bomgen.build import build_substation, issue_refusal, record_issue
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.substation import AcceptedWarning, Checks, IssueRecord, OverrideNote
from bomgen.revision import file_sha256, previous_from_record

EXAMPLES = Path(__file__).parents[2] / "examples"


@pytest.fixture
def loaded(tmp_path: Path) -> LoadedSubstation:
    shutil.copytree(EXAMPLES, tmp_path / "project")
    return load_substation(tmp_path / "project" / "substations" / "gis01" / "substation.yaml")


def with_issues(loaded: LoadedSubstation, *records: IssueRecord) -> LoadedSubstation:
    return replace(
        loaded, substation=loaded.substation.model_copy(update={"issues": list(records)})
    )


def record(file: Path, sha256: str, rev: str = "00") -> IssueRecord:
    return IssueRecord(
        rev=rev, date=date(2026, 11, 3), file=file, sha256=sha256, description="For review"
    )


def issued(loaded: LoadedSubstation) -> Path:
    out = loaded.file.parent / "out" / "rev00.xlsx"
    out.parent.mkdir()
    return build_substation(loaded, out, checks=False).path


def test_no_record_means_no_previous_issue(loaded: LoadedSubstation) -> None:
    assert previous_from_record(loaded) == (None, None)


def test_previous_issue_from_record_when_hash_matches(loaded: LoadedSubstation) -> None:
    path = issued(loaded)
    target = with_issues(loaded, record(Path("out/rev00.xlsx"), file_sha256(path)))
    previous, warning = previous_from_record(target)
    assert warning is None
    assert previous is not None
    assert previous.source == path.name
    assert "1" in previous.sheets


def test_the_latest_record_is_the_previous_issue(loaded: LoadedSubstation) -> None:
    path = issued(loaded)
    old = record(Path("out/missing.xlsx"), "0" * 64, rev="00")
    target = with_issues(loaded, old, record(Path("out/rev00.xlsx"), file_sha256(path), "01"))
    assert previous_from_record(target)[1] is None


def test_hash_mismatch_warns_and_uses_picker(loaded: LoadedSubstation) -> None:
    issued(loaded)
    target = with_issues(loaded, record(Path("out/rev00.xlsx"), "0" * 64))
    assert previous_from_record(target) == (
        None,
        "Rev 00's recorded file out/rev00.xlsx has changed since it was issued; "
        "choose the previous issue to compare with.",
    )


def test_missing_file_warns_and_uses_picker(loaded: LoadedSubstation) -> None:
    target = with_issues(loaded, record(Path("out/gone.xlsx"), "0" * 64))
    previous, warning = previous_from_record(target)
    assert previous is None
    assert warning == (
        "Rev 00's recorded file out/gone.xlsx is not there; choose the previous issue to "
        "compare with."
    )


def test_file_sha256_is_the_hex_digest(tmp_path: Path) -> None:
    file = tmp_path / "x.bin"
    file.write_bytes(b"abc")
    assert file_sha256(file) == hashlib.sha256(b"abc").hexdigest()


# -- Build as issued (ADR 0036) --


def project_of(loaded: LoadedSubstation) -> Path:
    return loaded.file.parents[2] / "project.yaml"


def test_build_as_issued_appends_record(loaded: LoadedSubstation) -> None:
    path = issued(loaded)
    accepted = AcceptedWarning(check="dc_float", reason="Vendor letter", date=date(2026, 11, 2))
    target = replace(
        loaded,
        substation=loaded.substation.model_copy(update={"checks": Checks(accepted=[accepted])}),
    )
    record = record_issue(project_of(loaded), target, path, "For review", today=date(2026, 11, 3))
    document = loaded.documents[loaded.substation.document]
    assert record.rev == document.rev
    assert record.file == Path("out/rev00.xlsx")
    assert record.sha256 == file_sha256(path)
    assert record.accepted_warnings == [accepted]
    again = load_substation(loaded.file)
    assert again.substation.issues == [record]


def test_a_recorded_rev_is_not_issued_again(loaded: LoadedSubstation) -> None:
    rev = loaded.documents[loaded.substation.document].rev
    assert issue_refusal(loaded) is None
    target = with_issues(loaded, record(Path("out/x.xlsx"), "0" * 64, rev=rev))
    assert issue_refusal(target) == (
        f"Rev {rev} is already issued; change the document's rev in the register first."
    )


def test_a_file_outside_the_project_is_recorded_absolute(
    loaded: LoadedSubstation, tmp_path: Path
) -> None:
    out = tmp_path / "elsewhere" / "rev.xlsx"
    out.parent.mkdir()
    path = build_substation(loaded, out, checks=False).path
    record = record_issue(project_of(loaded), loaded, path, "x", today=date(2026, 11, 3))
    assert record.file == path


def test_an_issue_records_the_risky_overrides_with_their_reasons(loaded: LoadedSubstation) -> None:
    """ADR 0040: what weakened a check at issue time, printed on the Revision History sheet."""
    notes = [
        OverrideNote(
            panel_id="psa1", subject="main_mcb", automatic="10 A", override="6 A", reason="Feeder"
        )
    ]
    path = issued(loaded)
    record_issue(
        loaded.file.parents[2] / "project.yaml", loaded, path, "For review", overrides=notes
    )
    again = load_substation(loaded.file)
    assert again.substation.issues[-1].overrides == notes
