# Local dev environment — how to start it

`docker-compose.yml` is the documented normal path (per `DESIGN.md` §1) and should still be used if Docker Desktop works on your machine. **On this machine it doesn't** — Docker Desktop's engine is unrecoverable (confirmed: no `dockerd` process at all inside its VM, even after a full process kill + `wsl --shutdown` + clean relaunch). Postgres runs natively instead, in an isolated user-space conda environment — no admin rights, no WSL, no Docker needed.

## Postgres (working)

Installed via a dedicated `micromamba` env (this machine already had `micromamba` at `G:\dem\.micromamba\micromamba.exe`; conda-forge ships Postgres 16 for win-64):

```bash
"G:/dem/.micromamba/micromamba.exe" create -n reconcile_db -c conda-forge postgresql=16 -y
```

Data directory lives at `backend/.devdb/pgdata` (gitignored), initialized once with:
```bash
PGBIN="C:/Users/Shriyash Beohar/AppData/Roaming/mamba/envs/reconcile_db/Library/bin"
"$PGBIN/initdb.exe" -D "G:/dem/business_ops/backend/.devdb/pgdata" -U postgres --auth=trust -E UTF8
```

**To start it** (do this every session — it does not auto-start):
```bash
PGBIN="C:/Users/Shriyash Beohar/AppData/Roaming/mamba/envs/reconcile_db/Library/bin"
"$PGBIN/pg_ctl.exe" -D "G:/dem/business_ops/backend/.devdb/pgdata" -l "G:/dem/business_ops/backend/.devdb/pg.log" -o "-p 5432" start
```

**To stop it:**
```bash
"$PGBIN/pg_ctl.exe" -D "G:/dem/business_ops/backend/.devdb/pgdata" stop
```

The `reconcile` role (superuser, for local-dev simplicity — this is a throwaway dev DB, not a security-sensitive one) and `reconcile_dev` database were created once and persist across restarts as long as `.devdb/pgdata` isn't deleted:
```sql
CREATE ROLE reconcile LOGIN SUPERUSER PASSWORD 'reconcile';
CREATE DATABASE reconcile_dev OWNER reconcile;
```
Matches `backend/.env`'s existing `DATABASE_URL`/`DATABASE_URL_SYNC` exactly — no app config changes needed regardless of which way Postgres is actually running.

## Redis (unresolved — not blocking)

`redis`/`valkey` aren't available for win-64 on conda-forge. Attempted `winget install Memurai.MemuraiDeveloper` (a Windows-native Redis-compatible server) — failed non-interactively (exit 1602, "You cancelled the installation"): its MSI needs UAC elevation, which can't be approved from a non-interactive session. If you want Redis for real, run that winget command yourself from an elevated/interactive prompt and approve the UAC dialog, or install `redis-server` via `apt` in WSL2 (needs your sudo). **This isn't a hard blocker**: the job-progress WebSocket push is explicitly designed to fail open (`DESIGN.md` §4) — a Redis outage never fails the actual settlement-processing job, only the live-progress UX. If Memurai didn't finish installing, either retry that, or fall back to the WSL2-native `redis-server` (Ubuntu 24.04's `apt` package) once WSL2 access is sorted out, or accept the gap for Phase 1 and revisit when Phase 2's job types make WS progress more load-bearing.

## Everything else

Unchanged from `DESIGN.md` §1 / the scaffolding report: `uv run alembic upgrade head`, `uv run python scripts/seed_reference_data.py`, `uv run uvicorn app.main:app --reload`, `uv run pytest`.
