"""Rule texts name the numbers their value came from (plan M48, the override contract)."""

from bomgen.engine.rules_text import main_mcb_rule


def test_main_mcb_rule_names_the_rating_the_design_current_and_the_minimum() -> None:
    assert main_mcb_rule(16, 7.08, 6) == "16 A: next standard size above 7.1 A, minimum 6 A"


def test_main_mcb_rule_says_when_the_minimum_sets_the_rating() -> None:
    assert main_mcb_rule(6, 1.5, 6) == "6 A: the minimum main MCB; design current 1.5 A"


def test_main_mcb_rule_of_a_panel_without_dc_loads() -> None:
    assert main_mcb_rule(0, 0.0, 6) == "No DC loads"
