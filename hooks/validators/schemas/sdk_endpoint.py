"""Schema for autonoma/.sdk-endpoint."""
from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, field_validator

from .common import NonEmptyStr


class SdkEndpoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: NonEmptyStr

    @field_validator("url")
    @classmethod
    def must_be_http_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(".sdk-endpoint must use http or https")
        if not parsed.netloc:
            raise ValueError(".sdk-endpoint must include a host")
        return value
