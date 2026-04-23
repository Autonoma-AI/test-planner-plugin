"""Schema for autonoma/features.json."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from .common import NonEmptyStr


class Feature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NonEmptyStr
    type: Literal["page", "api", "flow", "component", "modal", "settings"]
    path: NonEmptyStr
    core: StrictBool


class FeaturesDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: list[Feature] = Field(min_length=1)
    total_features: StrictInt = Field(ge=1)
    total_routes: StrictInt = Field(ge=0)
    total_api_routes: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def validate_counts(self) -> "FeaturesDocument":
        if self.total_features != len(self.features):
            raise ValueError(
                f"total_features ({self.total_features}) does not match features array length ({len(self.features)})"
            )
        if not any(feature.core for feature in self.features):
            raise ValueError("At least one feature must have core: true")
        return self
