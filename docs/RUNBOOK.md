# Runbook

## What runs

| Process | Command | Purpose |
|---|---|---|
| supervisor | `python -m worker supervise` | starts and restarts the three below; re-points the App webhook when the tunnel URL changes |
| webhook | `python -m worker webhook` | HTTP receiver on `WEBHOOK_PORT` (8787); verifies signatures; writes queue/accounts |
| serve | `python -m worker serve` | claims jobs, clones, generates docs, pushes `docs/auto`, opens/updates PR |
| tunnel | `bin/cloudflared.exe tunnel --url http://localhost:8787` | public HTTPS ingress for GitHub |

On the LAN worker host the supervisor is registered as a Windows scheduled task **docbot** that
runs at logon (see below). Logs: `state/supervisor.log`, `state/webhook.log`, `state/serve.log`,
`state/tunnel.log`. Job records: `state/jobs.jsonl`. Public URL: `state/tunnel_url.txt`.

## Health checks

```
type state\tunnel_url.txt                          # current public URL
curl https://<that-host>/healthz                   # -> ok
python -m worker jobs                              # queue
python -m worker accounts                          # plans
tail -f state/serve.log                            # live job progress
```

## Tunnel URL changed (quick tunnel restarted)

The supervisor updates the **App** webhook automatically via `PATCH /app/hook/config`.
The **Marketplace listing** webhook has no API: open
https://github.com/marketplace/docbot-joshebel/hook and paste the URL from `state/tunnel_url.txt`.
Until that's done, `marketplace_purchase` events are lost (GitHub retries for a while, and plans can
be fixed by hand with `python -m worker accounts`).

**Permanent fix:** a named Cloudflare tunnel with a stable hostname. Needs a Cloudflare account and a
domain on it: `bin\cloudflared tunnel login`, `tunnel create docbot`, `tunnel route dns docbot hooks.<domain>`,
then replace the tunnel child's argv in `worker/supervisor.py` with `tunnel run docbot`, and set both
GitHub webhooks to `https://hooks.<domain>/` once.

## Scheduled task

```
schtasks /Query /TN docbot /V /FO LIST
schtasks /Run /TN docbot
schtasks /End /TN docbot
```

Created with `schtasks /Create /TN docbot /SC ONLOGON /TR "<python> -m worker supervise" ...`
(working directory is the repo; see `scripts/docbot-task.cmd`).

## Failure modes

| Symptom | Where to look | Fix |
|---|---|---|
| jobs stay `queued` | `state/serve.log` | serve died? supervisor restarts it; check LAN vLLM at `LOCAL_BASE_URL` |
| `model returned reasoning only` | serve.log | `LOCAL_ENABLE_THINKING=0` must be set |
| `RepoTooLarge` | jobs.jsonl `status=too_large` | intended; raise `MAX_REPO_BYTES` only deliberately |
| GitHub 401 on token | serve.log | wrong `.pem` / `GH_APP_ID`, or clock skew |
| webhook 401 `bad signature` | webhook.log | secret in GitHub form ≠ `GH_WEBHOOK_SECRET` |
| no deliveries in GitHub → App → Advanced | — | webhook inactive, or URL stale (see above) |
| paid lane never used | jobs.jsonl `backend=local` | needs `ANTHROPIC_API_KEY`, `SPILL_ENABLED=1`, account plan `pro`, and depth > `SPILL_QUEUE_DEPTH` or local outage |

## Money path

Marketplace purchase → `marketplace_purchase` webhook → `accounts.plan = pro` → pro jobs eligible for
the Anthropic lane under `DAILY_USD_CAP`. Payout is handled by GitHub Marketplace to the account on
file. Transactions: https://github.com/marketplace/docbot-joshebel/insights/transactions
