"""Schema for autonoma/.scenario-validation.json."""
from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, StrictBool, field_validator

from .common import NonEmptyStr


class ScenarioValidationDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "failed"]
    preflightPassed: StrictBool
    smokeTestPassed: StrictBool
    validatedScenarios: list[str]
    failedScenarios: list[str]
    blockingIssues: list[str]
    recipePath: NonEmptyStr
    validationMode: Literal["sdk-check", "endpoint-lifecycle"]
    endpointUrl: NonEmptyStr

    @field_validator("endpointUrl")
    @classmethod
    def absolute_http_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("endpointUrl must be an absolute http/https URL")
        return value
