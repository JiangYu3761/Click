# Sentence Reader Runtime Portability

Updated: 2026-06-24

## Current Decision

V2.0N does not pretend the App is clean-Mac portable. It adds a hard portability report so packaging can distinguish:

- current-machine ready
- clean-Mac ready
- known blockers
- feature-specific portability risks

This is the right product boundary because the app currently runs well on this machine, but the bundled ReaderRuntime still relies on external system pieces.

## Current State

The packaged app includes:

- `ReaderRuntime/reader_api`
- `ReaderRuntime/migrations`
- `ReaderRuntime/scripts/run_reader_api.sh`
- `ReaderRuntime/.venv-reader-api`
- `ReaderRuntime/runtime_manifest.json`
- `ReaderRuntime/scripts/sentence_reader_runtime_portability.py`
- `ReaderRuntime/scripts/sentence_reader_runtime_bootstrap.py`
- `ReaderRuntime/scripts/sentence_reader_runtime_config.py`
- `ReaderRuntime/scripts/sentence_reader_first_run_preflight.py`

The V2.0N report is generated at:

- `reports/sentence_reader_runtime_portability_report.json`
- `reports/sentence_reader_runtime_portability_report.md`

## Known Clean-Mac Blockers

The current report identifies these blockers:

- `runtime_python_points_to_xcode`
- `runtime_python_points_outside_ReaderRuntime`
- `postgres_not_bundled`

This means the package is valid for this Mac, but it is not yet a universal installer.

## V2.0O Bootstrap Boundary

V2.0O adds `sentence_reader_runtime_bootstrap.py`.

It can:

- inspect candidate Python runtimes
- select a working Reader API Python
- create a user-level venv under `~/Library/Application Support/SentenceReader/Runtime/.venv-reader-api` when explicitly asked
- install dependencies only when explicitly asked
- check whether PostgreSQL is already running or whether Postgres.app tools are available
- write `reports/sentence_reader_runtime_bootstrap_report.json`

It does not:

- silently install Python dependencies
- silently install PostgreSQL
- mark clean-Mac readiness as solved while PostgreSQL is still external

## V2.0P First-Run Boundary

V2.0P adds two runtime-facing tools:

- `sentence_reader_runtime_config.py`
- `sentence_reader_first_run_preflight.py`

The runtime config file uses schema `sentence_reader.runtime_config.v1` and defaults to:

```text
~/Library/Application Support/SentenceReader/config/runtime_config.json
```

FunASR can now be resolved from:

1. Swift `UserDefaults`
2. `SENTENCE_READER_FUNASR_PYTHON` / `SENTENCE_READER_FUNASR_WORKER`
3. `runtime_config.json`
4. the legacy local path as a compatibility fallback

The first-run preflight report uses schema `sentence_reader.first_run_preflight_report.v1` and writes:

- `reports/sentence_reader_first_run_preflight_report.json`
- `reports/sentence_reader_first_run_preflight_report.md`

It checks:

- PostgreSQL server/tools readiness
- Reader API startup and migration script boundary
- runtime bootstrap result
- FunASR path readiness and Apple Speech fallback
- non-destructive policy flags

It does not:

- auto-install PostgreSQL
- auto-install Python packages
- mutate database schema beyond the existing explicit Reader API startup/migration path
- make missing FunASR block normal reading

## Current Strategy

For this machine:

- keep using packaged ReaderRuntime
- keep using Postgres.app through `/Applications/Postgres.app/Contents/Versions/latest/bin`
- keep running migration on startup through `run_reader_api.sh`
- keep FunASR configurable, with Apple Speech fallback when FunASR is missing

For clean-Mac productization:

- replace the copied Xcode-linked virtualenv with a relocatable Python runtime or installer-created venv
- expose PostgreSQL and FunASR first-run preflight inside the app
- eventually replace external PostgreSQL assumptions with an installer-managed or clearly guided setup

## Acceptance

V2.0N passes when:

- the package can still launch Reader API on this machine
- `sentence_reader_runtime_portability.py` says `current_machine_ready=true`
- the same report either says `clean_mac_ready=true` or lists explicit clean-Mac blockers
- product diagnostics includes the portability report
- static smoke checks lock the portability script and package manifest markers

V2.0O passes when:

- the runtime bootstrap report says `startup_ready=true`
- the smoke test proves a user-level venv can be created without installing dependencies
- `run_reader_api.sh` can use the bootstrap selector when bundled Python is unavailable
- product diagnostics includes runtime bootstrap status
- runtime launch smoke still passes

V2.0P passes when:

- the runtime config script can resolve FunASR paths from configurable sources
- the first-run preflight report can be generated with `first_run_ready=true`
- product diagnostics includes first-run preflight status
- package creation copies config/preflight scripts into ReaderRuntime
- Swift no longer relies only on a hard-coded FunASR path
