from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


class VisionConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class VisionClientResult:
    structured_data: Mapping[str, Any] | None = None
    raw_json: str | None = None


class VisionClientProtocol(Protocol):
    async def extract_structured_label(
        self,
        *,
        image_bytes: bytes,
        prompt: str,
        schema: dict[str, Any],
        model: str,
        detail: str,
    ) -> VisionClientResult:
        ...


class OpenAIVisionClient:
    def __init__(self, api_key: str | None = None) -> None:
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise VisionConfigurationError("OPENAI_API_KEY is required for real vision extraction.")

        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key, timeout=12.0)

    async def extract_structured_label(
        self,
        *,
        image_bytes: bytes,
        prompt: str,
        schema: dict[str, Any],
        model: str,
        detail: str,
    ) -> VisionClientResult:
        image_url = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")
        response = await self._client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": image_url, "detail": detail},
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "extracted_label",
                    "schema": schema,
                    "strict": True,
                }
            },
        )

        structured = _find_parsed_output(response)
        raw_json = getattr(response, "output_text", None)
        return VisionClientResult(structured_data=structured, raw_json=raw_json)


def _find_parsed_output(response: object) -> Mapping[str, Any] | None:
    direct = getattr(response, "output_parsed", None)
    if isinstance(direct, Mapping):
        return direct

    for output in getattr(response, "output", []) or []:
        for content in getattr(output, "content", []) or []:
            parsed = getattr(content, "parsed", None)
            if isinstance(parsed, Mapping):
                return parsed
    return None
