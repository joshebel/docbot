import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from worker import webhook
from worker.accounts import Accounts
from worker.llm import Router, Spend
from worker.queue import SqliteQueue

SECRET = "s3cret"


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


class TestVerify(unittest.TestCase):
    def test_sig(self):
        b = b'{"a":1}'
        self.assertTrue(webhook.verify(SECRET, b, sign(b)))
        self.assertFalse(webhook.verify(SECRET, b + b" ", sign(b)))
        self.assertFalse(webhook.verify(SECRET, b, "sha1=abc"))
        self.assertFalse(webhook.verify("", b, sign(b)))


class TestDispatcher(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = Path(self.tmp.name) / "q.sqlite"
        self.q, self.a = SqliteQueue(p), Accounts(p)
        self.d = webhook.Dispatcher(self.q, self.a, "docs/auto")

    def tearDown(self):
        self.q.close(); self.a.close(); self.tmp.cleanup()

    def test_installation_enqueues_and_dedupes(self):
        p = {"action": "created", "installation": {"id": 7, "account": {"login": "Alice"}},
             "repositories": [{"full_name": "alice/a"}, {"full_name": "alice/b"}]}
        self.d.handle("installation", p)
        self.assertEqual(self.q.depth(), 2)
        self.assertEqual(self.a.installation("alice"), "7")
        self.assertIn("already queued", self.d.handle("installation", p))
        self.assertEqual(self.q.depth(), 2)

    def test_push_filters(self):
        base = {"repository": {"full_name": "x/y", "default_branch": "main"},
                "installation": {"id": 1}, "sender": {"login": "x"}}
        self.assertIn("ignored", self.d.handle("push", {**base, "ref": "refs/heads/docs/auto"}))
        self.assertIn("ignored branch delete", self.d.handle("push", {**base, "ref": "refs/heads/main", "deleted": True}))
        # pushes made with the App's own token still count: only the ref matters
        bot = {**base, "ref": "refs/heads/main", "sender": {"login": "docbot[bot]"}}
        self.assertIn("queued", self.d.handle("push", bot))
        self.assertEqual(self.q.list()[0].ref, "main")

    def test_marketplace_plans(self):
        mp = lambda action, plan: {"action": action, "marketplace_purchase": {
            "account": {"login": "Bob"}, "plan": {"name": plan}}}
        self.d.handle("marketplace_purchase", mp("purchased", "Pro"))
        self.assertEqual(self.a.plan("bob"), "pro")
        self.d.handle("marketplace_purchase", mp("cancelled", "Pro"))
        self.assertEqual(self.a.plan("bob"), "free")
        self.assertEqual(self.a.plan("nobody"), "free")

    def test_unknown_event(self):
        self.assertIn("ignored", self.d.handle("star", {}))


class FakeLocal:
    model, name, max_model_len = "local-m", "local", 1000
    def __init__(self, ok=True): self.ok = ok
    def healthy(self): return self.ok


class TestRouter(unittest.TestCase):
    def _router(self, spill=True, cap=5.0, local_ok=True, paid=True):
        cfg = SimpleNamespace(spill_enabled=spill, spill_queue_depth=20, daily_usd_cap=cap,
                              log_dir=Path(self.tmp.name))
        r = Router.__new__(Router)
        r.cfg, r.local, r.spend = cfg, FakeLocal(local_ok), Spend(cfg.log_dir)
        r.paid = SimpleNamespace(name="anthropic", model="claude-opus-5") if paid else None
        return r

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_free_never_spills(self):
        r = self._router(local_ok=False)
        self.assertEqual(r.pick(100, "free").name, "local")

    def test_pro_spills_on_depth_or_outage(self):
        r = self._router()
        self.assertEqual(r.pick(5, "pro").name, "local")
        self.assertEqual(r.pick(21, "pro").name, "anthropic")
        self.assertEqual(self._router(local_ok=False).pick(0, "pro").name, "anthropic")

    def test_cap_blocks_spill(self):
        r = self._router(cap=1.0)
        r.spend.add(1.5)
        self.assertEqual(r.pick(50, "pro").name, "local")
        with self.assertRaises(RuntimeError):
            self._router(cap=0.0, local_ok=False).pick(0, "pro")

    def test_spill_disabled(self):
        self.assertEqual(self._router(spill=False, local_ok=False).pick(99, "pro").name, "local")


if __name__ == "__main__":
    unittest.main()
