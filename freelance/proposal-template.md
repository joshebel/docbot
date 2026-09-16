# Proposal template

Run `python -m worker pitch <repo-url> --client "<Name>" --budget <n>` first; it writes
`freelance/pitches/<repo>.md` with the specific observations. Then edit into this shape.
Keep it under 250 words. Upwork clients read the first two lines and skim the rest.

---

Hi {name},

I looked at {repo} before writing this. {one sentence naming 2–3 real things: e.g. "The CLI
in `shorten/cli.py` and the `Store` class in `store.py` are the two entry points; the base62
codec is the only pure module."}

{one or two sentences on what's missing: e.g. "Your README covers install but not the CLI
subcommands, and there's no reference for the public `Store` API."}

Here's what I'd deliver as a pull request to your repo:

- README rewritten from the code: real install/usage commands, configuration, layout
- One guide per module ({list them}) — purpose, key components, entry points, gotchas
- API reference for the public surface
- A short list of clarifying questions where the code left intent ambiguous

First draft in {3 business days}; {1} revision round included. Fixed price {$900} — that
covers everything above for a repo this size.

One question so I get the audience right: {specific question — e.g. "is this for users
installing the CLI, or for contributors?"}

{Your name}

---

## Don'ts
- Don't paste the pitch tool's output unedited — read it, cut anything not true.
- Don't mention "AI" in the first paragraph; do answer honestly if asked (see gigs.md FAQ).
- Don't quote below $350; the floor exists because review time is real.
- Don't propose on jobs asking for end-user manuals or marketing sites.

## Job search filters (Upwork)
Keywords: "documentation" "README" "API documentation" "document codebase" "technical docs"
Filters: fixed-price ≥ $300, client payment verified, posted < 3 days.
Skip: hourly-only under $30, "ongoing content writer", anything without a repo.
