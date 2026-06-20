from typing import Literal

from pydantic import BaseModel


class ApplicationData(BaseModel):
    brand_name: str
    product_class: str
    producer: str
    country_of_origin: str
    abv: str
    net_contents: str
    government_warning: str


class ExtractedLabel(BaseModel):
    brand_name: str | None = None
    product_class: str | None = None
    producer: str | None = None
    country_of_origin: str | None = None
    abv: str | None = None
    net_contents: str | None = None
    government_warning: str | None = None


class FieldResult(BaseModel):
    field: str
    status: Literal["PASS", "FAIL"]
    application_value: str
    extracted_value: str | None
    strategy: str
    score: float | None = None
    normalized_application_value: str | None = None
    normalized_extracted_value: str | None = None
    message: str


class VerificationResult(BaseModel):
    verdict: Literal["PASS", "NEEDS_REVIEW"]
    fields: list[FieldResult]
