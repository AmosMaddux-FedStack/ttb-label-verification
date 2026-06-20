from __future__ import annotations

from app.vision.client import VisionClientResult


class FakeVisionClient:
    def __init__(self, result: VisionClientResult | Exception) -> None:
        self.result = result
        self.calls = 0
        self.last_prompt: str | None = None
        self.last_schema: dict | None = None
        self.last_model: str | None = None
        self.last_detail: str | None = None

    async def extract_structured_label(
        self,
        *,
        image_bytes: bytes,
        prompt: str,
        schema: dict,
        model: str,
        detail: str,
    ) -> VisionClientResult:
        self.calls += 1
        self.last_prompt = prompt
        self.last_schema = schema
        self.last_model = model
        self.last_detail = detail

        if isinstance(self.result, Exception):
            raise self.result
        return self.result
