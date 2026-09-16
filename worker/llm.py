"""Model backends + router. Local (OpenAI-compatible vLLM) is the default;
the Anthropic lane is the paid tier. Spill rule: pro-plan job AND (queue depth
> N or local health-check fail) -> paid lane, bounded by a daily $ cap tracked
on disk. Free-plan jobs never leave the local box."""
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .log import info


@dataclass
class Usage:
    prompt: int = 0
    completion: int = 0

    def add(self, u):
        self.prompt += u.prompt
        self.completion += u.completion


class Backend:
    name = "?"
    model = "?"
    usd_per_mtok_in = 0.0
    usd_per_mtok_out = 0.0
    max_model_len = 32768

    def chat(self, messages, max_tokens, temperature=0.0) -> tuple[str, Usage]:
        raise NotImplementedError

    def healthy(self) -> bool:
        return True

    def cost(self, u: Usage) -> float:
        return (u.prompt * self.usd_per_mtok_in + u.completion * self.usd_per_mtok_out) / 1e6


class LocalBackend(Backend):
    name = "local"

    def __init__(self, base_url, api_key="", model="", enable_thinking=False):
        self.base_url = base_url
        self.api_key = api_key
        self.enable_thinking = enable_thinking
        self.model = model or self._first_model()
        self.max_model_len = self._max_len()

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _get(self, path):
        req = urllib.request.Request(self.base_url + path, headers=self._headers())
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)

    def models(self):
        return self._get("/models")["data"]

    def _first_model(self):
        return self.models()[0]["id"]

    def _max_len(self):
        for m in self.models():
            if m["id"] == self.model:
                return int(m.get("max_model_len") or 32768)
        return 32768

    def healthy(self):
        try:
            self._get("/models")
            return True
        except Exception as e:
            info("local health-check failed", err=e)
            return False

    def chat(self, messages, max_tokens, temperature=0.0):
        body = {
            "model": self.model, "messages": messages, "max_tokens": max_tokens,
            "temperature": temperature,
            "chat_template_kwargs": {"enable_thinking": self.enable_thinking},
        }
        data = json.dumps(body).encode()
        for attempt in range(3):
            try:
                req = urllib.request.Request(self.base_url + "/chat/completions", data=data,
                                             headers=self._headers())
                with urllib.request.urlopen(req, timeout=1800) as r:
                    j = json.load(r)
                break
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt == 2:
                    raise
                info("local call failed, retrying", attempt=attempt, err=e)
                time.sleep(2 ** attempt)
        msg = j["choices"][0]["message"]
        text = msg.get("content") or ""
        if not text and msg.get("reasoning"):
            # thinking ate the budget; surface loudly rather than emit empty docs
            raise RuntimeError("model returned reasoning only (raise max_tokens or disable thinking)")
        u = j.get("usage") or {}
        return text, Usage(u.get("prompt_tokens", 0), u.get("completion_tokens", 0))


class AnthropicBackend(Backend):
    """Paid lane. Messages API over urllib (stdlib, same as the other clients).
    Model defaults to claude-opus-5; thinking is adaptive by default on that
    model so we don't send a `thinking` field. Effort is capped at medium:
    doc generation is routine work and effort is the main cost lever."""
    name = "anthropic"
    API = "https://api.anthropic.com/v1/messages"
    VERSION = "2023-06-01"
    PRICES = {  # USD per MTok in/out, from the API pricing table (2026-06)
        "claude-opus-5": (5.0, 25.0), "claude-opus-4-8": (5.0, 25.0),
        "claude-sonnet-5": (2.0, 10.0), "claude-haiku-4-5": (1.0, 5.0),
        "claude-fable-5-1": (10.0, 50.0),
    }
    max_model_len = 1_000_000

    def __init__(self, api_key, model="claude-opus-5", effort="medium"):
        self.api_key = api_key
        self.model = model
        self.effort = effort
        self.usd_per_mtok_in, self.usd_per_mtok_out = self.PRICES.get(model, (10.0, 50.0))

    def healthy(self):
        return bool(self.api_key)

    def chat(self, messages, max_tokens, temperature=0.0):
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        turns = [m for m in messages if m["role"] != "system"]
        body = {
            "model": self.model, "max_tokens": max_tokens, "messages": turns,
            "output_config": {"effort": self.effort},
            # server-side refusal fallback: routes by refusal category, no model list to maintain
            "fallbacks": "default",
        }
        if system:
            body["system"] = system
        headers = {
            "Content-Type": "application/json", "x-api-key": self.api_key,
            "anthropic-version": self.VERSION,
            "anthropic-beta": "server-side-fallback-2026-07-01",
        }
        data = json.dumps(body).encode()
        for attempt in range(3):
            req = urllib.request.Request(self.API, data=data, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=600) as r:
                    j = json.load(r)
                break
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:300]
                if e.code in (408, 409, 429) or e.code >= 500:
                    if attempt == 2:
                        raise RuntimeError(f"anthropic {e.code}: {detail}") from None
                    time.sleep(2 ** attempt * 2)
                    continue
                raise RuntimeError(f"anthropic {e.code}: {detail}") from None
            except (urllib.error.URLError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        if j.get("stop_reason") == "refusal":
            raise RuntimeError(f"anthropic refused: {(j.get('stop_details') or {}).get('category')}")
        text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
        u = j.get("usage") or {}
        served = j.get("model", self.model)
        if served != self.model:
            info("anthropic fallback served", model=served)
        return text, Usage(u.get("input_tokens", 0), u.get("output_tokens", 0))


class Spend:
    """Daily USD ledger, one JSON file. Only the paid lane writes non-zero rows."""

    def __init__(self, log_dir: Path):
        self.path = Path(log_dir) / "spend.json"

    def _load(self):
        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            return {}

    def today(self) -> float:
        return float(self._load().get(time.strftime("%Y-%m-%d"), 0.0))

    def add(self, usd: float):
        if usd <= 0:
            return
        d = self._load()
        k = time.strftime("%Y-%m-%d")
        d[k] = float(d.get(k, 0.0)) + usd
        self.path.write_text(json.dumps(d, indent=1))


class Router:
    def __init__(self, cfg):
        self.cfg = cfg
        self.local = LocalBackend(cfg.local_base_url, cfg.local_api_key, cfg.local_model,
                                  cfg.local_enable_thinking)
        self.paid = AnthropicBackend(cfg.anthropic_api_key, cfg.anthropic_model, cfg.anthropic_effort) \
            if cfg.anthropic_api_key else None
        self.spend = Spend(cfg.log_dir)

    def pick(self, queue_depth: int, plan: str = "free") -> Backend:
        if plan == "free" or not (self.cfg.spill_enabled and self.paid):
            return self.local
        local_ok = self.local.healthy()
        spill = queue_depth > self.cfg.spill_queue_depth or not local_ok
        if not spill:
            return self.local
        if self.spend.today() >= self.cfg.daily_usd_cap:
            info("spill wanted but daily cap reached; staying local", spent=round(self.spend.today(), 2))
            if not local_ok:
                raise RuntimeError("local backend down and daily paid cap reached")
            return self.local
        info("spilling to paid lane", depth=queue_depth, plan=plan)
        return self.paid
