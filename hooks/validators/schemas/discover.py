"""Schema for autonoma/discover.json."""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

from .common import NonEmptyStr


TypeName = Annotated[str, Field(pattern=r"^(?:[A-Za-z][A-Za-z0-9_]*|enum\([^()]+\))(?:\[\])?$")]


class FieldModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: NonEmptyStr
    type: TypeName
    isRequired: StrictBool
    isId: StrictBool
    hasDefault: StrictBool


class ModelModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: NonEmptyStr
    fields: list[FieldModel]


class Edge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_: NonEmptyStr = Field(alias="from")
    to: NonEmptyStr
    localField: NonEmptyStr
    foreignField: NonEmptyStr
    nullable: StrictBool


class Relation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parentModel: NonEmptyStr
    childModel: NonEmptyStr
    parentField: NonEmptyStr
    childField: NonEmptyStr


class DiscoverSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    models: list[ModelModel] = Field(min_length=1)
    edges: list[Edge]
    relations: list[Relation]
    scopeField: NonEmptyStr


class DiscoverDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: DiscoverSchema = Field(alias="schema")

    @property
    def schema(self) -> DiscoverSchema:
        return self.schema_

    @field_validator("schema_", mode="before")
    @classmethod
    def schema_must_be_object(cls, value: object) -> object:
        if not isinstance(value, dict):
            raise ValueError('discover.json must contain a "schema" object')
        return value
