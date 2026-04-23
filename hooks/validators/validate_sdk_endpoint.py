#!/usr/bin/env python3
"""Validates autonoma/.sdk-endpoint."""
from __future__ import annotations

import sys
from pathlib import Path

from pydantic import ValidationError

from schemas.common import format_errors
from schemas.sdk_endpoint import SdkEndpoint


def main() -> int:
    try:
        value = Path(sys.argv[1]).read_text().strip()
        SdkEndpoint.model_validate({"url": value})
    except ValidationError as exc:
        print(format_errors(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Unable to read file: {exc}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
