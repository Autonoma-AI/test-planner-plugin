from pydantic import ValidationError
import pytest

from schemas.sdk_endpoint import SdkEndpoint


def test_sdk_endpoint_accepts_http_url():
    assert SdkEndpoint.model_validate({"url": "http://localhost:3000"}).url == "http://localhost:3000"


def test_sdk_endpoint_rejects_relative_url():
    with pytest.raises(ValidationError, match="http or https"):
        SdkEndpoint.model_validate({"url": "/api/autonoma"})
