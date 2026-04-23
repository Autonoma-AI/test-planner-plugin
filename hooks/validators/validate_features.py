#!/usr/bin/env python3
"""Validates autonoma/features.json schema."""
from __future__ import annotations

import sys
from pathlib import Path

from pydantic import ValidationError

from schemas.common import format_errors, load_json_object
from schemas.features import FeaturesDocument


def main() -> int:
    try:
        payload = load_json_object(Path(sys.argv[1]))
        FeaturesDocument.model_validate(payload)
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
