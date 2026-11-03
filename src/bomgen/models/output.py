"""Base for the engine's output models (ADR 0005, ADR 0014)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field


class OutputModel(BaseModel):
    """Base for engine output: immutable, no unknown fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Derived[T](OutputModel):
    """A value the engine derives and the engineer may override (plan M48): the engine's
    ``value`` with its ``rule`` text, and the ``override`` when one is written."""

    value: T
    rule: str
    override: T | None = None
    unit: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def source(self) -> Literal["engine", "override"]:
        return "engine" if self.override is None else "override"
