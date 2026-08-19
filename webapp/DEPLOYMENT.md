# AEGIS Web Application Deployment

The web application is a Node.js tRPC surface backed by the **canonical repository root**. It executes only read-only Python projections of committed AEGIS logic and evidence. Page load, the health check, the benchmark view, and the demo profile perform **zero** Bright Data, NVIDIA, Gemini, approval, commit, rollback, or benchmark-execution operations.

## Development

```bash
cd webapp
pnpm install
AEGIS_ROOT=.. pnpm dev
curl http://localhost:3000/healthz
```

On Windows PowerShell, set `$env:AEGIS_ROOT = (Resolve-Path ..).Path` and, if necessary, `$env:AEGIS_PYTHON = "python"` before `pnpm dev`.

## Production image

The root `Dockerfile` intentionally includes Python because the Node adapter invokes canonical `scripts/mission032_lifecycle_api.py`. Build from the repository root so `src/aegis/`, `benchmarks/`, `experiments/`, and `scripts/` are available. The image sets `AEGIS_ROOT=/app`, serves the Vite build through Express, and honors the platform-provided `PORT`.

The only configuration required for read-only demo routes is a working Python 3 interpreter. `DATABASE_URL` is optional for historical, controlled-replay, benchmark, Judge Mode, and downstream blocked-output routes; it is required only to persist user-created case configurations. Never commit `.env` files or provider credentials.

## Deployment status

The repository is **deployment-ready but not publicly deployed by this task**. A project owner must create a checkpoint and use the platform publishing control, or build the root container in an authorized environment. Verify `/healthz`, `/judge`, `/benchmark`, `/downstream`, and `/cases/mission_029_real_provider` after launch.
