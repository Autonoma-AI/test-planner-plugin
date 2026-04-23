"""Schema and discover cross-checks for autonoma/scenario-recipes.json."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, StrictInt, model_validator

from .common import NonEmptyStr
from .discover import DiscoverDocument


TYPE_PATTERN = re.compile(r"^(?:[A-Za-z][A-Za-z0-9_]*|enum\([^()]+\))(?:\[\])?$")
TOKEN_OR_REF_PATTERN = re.compile(r"^(?:\{\{\w+\}\}|_ref:.+)$")
TOKEN_PATTERN = re.compile(r"\{\{(\w+)\}\}")


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discoverPath: NonEmptyStr
    scenariosPath: NonEmptyStr


class Validation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["validated"]
    method: Literal["checkScenario", "checkAllScenarios", "endpoint-up-down"]
    phase: Literal["ok"]
    up_ms: StrictInt | None = Field(default=None, ge=0)
    down_ms: StrictInt | None = Field(default=None, ge=0)


class VariableDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: Literal["literal", "derived", "faker"]
    value: Any = None
    source: str | None = None
    format: str | None = None
    generator: str | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "VariableDefinition":
        if self.strategy == "literal":
            if "value" not in self.model_fields_set:
                raise ValueError('literal must have "value"')
            if not isinstance(self.value, (str, int, float, bool)) and self.value is not None:
                raise ValueError("literal.value must be a scalar")
        elif self.strategy == "derived":
            if self.source != "testRunId":
                raise ValueError('derived.source must be "testRunId"')
            if not isinstance(self.format, str) or not self.format.strip():
                raise ValueError("derived.format must be a non-empty string")
        elif self.strategy == "faker":
            if not isinstance(self.generator, str) or not self.generator.strip():
                raise ValueError("faker.generator must be a non-empty string")
        return self


class Variables(RootModel[dict[str, VariableDefinition]]):
    pass


class Recipe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NonEmptyStr
    description: NonEmptyStr
    create: dict[str, list[dict[str, Any]]] = Field(min_length=1)
    validation: Validation
    variables: Variables | None = None

    @model_validator(mode="after")
    def validate_variables(self) -> "Recipe":
        if self.variables is None:
            return self

        tokens_in_create = _find_tokens(self.create)
        var_keys = set(self.variables.root)
        missing_vars = tokens_in_create - var_keys
        if missing_vars:
            raise ValueError(f"tokens without variable definitions: {sorted(missing_vars)}")
        unused_vars = var_keys - tokens_in_create
        if unused_vars:
            raise ValueError(f"unused variable definitions: {sorted(unused_vars)}")
        return self


class ScenarioRecipesDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    source: Source
    validationMode: Literal["sdk-check", "endpoint-lifecycle"]
    recipes: list[Recipe] = Field(min_length=3)

    @model_validator(mode="after")
    def has_required_recipes(self) -> "ScenarioRecipesDocument":
        names = {recipe.name for recipe in self.recipes}
        missing_names = {"standard", "empty", "large"} - names
        if missing_names:
            raise ValueError(f"Missing required recipes: {sorted(missing_names)}")
        return self


def resolve_source_path(filepath: Path, source_path: str) -> Path:
    recipe_dir = filepath.resolve().parent
    raw_path = Path(source_path)
    if raw_path.is_absolute():
        return raw_path

    for base_dir in (recipe_dir, *recipe_dir.parents):
        candidate = (base_dir / source_path).resolve()
        if candidate.is_file():
            return candidate
    return (recipe_dir / source_path).resolve()


def build_discover_info(discover: DiscoverDocument) -> dict[str, Any]:
    model_map: dict[str, dict[str, Any]] = {}
    for model in discover.schema.models:
        field_map: dict[str, Any] = {}
        for field in model.fields:
            field_map[field.name] = field
        model_map[model.name] = field_map

    relation_fields: set[str] = set()
    nestable_fk_edges: dict[tuple[str, str], str] = {}
    for relation in discover.schema.relations:
        relation_fields.add(relation.parentField)
        child_model = relation.childModel
        child_fk = relation.childField
        parent_model = relation.parentModel
        if child_model in model_map and child_fk in model_map[child_model]:
            nestable_fk_edges[(child_model, child_fk)] = parent_model

    return {
        "models": model_map,
        "relation_fields": relation_fields,
        "nestable_fk_edges": nestable_fk_edges,
    }


def cross_check(recipes: ScenarioRecipesDocument, discover: DiscoverDocument) -> None:
    discover_info = build_discover_info(discover)
    for index, recipe in enumerate(recipes.recipes):
        error = _validate_create_against_discover(recipe.create, discover_info, index)
        if error is not None:
            raise ValueError(error)


def _find_tokens(obj: Any) -> set[str]:
    tokens: set[str] = set()
    if isinstance(obj, str):
        tokens.update(TOKEN_PATTERN.findall(obj))
    elif isinstance(obj, list):
        for item in obj:
            tokens.update(_find_tokens(item))
    elif isinstance(obj, dict):
        for value in obj.values():
            tokens.update(_find_tokens(value))
    return tokens


def _parse_type(type_name: str) -> dict[str, Any] | None:
    if not isinstance(type_name, str):
        return None
    is_list = type_name.endswith("[]")
    base = type_name[:-2] if is_list else type_name
    if not TYPE_PATTERN.match(type_name):
        return None
    if base.startswith("enum(") and base.endswith(")"):
        values = [value.strip() for value in base[5:-1].split(",") if value.strip()]
        return {"kind": "enum", "values": values, "is_list": is_list}
    return {"kind": "scalar", "name": base, "is_list": is_list}


def _validate_value_against_field(value: Any, field: Any, path: str) -> str | None:
    parsed_type = _parse_type(field.type)
    if parsed_type is None:
        return f"{path} has unsupported discover type: {field.type}"

    if isinstance(value, str) and TOKEN_OR_REF_PATTERN.match(value):
        return None

    if parsed_type["is_list"]:
        if not isinstance(value, list):
            return f"{path} must be a list because discover type is {field.type}"
        return None

    if isinstance(value, list):
        return f"{path} must not be a list because discover type is {field.type}"

    if parsed_type["kind"] == "enum" and isinstance(value, str):
        if value not in parsed_type["values"]:
            return f'{path} has invalid enum value "{value}". Expected one of {parsed_type["values"]}'

    return None


def _validate_create_against_discover(create: dict[str, list[dict[str, Any]]], discover_info: dict[str, Any], recipe_index: int) -> str | None:
    model_map = discover_info["models"]
    relation_fields = discover_info["relation_fields"]
    nestable_fk_edges = discover_info.get("nestable_fk_edges", {})
    top_level_models = set(create.keys())

    for model_name, entities in create.items():
        if model_name not in model_map:
            return f"recipes[{recipe_index}].create.{model_name} is not present in discover schema"
        if not isinstance(entities, list):
            return f"recipes[{recipe_index}].create.{model_name} must be an array"

        field_map = model_map[model_name]
        for entity_index, entity in enumerate(entities):
            if not isinstance(entity, dict):
                return f"recipes[{recipe_index}].create.{model_name}[{entity_index}] must be an object"
            for field_name, value in entity.items():
                if field_name.startswith("_"):
                    continue
                if field_name in relation_fields:
                    continue
                if field_name not in field_map:
                    return (
                        f"recipes[{recipe_index}].create.{model_name}[{entity_index}].{field_name} "
                        "is not present in discover schema"
                    )

                if isinstance(value, dict) and "_ref" in value and len(value) == 1:
                    parent_model = nestable_fk_edges.get((model_name, field_name))
                    if parent_model and parent_model in top_level_models:
                        return (
                            f"recipes[{recipe_index}].create.{model_name}[{entity_index}].{field_name} "
                            f'uses {{"_ref": "..."}} but {model_name} should be nested under '
                            f"{parent_model} using the relation field instead of flat _ref. "
                            "The dashboard may reorder JSON keys, which breaks flat _ref resolution. "
                            "Use a nested tree structure rooted at the scope entity."
                        )

                error = _validate_value_against_field(
                    value,
                    field_map[field_name],
                    f"recipes[{recipe_index}].create.{model_name}[{entity_index}].{field_name}",
                )
                if error is not None:
                    return error
    return None
