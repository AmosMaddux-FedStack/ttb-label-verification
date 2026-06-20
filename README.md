# TTB Label Verification POC

Phase 0 deploys a minimal Python 3.12 FastAPI app with a plain HTML/JS frontend served from the
same origin.

## Secrets

API keys and secrets must only live in environment variables or an untracked local `.env` file.
Never commit real secrets. `.env.example` is only a placeholder template.

## Local Setup

```bash
uv lock
uv run pytest
uv run uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/health
```

The frontend calls same-origin `/health` and should display:

```json
{
  "status": "ok"
}
```

## Deploy To Railway

1. Commit and push this repo to GitHub.
2. Create a new Railway project from the GitHub repo.
3. Add this Railway environment variable:

   ```text
   APP_ENV=production
   ```

4. Deploy. Railway uses the committed `railway.json` start command:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
   ```

5. In Railway service settings, open Networking / Public Networking and generate a Railway domain.
6. Open the generated URL and `/health`.

Exit check:

- The live `/` page loads.
- The live `/health` endpoint returns `{"status":"ok"}`.
- The frontend displays the health response.
- Browser dev tools show a same-origin `/health` request with no CORS error.
