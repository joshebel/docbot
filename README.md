# docbot

LAN worker for a GitHub App that generates and maintains repository documentation. It polls a local SQLite queue, clones the target repo with an App installation token, generates a README, per-module docs, and an API reference using a local vLLM model (with an optional Anthropic paid lane), pushes the results to a `docs/auto` branch, and opens (or updates) a pull request. Stdlib only; RS256 signing via the `openssl` CLI.

## Features

- **Three document types per job**: `README.md`, per-module docs under `docs/modules/`, and an API reference at `docs/API.md`.
- **Local-first inference**: talks to an OpenAI-compatible vLLM endpoint; no cloud dependency for the free tier.
- **Paid spill lane**: pro-plan jobs can spill to Anthropic when the local queue is deep or the local backend is unhealthy, bounded by a daily USD cap.
- **Idempotent reruns**: the worker force-pushes the same `docs/auto` branch; if the generated docs are unchanged it skips the push and reports `no_change`.
- **GitHub webhook receiver**: handles installation, push, and Marketplace purchase events; verifies `X-Hub-Signature-256`.
- **Supervisor mode**: keeps the webhook receiver, worker loop, and a Cloudflare tunnel alive in one process.
- **Freelance track**: the same pipeline sold as a fixed-price service; `python -m worker pitch` drafts a repo-specific proposal.

## Installation / Setup

```bash
cp .env.example .env      # fill in values
python -m worker check    # verify the inference endpoint (model, context, tok/s)
python -m unittest -q
```

See `docs/SETUP.md` for GitHub App creation details and `docs/MARKETPLACE.md` for plan configuration and the publish checklist.

## Usage

All commands are run from the repository root:

```bash
# Dry run against a local checkout; writes docs to ./out/, no GitHub calls
python -m worker local ../some-repo

# Queue a job manually (optional ref argument)
python -m worker enqueue owner/repo
python -m worker enqueue owner/repo main

# Process one queued job and exit
python -m worker run-once

# Poll loop (the long-running worker)
python -m worker serve

# GitHub webhook receiver (install / push / marketplace events)
python -m worker webhook

# Dump the current queue
python -m worker jobs

# Account → plan table
python -m worker accounts

# Run webhook + serve + Cloudflare tunnel, keep them alive
python -m worker supervise

# Draft a freelance proposal for a repo (URL or local path)
python -m worker pitch <url|path> [--client NAME] [--budget USD]
```

Two long-running processes are typical in production: `serve` (does the work) and `webhook` (turns GitHub events into queue rows). Both share `QUEUE_PATH`. Expose `webhook` via a tunnel or reverse proxy and point the App's webhook URL at it; or move it to a VPS with an HTTP `Queue` implementation later.

Per-job records are written to `state/jobs.jsonl` (repo, files sent, tokens in/out, model, wall time, plan). Paid-lane spend is tracked in `state/spend.json`.

## Configuration

All settings come from environment variables (or a `.env` file, which is loaded without overriding real env vars). Key variables:

| Variable | Default | Description |
|---|---|---|
| `LOCAL_BASE_URL` | `http://127.0.0.1:8000/v1` | OpenAI-compatible endpoint |
| `LOCAL_API_KEY` | | Bearer key for the local endpoint |
| `LOCAL_MODEL` | | Model name (auto-detected if empty) |
| `LOCAL_ENABLE_THINKING` | `0` | Enable vLLM thinking mode |
| `ANTHROPIC_API_KEY` | | Enables the paid lane when set |
| `ANTHROPIC_MODEL` | `claude-opus-5` | Anthropic model |
| `ANTHROPIC_EFFORT` | `medium` | Effort level for Anthropic |
| `SPILL_ENABLED` | `0` | `1` to allow paid-lane spill |
| `SPILL_QUEUE_DEPTH` | `20` | Queue depth threshold for spill |
| `DAILY_USD_CAP` | `5` | Daily spend cap for the paid lane |
| `GH_APP_ID` | | GitHub App ID |
| `GH_INSTALLATION_ID` | | Installation ID (for manual enqueue) |
| `GH_APP_PRIVATE_KEY_PATH` | | Path to the App's RS256 private key |
| `GH_WEBHOOK_SECRET` | | Webhook HMAC secret |
| `WEBHOOK_BIND` | `0.0.0.0` | Webhook bind address |
| `WEBHOOK_PORT` | `8787` | Webhook port |
| `DOCS_BRANCH` | `docs/auto` | Branch to push generated docs |
| `QUEUE_PATH` | `./state/queue.sqlite` | SQLite queue file |
| `WORK_DIR` | `./work` | Clone destination |
| `LOG_DIR` | `./state` | Job log and spend ledger directory |
| `POLL_SECONDS` | `15` | Poll interval for `serve` |
| `MAX_REPO_BYTES` | `40_000_000` | Repo size cap |
| `MAX_FILES` | `3000` | File count cap |
| `MAX_FILE_BYTES` | `200_000` | Per-file size cap |

### Tiers

| Plan | Model | Route |
|---|---|---|
| `free` | local vLLM only | always |
| `pro` | local, spills to Anthropic (`ANTHROPIC_MODEL`) | when queue depth > `SPILL_QUEUE_DEPTH` or local is unhealthy, until `DAILY_USD_CAP` |

Plans are set by Marketplace purchase webhooks (see `docs/MARKETPLACE.md`). The paid lane is off until `ANTHROPIC_API_KEY` is set and `SPILL_ENABLED=1`.

## Project Layout

- `worker/config.py` – env → `Config` dataclass
- `worker/queue.py` – `Queue` interface + `SqliteQueue` implementation
- `worker/github.py` – App JWT, installation token, clone/push/PR
- `worker/ingest.py` – tree scan, signatures, skip lists, size caps
- `worker/llm.py` – local backend, Anthropic backend, plan-aware spill router, spend ledger
- `worker/generate.py` – README / module docs / API reference generation
- `worker/webhook.py` – signed webhook receiver → queue/accounts
- `worker/accounts.py` – account → plan mapping (fed by Marketplace events)
- `worker/supervisor.py` – keeps webhook + worker + tunnel alive
- `worker/pitch.py` – freelance proposal drafts
- `worker/__main__.py` – CLI entry point and job loop
- `docs/SETUP.md` – App creation guide
- `docs/MARKETPLACE.md` – plans, listing copy, publish checklist
- `freelance/` – profile, gig tiers, proposal template, delivery workflow
- `examples/click/` – unedited portfolio sample

## Development / Testing

```bash
python -m unittest -q
```

Test files:

- `tests/test_webhook.py` – signature verification, event dispatch, router spill logic
- `tests/test_worker.py` – queue round-trip, ingest skip/signature/cap, misc helpers

## Freelance Track

The same pipeline sold as a fixed-price service ($350–$1,600 per repo). `freelance/` contains the profile, gig tiers, proposal template, and delivery workflow. `python -m worker pitch <repo>` drafts a repo-specific proposal; `examples/click/` is an unedited portfolio sample.
