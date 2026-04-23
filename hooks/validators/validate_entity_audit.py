#!/usr/bin/env python3
"""Validates entity-audit.md frontmatter format."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from schemas.common import format_errors, load_yaml_frontmatter
from schemas.entity_audit import EntityAuditDocument


def main() -> int:
    path = Path(sys.argv[1])
    try:
        fm, body = load_yaml_frontmatter(path)
        audit = EntityAuditDocument.model_validate(fm)
    except ValidationError as exc:
        print(format_errors(exc), file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    computed_factory_count = audit.computed_factory_count
    if computed_factory_count != fm["factory_count"]:
        sys.stderr.write(
            f'[validate-entity-audit] autofixing factory_count: was '
            f'{fm["factory_count"]}, now {computed_factory_count}\n'
        )
        fm["factory_count"] = computed_factory_count
        new_fm = yaml.safe_dump(fm, sort_keys=False).rstrip() + "\n"
        path.write_text("---\n" + new_fm + "---" + body)

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
