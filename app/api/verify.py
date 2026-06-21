from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.api.models import ErrorResponse, VerifyResponse
from app.verification.comparisons import verify_label
from app.verification.models import ApplicationData
from app.vision.service import VisionService


MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
REQUIRED_FIELDS = [
    "brand_name",
    "product_class",
    "producer",
    "country_of_origin",
    "abv",
    "net_contents",
    "government_warning",
]

logger = logging.getLogger(__name__)
router = APIRouter()

OptionalForm = Annotated[str | None, Form()]
VisionServiceProvider = Callable[[], VisionService]


def get_vision_service_provider() -> VisionServiceProvider:
    return VisionService.from_env


def _error_response(status_code: int, message: str, errors: dict[str, str]) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(message=message, errors=errors).model_dump(),
    )


def _latency_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _log_request(
    *,
    latency_ms: int,
    verdict: str,
    failure_count: int,
    content_type: str | None,
    upload_size: int,
    event: str = "verify_request_complete",
) -> None:
    exceeded_budget = latency_ms > 5000
    log = logger.warning if exceeded_budget else logger.info
    log(
        "%s latency_ms=%s verdict=%s failure_count=%s content_type=%s upload_size=%s exceeded_budget=%s",
        event,
        latency_ms,
        verdict,
        failure_count,
        content_type,
        upload_size,
        exceeded_budget,
    )


def _validate_fields(values: dict[str, str | None]) -> tuple[dict[str, str], dict[str, str]]:
    cleaned: dict[str, str] = {}
    errors: dict[str, str] = {}

    for field in REQUIRED_FIELDS:
        value = values.get(field)
        if value is None:
            errors[field] = "This field is required."
            continue

        stripped = value.strip()
        if not stripped:
            errors[field] = "This field cannot be empty."
            continue

        cleaned[field] = stripped

    return cleaned, errors


async def _validate_image(image: UploadFile | None) -> tuple[bytes | None, dict[str, str], int]:
    if image is None:
        return None, {"image": "Image file is required."}, 0

    if image.content_type not in ALLOWED_IMAGE_TYPES:
        return None, {"image": "Unsupported file type."}, 0

    data = await image.read()
    size = len(data)
    if size > MAX_UPLOAD_BYTES:
        return None, {"image": "File is larger than 8 MB."}, size

    return data, {}, size


@router.post(
    "/verify",
    response_model=VerifyResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def verify_endpoint(
    vision_service_provider: Annotated[VisionServiceProvider, Depends(get_vision_service_provider)],
    image: Annotated[UploadFile | None, File()] = None,
    brand_name: OptionalForm = None,
    product_class: OptionalForm = None,
    producer: OptionalForm = None,
    country_of_origin: OptionalForm = None,
    abv: OptionalForm = None,
    net_contents: OptionalForm = None,
    government_warning: OptionalForm = None,
) -> VerifyResponse | JSONResponse:
    start = time.perf_counter()
    content_type = image.content_type if image else None

    field_values = {
        "brand_name": brand_name,
        "product_class": product_class,
        "producer": producer,
        "country_of_origin": country_of_origin,
        "abv": abv,
        "net_contents": net_contents,
        "government_warning": government_warning,
    }
    cleaned_fields, field_errors = _validate_fields(field_values)
    image_bytes, image_errors, upload_size = await _validate_image(image)
    errors = {**image_errors, **field_errors}

    if errors:
        status_code = 415 if "Unsupported file type" in errors.get("image", "") else 400
        if "larger than 8 MB" in errors.get("image", ""):
            status_code = 413

        latency = _latency_ms(start)
        _log_request(
            latency_ms=latency,
            verdict="INVALID",
            failure_count=len(errors),
            content_type=content_type,
            upload_size=upload_size,
            event="verify_request_invalid",
        )
        return _error_response(
            status_code,
            "Please provide an image and all required label fields.",
            errors,
        )

    application = ApplicationData(**cleaned_fields)

    try:
        vision_service = vision_service_provider()
        extracted = await vision_service.extract_label(
            image_bytes or b"",
            filename=image.filename if image else None,
            content_type=content_type,
        )
        verification = verify_label(application, extracted)
    except Exception:
        latency = _latency_ms(start)
        logger.exception(
            "verify_request_failed latency_ms=%s content_type=%s upload_size=%s",
            latency,
            content_type,
            upload_size,
        )
        return _error_response(
            500,
            "Verification failed unexpectedly.",
            {"server": "Unexpected internal failure."},
        )

    latency = _latency_ms(start)
    failure_count = sum(field.status == "FAIL" for field in verification.fields)
    _log_request(
        latency_ms=latency,
        verdict=verification.verdict,
        failure_count=failure_count,
        content_type=content_type,
        upload_size=upload_size,
    )

    return VerifyResponse(
        verification=verification,
        latency_ms=latency,
        extracted_label=extracted,
    )
