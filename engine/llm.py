"""Phase 5 — LLM access layer with Gemini -> Groq fallback.

Talks to the providers' REST APIs directly via ``requests`` (no extra
dependencies). API keys are read from environment variables (or a local
``.env`` file that is git-ignored) and are never logged.

Providers and default models (free tiers as of mid-2026):
- Gemini: ``gemini-flash-latest`` (alias to the newest flash; older names like
  ``gemini-2.5-flash`` are 404 for new accounts, so we use the alias).
- Groq: ``llama-3.3-70b-versatile`` (~1k requests/day free).

All calls are optional for the engine: when no key is configured, the AI
features are simply unavailable and the rule-based pipeline runs as usual.
"""

import os
import re

import requests

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
REQUEST_TIMEOUT = 60.0


class LLMError(RuntimeError):
    """Raised when no configured provider responds successfully."""


def load_dotenv(paths=(".env",)) -> bool:
    """Load ``KEY=VALUE`` pairs from a local env file into ``os.environ``.

    Existing environment variables win over file values. Returns ``True``
    if a file was found and parsed. This is a tiny stand-in for
    python-dotenv to keep the dependency footprint at zero.
    """
    found = False
    for path in paths:
        if not os.path.isfile(path):
            continue
        found = True
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        break
    return found


class GeminiProvider:
    """Gemini via the generativelanguage REST endpoint."""

    name = "gemini"

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
        self.model = model or os.environ.get("AUREON_LLM_MODEL_GEMINI") or DEFAULT_GEMINI_MODEL

    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, system: str, prompt: str, temperature: float = 0.7) -> str:
        url = f"{GEMINI_ENDPOINT}/{self.model}:generateContent"
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        resp = requests.post(
            url, json=body, params={"key": self.api_key}, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()


class GroqProvider:
    """Groq via its OpenAI-compatible chat completions endpoint."""

    name = "groq"

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "").strip()
        self.model = model or os.environ.get("AUREON_LLM_MODEL_GROQ") or DEFAULT_GROQ_MODEL

    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, system: str, prompt: str, temperature: float = 0.7) -> str:
        resp = requests.post(
            GROQ_ENDPOINT,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


class LLMClient:
    """Speaks to the first available provider, falling through on failure."""

    def __init__(self, providers: list = None):
        load_dotenv()
        self.providers = providers or [
            GeminiProvider(),
            GroqProvider(),
        ]

    def available(self) -> bool:
        return any(p.available() for p in self.providers)

    def providers_available(self) -> list:
        return [p.name for p in self.providers if p.available()]

    def chat(self, system: str, prompt: str, temperature: float = 0.7):
        """Return ``(text, provider_name)`` from the first working provider."""
        errors = []
        for provider in self.providers:
            if not provider.available():
                continue
            try:
                return provider.chat(system, prompt, temperature), provider.name
            except Exception as exc:  # noqa: BLE001 - fall through to next provider
                errors.append(f"{provider.name}: {exc}")
        detail = "; ".join(errors) if errors else "no API key configured"
        raise LLMError(f"all LLM providers failed ({detail})")


def extract_json(text: str):
    """Best-effort parse of ``{...}`` / ``[...]`` possibly wrapped in fences."""
    if not text:
        raise ValueError("empty LLM response")
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start = min(
        (idx for idx in (cleaned.find("{"), cleaned.find("[")) if idx != -1),
        default=0,
    )
    return _json_loads(cleaned[start:])


def _json_loads(text: str):
    try:
        return __import__("json").loads(text)
    except ValueError:
        raise ValueError(f"invalid JSON from LLM: {text[:200]!r}") from None
