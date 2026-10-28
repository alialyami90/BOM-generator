"""Breaker and auxiliary-contact rows (spec: Derivation rules -> Breaker part numbers;
Columns of a panel BOM, DESCRIPTION)."""

from bomgen.engine.errors import EngineError
from bomgen.models.bom import BomLine, Group
from bomgen.models.library import Library
from bomgen.models.panel import Panel, PanelKind


def rating_at_least(library: Library, amps: float) -> int:
    """The smallest catalogue MCB rating of at least ``amps``."""
    ratings = library.catalogues.mcb.ratings_a
    for rating in ratings:
        if rating >= amps:
            return rating
    raise EngineError(f"{amps:.2f} A is above the largest catalogue MCB ({ratings[-1]} A)")


def rating_above(library: Library, amps: float) -> int:
    """The smallest catalogue MCB rating strictly above ``amps``."""
    ratings = library.catalogues.mcb.ratings_a
    for rating in ratings:
        if rating > amps:
            return rating
    raise EngineError(f"no catalogue MCB above {amps:g} A (largest {ratings[-1]} A)")


def mcb_line(library: Library, group: Group, tag: str, rating: int, load: str) -> BomLine:
    """``<rating>A, <poles>P MCB For <load>`` with the catalogue code in F and G."""
    mcb = library.catalogues.mcb
    code = mcb.code_for(rating)
    return BomLine(
        group=group,
        tag=tag,
        description=f"{rating}A, {mcb.poles}P MCB For {load}",
        qty=1,
        make=mcb.make,
        model=code,
        ordering_code=code,
    )


def aux_contact_line(
    library: Library, group: Group, description: str, qty: int, hwio: int
) -> BomLine:
    """The auxiliary contacts of a group's breakers, one untagged row."""
    aux = library.catalogues.aux_contact
    return BomLine(
        group=group,
        description=description,
        qty=qty,
        make=aux.make,
        model=aux.model,
        ordering_code=aux.ordering_code,
        hwio=hwio,
    )


def alarms_wired(panel: Panel) -> bool:
    """Whether the panel's aux contacts are wired to the Axion DI cards (plan Q31: the
    console's are not; the workbook gives it no HWIO column)."""
    return panel.kind is not PanelKind.CONSOLE
