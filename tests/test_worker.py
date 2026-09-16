import json
import tempfile
import unittest
from pathlib import Path

from worker import github, ingest, log, queue
from worker.generate import _clean, _json_list, _modules


class TestQueue(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            q = queue.SqliteQueue(Path(d) / "q.sqlite")
            j = q.enqueue("a/b", "1")
            self.assertEqual(q.depth(), 1)
            c = q.claim()
            self.assertEqual(c.id, j.id)
            self.assertEqual(c.attempts, 1)
            self.assertIsNone(q.claim())
            q.fail(c.id, "boom", retry=True)
            self.assertEqual(q.depth(), 1)
            q.complete(q.claim().id, "url")
            self.assertEqual(q.list()[0].status, "done")
            q.close()


class TestIngest(unittest.TestCase):
    def test_skips_and_sigs(self):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d)
            (r / "node_modules").mkdir(); (r / "node_modules" / "x.js").write_text("junk")
            (r / "pkg").mkdir()
            (r / "pkg" / "m.py").write_text('"""Mod doc."""\nclass A:\n    """A doc."""\n    def go(self, x): pass\ndef _p(): pass\n')
            (r / "README.md").write_text("# hi")
            (r / "bin.dat").write_bytes(b"\0\1\2")
            s = ingest.scan(r, 10**7, 100, 10**5)
            self.assertEqual([f.path for f in s.files], ["README.md", "pkg/m.py"])
            self.assertEqual(s.readme, "# hi")
            sig = ingest.signatures(s, s.files[1])
            self.assertIn("class A()", sig)
            self.assertIn("def go(self, x)", sig)
            self.assertNotIn("_p", sig)
            ctx = ingest.build_context(s, "t", 4000)
            self.assertIn("pkg/m.py", ctx)
            (r / "tests").mkdir(); (r / "tests" / "t.py").write_text("def test_x(): pass\n")
            s = ingest.scan(r, 10**7, 100, 10**5)
            self.assertEqual(list(_modules(s)), ["pkg"])

    def test_cap(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "big.txt").write_text("x" * 5000)
            with self.assertRaises(ingest.RepoTooLarge):
                ingest.scan(Path(d), 1000, 100, 10**5)


class TestMisc(unittest.TestCase):
    def test_scrub(self):
        s = log.scrub("tok ghs_abcdefghijklmnopqrstuvwxyz012345 and Bearer eyJabc.def.ghi")
        self.assertNotIn("ghs_", s)
        self.assertNotIn("eyJabc", s)

    def test_jwt_shape(self):
        self.assertEqual(github._b64url(b"\xfb\xff"), "-_8")

    def test_clean(self):
        self.assertEqual(_clean("<think>x</think>```markdown\n# T\n```"), "# T\n")
        self.assertEqual(_json_list('sure: ["a/b.py", "c"] ok'), ["a/b.py", "c"])


if __name__ == "__main__":
    unittest.main()
