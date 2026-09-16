# Privacy Policy — docbot

_Last updated: 2026-09-16_

docbot is a GitHub App that generates and maintains repository documentation by opening pull
requests. This policy describes what data it touches and what happens to it.

## What docbot accesses

When docbot is installed on a repository and a job runs, it:

- clones the repository's default branch (or the branch that was pushed) using a short-lived
  GitHub App installation token;
- reads the file tree, public function/class signatures and docstrings, the existing README,
  and the full contents of a small number of source files the model requests;
- skips vendored, generated, binary and build directories, and refuses repositories over a
  configured size cap.

docbot receives webhook events from GitHub (`installation`, `installation_repositories`,
`push`, `marketplace_purchase`). These contain repository names, the installing account's
login, and plan names. No commit contents are included in webhooks.

## What docbot stores

- **Job records**: repository name, list of files sent to the model, token counts, model name,
  wall time, and result status. No source code.
- **Account records**: GitHub account login, installation id, and current Marketplace plan.
- **Cloned source**: kept on the worker only for the duration of a job and deleted when the
  job finishes, whether it succeeds or fails.

docbot does not store GitHub credentials beyond the App's own private key, and never logs
installation tokens.

## Where processing happens

- **Free tier**: all model inference runs on infrastructure operated by the docbot operator.
  Source is not sent to any third party.
- **Pro tier**: when the operator's local queue is congested or unavailable, a job may be
  routed to Anthropic's API (https://www.anthropic.com/legal/privacy). Only the repository
  context described above is sent; Anthropic's terms govern retention on their side. Daily
  spend on this lane is capped and logged.

## What docbot writes

docbot pushes a branch named `docs/auto` and opens or updates one pull request on it. It never
merges, never writes to other branches, and never modifies repository settings.

## Retention and deletion

Uninstalling the App stops all processing immediately. Job and account records are retained
for operational debugging for up to 90 days and can be deleted on request. Cloned source is
never retained after a job.

## Contact

Open an issue at https://github.com/joshebel/docbot/issues or email the maintainer via the
GitHub profile at https://github.com/joshebel.
