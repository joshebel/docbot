"""Account -> plan mapping, fed by Marketplace purchase webhooks.
Plans: free (local model only) | pro (eligible for paid lane, private repos).
Shares the SQLite file with the queue; separate connection, separate table."""
import sqlite3
import time
from pathlib import Path

FREE, PRO = "free", "pro"
# Marketplace plan names -> internal tier. Keep in sync with docs/MARKETPLACE.md.
PLAN_MAP = {"Free": FREE, "Pro": PRO}


class Accounts:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(str(path), isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS accounts(
               login TEXT PRIMARY KEY, plan TEXT, marketplace_plan TEXT,
               installation_id TEXT, updated REAL)"""
        )

    def close(self):
        self.db.close()

    def plan(self, login: str) -> str:
        r = self.db.execute("SELECT plan FROM accounts WHERE login=?", (login.lower(),)).fetchone()
        return r[0] if r else FREE

    def set_plan(self, login: str, marketplace_plan: str):
        plan = PLAN_MAP.get(marketplace_plan, FREE)
        self.db.execute(
            """INSERT INTO accounts(login, plan, marketplace_plan, updated) VALUES(?,?,?,?)
               ON CONFLICT(login) DO UPDATE SET plan=excluded.plan,
               marketplace_plan=excluded.marketplace_plan, updated=excluded.updated""",
            (login.lower(), plan, marketplace_plan, time.time()),
        )
        return plan

    def set_installation(self, login: str, installation_id):
        self.db.execute(
            """INSERT INTO accounts(login, plan, installation_id, updated) VALUES(?,?,?,?)
               ON CONFLICT(login) DO UPDATE SET installation_id=excluded.installation_id,
               updated=excluded.updated""",
            (login.lower(), FREE, str(installation_id), time.time()),
        )

    def installation(self, login: str) -> str:
        r = self.db.execute("SELECT installation_id FROM accounts WHERE login=?", (login.lower(),)).fetchone()
        return (r[0] or "") if r else ""

    def all(self):
        return self.db.execute("SELECT login, plan, marketplace_plan, installation_id FROM accounts").fetchall()
