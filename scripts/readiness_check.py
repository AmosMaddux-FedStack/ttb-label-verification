from __future__ import annotations

import argparse
import json
import mimetypes
import os
import time
import uuid
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError


REQUIRED_FIELDS = [
    "brand_name",
    "product_class",
    "producer",
    "country_of_origin",
    "abv",
    "net_contents",
    "government_warning",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run read-only readiness checks against the app.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("READINESS_BASE_URL", "http://127.0.0.1:8000"),
        help="App base URL. Defaults to READINESS_BASE_URL or local dev server.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Also POST /verify using local image and fields from env vars.",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    checks = [
        check_get(f"{base_url}/health", expected_json={"status": "ok"}),
        check_get(f"{base_url}/"),
    ]

    if args.verify:
        checks.append(check_verify(f"{base_url}/verify"))

    print(json.dumps({"base_url": base_url, "checks": checks}, indent=2))
    return 0 if all(check["ok"] for check in checks) else 1


def check_get(url: str, *, expected_json: dict[str, Any] | None = None) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        response = request.urlopen(url, timeout=15)
        body = response.read()
        result: dict[str, Any] = {
            "name": f"GET {url}",
            "ok": 200 <= response.status < 300,
            "status": response.status,
            "latency_ms": elapsed_ms(start),
        }
        if expected_json is not None:
            result["ok"] = result["ok"] and json.loads(body.decode("utf-8")) == expected_json
        return result
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return failure(f"GET {url}", start, exc)


def check_verify(url: str) -> dict[str, Any]:
    start = time.perf_counter()
    image_path = os.environ.get("READINESS_LABEL_IMAGE")
    fields = {field: os.environ.get(f"READINESS_{field.upper()}") for field in REQUIRED_FIELDS}

    missing = [field for field, value in fields.items() if not value]
    if not image_path:
        missing.append("READINESS_LABEL_IMAGE")
    if missing:
        return {
            "name": f"POST {url}",
            "ok": False,
            "status": None,
            "latency_ms": elapsed_ms(start),
            "error": "Missing required readiness inputs.",
            "missing": missing,
        }

    try:
        body, content_type = multipart_body(
            fields={field: value or "" for field, value in fields.items()},
            image_path=Path(image_path),
        )
        req = request.Request(
            url,
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        response = request.urlopen(req, timeout=30)
        payload = json.loads(response.read().decode("utf-8"))
        return {
            "name": f"POST {url}",
            "ok": 200 <= response.status < 300,
            "status": response.status,
            "latency_ms": elapsed_ms(start),
            "verdict": payload.get("verification", {}).get("verdict"),
            "api_latency_ms": payload.get("latency_ms"),
        }
    except (OSError, HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return failure(f"POST {url}", start, exc)


def multipart_body(*, fields: dict[str, str], image_path: Path) -> tuple[bytes, str]:
    boundary = f"----readiness-{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )

    content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    chunks.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="image"; filename="{image_path.name}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8"),
            image_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def failure(name: str, start: float, exc: Exception) -> dict[str, Any]:
    return {
        "name": name,
        "ok": False,
        "status": getattr(exc, "code", None),
        "latency_ms": elapsed_ms(start),
        "error": type(exc).__name__,
    }


def elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


if __name__ == "__main__":
    raise SystemExit(main())
