"""GitHub webhook receiver. stdlib http.server; verifies X-Hub-Signature-256
and turns events into queue/account writes. No outbound calls, no secrets in
logs. Run behind a tunnel or reverse proxy; or move to the VPS later — it only
needs the same SQLite file (or the future HTTP queue impl)."""
import hashlib
import hmac
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from .accounts import Accounts
from .log import info
from .queue import Queue


def verify(secret: str, body: bytes, sig_header: str) -> bool:
    if not secret or not sig_header or not sig_header.startswith("sha256="):
        return False
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, sig_header[len("sha256="):])


class Dispatcher:
    """Pure event -> side-effect logic; testable without HTTP."""

    def __init__(self, queue: Queue, accounts: Accounts, docs_branch: str):
        self.q, self.acct, self.docs_branch = queue, accounts, docs_branch

    def handle(self, event: str, p: dict) -> str:
        fn = getattr(self, "on_" + event, None)
        return fn(p) if fn else f"ignored {event}"

    def _enqueue(self, repo: str, installation_id, ref="") -> str:
        if self.q.has_queued(repo):
            return f"already queued {repo}"
        j = self.q.enqueue(repo, str(installation_id), ref)
        info("webhook enqueued", repo=repo, job=j.id)
        return f"queued {repo}"

    def on_installation(self, p):
        inst = p["installation"]
        login = inst["account"]["login"]
        if p["action"] in ("deleted", "suspend"):
            return f"installation {p['action']} for {login}"
        self.acct.set_installation(login, inst["id"])
        if p["action"] not in ("created", "unsuspend", "new_permissions_accepted"):
            return f"installation {p['action']}"
        out = [self._enqueue(r["full_name"], inst["id"]) for r in p.get("repositories", [])]
        return "; ".join(out) or "installation created (no repos)"

    def on_installation_repositories(self, p):
        inst = p["installation"]
        out = [self._enqueue(r["full_name"], inst["id"]) for r in p.get("repositories_added", [])]
        return "; ".join(out) or "no repos added"

    def on_push(self, p):
        repo = p["repository"]["full_name"]
        default = p["repository"].get("default_branch", "main")
        if p.get("ref") != f"refs/heads/{default}":
            return f"ignored push to {p.get('ref')}"
        if p.get("sender", {}).get("login", "").endswith("[bot]"):
            return "ignored bot push"
        return self._enqueue(repo, p["installation"]["id"], default)

    def on_marketplace_purchase(self, p):
        login = p["marketplace_purchase"]["account"]["login"]
        action = p["action"]
        if action in ("cancelled", "pending_change_cancelled"):
            plan = self.acct.set_plan(login, "Free")
        else:  # purchased, changed
            plan = self.acct.set_plan(login, p["marketplace_purchase"]["plan"]["name"])
        info("marketplace", login=login, action=action, plan=plan)
        return f"{login} -> {plan}"

    def on_ping(self, p):
        return "pong"


def make_handler(secret: str, dispatcher: Dispatcher):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet; we log our own lines
            pass

        def _reply(self, code, text):
            b = text.encode()
            self.send_response(code)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            self._reply(200, "ok" if self.path == "/healthz" else "docbot")

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n)
            if not verify(secret, body, self.headers.get("X-Hub-Signature-256", "")):
                info("webhook bad signature", ip=self.client_address[0])
                return self._reply(401, "bad signature")
            event = self.headers.get("X-GitHub-Event", "")
            try:
                result = dispatcher.handle(event, json.loads(body or b"{}"))
            except Exception as e:
                info("webhook handler error", event=event, err=repr(e))
                return self._reply(500, "error")
            info("webhook", event=event, result=result)
            self._reply(200, result)
    return H


def serve(cfg):
    # connections are opened here, in the serving thread, on purpose
    from .queue import SqliteQueue
    d = Dispatcher(SqliteQueue(cfg.queue_path), Accounts(cfg.queue_path), cfg.docs_branch)
    # single-threaded on purpose: handlers are sub-ms sqlite writes, and the
    # sqlite connections are bound to the thread that created them
    srv = HTTPServer((cfg.webhook_bind, cfg.webhook_port), make_handler(cfg.gh_webhook_secret, d))
    info("webhook listening", bind=cfg.webhook_bind, port=cfg.webhook_port)
    srv.serve_forever()
