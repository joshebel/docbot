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
python -m worker enqueue owner/repo       # queue a job
python -m worker run-once                 # process one
python -m worker serve                    # poll loop
```

Per-job records: `state/jobs.jsonl` (repo, files sent, tokens in/out, model, wall time).
Paid-lane spend ledger: `state/spend.json`.

## Layout

- `worker/config.py` env → Config
- `worker/queue.py` Queue interface + SQLite impl
- `worker/github.py` App JWT, installation token, clone/push/PR
- `worker/ingest.py` tree, signatures, skip lists, size cap
- `worker/llm.py` local backend, Anthropic stub, spill router, $ cap
- `worker/generate.py` README / modules / API generation
- `worker/__main__.py` CLI + job loop
