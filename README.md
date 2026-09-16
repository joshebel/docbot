# docbot

LAN worker for a GitHub App that generates and maintains repo docs.
Polls a local queue, clones with an App installation token, generates
README / per-module docs / API reference with a local vLLM model, pushes
`docs/auto`, opens (or updates) a PR. Stdlib only; RS256 via `openssl`.

## Setup

```
cp .env.example .env      # fill in
python -m worker check    # verify inference endpoint
python -m unittest -q
```

## Run

```
python -m worker local ../some-repo       # dry run, writes ./out/, no GitHub
python -m worker enqueue owner/repo       # queue a job manually
python -m worker run-once                 # process one
python -m worker serve                    # poll loop (the worker)
python -m worker webhook                  # GitHub webhook receiver (install/push/marketplace)
python -m worker accounts                 # account -> plan table
```

Two long-running processes: `serve` (does the work) and `webhook` (turns GitHub events
into queue rows). Both share `QUEUE_PATH`. Expose `webhook` via a tunnel or reverse proxy
and point the App's webhook URL at it; or move it to a VPS with an HTTP `Queue` impl later.

Per-job records: `state/jobs.jsonl` (repo, files sent, tokens in/out, model, wall time, plan).
Paid-lane spend ledger: `state/spend.json`.

## Tiers

| Plan | Model | Route |
|---|---|---|
| `free` | local vLLM only | always |
| `pro` | local, spills to Anthropic (`ANTHROPIC_MODEL`) | when queue depth > `SPILL_QUEUE_DEPTH` or local is unhealthy, until `DAILY_USD_CAP` |

Plans are set by Marketplace purchase webhooks (`docs/MARKETPLACE.md`). Paid lane is off
until `ANTHROPIC_API_KEY` is set and `SPILL_ENABLED=1`.

## Freelance track

The same pipeline sold as a fixed-price service ($350–$1,600 per repo). `freelance/` has the
profile, gig tiers, proposal template and delivery workflow; `python -m worker pitch <repo>`
drafts a repo-specific proposal; `examples/click/` is an unedited portfolio sample.

## Layout

- `worker/config.py` env → Config
- `worker/queue.py` Queue interface + SQLite impl
- `worker/github.py` App JWT, installation token, clone/push/PR
- `worker/ingest.py` tree, signatures, skip lists, size cap
- `worker/llm.py` local backend, Anthropic backend, plan-aware spill router, $ cap
- `worker/generate.py` README / modules / API generation
- `worker/webhook.py` signed webhook receiver → queue/accounts
- `worker/accounts.py` account → plan (fed by Marketplace events)
- `worker/__main__.py` CLI + job loop
- `docs/SETUP.md` App creation; `docs/MARKETPLACE.md` plans, listing copy, publish checklist
