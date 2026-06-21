from pydantic import BaseModel

from app.verification.models import ExtractedLabel, VerificationResult


class ErrorResponse(BaseModel):
    message: str
    errors: dict[str, str]


class VerifyResponse(BaseModel):
    verification: VerificationResult
    latency_ms: int
    extracted_label: ExtractedLabel
