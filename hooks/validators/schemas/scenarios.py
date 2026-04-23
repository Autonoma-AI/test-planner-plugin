"""Schema for autonoma/scenarios.md frontmatter."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from .common import NonEmptyStr, TokenStr


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NonEmptyStr
    description: NonEmptyStr
    entity_types: list[NonEmptyStr]
    total_entities: StrictInt = Field(ge=0)


class EntityType(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: NonEmptyStr


class VariableField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: TokenStr
    entity: NonEmptyStr
    scenarios: list[NonEmptyStr] = Field(min_length=1)
    reason: NonEmptyStr
    test_reference: NonEmptyStr


class ScenariosDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_count: StrictInt = Field(ge=3)
    scenarios: list[Scenario]
    entity_types: list[EntityType] = Field(min_length=1)
    variable_fields: list[VariableField]
    planning_sections: list[NonEmptyStr] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_document(self) -> "ScenariosDocument":
        if len(self.scenarios) != self.scenario_count:
            raise ValueError(
                f"scenarios list length ({len(self.scenarios)}) must match scenario_count ({self.scenario_count})"
            )

        names = {scenario.name for scenario in self.scenarios}
        missing_names = {"standard", "empty", "large"} - names
        if missing_names:
            raise ValueError(f"Missing required scenarios: {sorted(missing_names)}")

        for index, variable in enumerate(self.variable_fields):
            for name in variable.scenarios:
                if name not in names:
                    raise ValueError(
                        f"variable_fields[{index}].scenarios references unknown scenario: {name}"
                    )

        required_sections = {"schema_summary", "relationship_map", "variable_data_strategy"}
        missing_sections = required_sections - set(self.planning_sections)
        if missing_sections:
            raise ValueError(f"planning_sections missing required entries: {sorted(missing_sections)}")
        return self
