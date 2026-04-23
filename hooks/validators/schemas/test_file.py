"""Schema for individual qa-tests markdown frontmatter."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .common import Criticality, NonEmptyStr


__test__ = False


class TestFileDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: NonEmptyStr
    description: NonEmptyStr
    criticality: Criticality
    scenario: NonEmptyStr
    flow: NonEmptyStr
