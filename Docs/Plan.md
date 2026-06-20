# Phase 0 Plan: Deploy-First FastAPI + Hello Frontend

## Summary

Create a minimal Python 3.12 FastAPI app with a plain HTML/JS frontend served by the backend. The only goal is to get one live deployed URL before building real TTB label features.

Use one service, no database, no real API keys, and no vision/model integration yet.

## Repo Structure And Files

```text
fedstack_opener/
  AGENTS.md
  README.md
  railway.json
  pyproject.toml
  uv.lock
  .python-version
  .env.example
  .gitignore
  app/
    __init__.py
    main.py
    static/
      index.html
      app.js
      styles.css
  tests/
    test_health.py
```

Create:

- `pyproject.toml`: Python `>=3.12`, managed by `uv`; dependencies are `fastapi` and `uvicorn`; dev dependencies are `pytest` and `httpx`.
- `uv.lock`: committed for reproducible installs.
- `.python-version`: `3.12`, so local/dev/deploy runtimes prefer Python 3.12.
- `.env.example`: placeholder-only config, starting with `APP_ENV=local`; no real secrets.
- `.gitignore`: ignore `.env`, `.env.*`, virtualenvs, Python caches, test caches, build output, and editor files; explicitly allow `.env.example`.
- `railway.json`: committed Railway start command so deploy behavior is not hidden in dashboard-only settings.
- `app/main.py`: FastAPI app with `GET /health`, static asset mounting, and `GET /` serving the frontend.
- `app/static/*`: plain, readable hello frontend that calls `/health` on page load and displays success/failure clearly.
- `tests/test_health.py`: minimal API test for `/health`.
- `README.md`: local setup, test commands, run command, Railway deploy steps, and secrets policy.

## Public Interface

- `GET /health`
  - Returns:
    ```json
    {"status": "ok"}
    ```

- `GET /`
  - Returns the hello frontend.

Frontend behavior:
- On load, call relative path `/health`.
- If healthy, show a clear “backend is healthy” message.
- If unavailable, show a clear refresh/retry message.

## CORS

No CORS middleware is needed in Phase 0 because the frontend and backend are served from the same
FastAPI origin. The frontend must use relative API paths such as `/health`, never a hardcoded
Railway URL.

If a later phase splits frontend and backend hosting, add explicit allowlisted origins from
environment variables. Do not use wildcard CORS for secret-bearing or upload endpoints.

## Secrets Policy

- Real API keys and secrets must only live in deployment environment variables or an untracked local
  `.env` file.
- `.env` and `.env.*` must be ignored by git.
- `.env.example` is committed and must contain placeholders only.
- No secret values may appear in source code, tests, README examples, plan files, or committed
  config.
- Before the first commit, verify:
  ```bash
  git check-ignore .env
  git check-ignore .env.local
  git status --short
  ```

## Deploy Steps

Use Railway as the Phase 0 target because it can serve the FastAPI API and static frontend from one public URL.

1. Create the Phase 0 files.
2. Run:
   ```bash
   uv lock
   uv run pytest
   ```
3. Confirm `.env` and `.env.local` are ignored by git.
4. Commit the repo.
5. Push to GitHub.
6. Create a Railway project from the GitHub repo.
7. Configure Railway environment variable:
   ```text
   APP_ENV=production
   ```
8. Railway should use the committed `railway.json` start command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
   ```
9. Deploy.
10. In Railway service settings, open Networking / Public Networking and generate a Railway domain.
11. Verify:
   ```text
   https://<railway-url>/
   https://<railway-url>/health
   ```

`railway.json` contents:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
  }
}
```

Railway notes:

- Railway can deploy this as one Python service using Railpack because the repo includes
  `pyproject.toml` and `uv.lock`.
- Do not rely on Railway's auto-detected FastAPI command, because auto-detection commonly assumes
  a root-level `main.py` while this plan uses `app/main.py`.
- Railway services are not publicly reachable until a domain is generated.
- If Railway free/trial availability is blocked by account state, expired credits, or billing
  requirements, use Render free web service as the fallback with the same FastAPI app and start
  command.

## Test Plan

Before deploy:

- `uv run pytest` passes.
- `uv run uvicorn app.main:app --reload` starts locally.
- `http://127.0.0.1:8000/health` returns `{"status":"ok"}`.
- `http://127.0.0.1:8000/` loads the hello frontend.
- Frontend displays health success after calling `/health`.

After deploy:

- Deployed `/` loads.
- Deployed `/health` returns `200`.
- Frontend health message succeeds from the deployed URL.
- Repo contains no `.env` file and no real secrets.
- `git check-ignore .env` and `git check-ignore .env.local` both confirm those files are ignored.
- Browser dev tools show the frontend requests same-origin `/health`, with no CORS error and no
  hardcoded backend URL.

## Assumptions

- Plain HTML/JS is preferred over React for Phase 0 because the goal is the fastest deployable proof.
- One hosted backend service is preferred over separate frontend/backend hosting for now.
- No upload, batch upload, TTB rules, OCR, model calls, or secret-bearing integrations are included in Phase 0.
- Railway is the primary Phase 0 deploy target; Render free web service is the fallback only if
  Railway free/trial deployment is blocked by account or billing constraints.


## Phase 1 Plan: Comparison Engine

## Summary

Add a small verification package that compares structured `ApplicationData` against structured
`ExtractedLabel` data. Each field gets its own pure comparison function that returns a
`FieldResult`. A top-level `verify_label()` function aggregates results into a
`VerificationResult`.

No model calls, no image handling, no upload flow, no database, and no UI work are included in
this phase.

## Review Result

Phase 1 is approved with the test additions below. The exact review scenarios are all covered by
planned tests:

- Case-only brand difference passes: covered by `Brand case-only difference passes`.
- `45%` vs `45% Alc./Vol. (90 Proof)` passes: covered by `45% matches 45% Alc./Vol. (90 Proof)`.
- `750 mL` vs `750ml` passes: covered by `750 mL matches 750ml`.
- `USA` vs `United States` passes: covered by `USA matches United States`.
- Government warning in title case fails: covered by `Title-case warning fails`.
- Government warning missing the colon fails: covered by `Warning missing colon fails`.
- Correct all-caps warning passes: covered by `Exact all-caps warning passes`.
- Misread warning returns the extracted text in the result: covered by `Misread warning failure keeps extracted warning text`.

## Files To Add Or Change

```text
app/
  verification/
    __init__.py
    models.py
    comparisons.py

tests/
  test_verification_comparisons.py

pyproject.toml
uv.lock
```

Dependency change:

- `rapidfuzz`

Use `rapidfuzz` for fuzzy string matching because it is fast, deterministic, actively used, and has
no AI or network dependency at runtime.

## Pydantic Models

`ApplicationData` represents the expected/source-of-truth application values.

Fields:

- `brand_name: str`
- `product_class: str`
- `producer: str`
- `country_of_origin: str`
- `abv: str`
- `net_contents: str`
- `government_warning: str`

`ExtractedLabel` represents values extracted from the label. Fields are nullable because future
OCR/vision extraction may miss fields.

Fields:

- `brand_name: str | None = None`
- `product_class: str | None = None`
- `producer: str | None = None`
- `country_of_origin: str | None = None`
- `abv: str | None = None`
- `net_contents: str | None = None`
- `government_warning: str | None = None`

`FieldResult` represents one result per compared field.

Fields:

- `field: str`
- `status: Literal["PASS", "FAIL"]`
- `application_value: str`
- `extracted_value: str | None`
- `strategy: str`
- `score: float | None = None`
- `normalized_application_value: str | None = None`
- `normalized_extracted_value: str | None = None`
- `message: str`

`VerificationResult` represents aggregated comparison output.

Fields:

- `verdict: Literal["PASS", "NEEDS_REVIEW"]`
- `fields: list[FieldResult]`

Verdict rule:

- If any `FieldResult.status == "FAIL"`, verdict is `NEEDS_REVIEW`.
- Otherwise verdict is `PASS`.
- Missing extracted values count as `FAIL`.

## Comparison Strategies

Shared fuzzy normalization for brand, product class, and producer:

- Trim outer whitespace.
- Collapse repeated internal whitespace.
- Lowercase.
- Remove most punctuation.
- Compare with `rapidfuzz.fuzz.token_sort_ratio`.
- Threshold: `90.0`.
- `score >= 90.0` is `PASS`; otherwise `FAIL`.

Functions:

- `compare_brand_name(application, extracted) -> FieldResult`
- `compare_product_class(application, extracted) -> FieldResult`
- `compare_producer(application, extracted) -> FieldResult`

Country comparison:

- Function: `compare_country_of_origin(application, extracted) -> FieldResult`
- Normalize whitespace, punctuation, and case.
- Map synonyms to canonical country names.
- Examples:
  - `usa`, `u.s.a.`, `us`, `u.s.`, `united states of america` -> `united states`
  - `uk`, `u.k.`, `great britain` -> `united kingdom`
- Pass only if canonical values match exactly.
- Unknown countries fall back to normalized exact match.

ABV comparison:

- Function: `compare_abv(application, extracted) -> FieldResult`
- Parse numeric ABV from strings like:
  - `13.5%`
  - `13.5 % alc/vol`
  - `ALC 13.5% BY VOL`
  - `13.50`
  - `45% Alc./Vol. (90 Proof)`
- Normalize to percent as a decimal number.
- Prefer a number marked by `%`, `alc`, `vol`, or `abv` when multiple numbers are present.
- Ignore proof values when an ABV percentage is present.
- If only proof is present, convert proof to ABV by dividing by `2`.
- Pass if absolute difference is `<= 0.1` percentage points.
- Fail if either side has no parseable number.

Net contents comparison:

- Function: `compare_net_contents(application, extracted) -> FieldResult`
- Parse amount and unit.
- Normalize to milliliters.
- Supported units:
  - `ml`, `milliliter`, `milliliters`
  - `l`, `liter`, `liters`
  - `cl`, `centiliter`, `centiliters`
  - `fl oz`, `fluid ounce`, `fluid ounces`
- Pass if normalized values differ by `<= 1 ml`.
- Fail if either side cannot be parsed.

Government warning comparison:

- Function: `compare_government_warning(application, extracted) -> FieldResult`
- Exact string equality only.
- Case-sensitive.
- No fuzzy matching.
- No punctuation normalization.
- No whitespace normalization.
- Any missing, changed-case, extra-space, missing-punctuation, missing-colon, or reworded warning
  fails.
- On failure, the `FieldResult.extracted_value` must preserve and return the extracted warning text
  exactly as received, so a user can see what the model/OCR read.

Top-level function:

- `verify_label(application: ApplicationData, extracted: ExtractedLabel) -> VerificationResult`
- It runs all field comparison functions and applies the verdict rule.

## Test Cases

Model tests:

- `ApplicationData` accepts complete string data.
- `ExtractedLabel` accepts missing extracted fields as `None`.
- `FieldResult` and `VerificationResult` serialize cleanly with expected literals.

Fuzzy field tests:

- Brand exact match passes.
- Brand case-only difference passes.
- Brand case/punctuation difference passes.
- Brand minor OCR typo above threshold passes.
- Brand materially different value fails.
- Product class fuzzy equivalent passes.
- Product class wrong class fails.
- Producer legal suffix or punctuation variation passes when score is above threshold.
- Producer unrelated name fails.
- Fuzzy score exactly at threshold passes.

Country tests:

- `USA` matches `United States`.
- `U.S.A.` matches `United States of America`.
- Case and punctuation differences pass through synonym normalization.
- Different countries fail.
- Unknown country strings pass only when normalized exact values match.
- Missing extracted country fails.

ABV tests:

- `13.5%` matches `13.5 % alc/vol`.
- `ALC 13.50% BY VOL` matches `13.5`.
- `45%` matches `45% Alc./Vol. (90 Proof)`.
- Difference within `0.1` percentage points passes.
- Difference greater than `0.1` fails.
- Missing extracted ABV fails.
- Unparseable ABV fails.

Net contents tests:

- `750 mL` matches `750ml`.
- `750 ml` matches `0.75 L`.
- `750 ml` matches `75 cl`.
- `750 ml` matches equivalent fluid ounces within tolerance.
- Different sizes fail.
- Missing extracted net contents fails.
- Unparseable net contents fails.

Government warning tests:

- Exact all-caps warning passes.
- Title-case warning fails.
- Lowercase warning fails.
- Warning missing colon fails.
- Missing punctuation fails.
- Extra space fails.
- Missing extracted warning fails.
- Reworded warning fails.
- Misread warning failure keeps extracted warning text in `FieldResult.extracted_value`.

Verification result tests:

- All fields passing gives `verdict == "PASS"`.
- One failing field gives `verdict == "NEEDS_REVIEW"`.
- Multiple failing fields still gives `NEEDS_REVIEW`.
- Result includes one `FieldResult` per compared field.
- Failed government warning result includes the exact extracted warning text.

## Risks / Review Points

- Fuzzy threshold `90.0` is conservative but may need tuning once real labels arrive.
- ABV and net-content tolerances are deterministic guesses for Phase 1; they should be reviewed
  against actual TTB/business expectations later.
- Government warning is intentionally strict per project rules, even if OCR introduces small
  whitespace, punctuation, or case differences.
- The ABV parser must avoid accidentally comparing proof numbers as ABV when both are present.



# Phase 2 Plan: VisionService For Structured Label Extraction

## Summary

Add a `VisionService` that accepts one label image and returns the existing `ExtractedLabel` Pydantic model from `app/verification/models.py`. This phase introduces AI only for extraction, not verification: comparison remains the deterministic Phase 1 engine.

Use the OpenAI Responses API with `gpt-5.4-mini` by default, configurable via `VISION_MODEL`. OpenAI’s current docs say current GPT models support image input and vision; Structured Outputs should be used over JSON mode when schema adherence matters. Sources: [Models](https://developers.openai.com/api/docs/models), [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [Images and vision](https://developers.openai.com/api/docs/guides/images-vision).

## Review Result

Phase 2 is approved with the clarifications and test additions below.

- Government warning capture: the prompt must make verbatim warning transcription the highest-priority extraction requirement. It must say not to correct casing, punctuation, spacing, line breaks, spelling, or wording, and to return `null` if the warning cannot be read character-by-character.
- Non-label image: a valid image that is not an alcohol beverage label must return an all-null `ExtractedLabel` and must not throw.
- Model timeout/API error: timeout or OpenAI client failure must return an all-null `ExtractedLabel`, log a concise warning, and let downstream verification produce `NEEDS_REVIEW`.
- Malformed structured output: parsing must be defensive against missing output, malformed JSON, extra keys, wrong types, or schema validation errors. The service must catch parse/validation failures and return an all-null `ExtractedLabel` without leaking raw model text to users.
- Mockability: `VisionService` must accept an injected client/adapter and must expose a small fakeable interface so Phase 2 and Phase 3 tests never need real OpenAI API calls.

## Key Changes

- Add `app/vision/service.py` with an async `VisionService.extract_label(image_bytes, filename=None, content_type=None) -> ExtractedLabel`.
- Add `app/vision/preprocessing.py` for deterministic image preparation using Pillow: EXIF-correct orientation, RGB conversion, downscale long edge to 1600px, JPEG re-encode at quality 82, and cap oversized payloads before model submission.
- Add `app/vision/client.py` with a small `VisionClientProtocol` / adapter boundary around the OpenAI SDK. `VisionService` receives this client through its constructor so tests can pass a fake client.
- Add dependencies: `openai` and `pillow`; update `.env.example` with placeholder names only: `OPENAI_API_KEY=` and `VISION_MODEL=gpt-5.4-mini`.
- Keep secrets in environment variables only. The service reads `OPENAI_API_KEY` from env and never accepts keys through request payloads or committed config.
- Do not add an upload API or UI in this phase unless approved later; this is the service layer plus tests.

## Structured Extraction Behavior

- Send the preprocessed image to the Responses API as image input with `detail: "high"` because label text and the government warning require readable fine detail.
- Request Structured Outputs with a strict JSON schema matching `ExtractedLabel`: `brand_name`, `product_class`, `producer`, `country_of_origin`, `abv`, `net_contents`, and `government_warning`, each `string | null`, with no extra properties.
- Parse only the structured response object and validate it with `ExtractedLabel.model_validate`; do not regex, substring, or string-parse the model response.
- Treat missing structured output, malformed JSON, wrong field types, extra properties, or Pydantic validation errors as controlled extraction failure. Return an all-null `ExtractedLabel` and log a concise warning.
- For blurry, angled, glare-obscured, cropped, or partially unreadable images, return partial data with unreadable fields as `null`; do not throw just because image quality is poor.
- For a valid image that is not an alcohol beverage label, return an all-null `ExtractedLabel`; do not guess values from nearby text or scene context.
- For non-image bytes or preprocessing failure, return an all-null `ExtractedLabel` and log a concise warning, since the downstream verifier will produce `NEEDS_REVIEW`.
- For model timeout, rate-limit, network failure, SDK error, or response refusal, return an all-null `ExtractedLabel` and log a concise warning without exposing raw provider error text to the end user.

Extraction prompt:

```text
You are extracting text fields from a photographed alcohol beverage label for a TTB label verification proof of concept.

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
```

## Test Plan

- Unit-test preprocessing with generated in-memory images: large image is downscaled, orientation path is handled, output is JPEG/RGB, and small images are not enlarged.
- Unit-test prompt/schema construction: exactly the seven existing `ExtractedLabel` fields are requested, fields are nullable, extra properties are disallowed, and the government-warning instruction says verbatim/exact.
- Unit-test prompt/schema construction: government-warning instructions explicitly forbid correcting casing, punctuation, colon, spacing, spelling, wording, or line breaks.
- Unit-test service parsing with a fake OpenAI client returning complete structured data.
- Unit-test partial extraction: fake response omits unreadable fields as `null`, and service returns an `ExtractedLabel` with those nulls.
- Unit-test blurry/glare behavior through the fake client: model returns partial/null data, service does not throw.
- Unit-test non-label image behavior through the fake client: model returns all fields as `null`, and service returns an all-null `ExtractedLabel` without throwing.
- Unit-test malformed structured response: missing output, malformed JSON, extra keys, wrong types, and validation failure each return all-null `ExtractedLabel` without leaking raw model text.
- Unit-test API timeout/client error: service handles timeout, rate-limit, network failure, and generic SDK error gracefully and returns all-null `ExtractedLabel`.
- Unit-test no string parsing: fake response should be consumed from the structured output object only.
- Unit-test mockability: `VisionService` can be constructed with a fake client/adapter, and tests assert no OpenAI SDK network method is called.
- Unit-test env config: `VISION_MODEL` overrides the default model, and missing `OPENAI_API_KEY` produces a controlled startup/config error rather than a hardcoded fallback.

## Assumptions

- Phase 2 returns the existing `ExtractedLabel` shape exactly; no new fields like confidence, warnings, or raw OCR text are added yet.
- Default model is `gpt-5.4-mini` for latency/cost under the project’s 5-second target, with `VISION_MODEL` allowing later tuning.
- `detail: "high"` is chosen over `low` because the government warning must be copied exactly; preprocessing protects latency by bounding image size first.
- Network/API integration tests are not required in Phase 2. Tests mock the OpenAI client and avoid real API calls.
- Phase 3 must depend on the service interface or a callable extractor boundary, not directly on the OpenAI SDK, so endpoint tests can inject fake extraction results.
