#!/usr/bin/env python3
"""Validates scenarios.md frontmatter format."""
from __future__ import annotations

import sys
from pathlib import Path

from pydantic import ValidationError

from schemas.common import format_errors, load_yaml_frontmatter
from schemas.scenarios import ScenariosDocument


def main() -> int:
    try:
        fm, _body = load_yaml_frontmatter(Path(sys.argv[1]))
        ScenariosDocument.model_validate(fm)
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
