#!/usr/bin/env python3
"""Validates qa-tests/INDEX.md frontmatter format."""
from __future__ import annotations

import sys
from pathlib import Path

from pydantic import ValidationError

from schemas.common import format_errors, load_json_object, load_yaml_frontmatter
from schemas.features import FeaturesDocument
from schemas.test_index import TestIndexDocument, cross_check, features_path_for_index


def main() -> int:
    path = Path(sys.argv[1])
    try:
        fm, _body = load_yaml_frontmatter(path)
        index = TestIndexDocument.model_validate(fm)

        features_path = features_path_for_index(path)
        if not features_path.is_file():
            raise ValueError(
                f"features.json not found at {features_path}. Step 1 must output autonoma/features.json."
            )
        features = FeaturesDocument.model_validate(load_json_object(features_path))
        cross_check(index, features)
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
