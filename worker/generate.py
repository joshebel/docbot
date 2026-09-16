"""Doc generation: README, per-module docs, API reference.
Every call shares one system prefix (repo context) so vLLM's prefix cache
absorbs the big part; per-call user messages stay small."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .ingest import Snapshot, build_context, signatures
from .llm import Backend, Usage
from .log import info

SYSTEM_RULES = """You are a senior engineer writing documentation for the repository below.
Rules: be accurate to the code shown; never invent APIs, flags, or files that are not present.
If something is unclear, say so briefly instead of guessing. Output GitHub-flavored Markdown only,
no preamble, no closing remarks, no code fences around the whole document."""

THINK_RE = re.compile(r"<think>.*?</think>\s*", re.S)


@dataclass
class Result:
    files: dict = field(default_factory=dict)    # rel path -> content
    files_sent: list = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    calls: int = 0


def _clean(text: str) -> str:
    text = THINK_RE.sub("", text).strip()
    # strip a single outer ```markdown fence if the model wrapped everything
    m = re.fullmatch(r"```(?:markdown|md)?\n(.*)\n```", text, re.S)
    return (m.group(1) if m else text).rstrip() + "\n"


def _json_list(text: str) -> list:
    m = re.search(r"\[.*?\]", text, re.S)
    if not m:
        return []
    try:
        v = json.loads(m.group(0))
        return [str(x) for x in v if isinstance(x, str)]
    except ValueError:
        return []


TEST_DIRS = {"tests", "test", "spec", "specs", "__tests__", "testing"}


def _modules(snap: Snapshot) -> dict:
    """Group code files by top-level directory (or 'root'). Test dirs are
    covered by the README's development section, not their own page."""
    groups = {}
    for f in snap.files:
        if f.lang in ("markdown", "rst", "text", "json", "yaml", "toml", "html", "css"):
            continue
        parts = Path(f.path).parts
        if parts[0] in TEST_DIRS:
            continue
        key = parts[0] if len(parts) > 1 else "root"
        groups.setdefault(key, []).append(f)
    return groups


class Generator:
    def __init__(self, backend: Backend, snap: Snapshot, repo_name: str, max_file_bytes: int,
                 context_tokens: int):
        self.b = backend
        self.snap = snap
        self.repo = repo_name
        self.max_file_bytes = max_file_bytes
        self.prefix = SYSTEM_RULES + "\n\n" + build_context(snap, repo_name, context_tokens)
        self.res = Result()

    def _call(self, user: str, max_tokens: int, temperature=0.0) -> str:
        # temperature 0: unchanged source -> (near-)identical docs -> clean no-op reruns
        text, u = self.b.chat(
            [{"role": "system", "content": self.prefix}, {"role": "user", "content": user}],
            max_tokens=max_tokens, temperature=temperature)
        self.res.usage.add(u)
        self.res.calls += 1
        info("llm call", n=self.res.calls, tok_in=u.prompt, tok_out=u.completion, model=self.b.model)
        return text

    def _request_files(self, purpose: str, limit: int) -> str:
        """Ask the model which files it needs, then inline them."""
        ask = (f"To write {purpose}, which files do you need the full source of? "
               f"Reply with a JSON array of at most {limit} repo-relative paths from the tree, nothing else.")
        wanted = _json_list(self._call(ask, 300, temperature=0.0))[:limit]
        known = {f.path for f in self.snap.files}
        chunks = []
        for p in wanted:
            if p in known:
                src = self.snap.get(p, self.max_file_bytes)
                if src:
                    chunks.append(f"### {p}\n```\n{src}\n```")
                    if p not in self.res.files_sent:
                        self.res.files_sent.append(p)
        return "\n\n".join(chunks)

    def readme(self):
        extra = self._request_files("the README", 6)
        prompt = ("Write the repository README.md. Sections: title + one-paragraph summary, features, "
                  "installation/setup, usage (with real commands from the code), configuration, "
                  "project layout (short), development/testing, license (only if a LICENSE file exists). "
                  "Preserve any accurate facts from the existing README; replace stale ones.\n\n"
                  + (f"Full source of files you requested:\n\n{extra}" if extra else ""))
        self.res.files["README.md"] = _clean(self._call(prompt, 3000))

    def module_docs(self):
        for name, files in _modules(self.snap).items():
            paths = "\n".join(f.path for f in files)
            extra = self._request_files(f"docs for module `{name}`", 4)
            prompt = (f"Write docs/modules/{name}.md for the `{name}` module. Files:\n{paths}\n\n"
                      "Cover: purpose, key components and how they interact, public entry points, "
                      "notable design decisions, gotchas. Keep it under ~600 words.\n\n"
                      + (f"Full source of files you requested:\n\n{extra}" if extra else ""))
            self.res.files[f"docs/modules/{name}.md"] = _clean(self._call(prompt, 1800))

    def api_reference(self):
        prompt = ("Write docs/API.md: an API reference of the public surface listed in the signatures "
                  "section. One heading per file, then one entry per public class/function with a "
                  "one-to-two sentence description derived from names, docstrings and context. "
                  "Skip files with no public symbols. Do not invent parameters not shown.")
        self.res.files["docs/API.md"] = _clean(self._call(prompt, 5000))

    def run(self) -> Result:
        self.readme()
        self.module_docs()
        self.api_reference()
        return self.res
