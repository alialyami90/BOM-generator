"""Project file model: project info, documents, output settings and design constants.

Models the spec section "Inputs the tool needs" (3. Project settings) and ADR 0010.
Paths stay as written (relative to the project file); the loader resolves them.
"""

from pathlib import Path
from string import Formatter

from pydantic import (
    Field,
    NonNegativeFloat,
    PositiveFloat,
    PositiveInt,
    field_validator,
    model_validator,
)

from bomgen.models._base import ExcelSheetName, InputModel, PartId, Quantity, Rev, check_template
from bomgen.models.panel import DocumentInfo

FILE_NAME_PLACEHOLDERS = {"doc_no", "rev"}
_FILE_NAME_FORBIDDEN = set('<>:"/\\|?*')


class ProjectInfo(InputModel):
    name: str
    substation: str
    doc_no: str
    rev: Rev = "0"
    logo: Path | None = None


class CalcDocument(DocumentInfo):
    """Header values of a calculation sheet; ``scope`` is its scope line."""

    scope: str


class Documents(InputModel):
    power_consumption: CalcDocument
    heat_dissipation: CalcDocument
    heat_calculations: CalcDocument


class SheetNames(InputModel):
    power_consumption: ExcelSheetName = "Power Consumption"
    heat_dissipation: ExcelSheetName = "Heat Dissipation"
    heat_calculations: ExcelSheetName = "Heat Calculations"


class OutputSettings(InputModel):
    """Workbook file name template and calculation sheet names."""

    file_name: str = "{doc_no}_PSA_BOM_Rev{rev}.xlsx"
    sheet_names: SheetNames = Field(default_factory=SheetNames)

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


class DesignConstants(InputModel):
    """Calculation constants with the spec's defaults (Inputs, 3. Project settings)."""

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

    @model_validator(mode="after")
    def _t_max_above_t_int(self) -> "DesignConstants":
        if self.t_max_c <= self.t_int_c:
            raise ValueError("t_max_c must be greater than t_int_c")
        return self


class LooseExtra(InputModel):
    """A loose-material row, optionally with kit children and a feeding panel."""

    part_id: PartId
    qty: Quantity = 1
    tag: str | None = None
    children: list[PartId] = Field(default_factory=list)
    fed_from: str | None = None


class LooseMaterial(InputModel):
    host_panel: str
    items: list[LooseExtra] = Field(default_factory=list)


class Project(InputModel):
    """The project file (``project.yaml``)."""

    project: ProjectInfo
    library: Path
    panels: list[Path] = Field(min_length=1)
    documents: Documents
    output: OutputSettings = Field(default_factory=OutputSettings)
    constants: DesignConstants = Field(default_factory=DesignConstants)
    loose_material: LooseMaterial | None = None
