"""Keeps the pipeline alive: webhook receiver + worker loop + Cloudflare tunnel.
Restarts any child that exits (with backoff). When the tunnel hostname changes
(quick tunnels get a fresh *.trycloudflare.com on every start) the App webhook
is re-pointed through the GitHub API so pushes keep flowing without a human.

    python -m worker supervise            # foreground; Ctrl-C stops everything

Children log to state/<name>.log. Current public URL is in state/tunnel_url.txt."""
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

from . import github
from .log import info

TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


class Child:
    def __init__(self, name, argv, log_dir: Path):
        self.name, self.argv = name, argv
        self.log_path = log_dir / f"{name}.log"
        self.proc = None
        self.failures = 0
        self.started = 0.0

    def start(self):
        self.log = open(self.log_path, "ab", buffering=0)
        self.proc = subprocess.Popen(self.argv, stdout=self.log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL)
        self.started = time.time()
        info("supervisor started", child=self.name, pid=self.proc.pid)

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
        if self.alive():
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def ensure(self):
        if self.alive():
            if time.time() - self.started > 300:
                self.failures = 0        # ran long enough: reset backoff
            return
        if self.proc is not None:
            info("supervisor child exited", child=self.name, code=self.proc.returncode)
            self.failures += 1
            time.sleep(min(60, 2 ** self.failures))
        self.start()


def tunnel_url(log_path: Path, since: float) -> str:
    """Newest trycloudflare hostname written after `since`."""
    try:
        if log_path.stat().st_mtime < since:
            return ""
        text = log_path.read_bytes()[-200_000:].decode("utf-8", "replace")
    except OSError:
        return ""
    urls = TUNNEL_RE.findall(text)
    return urls[-1] if urls else ""


def run(cfg):
    log_dir = cfg.log_dir
    cloudflared = str(Path("bin") / ("cloudflared.exe" if os.name == "nt" else "cloudflared"))
    py = sys.executable
    children = [
        Child("webhook", [py, "-m", "worker", "webhook"], log_dir),
        Child("serve", [py, "-m", "worker", "serve"], log_dir),
        Child("tunnel", [cloudflared, "tunnel", "--url", f"http://localhost:{cfg.webhook_port}",
                         "--no-autoupdate"], log_dir),
    ]
    tunnel = children[2]
    url_file = log_dir / "tunnel_url.txt"
    current_url = url_file.read_text().strip() if url_file.exists() else ""
    stopping = False

    def _stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    info("supervisor up", pid=os.getpid())
    while not stopping:
        for c in children:
            c.ensure()
        url = tunnel_url(tunnel.log_path, tunnel.started - 1)
        if url and url != current_url:
            target = url + "/"
            try:
                github.set_app_webhook_url(cfg.gh_app_id, cfg.gh_private_key_path, target)
                url_file.write_text(target)
                current_url = url
                info("supervisor re-pointed App webhook", url=target)
                info("NOTE: Marketplace listing webhook has no API; update it manually if the URL changed")
            except Exception as e:
                info("supervisor webhook update failed", err=repr(e))
        time.sleep(5)
    for c in children:
        c.stop()
    info("supervisor stopped")
