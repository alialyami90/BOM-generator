"""Project file model: project info, library, document register and defaults (ADR 0012).

Also holds the settings models a substation file shares with it (spec: Inputs the tool
needs, 3. Project settings; ADR 0010). Paths stay as written (relative to the file that
holds them); the loader resolves them.
"""

from pathlib import Path
from string import Formatter
from typing import Annotated

from pydantic import (
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    StringConstraints,
    field_validator,
    model_validator,
)

from bomgen.models._base import (
    DocumentKey,
    ExcelSheetName,
    InputModel,
    PartId,
    Quantity,
    check_template,
)
from bomgen.models.library import CatalogueChoice
from bomgen.models.panel import DocumentInfo, PanelId

FILE_NAME_PLACEHOLDERS = {"doc_no", "rev"}
_FILE_NAME_FORBIDDEN = set('<>:"/\\|?*')


class SheetNames(InputModel):
    loose_material: ExcelSheetName = "Loose Material"  # ADR 0020
    power_consumption: ExcelSheetName = "Power Consumption"
    heat_dissipation: ExcelSheetName = "Heat Dissipation"
    heat_calculations: ExcelSheetName = "Heat Calculations"


class OutputSettings(InputModel):
    """Workbook file name template, the names of the generated sheets, and the footnotes the
    Power Consumption sheet prints after its NOTES (spec: Power Consumption sheet)."""

    file_name: str = "{doc_no}_PSA_BOM_Rev{rev}.xlsx"
    sheet_names: SheetNames = Field(default_factory=SheetNames)
    power_footnotes: list[str] = Field(default_factory=list)  # one row each; "\n" breaks the line

    @field_validator("power_footnotes")
    @classmethod
    def _footnotes_not_blank(cls, value: list[str]) -> list[str]:
        if any(not note.strip() for note in value):
            raise ValueError("a power footnote must not be blank")
        return value

    @field_validator("file_name")
    @classmethod
    def _valid_file_name(cls, value: str) -> str:
        check_template(value, FILE_NAME_PLACEHOLDERS)
        for _text, name, spec, conversion in Formatter().parse(value):
            if name is not None and (name not in FILE_NAME_PLACEHOLDERS or spec or conversion):
                raise ValueError(
                    f"placeholder '{name}' must be written plainly, as {{doc_no}} or {{rev}}, "
                    "without attribute or index access, conversion or format spec"
                )
        if not value.endswith(".xlsx"):
            raise ValueError("file name must end in .xlsx")
        literal = "".join(text for text, _name, _spec, _conv in Formatter().parse(value))
        bad = sorted(set(literal) & _FILE_NAME_FORBIDDEN)
        if bad:
            raise ValueError(f"file name must not contain any of {' '.join(bad)}")
        return value

    def resolve_file_name(self, doc_no: str, rev: str) -> str:
        """Return the workbook file name for a document number and revision."""
        return self.file_name.format(doc_no=doc_no, rev=rev)


class ConstantOverrides(InputModel):
    """Design constants as written in a file; unwritten keys keep the inherited value."""

    dc_voltage_v: PositiveFloat = 125
    ac_voltage_v: PositiveFloat = 230
    power_margin: NonNegativeFloat = 0.25
    current_factor: PositiveFloat = 1.3
    btu_per_w: PositiveFloat = 3.41
    t_max_c: float = 35
    t_int_c: float = 25
    air_constant_m3k_per_wh: PositiveFloat = 4.1
    steel_coefficient_w_per_m2c: PositiveFloat = 5.5
    min_main_mcb_a: PositiveInt = 6
    min_branch_mcb_a: PositiveInt = 2  # the smallest branch MCB (ADR 0017)
    inrush_min_ms: PositiveFloat = 10  # shorter inrush does not size the branch MCB
    dc_float_v: PositiveFloat = 140  # battery float voltage, checked against input_v_max


class DesignConstants(ConstantOverrides):
    """Calculation constants with the spec's defaults (Inputs, 3. Project settings)."""

    @model_validator(mode="after")
    def _t_max_above_t_int(self) -> "DesignConstants":
        if self.t_max_c <= self.t_int_c:
            raise ValueError("t_max_c must be greater than t_int_c")
        return self


class LooseExtra(InputModel):
    """A loose-material row: a library part, optionally with kit children and a feeding
    panel, or a free-text item with only a description (ADR 0022)."""

    part_id: PartId | None = None
    description: str | None = None  # a free-text item's description
    qty: Quantity = 1
    tag: str | None = None
    children: list[PartId] = Field(default_factory=list)
    fed_from: str | None = None

    @model_validator(mode="after")
    def _part_or_description(self) -> "LooseExtra":
        text = (self.description or "").strip()
        if (self.part_id is None) == (not text):
            raise ValueError("a loose item names a library part_id or a description (exactly one)")
        if self.part_id is None:
            for key in ("children", "fed_from"):
                if getattr(self, key):
                    raise ValueError(f"{key} needs a library part; a free-text item has none")
        return self


class LooseMaterial(InputModel):
    title: str = "PSA Panels Loose Material and Auxiliary Equipment"  # the table's title row
    host_panel: str  # the panel whose document the Loose Material sheet is issued under
    items: list[LooseExtra] = Field(default_factory=list)


class Spares(InputModel):
    """Every spare as a user input, defaults as today (ADR 0013)."""

    port_fraction: Annotated[float, Field(ge=0, lt=1)] = 0.20
    sfp_per_l1: NonNegativeInt = 3
    dc_branches_per_feed: NonNegativeInt = 3
    ac_branches: NonNegativeInt = 1
    rack_u_reserved: NonNegativeInt = 10


def merge_defaults[M: InputModel](base: M, override: InputModel | None) -> M:
    """``base`` with the keys written in ``override`` replaced, validated again as a whole."""
    if override is None:
        return base
    written = {name: getattr(override, name) for name in override.model_fields_set}
    return type(base).model_validate(base.model_dump() | written)


class ProjectInfo(InputModel):
    id: PanelId
    name: str
    client: str | None = None
    logo: Path | None = None


LibraryVersion = Annotated[
    str,
    StringConstraints(
        pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(\+local\.[1-9][0-9]*)?$"
    ),
]


class LibrarySelection(InputModel):
    """The installed library every substation uses; ``file`` loads one from disk instead."""

    name: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")]
    version: LibraryVersion
    file: Path | None = None


class RegisterEntry(DocumentInfo):
    """One document of the project's register; ``key`` is what panels and sheets name."""

    key: DocumentKey
    substation: PanelId
    title: str | None = None


class Defaults(InputModel):
    """Values every substation inherits key by key."""

    constants: DesignConstants = Field(default_factory=DesignConstants)
    spares: Spares = Field(default_factory=Spares)
    catalogue_choice: CatalogueChoice = Field(default_factory=CatalogueChoice)


class Project(InputModel):
    """The project file (``project.yaml``)."""

    project: ProjectInfo
    library: LibrarySelection
    documents: list[RegisterEntry] = Field(default_factory=list)
    defaults: Defaults = Field(default_factory=Defaults)
    substations: list[Path]  # required, but a new project may list none yet

    @field_validator("documents")
    @classmethod
    def _unique_keys(cls, entries: list[RegisterEntry]) -> list[RegisterEntry]:
        seen: set[str] = set()
        for entry in entries:
            if entry.key in seen:
                raise ValueError(f"duplicate document key '{entry.key}'")
            seen.add(entry.key)
        return entries
