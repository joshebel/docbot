"""Stderr logging + JSONL job records. Scrubs anything token-shaped."""
import json
import re
import sys
import time
from pathlib import Path

_TOKEN_RE = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}"
    r"|Bearer\s+[A-Za-z0-9._~+/=-]{8,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})"
)


def scrub(s):
    return _TOKEN_RE.sub("<redacted>", str(s))


def info(msg, **kv):
    tail = " ".join(f"{k}={scrub(v)}" for k, v in kv.items())
    print(time.strftime("%H:%M:%S"), scrub(msg), tail, file=sys.stderr, flush=True)


class JobLog:
    """One record per job: repo, files sent, tokens in/out, model, wall time."""

    def __init__(self, log_dir: Path):
        self.path = Path(log_dir) / "jobs.jsonl"

    def write(self, **rec):
        rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        if "error" in rec:
            rec["error"] = scrub(rec["error"])
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
