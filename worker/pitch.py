"""Proposal drafts for freelance documentation gigs.

    python -m worker pitch <git-url | local-path> [--client "Name"] [--budget 900]

Scans the repo exactly like a job would, then asks the model for a short, specific
proposal: what's missing, what we'd deliver, why it fits *their* code. The human
reviews and pastes it into Upwork/Fiverr — platforms forbid bot bidding, so this
stops at a draft on disk (freelance/pitches/<name>.md)."""
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .generate import _clean
from .ingest import build_context, scan
from .llm import LocalBackend
from .log import info

PROMPT = """You are drafting a freelance proposal on behalf of a documentation contractor.
The context above is OUR automated scan of the prospect's repository: the file tree, their
existing README verbatim (if any), and a "Signatures and docstrings" section that WE extracted
from their source. That section is not part of their docs — never refer to it as something
they wrote or should fix. Judge their documentation only by the README and any docs/ files.
Write the proposal in first person
("I"), plain and specific, no marketing tone, no emoji, under 230 words. Structure:

1. One sentence showing you actually read the code: name 2-3 concrete things (modules,
   entry points, a CLI, an API surface) using their real file/identifier names.
2. What is missing or weak in their current docs (existing README shown above, if any).
   Be factual; if the README is decent, say what it lacks rather than inventing problems.
3. Deliverables: a README with real install/usage commands, one guide per module, an
   API reference, delivered as a pull request so they review before merging. Mention that
   a first draft is ready in {turnaround}, with one revision round included.
4. Close with one clarifying question about their audience or the thing you were least
   sure about in the code.
{client_line}{budget_line}
Output only the proposal text."""


def _fetch(src: str, work: Path) -> Path:
    if Path(src).exists():
        return Path(src)
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", src.rstrip("/").split("/")[-1].removesuffix(".git"))
    dest = work / "pitch" / name
    if dest.exists():
        shutil.rmtree(dest, onexc=lambda f, x, e: (Path(x).chmod(0o700), f(x)))
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", "--no-tags", src, str(dest)],
                   check=True, capture_output=True)
    return dest


def run(cfg, src: str, client: str = "", budget: str = "", turnaround="3 business days"):
    t0 = time.time()
    root = _fetch(src, cfg.work_dir)
    snap = scan(root, cfg.max_repo_bytes, cfg.max_files, cfg.max_file_bytes)
    b = LocalBackend(cfg.local_base_url, cfg.local_api_key, cfg.local_model, cfg.local_enable_thinking)
    ctx = build_context(snap, root.name, int(b.max_model_len * 0.5))
    prompt = PROMPT.format(
        turnaround=turnaround,
        client_line=f"\nAddress the client as {client}." if client else "",
        budget_line=f"\nThe posted budget is ${budget}; do not haggle, just confirm it covers the scope." if budget else "",
    )
    text, u = b.chat([{"role": "system", "content": ctx}, {"role": "user", "content": prompt}],
                     max_tokens=700, temperature=0.2)
    out_dir = Path("freelance") / "pitches"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{root.name}.md"
    header = (f"<!-- draft for {src} | {len(snap.files)} files scanned | "
              f"{u.prompt} in / {u.completion} out tokens | review before sending -->\n\n")
    out.write_text(header + _clean(text), encoding="utf-8", newline="\n")
    info("pitch drafted", repo=root.name, files=len(snap.files), wall_s=round(time.time() - t0, 1))
    print(out.read_text(encoding="utf-8"))
    print(f"\n[saved to {out}]", file=sys.stderr)
    return out
