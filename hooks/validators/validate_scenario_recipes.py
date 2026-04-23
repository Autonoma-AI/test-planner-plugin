#!/usr/bin/env python3
"""Validates autonoma/scenario-recipes.json schema."""
from __future__ import annotations

import sys
from pathlib import Path

from pydantic import ValidationError

from schemas.common import format_errors, load_json_object
from schemas.discover import DiscoverDocument
from schemas.scenario_recipes import ScenarioRecipesDocument, cross_check, resolve_source_path


def main() -> int:
    path = Path(sys.argv[1])
    try:
        recipes = ScenarioRecipesDocument.model_validate(load_json_object(path))

        discover_path = resolve_source_path(path, recipes.source.discoverPath)
        if not discover_path.is_file():
            raise ValueError(f"source.discoverPath does not exist: {recipes.source.discoverPath}")
        discover = DiscoverDocument.model_validate(load_json_object(discover_path))
        cross_check(recipes, discover)
    except ValidationError as exc:
        print(format_errors(exc), file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
