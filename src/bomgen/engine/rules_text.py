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


def sfp_rule(used: int, spare: int, extra: int) -> str:
    """An SFP row's quantity: its links, then the spare and extra SFPs (plan M49)."""
    parts = [f"{used} link" + ("" if used == 1 else "s")]
    parts += [f"{n} {name}" for n, name in ((spare, "spare"), (extra, "extra")) if n]
    return " + ".join(parts)


def sfp_spare_rule(spare: int, *, l1: bool) -> str:
    """Where a switch row's automatic spare SFPs come from (plan M49)."""
    if l1:
        return f"{spare}: the project's spare SFPs per L1 row"
    return "0: the project sets spare SFPs on L1 rows only"
