# Delivery workflow

## 0. Before proposing (5 min, automated)
```
python -m worker pitch https://github.com/<client>/<repo> --client "Name" --budget 900
```
Read the draft. If the scan reports > 100k LOC or `RepoTooLarge`, re-tier before quoting.

## 1. Intake (client message)
Ask for:
1. Repo access — read-only collaborator invite to your GitHub account, or a zip.
2. Audience — users, contributors, or both. (Changes README emphasis.)
3. House style — existing docs to match, wording to avoid, license header needs.
4. Delivery — PR to a branch (default) or Markdown files.

Do not start until payment is funded in escrow (Upwork fixed-price milestone / Fiverr order).

## 2. Run (3–10 min wall, hands-off)
Local checkout:
```
git clone --depth 1 <url> work/client/<repo>
python -m worker local work/client/<repo> deliveries/<repo>
```
Or, if they installed the docbot App: `python -m worker enqueue <owner>/<repo>` → PR appears.

Tier → what to keep: Basic = README + one module; Standard = README, modules, API;
Premium = everything + architecture page + CONTRIBUTING (write those two by hand from the
generated material; the model output is the raw material).

## 3. QA (the part that earns the rate) — 30–60 min
Checklist, in order:
- [ ] Every command in the README actually exists (`grep` the flag/subcommand in the source).
- [ ] No invented parameters in the API reference — spot-check 10 entries against signatures.
- [ ] Module guide "gotchas" are real (open the file; confirm the claim). Delete any you can't verify.
- [ ] Remove anything that reads like it's about a different project (rare, but check).
- [ ] Tone matches client's existing docs; fix headings/casing.
- [ ] No secrets, internal URLs, or client names leaked into examples.
- [ ] Add the "Questions for you" section: 3–6 places where intent was unclear.

## 4. Deliver
- PR titled "docs: README, module guides, API reference" with a body listing files and the
  questions section. Or zip of `deliveries/<repo>/`.
- Message: what's included, the questions, revision window (7 days).

## 5. Revise
One pass per included revision. Re-run generation only if code changed; otherwise edit by hand.

## 6. Close
- Ask for the review (Upwork weights recent reviews heavily).
- Offer upkeep: "$120/mo, re-run on every release, PR delivered" — that's the subscription.
- `rm -rf work/client/<repo> deliveries/<repo>` — nothing retained.

## Guardrails
- Floor $350. Rush +50%. Anything over 200k LOC: decline or scope to a subsystem.
- Never document code the client doesn't have rights to (forks of proprietary code, etc.).
- Time budget per Standard job: ≤ 2 hours human. If QA finds > 5 errors, the repo is a bad
  fit for the pipeline — say so and refund rather than hand-write.
