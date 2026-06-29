# PostgreSQL Setup For Sentence Reader

Sentence Reader V1.2 is not complete until PostgreSQL is actually reachable and the real migration/smoke tests pass.

## Recommended Local Shape

Use one local PostgreSQL service for the user's personal systems, with `jiangyu_os` as the shared database and `reader` as this app's schema.

The Reader API defaults to:

```text
postgresql://localhost/jiangyu_os
```

Override it when needed:

```bash
export READER_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/jiangyu_os"
```

## Setup Options

Preferred for this Mac app:

- Postgres.app, because it is visible, local, and easy to start/stop.

Also acceptable:

- an existing PostgreSQL server reachable at `localhost:5432`
- a managed local service started outside this project

Not currently available in this shell:

- Homebrew
- Docker
- PostgreSQL command-line tools

## V1.2 Acceptance

After PostgreSQL is installed or exposed:

```bash
cd /Users/jiangyu/Documents/Codex/2026-06-23/readwise-mac-v1
./scripts/v12_data_acceptance.sh
```

That script checks:

- Reader API static contract
- Reader API mock CRUD
- PostgreSQL readiness
- `jiangyu_os` database creation
- `reader` schema migration
- direct PostgreSQL CRUD smoke
- live Reader API + PostgreSQL CRUD smoke

Only after this passes should V1.3 Swift App data integration begin.
