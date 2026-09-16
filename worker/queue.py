"""Job queue. Interface + SQLite impl. Swap SqliteQueue for an HTTP-backed
impl later; callers only see Queue."""
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Job:
    id: str
    repo: str            # owner/name
    installation_id: str
    ref: str             # branch to document; "" = default branch
    status: str = "queued"
    attempts: int = 0
    created: float = 0.0
    result: str = ""


class Queue:
    def enqueue(self, repo, installation_id="", ref="") -> Job: raise NotImplementedError
    def claim(self) -> "Job | None": raise NotImplementedError
    def complete(self, job_id, result=""): raise NotImplementedError
    def fail(self, job_id, err, retry=False): raise NotImplementedError
    def depth(self) -> int: raise NotImplementedError
    def has_queued(self, repo) -> bool: raise NotImplementedError
    def list(self, limit=50) -> list: raise NotImplementedError


class SqliteQueue(Queue):
    def __init__(self, path: Path):
        self.db = sqlite3.connect(str(path), isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS jobs(
               id TEXT PRIMARY KEY, repo TEXT, installation_id TEXT, ref TEXT,
               status TEXT, attempts INT, created REAL, result TEXT)"""
        )

    def close(self):
        self.db.close()

    def _row(self, r):
        return Job(*r) if r else None

    def enqueue(self, repo, installation_id="", ref=""):
        j = Job(uuid.uuid4().hex[:12], repo, installation_id, ref, "queued", 0, time.time(), "")
        self.db.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?)", tuple(asdict(j).values()))
        return j

    def claim(self):
        # BEGIN IMMEDIATE makes select+update atomic across worker processes.
        self.db.execute("BEGIN IMMEDIATE")
        try:
            r = self.db.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY created LIMIT 1"
            ).fetchone()
            if r:
                self.db.execute(
                    "UPDATE jobs SET status='running', attempts=attempts+1 WHERE id=?", (r[0],)
                )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        j = self._row(r)
        if j:
            j.status, j.attempts = "running", j.attempts + 1
        return j

    def complete(self, job_id, result=""):
        self.db.execute("UPDATE jobs SET status='done', result=? WHERE id=?", (result, job_id))

    def fail(self, job_id, err, retry=False):
        self.db.execute(
            "UPDATE jobs SET status=?, result=? WHERE id=?",
            ("queued" if retry else "failed", str(err)[:2000], job_id),
        )

    def depth(self):
        return self.db.execute("SELECT COUNT(*) FROM jobs WHERE status='queued'").fetchone()[0]

    def has_queued(self, repo):
        return bool(self.db.execute(
            "SELECT 1 FROM jobs WHERE repo=? AND status IN ('queued','running') LIMIT 1", (repo,)
        ).fetchone())

    def list(self, limit=50):
        rows = self.db.execute("SELECT * FROM jobs ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(r) for r in rows]

    def dump(self, limit=50):
        return json.dumps([asdict(j) for j in self.list(limit)], indent=1)
