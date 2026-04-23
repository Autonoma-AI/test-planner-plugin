"""Schema for autonoma/entity-audit.md frontmatter."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from .common import NonEmptyStr


class CreatedBy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner: NonEmptyStr
    via: NonEmptyStr
    why: NonEmptyStr


class AuditModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: NonEmptyStr
    independently_created: StrictBool | None = None
    has_creation_code: StrictBool | None = None
    creation_file: str | None = None
    creation_function: str | None = None
    side_effects: list[Any] | None = None
    created_by: list[CreatedBy] | None = None

    @model_validator(mode="after")
    def has_classification(self) -> "AuditModel":
        if self.independently_created is None and self.has_creation_code is None:
            raise ValueError("missing classification (independently_created or has_creation_code)")
        return self

    @property
    def is_v2(self) -> bool:
        return self.independently_created is not None

    @property
    def is_independent(self) -> bool:
        if self.independently_created is not None:
            return self.independently_created
        return bool(self.has_creation_code)


class EntityAuditDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_count: StrictInt = Field(ge=0)
    factory_count: StrictInt = Field(ge=0)
    models: list[AuditModel] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_document(self) -> "EntityAuditDocument":
        if self.model_count < 1:
            raise ValueError("model_count must be at least 1 - no models were audited")
        if len(self.models) != self.model_count:
            raise ValueError(
                f"model_count ({self.model_count}) does not match models array length ({len(self.models)})"
            )

        names = {model.name for model in self.models}
        for index, model in enumerate(self.models):
            if model.is_independent:
                if not isinstance(model.creation_file, str):
                    raise ValueError(
                        f"models[{index}] ({model.name}) independently_created=true but missing creation_file"
                    )
                if not isinstance(model.creation_function, str):
                    raise ValueError(
                        f"models[{index}] ({model.name}) independently_created=true but missing creation_function"
                    )

            if model.created_by is None:
                if model.is_v2:
                    raise ValueError(
                        f"models[{index}] ({model.name}) missing required field: created_by (list, may be empty)"
                    )
                continue

            if not model.is_independent and len(model.created_by) == 0:
                raise ValueError(
                    f"models[{index}] ({model.name}) is marked independently_created=false but has no "
                    "created_by entries. Every dependent must have at least one owner - "
                    "either find the creation path, or mark the model independently_created=true."
                )

            for owner_index, owner_entry in enumerate(model.created_by):
                if owner_entry.owner not in names:
                    raise ValueError(
                        f"models[{index}] ({model.name}).created_by[{owner_index}].owner={owner_entry.owner!r} "
                        "does not match any model in the audit. Check the owner name or add the owner model."
                    )
                if owner_entry.owner == model.name:
                    raise ValueError(
                        f"models[{index}] ({model.name}).created_by[{owner_index}].owner cannot be the model itself"
                    )
        return self

    @property
    def computed_factory_count(self) -> int:
        return sum(1 for model in self.models if model.is_independent)
