from __future__ import annotations

import json
import logging
import os
from typing import Any, Mapping

from pydantic import ValidationError

from app.verification.models import ExtractedLabel
from app.vision.client import OpenAIVisionClient, VisionClientProtocol
from app.vision.preprocessing import ImagePreprocessingError, prepare_image


DEFAULT_VISION_MODEL = "gpt-5.4-mini"
VISION_DETAIL = "high"
logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are extracting text fields from a photographed alcohol beverage label for a TTB label verification proof of concept.

Return only the structured JSON object required by the provided schema. Do not include explanations, markdown, or extra keys.

Extract these seven fields:

1. brand_name
   The brand name shown on the label.

2. product_class
   The product type or class shown on the label, such as wine, red wine, vodka, whiskey, beer, cider, or another visible class/type statement.

3. producer
   The producer, bottler, importer, winery, brewery, distillery, or responsible company shown on the label.

4. country_of_origin
   The country of origin shown on the label.

5. abv
   The alcohol by volume statement exactly as visible, such as "13.5% Alc. by Vol." or "40% ALC/VOL".

6. net_contents
   The net contents statement exactly as visible, such as "750 mL", "1 L", or "12 FL OZ".

7. government_warning
   The government warning text exactly as visible on the label. This field is critical because the downstream verifier requires an exact, case-sensitive match.

Rules:
- If a field is not visible, unreadable, blocked by glare, too blurry, cut off, or uncertain, return null for that field.
- Do not guess or infer values from context.
- For government_warning, transcribe the visible warning verbatim character by character.
- Preserve the government_warning exact wording, capitalization, punctuation, colon, parentheses, periods, spacing, and line breaks as much as the image allows.
- Do not correct the government_warning into the standard legal text.
- Do not fix capitalization, spelling, punctuation, spacing, or wording in the government_warning.
- Do not normalize the government_warning.
- Do not summarize or rewrite the government_warning.
- If the government_warning is present but you cannot read it character by character, return null for government_warning.
- For all other fields, copy the visible text as closely as possible without adding information.
- If the image is not an alcohol beverage label, return null for all fields.
- Return partial data when only some fields are readable.
"""


def null_extracted_label() -> ExtractedLabel:
    return ExtractedLabel()


def build_extracted_label_schema() -> dict[str, Any]:
    properties = {
        field: {"type": ["string", "null"]}
        for field in ExtractedLabel.model_fields
    }
    return {
        "type": "object",
        "properties": properties,
        "required": list(ExtractedLabel.model_fields),
        "additionalProperties": False,
    }


class VisionService:
    def __init__(
        self,
        *,
        client: VisionClientProtocol,
        model: str = DEFAULT_VISION_MODEL,
        detail: str = VISION_DETAIL,
    ) -> None:
        self.client = client
        self.model = model
        self.detail = detail

    @classmethod
    def from_env(cls, *, client: VisionClientProtocol | None = None) -> "VisionService":
        model = os.environ.get("VISION_MODEL", DEFAULT_VISION_MODEL)
        return cls(client=client or OpenAIVisionClient(), model=model)

    async def extract_label(
        self,
        image_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> ExtractedLabel:
        try:
            prepared = prepare_image(image_bytes)
        except ImagePreprocessingError:
            logger.warning("Vision extraction skipped because input is not a readable image.")
            return null_extracted_label()

        try:
            result = await self.client.extract_structured_label(
                image_bytes=prepared.data,
                prompt=EXTRACTION_PROMPT,
                schema=build_extracted_label_schema(),
                model=self.model,
                detail=self.detail,
            )
        except Exception as exc:
            logger.warning("Vision extraction failed with provider/client error: %s", type(exc).__name__)
            return null_extracted_label()

        return _parse_extracted_label(result.structured_data, result.raw_json)


def _parse_extracted_label(
    structured_data: Mapping[str, Any] | None,
    raw_json: str | None,
) -> ExtractedLabel:
    payload: Any = structured_data

    if payload is None and raw_json:
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            logger.warning("Vision extraction returned malformed structured JSON.")
            return null_extracted_label()

    if not isinstance(payload, Mapping):
        logger.warning("Vision extraction returned no structured object.")
        return null_extracted_label()

    expected_keys = set(ExtractedLabel.model_fields)
    if set(payload) != expected_keys:
        logger.warning("Vision extraction returned unexpected structured keys.")
        return null_extracted_label()

    try:
        return ExtractedLabel.model_validate(payload)
    except ValidationError:
        logger.warning("Vision extraction structured object failed validation.")
        return null_extracted_label()
