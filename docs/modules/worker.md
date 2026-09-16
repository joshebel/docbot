# `worker` module

The `worker` package is the entire docbot pipeline: it polls a local job queue, clones a repository with a GitHub App installation token, generates README / per-module docs / API reference with a local vLLM model (optionally spilling to Anthropic for paid plans), pushes `docs/auto`, and opens or updates a PR. Stdlib only; RS256 signing is delegated to the `openssl` CLI.

## Components

- **`config.py`** — `Config.from_env()` builds a dataclass from environment variables (loading `.env` via `setdefault` so real env wins). Creates `queue_path`, `work_dir`, and `log_dir` on disk.
- **`queue.py`** — `Queue` interface + `SqliteQueue` (WAL mode). `claim()` uses `BEGIN IMMEDIATE` so select+update is atomic across worker processes. `fail(job_id, err, retry)` re-queues or marks failed.
- **`github.py`** — App JWT, installation token, `clone`, `commit_and_push` (idempotent force-push to the same branch), `ensure_pr`.
- **`ingest.py`** — `scan()` walks the checkout, applies size/file caps, collects signatures and docstrings into a `Snapshot`. `build_context()` produces a deterministic shared prefix for every model call on the job.
- **`llm.py`** — `LocalBackend` (OpenAI-compatible vLLM, 3-retry with backoff) and `AnthropicBackend` (Messages API, effort-capped, server-side fallback). `Router.pick(queue_depth, plan)` implements the spill rule: free-plan jobs stay local; pro-plan jobs spill when queue depth exceeds `SPILL_QUEUE_DEPTH` or local is unhealthy, bounded by `Spend` (daily USD ledger in `state/spend.json`).
- **`generate.py`** — `Generator.run()` produces README, per-module docs, and API reference; returns a `Result` with `files`, `usage`, and `calls`.
- **`webhook.py`** — `Dispatcher` (pure event→side-effect logic) + `serve()` (stdlib `http.server`). Verifies `X-Hub-Signature-256`; handles installation, push, and Marketplace purchase events.
- **`accounts.py`** — `Accounts` maps login → plan, fed by Marketplace webhooks.
- **`log.py`** — `JobLog` writes one JSONL record per job (repo, tokens, model, wall time). `scrub()` strips token-shaped strings from stderr.
- **`supervisor.py`** — `run(cfg)` keeps the webhook receiver, worker loop, and Cloudflare tunnel alive as child processes.
- **`pitch.py`** — `run()` drafts a repo-specific freelance proposal.
- **`__main__.py`** — CLI entry point. `process()` is the core job loop: clone → scan → generate → push → PR. `cmd_local()` is a dry run with no GitHub.

## Entry points

```
python -m worker check          # verify inference endpoint
python -m worker local <path>   # dry run, writes ./out/
python -m worker enqueue owner/repo
python -m worker run-once       # process one job
python -m worker serve          # poll loop
python -m worker webhook        # GitHub webhook receiver
python -m worker supervise      # webhook + serve + tunnel
python -m worker pitch <repo>   # freelance proposal
```

## Design decisions

- **Stdlib only.** All HTTP is `urllib`; RS256 is `openssl` via subprocess. No pip dependencies.
- **Spill router.** Free-plan jobs never leave the local box. Pro-plan jobs spill to Anthropic only when queue depth or local health triggers it, and only until the daily USD cap is hit. If local is down *and* the cap is reached, the job raises rather than silently failing.
- **Idempotent push.** Re-running the worker force-pushes the same `docs/auto` branch; `commit_and_push` returns `None` when docs are unchanged, avoiding an empty PR.
- **Queue as interface.** `SqliteQueue` is the only impl today; the docstring notes an HTTP-backed impl can be swapped in later.

## Gotchas

- `LocalBackend` raises `RuntimeError` if the model returns only reasoning (thinking ate the token budget) — surface this by raising `max_tokens` or disabling thinking.
- `AnthropicBackend` uses `output_config.effort` and `fallbacks: "default"`; the `anthropic-beta` header is pinned to `server-side-fallback-2026-07-01`.
- `Spend` is a single JSON file with no locking; safe for a single worker process but not for concurrent writers.
- `claim()` increments `attempts`; the retry policy in `__main__.py` re-queues only when `attempts < 2` and the error is not `RepoTooLarge`.
