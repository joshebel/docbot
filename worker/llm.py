"""Model backends + router. Local (OpenAI-compatible vLLM) is the default;
Anthropic lane is wired but disabled. Spill rule: queue depth > N or local
health-check fail -> paid lane, bounded by a daily $ cap tracked on disk."""
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

    def chat(self, messages, max_tokens, temperature=0.2) -> tuple[str, Usage]:
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

    def chat(self, messages, max_tokens, temperature=0.2):
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
    """Stub. Enable by setting ANTHROPIC_API_KEY and SPILL_ENABLED=1.
    Pricing placeholders; verify before turning on."""
    name = "anthropic"
    usd_per_mtok_in = 3.0
    usd_per_mtok_out = 15.0

    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    def chat(self, messages, max_tokens, temperature=0.2):
        raise NotImplementedError("Anthropic lane is stubbed; not implemented yet")


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
        self.paid = AnthropicBackend(cfg.anthropic_api_key, cfg.anthropic_model) \
            if cfg.anthropic_api_key else None
        self.spend = Spend(cfg.log_dir)

    def pick(self, queue_depth: int) -> Backend:
        spill = queue_depth > self.cfg.spill_queue_depth or not self.local.healthy()
        if spill and self.cfg.spill_enabled and self.paid:
            if self.spend.today() >= self.cfg.daily_usd_cap:
                info("spill wanted but daily cap reached; staying local", spent=self.spend.today())
                return self.local
            info("spilling to paid lane", depth=queue_depth)
            return self.paid
        return self.local
