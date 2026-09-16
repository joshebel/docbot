"""Repo ingestion: tree + signatures/docstrings + existing README.
Full source only on request. Vendored/generated/build dirs skipped. Hard cap."""
import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", "third_party", "thirdparty", "dist", "build",
    "target", "out", ".venv", "venv", "env", "__pycache__", ".tox", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".next", ".nuxt", "coverage", "site-packages", "bin", "obj", ".idea", ".vscode",
    ".gradle", ".terraform", "Pods", "DerivedData", ".cache", "bower_components", ".eggs",
}
SKIP_SUFFIX = {
    ".min.js", ".min.css", ".map", ".lock", ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".o",
    ".a", ".class", ".jar", ".war", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".pdf",
    ".zip", ".gz", ".tar", ".bz2", ".xz", ".7z", ".woff", ".woff2", ".ttf", ".eot", ".mp3", ".mp4",
    ".mov", ".wav", ".sqlite", ".db", ".bin", ".pb", ".onnx", ".safetensors", ".pt", ".ckpt", ".ipynb",
}
SKIP_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock",
              "go.sum", "composer.lock", "Gemfile.lock", "Pipfile.lock", "uv.lock"}
GENERATED_RE = re.compile(r"(^|/)(generated|gen|_gen|autogen|\.generated)(/|$)|\.pb\.(go|py|js|ts)$|_pb2(_grpc)?\.py$")

LANG = {
    ".py": "python", ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin",
    ".cs": "csharp", ".rb": "ruby", ".php": "php", ".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp",
    ".hpp": "cpp", ".swift": "swift", ".sh": "shell", ".bash": "shell", ".ps1": "powershell",
    ".sql": "sql", ".md": "markdown", ".rst": "rst", ".toml": "toml", ".yaml": "yaml", ".yml": "yaml",
    ".json": "json", ".html": "html", ".css": "css", ".dockerfile": "docker", ".tf": "terraform",
}
README_NAMES = ("README.md", "README.rst", "README.txt", "README", "readme.md", "Readme.md")


class RepoTooLarge(Exception):
    pass


@dataclass
class RepoFile:
    path: str
    size: int
    lang: str


@dataclass
class Snapshot:
    root: Path
    files: list = field(default_factory=list)
    total_bytes: int = 0
    readme: str = ""
    skipped_dirs: int = 0

    def get(self, rel, max_bytes):
        p = self.root / rel
        if not p.is_file() or ".." in Path(rel).parts:
            return None
        b = p.read_bytes()
        if len(b) > max_bytes:
            b = b[:max_bytes] + b"\n... [truncated]"
        return b.decode("utf-8", errors="replace")


def _is_binary(p: Path) -> bool:
    try:
        with p.open("rb") as f:
            return b"\0" in f.read(4096)
    except OSError:
        return True


def scan(root: Path, max_repo_bytes, max_files, max_file_bytes) -> Snapshot:
    root = Path(root)
    snap = Snapshot(root=root)
    # sort by posix string: stable across OSes (Windows Path compare is case-insensitive)
    for p in sorted(root.rglob("*"), key=lambda x: x.relative_to(root).as_posix()):
        rel = p.relative_to(root)
        parts = rel.parts
        if any(part in SKIP_DIRS for part in parts[:-1]):
            continue
        if p.is_dir():
            if p.name in SKIP_DIRS:
                snap.skipped_dirs += 1
            continue
        if p.name in SKIP_NAMES or p.suffix.lower() in SKIP_SUFFIX or GENERATED_RE.search(rel.as_posix()):
            continue
        if any(rel.as_posix().endswith(s) for s in (".min.js", ".min.css")):
            continue
        size = p.stat().st_size
        if size == 0 or size > max_file_bytes or _is_binary(p):
            continue
        lang = LANG.get(p.suffix.lower(), "dockerfile" if p.name.lower() == "dockerfile" else "text")
        snap.files.append(RepoFile(rel.as_posix(), size, lang))
        snap.total_bytes += size
        if snap.total_bytes > max_repo_bytes:
            raise RepoTooLarge(f"repo exceeds MAX_REPO_BYTES={max_repo_bytes} (at {rel})")
        if len(snap.files) > max_files:
            raise RepoTooLarge(f"repo exceeds MAX_FILES={max_files}")
    for name in README_NAMES:
        if (root / name).is_file():
            snap.readme = (root / name).read_text(encoding="utf-8", errors="replace")[:20000]
            break
    return snap


# --- signatures ---------------------------------------------------------

def _py_sigs(src: str) -> str:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return _generic_sigs(src, "python")
    out = []
    doc = ast.get_docstring(tree)
    if doc:
        out.append(f'"""{doc.strip().splitlines()[0][:200]}"""')

    def sig(fn):
        args = [a.arg for a in fn.args.posonlyargs + fn.args.args]
        if fn.args.vararg: args.append("*" + fn.args.vararg.arg)
        args += [a.arg for a in fn.args.kwonlyargs]
        if fn.args.kwarg: args.append("**" + fn.args.kwarg.arg)
        ret = f" -> {ast.unparse(fn.returns)}" if fn.returns else ""
        pre = "async def" if isinstance(fn, ast.AsyncFunctionDef) else "def"
        return f"{pre} {fn.name}({', '.join(args)}){ret}"

    def walk(nodes, indent):
        for n in nodes:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if n.name.startswith("_") and not n.name.startswith("__"):
                    continue
                d = ast.get_docstring(n)
                out.append(f"{indent}{sig(n)}" + (f"  # {d.strip().splitlines()[0][:120]}" if d else ""))
            elif isinstance(n, ast.ClassDef):
                bases = ", ".join(ast.unparse(b) for b in n.bases)
                d = ast.get_docstring(n)
                out.append(f"{indent}class {n.name}({bases})" + (f"  # {d.strip().splitlines()[0][:120]}" if d else ""))
                walk(n.body, indent + "    ")
    walk(tree.body, "")
    return "\n".join(out)


_GENERIC = {
    "javascript": r"^\s*(export\s+)?(default\s+)?(async\s+)?(function\s*\*?\s*\w+|class\s+\w+|const\s+\w+\s*=\s*(async\s*)?\(|module\.exports)",
    "typescript": r"^\s*(export\s+)?(default\s+)?(async\s+)?(function\s*\*?\s*\w+|class\s+\w+|interface\s+\w+|type\s+\w+\s*=|enum\s+\w+|const\s+\w+\s*=\s*(async\s*)?\()",
    "go": r"^\s*(func\s|type\s+\w+\s+(struct|interface))",
    "rust": r"^\s*(pub(\(\w+\))?\s+)?(fn|struct|enum|trait|impl|mod|type)\s",
    "java": r"^\s*(public|protected)\s.*(\(|class\s|interface\s|enum\s)",
    "kotlin": r"^\s*(public\s+|internal\s+)?(fun|class|object|interface|data class)\s",
    "csharp": r"^\s*(public|protected|internal)\s.*(\(|class\s|interface\s|struct\s|enum\s)",
    "ruby": r"^\s*(def|class|module)\s",
    "php": r"^\s*(public|protected|abstract|final)?\s*(static\s+)?(function|class|interface|trait)\s",
    "c": r"^[A-Za-z_][\w\s\*]*\s\**\w+\s*\([^;]*\)\s*\{?\s*$",
    "cpp": r"^[A-Za-z_][\w\s\*:<>,]*\s\**\w+\s*\([^;]*\)\s*(const)?\s*\{?\s*$|^\s*(class|struct|namespace)\s+\w+",
    "swift": r"^\s*(public\s+|open\s+)?(func|class|struct|enum|protocol|extension)\s",
    "shell": r"^\s*(function\s+)?\w+\s*\(\)\s*\{",
    "powershell": r"^\s*function\s+[\w-]+",
    "sql": r"^\s*(create\s+(or\s+replace\s+)?(table|view|function|procedure|index))",
}


def _generic_sigs(src: str, lang: str) -> str:
    pat = _GENERIC.get(lang)
    lines = src.splitlines()
    if not pat:
        return "\n".join(l for l in lines[:25] if l.strip())
    rx = re.compile(pat, re.I)
    out = [l.rstrip()[:160] for l in lines if rx.match(l)]
    return "\n".join(out[:120])


def signatures(snap: Snapshot, rf: RepoFile) -> str:
    src = snap.get(rf.path, 400_000) or ""
    if rf.lang == "python":
        return _py_sigs(src)
    if rf.lang in ("markdown", "rst", "text", "toml", "yaml", "json", "html", "css", "docker", "terraform"):
        # config/doc files: first lines are usually enough
        return "\n".join(l for l in src.splitlines()[:15] if l.strip())[:800]
    return _generic_sigs(src, rf.lang)


def tree_text(snap: Snapshot) -> str:
    return "\n".join(f"{f.path}  ({f.size}B)" for f in snap.files)


def est_tokens(s: str) -> int:
    return len(s) // 4 + 1


def build_context(snap: Snapshot, repo_name: str, token_budget: int) -> str:
    """Shared prefix for every model call on this job. Deterministic ordering so
    vLLM prefix cache hits across calls."""
    head = [f"# Repository: {repo_name}", "", "## File tree", tree_text(snap), ""]
    if snap.readme:
        head += ["## Existing README", snap.readme, ""]
    head_txt = "\n".join(head)
    budget = token_budget - est_tokens(head_txt)
    sigs = []
    code_files = [f for f in snap.files if f.lang not in ("markdown", "rst", "text")]
    for f in code_files:
        s = signatures(snap, f)
        if s.strip():
            sigs.append((f, f"### {f.path}\n```\n{s}\n```"))
    total = sum(est_tokens(t) for _, t in sigs)
    if total > budget and sigs:
        # trim proportionally; keep every file represented
        scale = max(budget, 0) / total
        sigs = [(f, t[: max(200, int(len(t) * scale))]) for f, t in sigs]
    body = "\n\n".join(t for _, t in sigs)
    return head_txt + "## Signatures and docstrings (public surface)\n\n" + body + "\n"
