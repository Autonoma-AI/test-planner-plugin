"""Schema for qa-tests/INDEX.md frontmatter."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from .common import NonEmptyStr
from .features import FeaturesDocument


__test__ = False


class TestFolder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NonEmptyStr
    description: NonEmptyStr
    test_count: StrictInt = Field(ge=1)
    critical: StrictInt = Field(ge=0)
    high: StrictInt = Field(ge=0)
    mid: StrictInt = Field(ge=0)
    low: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def criticality_sum_matches(self) -> "TestFolder":
        total = self.critical + self.high + self.mid + self.low
        if total != self.test_count:
            raise ValueError(
                f"criticality counts ({total}) do not sum to test_count ({self.test_count})"
            )
        return self


class CoverageCorrelation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    routes_or_features: StrictInt = Field(ge=1)
    expected_test_range_min: StrictInt
    expected_test_range_max: StrictInt

    @model_validator(mode="after")
    def min_before_max(self) -> "CoverageCorrelation":
        if self.expected_test_range_min > self.expected_test_range_max:
            raise ValueError("expected_test_range_min must be <= expected_test_range_max")
        return self


class TestIndexDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_tests: StrictInt = Field(ge=1)
    total_folders: StrictInt = Field(ge=1)
    folders: list[TestFolder]
    coverage_correlation: CoverageCorrelation

    @model_validator(mode="after")
    def validate_totals(self) -> "TestIndexDocument":
        if len(self.folders) != self.total_folders:
            raise ValueError(
                f"folders list length ({len(self.folders)}) must match total_folders ({self.total_folders})"
            )
        computed_total = sum(folder.test_count for folder in self.folders)
        if computed_total != self.total_tests:
            raise ValueError(
                f"Sum of folder test_counts ({computed_total}) does not match total_tests ({self.total_tests})"
            )
        tmin = self.coverage_correlation.expected_test_range_min
        if self.total_tests < tmin:
            rf = self.coverage_correlation.routes_or_features
            raise ValueError(
                f"total_tests ({self.total_tests}) is below minimum ({tmin}) for {rf} routes/features. Too few tests - add more coverage."
            )
        return self


def features_path_for_index(index_path: Path) -> Path:
    return index_path.parent.parent / "features.json"


def cross_check(index: TestIndexDocument, features: FeaturesDocument) -> None:
    feature_count = features.total_features
    if feature_count <= 0:
        return
    min_tests = feature_count * 2
    if index.total_tests < min_tests:
        rf = index.coverage_correlation.routes_or_features
        raise ValueError(
            f"total_tests ({index.total_tests}) is too low for {feature_count} features in features.json. "
            f"Expected at least {min_tests} tests (2 per feature). "
            f"Agent declared {rf} routes_or_features in INDEX but features.json has {feature_count}."
        )
    if index.coverage_correlation.routes_or_features < feature_count:
        raise ValueError(
            f"coverage_correlation.routes_or_features ({index.coverage_correlation.routes_or_features}) "
            f"is less than total_features in features.json ({feature_count}). The agent is underreporting features."
        )
