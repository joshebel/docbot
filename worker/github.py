"""GitHub App auth + REST + git plumbing. stdlib only; RS256 via openssl CLI.

Token hygiene: the installation token never appears on a command line or in
a URL. git gets it through an inline credential helper that reads $GIT_TOKEN
at run time, so process listings and git error output stay clean."""
import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
UA = "docbot-worker/0.1"


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def app_jwt(app_id: str, key_path: str) -> str:
    """RS256 JWT for the App itself (10 min max)."""
    now = int(time.time())
    header = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({"iat": now - 60, "exp": now + 540, "iss": app_id}).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", key_path],
        input=signing_input, capture_output=True, check=True,
    ).stdout
    return f"{header}.{payload}.{_b64url(sig)}"


def _req(method, url, token=None, body=None, accept="application/vnd.github+json"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", accept)
    req.add_header("User-Agent", UA)
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise RuntimeError(f"GitHub {method} {url} -> {e.code}: {detail}") from None


def installation_token(app_id, key_path, installation_id) -> str:
    jwt = app_jwt(app_id, key_path)
    r = _req("POST", f"{API}/app/installations/{installation_id}/access_tokens", token=jwt)
    return r["token"]


def repo_info(token, repo):
    return _req("GET", f"{API}/repos/{repo}", token=token)


def _git(args, cwd, token=None):
    env = dict(os.environ)
    cmd = ["git"]
    if token:
        env["GIT_TOKEN"] = token
        # helper body is literal text; git's shell expands $GIT_TOKEN at call time
        cmd += ["-c", "credential.helper=", "-c",
                "credential.helper=!f(){ echo username=x-access-token; echo \"password=$GIT_TOKEN\"; }; f"]
    cmd += args
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.strip()[:800]}")
    return p.stdout


def clone(token, repo, ref, dest):
    args = ["clone", "--depth", "1", "--no-tags"]
    if ref:
        args += ["--branch", ref]
    args += [f"https://github.com/{repo}.git", str(dest)]
    _git(args, cwd=None, token=token)
    return _git(["rev-parse", "HEAD"], cwd=dest).strip()


def commit_and_push(token, dest, branch, message, files):
    """Idempotent: rerun creates the same branch name and force-pushes."""
    _git(["checkout", "-B", branch], cwd=dest)
    _git(["add", "--", *files], cwd=dest)
    status = _git(["status", "--porcelain"], cwd=dest)
    if not status.strip():
        return None
    _git(["-c", "user.name=docbot[bot]", "-c", "user.email=docbot[bot]@users.noreply.github.com",
          "commit", "-q", "-m", message], cwd=dest)
    _git(["push", "--force", "origin", branch], cwd=dest, token=token)
    return _git(["rev-parse", "HEAD"], cwd=dest).strip()


def ensure_pr(token, repo, head, base, title, body):
    owner = repo.split("/")[0]
    prs = _req("GET", f"{API}/repos/{repo}/pulls?state=open&head={owner}:{head}&base={base}", token=token)
    if prs:
        pr = prs[0]
        _req("PATCH", pr["url"], token=token, body={"title": title, "body": body})
        return pr["html_url"], False
    pr = _req("POST", f"{API}/repos/{repo}/pulls", token=token,
              body={"title": title, "head": head, "base": base, "body": body})
    return pr["html_url"], True
