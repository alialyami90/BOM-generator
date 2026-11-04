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


def ac_spare_rule(rating_a: int) -> str:
    """An AC spare branch (spec: Derivation rules -> AC distribution, plan M58)."""
    return f"{rating_a} A: the largest housekeeping branch"


def dc_spare_rule(rating_a: int, *, branches: int) -> str:
    """A DC spare branch on each feed (spec: Derivation rules -> DC distribution, plan M58)."""
    if not branches:
        return f"{rating_a} A: the minimum branch MCB"
    return f"{rating_a} A: the largest of {branches} device branch" + (
        "" if branches == 1 else "es"
    )


def switch_count_rule(count: int, used: int, usable: int, *, ieds: bool) -> str:
    """A switch level's count per side: the ports it takes and the usable on each (plan M72)."""
    if ieds and not used:
        return f"{count}: no IED port lands on L1"
    what = "IED ports" if ieds else "ports"
    return f"{count}: {used} {what} per side, {usable} usable on each"


def reserved_rule(*, uplinks: int, interlink: bool, ring: bool) -> str:
    """The ports each switch keeps off the devices (ADR 0013, R1 and R2; plan M72)."""
    if ring:
        return "2 ring ports on each switch"
    text = f"{uplinks} uplink" + ("" if uplinks == 1 else "s")
    return text + (" and the A\u2013B interlink" if interlink else "") + " on each switch"


def spare_ports_rule(fraction: float) -> str:
    """The share of a switch's device ports the spare keeps free (R1; plan M72)."""
    return f"{fraction:.0%} of the device ports kept free"


def grounding_rule(busbars: list[str]) -> str:
    """The busbars a panel gets: the ones its options name (spec: grounding; plan M77)."""
    if not busbars:
        return "No busbars: none chosen in the panel options"
    n = len(busbars)
    return f"{n} busbar{'' if n == 1 else 's'} from the panel options: {', '.join(busbars)}"


def cable_manager_rule(count: int) -> str:
    """Group C's cable managers (spec: Where in the panel, Q32; plan M77)."""
    if not count:
        return "0: no rack-mounted switch, firewall or patch panel takes one"
    return f"{count}: one under each rack-mounted switch, firewall and patch panel"


def fan_rule(fans: int, airflow_m3h: float, required_m3h: float, *, larger: bool) -> str:
    """The fan a forced cabinet gets (spec: Heat Dissipation; ADR 0029, plan M77)."""
    moved = f"{fans} fan{'' if fans == 1 else 's'} move {airflow_m3h:.0f} m³/h"
    need = f"for the {required_m3h:.0f} m³/h required"
    if airflow_m3h < required_m3h:
        return f"the largest fan; {moved} {need}"
    if larger:
        return f"the smallest larger fan whose {moved} {need}"
    return f"the catalogue fan; {moved} {need}"
