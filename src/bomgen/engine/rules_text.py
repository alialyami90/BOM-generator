"""Rule texts: the one line saying how the engine reached a derived value (plan M48).

Each text names the numbers it used, so the engineer can check it without the spec.
"""


def main_mcb_rule(rating_a: int, design_current_a: float, min_main_a: int) -> str:
    """Q1/Q2 (spec: Derivation rules -> DC distribution, main MCB)."""
    if rating_a == 0:
        return "No DC loads"
    if design_current_a < min_main_a and rating_a == min_main_a:
        return f"{rating_a} A: the minimum main MCB; design current {design_current_a:.1f} A"
    return (
        f"{rating_a} A: next standard size above {design_current_a:.1f} A, minimum {min_main_a} A"
    )
