# Freelance track

Sell docbot's output as a service. One $500–$1,500 documentation project ≈ months of
Marketplace subscriptions. The worker does the clone → generate → PR; a human fronts the
account, reviews the output, and talks to the client.

| File | Use |
|---|---|
| `profile.md` | Upwork profile: title, overview, skills, rate. Paste once. |
| `gigs.md` | Fiverr gig + Upwork Project Catalog: three tiers with scope and price. |
| `proposal-template.md` | Skeleton for job proposals; `python -m worker pitch <repo>` fills the specifics. |
| `workflow.md` | Intake → run → QA → deliver → revise. Checklists and guardrails. |
| `pitches/` | Generated proposal drafts (gitignored except the click sample). |
| `../examples/click/` | Portfolio sample: docs generated for pallets/click, unedited. |

## Rules (platform ToS + reputation)

- Proposals and messages are sent by a human. The tool drafts; it never submits.
- Never claim the docs are hand-written. "AI-assisted, human-reviewed" is accurate and sells fine.
- Review every deliverable before it goes out. The model is good; it is not infallible.
- Never accept repos you can't legally process (client must have rights); never keep source
  after delivery.

## Accounts you need to create (human-only)

1. Upwork — freelancer profile, ID verification, payout method. Free plan is fine to start;
   Connects (bid tokens) cost ~$0.15 each, a proposal uses 8–16.
2. Optional: Fiverr — gig-based, buyers come to you; slower start, less proposal grind.
3. A public example repo or the `examples/` folder link for the portfolio.
