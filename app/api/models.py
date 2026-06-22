from typing import Literal

from pydantic import BaseModel
from pydantic import Field

from app.verification.models import ExtractedLabel, VerificationResult


class ErrorResponse(BaseModel):
    message: str
    errors: dict[str, str]


class VerifyResponse(BaseModel):
    verification: VerificationResult
    latency_ms: int
    extracted_label: ExtractedLabel
    timings: dict[str, int | str | bool | None] = Field(default_factory=dict)


class BatchSummary(BaseModel):
    passed: int
    needs_review: int
    total: int
    latency_ms: int


class BatchItemResult(BaseModel):
    index: int
    filename: str | None
    status: Literal["PASS", "NEEDS_REVIEW"]
    verification: VerificationResult | None = None
    extracted_label: ExtractedLabel | None = None
    latency_ms: int
    timings: dict[str, int | str | bool | None] = Field(default_factory=dict)
    errors: dict[str, str]


class BatchVerifyResponse(BaseModel):
    summary: BatchSummary
    results: list[BatchItemResult]
