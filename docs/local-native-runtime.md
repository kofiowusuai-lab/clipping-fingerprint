# Local native SupoClip runtime

API: http://127.0.0.1:8000 (OpenAPI: /docs).
All service ports are loopback-only. No frontend or Hermes profiles were modified.

## Start / recover

From `/workspace`:

```sh
docker-compose --env-file .env.local -f compose.local-infra.yml up -d --wait
backend/.venv/bin/python scripts/local_runtime.py start
backend/.venv/bin/python scripts/local_runtime.py status
backend/.venv/bin/python scripts/local_verify.py
```

`start` waits for API database readiness before launching the worker, because API startup applies migrations. API/worker are detached native processes, not launchd services; restart them after reboot. Docker dependencies use `unless-stopped`.

Stop only SupoClip native processes with:

```sh
backend/.venv/bin/python scripts/local_runtime.py stop
```

Start the signed stdio MCP server with:

```sh
backend/.venv/bin/python scripts/local_runtime.py mcp
```

The wrapper reads `.env.mcp.local`; parent integrations may instead read `.env.local`, which also has `SUPOCLIP_API_URL`, `SUPOCLIP_USER_ID`, `SUPOCLIP_AUTH_SECRET`, and `BACKEND_AUTH_SECRET`.

## Credentials

- Signed user id: `65485bd9-c5d8-4330-94f2-080ba50109a7` (non-admin service user).
- Raw HMAC secret file: `.local/backend-auth-secret` (mode 0600).
- `.env.local` and `.env.mcp.local` are mode 0600 and gitignored. Never print or commit them.
- New independent random database, Redis, HMAC and encryption credentials.
- Only the existing OpenAI key was copied from videostudio; no unrelated secrets copied, and no profile files changed.

## Verification

- API `/health`, `/health/db`, `/health/redis`: healthy.
- Missing, unsigned, invalid-signature and expired requests: HTTP 401; valid signed request: HTTP 200.
- 22 database migrations applied; service user read back.
- Real stdio MCP initialized, 17 tools discovered; health, task listing, billing summary and font listing succeeded.
- Worker heartbeat present and a queued `cron:cleanup_media` job completed successfully. Cron results are intentionally not retained by arq; verifier checks the fresh completion event.
- Local `tiny.en` Whisper (72.1 MiB weights) transcribed the macOS `say` MP4 fixture: 27 words with valid word timestamps. Report: `.local/whisper-smoke-result.json`. Recheck via `backend/.venv/bin/python scripts/local_whisper_smoke.py`.
- `LLM=openai:gpt-4.1-mini`. Key is nonempty, has an sk- prefix, and is not a recognizable placeholder. Non-billable authenticated GET `https://api.openai.com/v1/models/gpt-4.1-mini` returned HTTP 200 and that model id. This verifies accepted credentials/model visibility, NOT inference quota, billing, or actual clipping quality. No paid inference or download jobs were run.
- Full LLM-driven clip generation/render pipeline remains untested deliberately. No known credential blocker, but inference quota remains unverified.
- Initial worker startup raced API migration and one startup cleanup failed with missing `media_deletions`; API migrated successfully and later cleanup jobs passed. The launcher now enforces readiness ordering.

## Handles / files

- Containers: `supoclip-local-postgres` (127.0.0.1:55432), `supoclip-local-redis` (127.0.0.1:56379).
- Native PID files: `.local/api.pid`, `.local/worker.pid`.
- Logs: `.local/logs/api.log`, `.local/logs/worker.log`.
- Latest non-billable report: `.local/verification.json`.
- Durable database/queue volumes belong to compose project `supoclip-local`; do not use `down -v` unless intentional data deletion.
