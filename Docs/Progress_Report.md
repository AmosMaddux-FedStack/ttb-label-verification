# Progress Report

## Current Status

Phase 0 is complete and deployed. Phase 1 comparison engine is implemented locally and all tests
pass.

Live app:

```text
https://ttb-label-verification-production-b67a.up.railway.app
```

Verified endpoints:

```text
GET /        -> 200, frontend HTML loads
GET /health  -> 200, {"status":"ok"}
```

The frontend calls same-origin `/health` and displays the health response on the page.

## Repository

GitHub remote:

```text
git@github.com:AmosMaddux-FedStack/ttb-label-verification.git
```

Branch:

```text
main
```

Phase 0 commit:

```text
b03d79a Scaffold Phase 0 FastAPI health app
```

Phase 0 deployment docs commit:

```text
bd16dc7 Document Phase 0 deployment progress
```

Push command used:

```bash
git push -u origin main
```

## Railway Deployment

Railway account used:

```text
amos.maddux@fedstack.com
```

Railway workspace:

```text
amosmaddux-fedstack's Projects
```

Railway project:

```text
ttb-label-verification
```

Project ID:

```text
8f92b9fb-44a6-4744-9a80-226fc80f2f36
```

Environment:

```text
production
```

Environment ID:

```text
bc930578-7c11-4513-b2d9-cdf8a13c8681
```

Service:

```text
ttb-label-verification
```

Service ID:

```text
823abc67-f4c0-4298-a0c9-414ad3e2dce2
```

Deployment ID:

```text
ad4dc8d5-fbed-4aa2-bf64-e90a6e44d41e
```

Public domain:

```text
https://ttb-label-verification-production-b67a.up.railway.app
```

Railway status after deploy:

```text
Online
```

## Commands Used

Local dependency lock and test:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv lock
UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run pytest
```

The `UV_CACHE_DIR` and `UV_PYTHON_INSTALL_DIR` overrides were needed in this sandbox because the
default uv cache and Python install directories under the home directory were read-only. On a
normal local machine, these shorter commands should be enough:

```bash
uv lock
uv run pytest
```

Git remote setup:

```bash
git remote set-url origin git@github.com:AmosMaddux-FedStack/ttb-label-verification.git
git ls-remote origin HEAD
```

Commit and push:

```bash
git branch -M main
git add .
git commit -m "Scaffold Phase 0 FastAPI health app"
git push -u origin main
```

Railway CLI login and deployment:

```bash
npx -y @railway/cli login
npx -y @railway/cli up --new --name ttb-label-verification -y --detach --json
npx -y @railway/cli variable set APP_ENV=production --skip-deploys --json
npx -y @railway/cli domain --json
npx -y @railway/cli status
npx -y @railway/cli domain list --json
```

Live verification:

```bash
curl -sS -i https://ttb-label-verification-production-b67a.up.railway.app/health
curl -sS -i https://ttb-label-verification-production-b67a.up.railway.app/
```

Expected `/health` response:

```json
{"status":"ok"}
```

## Files Created For Phase 0

```text
.env.example
.gitignore
.python-version
README.md
pyproject.toml
railway.json
uv.lock
app/__init__.py
app/main.py
app/static/index.html
app/static/app.js
app/static/styles.css
tests/test_health.py
```

`Docs/Plan.md` contains the Phase 0 plan and finalized Phase 1 plan.

## Phase 1 Comparison Engine

Phase 1 adds pure Python comparison logic for structured application data against structured label
extraction data. This phase does not include model calls, image handling, upload flow, database
state, or UI work.

Files added:

```text
app/verification/__init__.py
app/verification/models.py
app/verification/comparisons.py
tests/test_verification_comparisons.py
```

Implemented models:

- `ApplicationData`
- `ExtractedLabel`
- `FieldResult`
- `VerificationResult`

Implemented comparison functions:

- `compare_brand_name`
- `compare_product_class`
- `compare_producer`
- `compare_country_of_origin`
- `compare_abv`
- `compare_net_contents`
- `compare_government_warning`
- `verify_label`

Phase 1 verification command:

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run pytest
```

Latest result:

```text
47 passed in 0.23s
```

Strict government warning behavior:

- Exact all-caps warning passes.
- Title-case warning fails.
- Lowercase warning fails.
- Warning missing the colon fails.
- Missing punctuation fails.
- Extra space fails.
- Missing extracted warning fails.
- Reworded warning fails.
- Misread warning failures preserve the exact extracted warning text in `FieldResult.extracted_value`.

The implementation uses strict case-sensitive equality for the government warning:

```python
status = "PASS" if application == extracted else "FAIL"
```

The Phase 1 work honored the no-network requirement. No new dependency was installed during
execution; fuzzy matching is currently deterministic local standard-library logic.

## Important Decisions

- One FastAPI service serves both the API and the static frontend.
- No CORS middleware is needed in Phase 0 because frontend and backend are same-origin.
- Frontend uses relative `/health`, not a hardcoded backend URL.
- `.env` and `.env.*` are gitignored.
- `.env.example` is committed and contains placeholders only.
- `APP_ENV=production` is set in Railway.
- `railway.json` pins the start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Restart Checklist

From a fresh clone:

```bash
git clone git@github.com:AmosMaddux-FedStack/ttb-label-verification.git
cd ttb-label-verification
uv run pytest
uv run uvicorn app.main:app --reload
```

Open locally:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/health
```

To check Railway:

```bash
npx -y @railway/cli login
npx -y @railway/cli status
npx -y @railway/cli logs --lines 100
```

To redeploy from the current directory:

```bash
npx -y @railway/cli up --detach
```

## Next Phase Notes

Phase 0 intentionally does not include upload, batch upload, TTB rules, OCR, vision model calls, or
secret-bearing integrations.

Project rules still apply for the next phase:

- Single-label result under 5 seconds.
- Batch upload is required.
- Government warning match is exact and case-sensitive.
- Other fields are fuzzy/normalized.
- API keys must only live in environment variables, never in code or commits.
