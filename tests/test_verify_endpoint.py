import json
import logging
from io import BytesIO

import pytest
from fastapi.responses import JSONResponse
from PIL import Image

from app.api.models import VerifyResponse
from app.api.verify import verify_endpoint
from app.verification.models import ExtractedLabel


CANONICAL_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)


class MockVisionService:
    def __init__(
        self,
        extracted: ExtractedLabel | None = None,
        error: Exception | None = None,
    ) -> None:
        self.extracted = extracted or matching_extracted_label()
        self.error = error
        self.calls = 0

    async def extract_label(
        self,
        image_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> ExtractedLabel:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.extracted


def image_bytes(image_format: str = "JPEG") -> bytes:
    image = Image.new("RGB", (64, 64), "white")
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


class MockUploadFile:
    def __init__(self, content: bytes | None = None, content_type: str = "image/jpeg") -> None:
        self._content = content if content is not None else image_bytes()
        self.content_type = content_type
        self.filename = "label.jpg"

    async def read(self) -> bytes:
        return self._content


def upload_file(content: bytes | None = None, content_type: str = "image/jpeg") -> MockUploadFile:
    return MockUploadFile(content=content, content_type=content_type)


def matching_extracted_label(**overrides: str | None) -> ExtractedLabel:
    values = {
        "brand_name": "Acme Reserve",
        "product_class": "Red Wine",
        "producer": "Acme Winery LLC",
        "country_of_origin": "USA",
        "abv": "13.5% Alc. by Vol.",
        "net_contents": "750ml",
        "government_warning": CANONICAL_WARNING,
    }
    values.update(overrides)
    return ExtractedLabel(**values)


def form_data(**overrides: str | None) -> dict[str, str | None]:
    values: dict[str, str | None] = {
        "brand_name": "Acme Reserve",
        "product_class": "Red Wine",
        "producer": "Acme Winery LLC",
        "country_of_origin": "United States",
        "abv": "13.5%",
        "net_contents": "750 mL",
        "government_warning": CANONICAL_WARNING,
    }
    values.update(overrides)
    return values


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def provider_for(mock: MockVisionService):
    return lambda: mock


def response_body(response: VerifyResponse | JSONResponse) -> dict:
    if isinstance(response, VerifyResponse):
        return response.model_dump(mode="json")
    return json.loads(response.body)


def response_status(response: VerifyResponse | JSONResponse) -> int:
    if isinstance(response, VerifyResponse):
        return 200
    return response.status_code


async def call_verify(
    mock: MockVisionService,
    *,
    data: dict[str, str | None] | None = None,
    image: MockUploadFile | None = None,
) -> VerifyResponse | JSONResponse:
    values = data if data is not None else form_data()
    return await verify_endpoint(
        vision_service_provider=provider_for(mock),
        image=image,
        brand_name=values.get("brand_name"),
        product_class=values.get("product_class"),
        producer=values.get("producer"),
        country_of_origin=values.get("country_of_origin"),
        abv=values.get("abv"),
        net_contents=values.get("net_contents"),
        government_warning=values.get("government_warning"),
    )


@pytest.mark.anyio
async def test_successful_verify_returns_full_verification_result() -> None:
    mock = MockVisionService()

    response = await call_verify(mock, image=upload_file())
    body = response_body(response)

    assert response_status(response) == 200
    assert body["verification"]["verdict"] == "PASS"
    assert len(body["verification"]["fields"]) == 7
    assert isinstance(body["latency_ms"], int)
    assert body["latency_ms"] >= 0
    assert body["extracted_label"]["government_warning"] == CANONICAL_WARNING
    assert mock.calls == 1


@pytest.mark.anyio
async def test_failure_includes_expected_vs_found_and_overall_verdict() -> None:
    mock = MockVisionService(extracted=matching_extracted_label(brand_name="Wrong Brand"))

    response = await call_verify(mock, image=upload_file())
    body = response_body(response)
    brand_result = next(
        field for field in body["verification"]["fields"] if field["field"] == "brand_name"
    )

    assert response_status(response) == 200
    assert body["verification"]["verdict"] == "NEEDS_REVIEW"
    assert brand_result["status"] == "FAIL"
    assert brand_result["application_value"] == "Acme Reserve"
    assert brand_result["extracted_value"] == "Wrong Brand"


@pytest.mark.anyio
async def test_warning_extracted_text_is_surfaced_on_failure() -> None:
    title_case_warning = CANONICAL_WARNING.replace("GOVERNMENT WARNING", "Government Warning")
    mock = MockVisionService(extracted=matching_extracted_label(government_warning=title_case_warning))

    response = await call_verify(mock, image=upload_file())
    body = response_body(response)
    warning_result = next(
        field for field in body["verification"]["fields"] if field["field"] == "government_warning"
    )

    assert response_status(response) == 200
    assert body["verification"]["verdict"] == "NEEDS_REVIEW"
    assert body["extracted_label"]["government_warning"] == title_case_warning
    assert warning_result["extracted_value"] == title_case_warning


@pytest.mark.anyio
async def test_partial_extraction_returns_needs_review_not_exception() -> None:
    mock = MockVisionService(extracted=matching_extracted_label(producer=None, abv=None))

    response = await call_verify(mock, image=upload_file())

    assert response_status(response) == 200
    assert response_body(response)["verification"]["verdict"] == "NEEDS_REVIEW"


@pytest.mark.anyio
async def test_missing_image_returns_400_readable_error() -> None:
    mock = MockVisionService()

    response = await call_verify(mock, image=None)

    assert response_status(response) == 400
    assert response_body(response)["errors"]["image"] == "Image file is required."
    assert mock.calls == 0


@pytest.mark.anyio
async def test_empty_submission_returns_400_readable_error() -> None:
    mock = MockVisionService()

    response = await call_verify(
        mock,
        data={field: None for field in form_data()},
        image=None,
    )
    body = response_body(response)

    assert response_status(response) == 400
    assert body["message"] == "Please provide an image and all required label fields."
    assert body["errors"]["image"] == "Image file is required."
    assert body["errors"]["brand_name"] == "This field is required."
    assert mock.calls == 0


@pytest.mark.anyio
async def test_unsupported_content_type_returns_415_and_does_not_call_vision() -> None:
    mock = MockVisionService()

    response = await call_verify(
        mock,
        image=upload_file(content=b"not an image", content_type="text/plain"),
    )

    assert response_status(response) == 415
    assert response_body(response)["errors"]["image"] == "Unsupported file type."
    assert mock.calls == 0


@pytest.mark.anyio
async def test_oversized_image_returns_413() -> None:
    mock = MockVisionService()

    response = await call_verify(mock, image=upload_file(content=b"x" * (8 * 1024 * 1024 + 1)))

    assert response_status(response) == 413
    assert response_body(response)["errors"]["image"] == "File is larger than 8 MB."
    assert mock.calls == 0


@pytest.mark.anyio
async def test_missing_required_field_returns_400() -> None:
    mock = MockVisionService()
    data = form_data()
    data.pop("producer")

    response = await call_verify(mock, data=data, image=upload_file())

    assert response_status(response) == 400
    assert response_body(response)["errors"]["producer"] == "This field is required."
    assert mock.calls == 0


@pytest.mark.anyio
async def test_empty_required_field_returns_400() -> None:
    mock = MockVisionService()

    response = await call_verify(mock, data=form_data(producer="   "), image=upload_file())

    assert response_status(response) == 400
    assert response_body(response)["errors"]["producer"] == "This field cannot be empty."
    assert mock.calls == 0


@pytest.mark.anyio
async def test_mocked_vision_exception_returns_generic_500() -> None:
    mock = MockVisionService(error=RuntimeError("boom"))

    response = await call_verify(mock, image=upload_file())
    body = response_body(response)

    assert response_status(response) == 500
    assert body["message"] == "Verification failed unexpectedly."
    assert "boom" not in str(body)


@pytest.mark.anyio
async def test_latency_is_logged_for_success(caplog) -> None:
    mock = MockVisionService()

    with caplog.at_level(logging.INFO, logger="app.api.verify"):
        response = await call_verify(mock, image=upload_file())

    assert response_status(response) == 200
    assert any("verify_request_complete" in message for message in caplog.messages)


@pytest.mark.anyio
async def test_latency_is_logged_for_4xx(caplog) -> None:
    mock = MockVisionService()

    with caplog.at_level(logging.INFO, logger="app.api.verify"):
        response = await call_verify(mock, image=None)

    assert response_status(response) == 400
    assert any("verify_request_invalid" in message for message in caplog.messages)


@pytest.mark.anyio
async def test_slow_path_over_budget_logs_warning(caplog, monkeypatch) -> None:
    mock = MockVisionService()
    ticks = iter([0.0, 5.25])
    monkeypatch.setattr("app.api.verify.time.perf_counter", lambda: next(ticks))

    with caplog.at_level(logging.WARNING, logger="app.api.verify"):
        response = await call_verify(mock, image=upload_file())

    assert response_status(response) == 200
    assert response_body(response)["latency_ms"] == 5250
    assert any("exceeded_budget=True" in message for message in caplog.messages)
