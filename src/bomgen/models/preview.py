"""The Device preview: every generated unit with its place, MCBs and strips (M24).

Built by ``engine.preview.device_preview``; part-picking design §6 and ADR 0013.
"""

from typing import Literal

from bomgen.models.output import OutputModel


class PreviewMcb(OutputModel):
    tag: str
    rating_a: int
    at_minimum: bool  # the rating is the branch floor (min_branch_mcb_a)


class PreviewUnit(OutputModel):
    device: str  # the equipment id
    role: str
    tag: str | None
    part_id: str  # the part the BOM uses, a derived part when overridden (ADR 0024)
    library_part_id: str
    n: int
    side: Literal["a", "b"] | None
    bom_code: str | None
    has_part_number: bool
    overridden: tuple[str, ...]  # the PartOverrides fields the entry sets
    placed: bool  # False: the panel has no room left for it
    din_rail: bool
    pinned: bool
    waist: bool  # a KVM or console
    away_from_waist: bool  # pinned elsewhere than waist height
    top_u: int | None  # the top of its block, U1 at the bottom; None on DIN rail or unplaced
    height_u: int
    cable_manager_u: int
    watts: float | None
    supply: str | None  # e.g. "125 VDC"
    ps1: PreviewMcb | None  # feed 1, or the QCOD of a single-fed unit
    ps2: PreviewMcb | None  # feed 2
    strips: tuple[str, ...]  # the unit's own terminal strip codes


class PreviewPanel(OutputModel):
    panel_id: str
    name: str
    number: int
    side: Literal["a", "b"] | None
    used_u: int
    overflow_u: int
    base_frame_mm: int | None
    units: tuple[PreviewUnit, ...]  # placed in stack order, then unplaced, then DIN rail


class PreviewIssue(OutputModel):
    severity: Literal["error", "warning"]
    kind: str
    message: str
    subject: str | None = None
    device: str | None = None
    panel: int | None = None


class DevicePreview(OutputModel):
    waist_u: int
    waist_height_mm: int
    rack_start_mm: int
    capacity_u: int
    enclosure_u: int
    panels: tuple[PreviewPanel, ...]
    issues: tuple[PreviewIssue, ...]
