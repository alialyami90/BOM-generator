"""Base for the engine's output models (ADR 0005, ADR 0014)."""

from pydantic import BaseModel, ConfigDict


class OutputModel(BaseModel):
    """Base for engine output: immutable, no unknown fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)
