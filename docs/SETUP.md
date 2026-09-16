# GitHub App setup (one-time)

The worker authenticates as a GitHub App installation. No PAT, no OAuth.

## 1. Create the App

1. GitHub → your avatar → **Settings** → **Developer settings** → **GitHub Apps** → **New GitHub App**.
   (For a personal-account app. For an org: org **Settings** → Developer settings.)
2. Fill in:
   - **GitHub App name**: `docbot-<yourname>` (must be globally unique)
   - **Homepage URL**: any URL, e.g. the repo URL
   - **Webhook**: **uncheck "Active"** — no receiver yet. Leave URL blank.
3. **Repository permissions** (only these; everything else "No access"):
   - **Contents**: Read and write — clone + push `docs/auto`
   - **Pull requests**: Read and write — open/update the PR
   - **Metadata**: Read-only (auto-selected)
4. **Where can this GitHub App be installed?** → **Only on this account** for now.
5. **Create GitHub App**.

## 2. Collect credentials

On the app's settings page after creation:

1. Note the **App ID** (top of the page, integer) → `GH_APP_ID`.
2. Scroll to **Private keys** → **Generate a private key**. A `.pem` downloads.
   Move it into this repo dir (it's gitignored) and set `GH_APP_PRIVATE_KEY_PATH=./<name>.pem`.
   Treat it like a password. It is the only secret the worker needs for GitHub.
3. Ignore the client ID / client secret; the worker does not use OAuth.

## 3. Install the App on the throwaway repo

1. Left sidebar of the app page → **Install App** → **Install** next to your account.
2. Choose **Only select repositories** → pick the throwaway repo → **Install**.
3. You land on `https://github.com/settings/installations/<NUMBER>`.
   That `<NUMBER>` is the **Installation ID** → `GH_INSTALLATION_ID`.

## 4. Configure and verify

```
cp .env.example .env          # set GH_APP_ID, GH_INSTALLATION_ID, GH_APP_PRIVATE_KEY_PATH
python -m worker check        # inference endpoint
python -m worker enqueue owner/throwaway-repo
python -m worker run-once
```

Expected: a branch `docs/auto` and an open PR titled "docs: auto-generated documentation".
Re-running `enqueue` + `run-once` force-pushes the same branch and updates the same PR.

## 5. Later (not now)

- **Webhook receiver**: re-enable the webhook on the app page, set the URL + `GH_WEBHOOK_SECRET`,
  subscribe to `push` (and `installation`) events. Until then, jobs are enqueued manually.
- **Public listing**: switch "Where can this App be installed" to "Any account".

## Troubleshooting

| Symptom | Cause |
|---|---|
| `401 A JSON web token could not be decoded` | wrong `.pem` or `GH_APP_ID` |
| `401 'Expiration time' claim ('exp') is too far in the future` | worker clock skew > ~1 min; sync time |
| `404 Not Found` on `/app/installations/<id>/access_tokens` | wrong `GH_INSTALLATION_ID`, or app not installed on that account |
| `403 Resource not accessible by integration` | missing Contents or Pull requests write permission; re-save app perms, then **accept** the new permissions on the installation page |
| `git push ... 403` | Contents permission is read-only, or repo not selected in the installation |
