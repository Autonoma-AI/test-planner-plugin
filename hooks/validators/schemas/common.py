"""Shared schema helpers for pipeline validators."""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import StringConstraints, ValidationError


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TokenStr = Annotated[str, StringConstraints(pattern=r"^\{\{\w+\}\}$")]


class Criticality(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MID = "mid"
    LOW = "low"


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        with path.open() as fh:
            payload = json.load(fh)
    except Exception as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Root must be a JSON object")
    return payload


def load_yaml_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    content = path.read_text()
    if not content.startswith("---"):
        raise ValueError("File must start with YAML frontmatter (---)")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Missing closing --- for frontmatter")

    try:
        fm = yaml.safe_load(parts[1])
    except Exception as exc:
        raise ValueError(f"Invalid YAML in frontmatter: {exc}") from exc

    if not isinstance(fm, dict):
        raise ValueError("Frontmatter must be a YAML mapping")
    return fm, parts[2]


def format_errors(exc: ValidationError) -> str:
    lines: list[str] = []
    for err in exc.errors():
        loc = _format_loc(err.get("loc", ()))
        msg = str(err.get("msg", "Invalid value"))
        if msg.startswith("Value error, "):
            msg = msg.removeprefix("Value error, ")
        lines.append(f"{loc}: {msg}" if loc else msg)
    return "\n".join(lines)


def _format_loc(loc: tuple[Any, ...] | list[Any]) -> str:
    out = ""
    for part in loc:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out
