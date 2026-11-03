"""IED schedule CSV and port text (plan M60, ADR 0034 item 5)."""

import pytest

from bomgen.io.ied_csv import parse_ports, ports_text, read_schedule

HEADER = "bay,name,qty,ports,attachment,lands_on\n"


def test_ports_text_reads_count_speed_and_media() -> None:
    assert parse_ports("2x100M MM + 1x1G RJ45") == [
        {"count": 2, "speed": "100M", "media": "MM"},
        {"count": 1, "speed": "1G", "media": "RJ45"},
    ]


def test_ports_text_count_defaults_to_one() -> None:
    assert parse_ports("1G SM") == [{"count": 1, "speed": "1G", "media": "SM"}]


def test_ports_text_names_what_it_cannot_read() -> None:
    with pytest.raises(ValueError, match="'fast fibre'"):
        parse_ports("fast fibre")


def test_ports_text_round_trips() -> None:
    ports = [
        {"count": 2, "speed": "100M", "media": "MM"},
        {"count": 1, "speed": "1G", "media": "RJ45"},
    ]
    assert parse_ports(ports_text(ports)) == ports


def test_csv_rows_become_schedule_rows() -> None:
    rows, problems = read_schedule(
        HEADER + "E01,SEL-411L,4,1x100M MM,dual,l1\nH01,GW,1,1G RJ45,single_a,l2\n"
    )
    assert problems == []
    assert rows == [
        {
            "bay": "E01",
            "name": "SEL-411L",
            "qty": 4,
            "ports": [{"count": 1, "speed": "100M", "media": "MM"}],
            "attachment": "dual",
            "lands_on": "l1",
        },
        {
            "bay": "H01",
            "name": "GW",
            "qty": 1,
            "ports": [{"count": 1, "speed": "1G", "media": "RJ45"}],
            "attachment": "single_a",
            "lands_on": "l2",
        },
    ]


def test_csv_empty_cells_take_the_row_defaults() -> None:
    rows, problems = read_schedule("bay,name\nE01,SEL-411L\n")
    assert problems == []
    assert rows == [{"bay": "E01", "name": "SEL-411L"}]


def test_csv_problems_name_the_row_and_column() -> None:
    rows, problems = read_schedule(HEADER + "E01,P,4,1x100M MM,both,l1\nE02,Q,x,,dual,l1\n")
    assert rows == []
    assert [(p["row"], p["column"]) for p in problems] == [(2, "attachment"), (3, "qty")]


def test_csv_needs_bay_and_name_columns() -> None:
    rows, problems = read_schedule("name,qty\nP,4\n")
    assert rows == []
    assert problems[0]["message"].startswith("The file needs the columns bay, name")


def test_csv_problems_say_what_to_write() -> None:
    _, problems = read_schedule(HEADER + "E02,Q,x,,dual,l1\n")
    assert problems[0]["message"] == "Enter a whole number, 1 or more."
