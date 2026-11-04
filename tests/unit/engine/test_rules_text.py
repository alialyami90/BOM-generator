"""Rule texts name the numbers their value came from (plan M48, the override contract)."""

from bomgen.engine.rules_text import (
    ac_spare_rule,
    dc_spare_rule,
    main_mcb_rule,
    reserved_rule,
    sfp_rule,
    sfp_spare_rule,
    spare_ports_rule,
    switch_count_rule,
)


def test_main_mcb_rule_names_the_rating_the_design_current_and_the_minimum() -> None:
    assert main_mcb_rule(16, 7.08, 6) == "16 A: next standard size above 7.1 A, minimum 6 A"


def test_main_mcb_rule_says_when_the_minimum_sets_the_rating() -> None:
    assert main_mcb_rule(6, 1.5, 6) == "6 A: the minimum main MCB; design current 1.5 A"


def test_main_mcb_rule_of_a_panel_without_dc_loads() -> None:
    assert main_mcb_rule(0, 0.0, 6) == "No DC loads"


def test_sfp_rule_names_links_spare_and_extra() -> None:
    assert sfp_rule(24, 3, 2) == "24 links + 3 spare + 2 extra"


def test_sfp_rule_drops_the_parts_that_are_zero() -> None:
    assert sfp_rule(1, 0, 0) == "1 link"
    assert sfp_rule(15, 0, 2) == "15 links + 2 extra"


def test_sfp_spare_rule_names_the_project_spare_on_an_l1_row() -> None:
    assert sfp_spare_rule(3, l1=True) == "3: the project's spare SFPs per L1 row"
    assert sfp_spare_rule(0, l1=False) == "0: the project sets spare SFPs on L1 rows only"


def test_ac_spare_rule_names_the_largest_housekeeping_branch() -> None:
    assert ac_spare_rule(2) == "2 A: the largest housekeeping branch"


def test_dc_spare_rule_names_the_largest_device_branch_or_the_floor() -> None:
    assert dc_spare_rule(2, branches=13) == "2 A: the largest of 13 device branches"
    assert dc_spare_rule(2, branches=0) == "2 A: the minimum branch MCB"


def test_switch_count_rule_names_the_ports_and_the_usable_per_switch() -> None:
    assert switch_count_rule(3, 40, 19, ieds=True) == "3: 40 IED ports per side, 19 usable on each"
    assert switch_count_rule(1, 8, 16, ieds=False) == "1: 8 ports per side, 16 usable on each"
    assert switch_count_rule(0, 0, 19, ieds=True) == "0: no IED port lands on L1"


def test_reserved_rule_names_what_each_switch_keeps() -> None:
    assert reserved_rule(uplinks=1, interlink=True, ring=False) == (
        "1 uplink and the A\u2013B interlink on each switch"
    )
    assert reserved_rule(uplinks=2, interlink=False, ring=False) == "2 uplinks on each switch"
    assert reserved_rule(uplinks=1, interlink=True, ring=True) == "2 ring ports on each switch"


def test_spare_ports_rule_names_the_fraction_kept_free() -> None:
    assert spare_ports_rule(0.2) == "20% of the device ports kept free"
