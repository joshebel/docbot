# API Reference

## `worker/__main__.py`

- `cmd_check(cfg)` — Verifies the inference endpoint is reachable.
- `process(cfg, router, jlog, job, queue_depth, plan)` — Executes a single job using the provided router and job log.
- `cmd_local(cfg, path, out)` — Performs a dry run against a local checkout, writing generated docs to `./out` without touching GitHub.
- `main(argv)` — Entry point for the CLI.

## `worker/accounts.py`

- `Accounts` — Manages the mapping of GitHub accounts to their subscription plans, fed by Marketplace purchase webhooks.
  - `__init__(self, path)` — Initializes the account store at the given path.
  - `close(self)` — Closes the underlying storage.
  - `plan(self, login) -> str` — Returns the current plan for a given login.
  - `set_plan(self, login, marketplace_plan)` — Updates the plan for a login based on a Marketplace event.
  - `set_installation(self, login, installation_id)` — Associates a GitHub App installation ID with a login.
  - `installation(self, login) -> str` — Returns the installation ID for a login.
  - `all(self)` — Returns all account records.

## `worker/config.py`

- `load_dotenv(path)` — Loads environment variables from a `.env` file without overriding existing real environment variables.
- `Config` — Environment-driven configuration object.
  - `from_env(cls)` — Class method to instantiate a `Config` from the current environment.

## `worker/generate.py`

- `Result` — Container for the output of a documentation generation run.
- `Generator` — Generates README, per-module docs, and API references using a model backend.
  - `__init__(self, backend, snap, repo_name, max_file_bytes, context_tokens)` — Initializes the generator with a model backend, repo snapshot, and limits.
  - `readme(self)` — Generates the repository README.
  - `module_docs(self)` — Generates documentation for individual modules.
  - `api_reference(self)` — Generates the API reference documentation.
  - `run(self) -> Result` — Executes the full generation pipeline and returns the result.

## `worker/github.py`

- `app_jwt(app_id, key_path) -> str` — Generates an RS256 JWT for the GitHub App itself, valid for a maximum of 10 minutes.
- `installation_token(app_id, key_path, installation_id) -> str` — Exchanges the App JWT for a short-lived installation token.
- `repo_info(token, repo)` — Fetches metadata for a repository using an installation token.
- `app_webhook_config(app_id, key_path)` — Retrieves the current App webhook configuration, masking the secret.
- `set_app_webhook_url(app_id, key_path, url)` — Re-points the App's webhook URL, useful when a tunnel hostname changes.
- `clone(token, repo, ref, dest)` — Clones a repository using the provided token and ref.
- `commit_and_push(token, dest, branch, message, files)` — Commits and force-pushes files to a branch; idempotent on rerun.
- `ensure_pr(token, repo, head, base, title, body)` — Opens a pull request or updates an existing one.

## `worker/ingest.py`

- `RepoTooLarge` — Exception raised when a repository exceeds size limits.
- `RepoFile` — Represents a single file in the repository snapshot.
- `Snapshot` — In-memory representation of the repository tree and file contents.
  - `get(self, rel, max_bytes)` — Retrieves the content of a file by relative path, truncated to `max_bytes`.
- `scan(root, max_repo_bytes, max_files, max_file_bytes) -> Snapshot` — Scans a local directory to build a repository snapshot.
- `signatures(snap, rf) -> str` — Extracts function/class signatures and docstrings from a file.
- `tree_text(snap) -> str` — Formats the repository tree as text.
- `est_tokens(s) -> int` — Estimates the token count for a string.
- `build_context(snap, repo_name, token_budget) -> str` — Builds a deterministic shared context prefix for model calls.

## `worker/llm.py`

- `Usage` — Tracks token usage and costs for a model call.
  - `add(self, u)` — Accumulates usage from another `Usage` object.
- `Backend` — Abstract base class for model backends.
  - `chat(self, messages, max_tokens, temperature) -> tuple[str, Usage]` — Sends a chat request and returns the response and usage.
  - `healthy(self) -> bool` — Checks if the backend is reachable.
  - `cost(self, u) -> float` — Calculates the USD cost for a given usage.
- `LocalBackend(Backend)` — Backend for local OpenAI-compatible vLLM instances.
  - `__init__(self, base_url, api_key, model, enable_thinking)` — Initializes the local backend.
  - `models(self)` — Lists available models.
  - `healthy(self)` — Checks local backend health.
  - `chat(self, messages, max_tokens, temperature)` — Sends a chat request to the local model.
- `AnthropicBackend(Backend)` — Paid lane backend using the Anthropic Messages API via stdlib `urllib`.
  - `__init__(self, api_key, model, effort)` — Initializes the Anthropic backend.
  - `healthy(self)` — Checks Anthropic API health.
  - `chat(self, messages, max_tokens, temperature)` — Sends a chat request to Anthropic.
- `Spend` — Daily USD ledger for the paid lane, stored in a JSON file.
  - `__init__(self, log_dir)` — Initializes the spend ledger.
  - `today(self) -> float` — Returns the total spend for the current day.
  - `add(self, usd)` — Adds a USD amount to the ledger.
- `Router` — Routes requests to the appropriate backend based on plan and queue depth.
  - `__init__(self, cfg)` — Initializes the router with configuration.
  - `pick(self, queue_depth, plan) -> Backend` — Selects a backend based on queue depth and the user's plan.

## `worker/log.py`

- `scrub(s)` — Removes token-shaped strings from a string to prevent leaks.
- `info(msg, **kv)` — Logs an informational message to stderr with optional key-value pairs.
- `JobLog` — Writes one JSONL record per job, including repo, files, tokens, model, and wall time.
  - `__init__(self, log_dir)` — Initializes the job log.
  - `write(self, **rec)` — Writes a job record to the log.

## `worker/pitch.py`

- `run(cfg, src, client, budget, turnaround)` — Drafts a repo-specific freelance proposal.

## `worker/queue.py`

- `Job` — Represents a queued job.
- `Queue` — Abstract interface for the job queue.
  - `enqueue(self, repo, installation_id, ref) -> Job` — Adds a job to the queue.
  - `claim(self) -> 'Job | None'` — Claims the next available job.
  - `complete(self, job_id, result)` — Marks a job as complete.
  - `fail(self, job_id, err, retry)` — Marks a job as failed, optionally for retry.
  - `depth(self) -> int` — Returns the number of jobs in the queue.
  - `has_queued(self, repo) -> bool` — Checks if a repo already has a queued job.
  - `list(self, limit) -> list` — Lists jobs up to a limit.
- `SqliteQueue(Queue)` — SQLite implementation of the `Queue` interface.
  - `__init__(self, path)` — Initializes the SQLite queue.
  - `close(self)` — Closes the database connection.
  - `enqueue(self, repo, installation_id, ref)` — Adds a job to the SQLite queue.
  - `claim(self)` — Claims the next job from SQLite.
  - `complete(self, job_id, result)` — Marks a job complete in SQLite.
  - `fail(self, job_id, err, retry)` — Marks a job failed in SQLite.
  - `depth(self)` — Returns the queue depth from SQLite.
  - `has_queued(self, repo)` — Checks for existing queued jobs in SQLite.
  - `list(self, limit)` — Lists jobs from SQLite.
  - `dump(self, limit)` — Dumps job records for debugging.

## `worker/supervisor.py`

- `Child` — Manages a child process for the pipeline.
  - `__init__(self, name, argv, log_dir)` — Initializes the child process manager.
  - `start(self)` — Starts the child process.
  - `alive(self)` — Checks if the child process is running.
  - `stop(self)` — Stops the child process.
  - `ensure(self)` — Ensures the child process is running, restarting if necessary.
- `tunnel_url(log_path, since) -> str` — Extracts the newest Cloudflare tunnel hostname from a log file.
- `run(cfg)` — Runs the supervisor loop, managing the webhook receiver, worker loop, and tunnel.

## `worker/webhook.py`

- `verify(secret, body, sig_header) -> bool` — Verifies the `X-Hub-Signature-256` header for a webhook request.
- `Dispatcher` — Handles GitHub webhook events and triggers side effects; testable without HTTP.
  - `__init__(self, queue, accounts, docs_branch)` — Initializes the dispatcher with dependencies.
  - `handle(self, event, p) -> str` — Routes an event to the appropriate handler.
  - `on_installation(self, p)` — Handles installation events.
  - `on_installation_repositories(self, p)` — Handles repository addition/removal events.
  - `on_push(self, p)` — Handles push events.
  - `on_marketplace_purchase(self, p)` — Handles Marketplace purchase events.
  - `on_ping(self, p)` — Handles ping events.
- `make_handler(secret, dispatcher)` — Creates an HTTP handler for the webhook server.
- `serve(cfg)` — Starts the webhook HTTP server.
