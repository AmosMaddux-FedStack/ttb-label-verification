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
