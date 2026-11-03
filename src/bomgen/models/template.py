"""A substation template (plan M55): what a new substation starts from, without its panels,
documents or quantities. Stored in the project folder as ``templates/<key>.yaml`` (Q63)."""

from typing import Any

from pydantic import Field

from bomgen.models._base import InputModel
from bomgen.models.library import CatalogueChoice
from bomgen.models.panel import Enclosure, PanelKind
from bomgen.models.project import LooseExtra, Spares
from bomgen.models.substation import DesignBasis, Equipment


class TemplatePanels(InputModel):
    """The generated panels' look; their numbers and documents are the new substation's."""

    cabinet_name: str | None = None
    tag_prefix: str | None = None
    kind: PanelKind | None = None
    enclosure: Enclosure | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class SubstationTemplate(InputModel):
    name: str
    description: str | None = None
    design_basis: DesignBasis | None = None
    catalogue_choice: CatalogueChoice | None = None
    spares: Spares | None = None
    panels: TemplatePanels | None = None
    equipment: list[Equipment] = Field(default_factory=list)  # parts and roles, quantity 1
    loose_items: list[LooseExtra] = Field(default_factory=list)  # no fed_from: no panels yet
