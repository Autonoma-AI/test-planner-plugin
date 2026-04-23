"""Schema for AUTONOMA.md frontmatter."""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from .common import NonEmptyStr


AppDescription = Annotated[str, Field(min_length=20)]


class CoreFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature: NonEmptyStr
    description: NonEmptyStr
    core: StrictBool


class AutonomaKB(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_name: NonEmptyStr
    app_description: AppDescription
    core_flows: list[CoreFlow] = Field(min_length=1)
    feature_count: StrictInt = Field(ge=1)
    skill_count: StrictInt = Field(ge=1)

    @model_validator(mode="after")
    def has_core_flow(self) -> "AutonomaKB":
        if not any(flow.core for flow in self.core_flows):
            raise ValueError("At least one core_flow must have core: true")
        return self
