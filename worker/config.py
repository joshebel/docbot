"""Env-driven config. Loads .env (if present) without overriding real env."""
import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path=".env"):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _env(k, default=""):
    return os.environ.get(k, default).strip()


def _int(k, default):
    v = _env(k)
    return int(v) if v else default


@dataclass
class Config:
    local_base_url: str
    local_api_key: str
    local_model: str
    local_enable_thinking: bool
    anthropic_api_key: str
    anthropic_model: str
    spill_enabled: bool
    spill_queue_depth: int
    daily_usd_cap: float
    gh_app_id: str
    gh_installation_id: str
    gh_private_key_path: str
    docs_branch: str
    queue_path: Path
    work_dir: Path
    log_dir: Path
    poll_seconds: int
    max_repo_bytes: int
    max_files: int
    max_file_bytes: int

    @classmethod
    def from_env(cls):
        load_dotenv()
        c = cls(
            local_base_url=_env("LOCAL_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/"),
            local_api_key=_env("LOCAL_API_KEY"),
            local_model=_env("LOCAL_MODEL"),
            local_enable_thinking=_env("LOCAL_ENABLE_THINKING", "0") == "1",
            anthropic_api_key=_env("ANTHROPIC_API_KEY"),
            anthropic_model=_env("ANTHROPIC_MODEL", "claude-sonnet-5"),
            spill_enabled=_env("SPILL_ENABLED", "0") == "1",
            spill_queue_depth=_int("SPILL_QUEUE_DEPTH", 20),
            daily_usd_cap=float(_env("DAILY_USD_CAP") or 5),
            gh_app_id=_env("GH_APP_ID"),
            gh_installation_id=_env("GH_INSTALLATION_ID"),
            gh_private_key_path=_env("GH_APP_PRIVATE_KEY_PATH"),
            docs_branch=_env("DOCS_BRANCH", "docs/auto"),
            queue_path=Path(_env("QUEUE_PATH", "./state/queue.sqlite")),
            work_dir=Path(_env("WORK_DIR", "./work")),
            log_dir=Path(_env("LOG_DIR", "./state")),
            poll_seconds=_int("POLL_SECONDS", 15),
            max_repo_bytes=_int("MAX_REPO_BYTES", 40_000_000),
            max_files=_int("MAX_FILES", 3000),
            max_file_bytes=_int("MAX_FILE_BYTES", 200_000),
        )
        for d in (c.queue_path.parent, c.work_dir, c.log_dir):
            d.mkdir(parents=True, exist_ok=True)
        return c
