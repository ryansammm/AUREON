"""Phase 5 — LLM-assisted musical ideation.

Asks the LLM for a short musical seed (a chord progression as Roman
numerals plus a melodic contour motif in scale steps) and returns a
validated dict the rule engine can realize. The LLM supplies creative
direction; the rule engine guarantees the result stays musical.

Everything here is optional: if no API key is configured (or the model
fails), callers fall back to the pure rule-based pipeline.
"""

import json

from .llm import LLMClient, extract_json
from .music_utils import roman_chord

MAX_DEGREES = 16
MIN_DEGREES = 4
MAX_MOTIF = 32
MIN_MOTIF = 4


class LLMIdeator:
    """Generate and validate a chord progression + motif from the LLM."""

    def __init__(self, config: dict, client: LLMClient = None):
        self.config = config
        self.client = client or LLMClient()

    def available(self) -> bool:
        return self.client.available()

    def generate_idea(
        self,
        key_root: str,
        mode: str,
        roles: list,
        bars: int = None,
        prompt: str = None,
        temperature: float = 0.9,
    ) -> dict:
        """Return ``{progression, motif, description, provider}``.

        Raises:
            LLMError / ValueError: on provider or validation failure so
            callers can fall back to the rule-based pipeline.
        """
        system = (
            "You are an expert electronic-music producer and music theorist. "
            "Return ONLY valid JSON. No markdown, no commentary, no code fences."
        )
        bars_clause = f"Target length: about {bars} bars." if bars else ""
        user = (
            f"Design a short musical idea for a {self.config['genre']} track.\n"
            f"Key: {key_root} {mode}. Instruments: {', '.join(roles)}.\n"
            f"{bars_clause}\n"
            f"User vibe: {prompt or 'none - use a classic feel for the genre'}.\n\n"
            'Return ONLY this JSON object:\n'
            '{\n'
            '  "progression": ["i", "VI", "III", "VII"],\n'
            '  "motif": [0, 2, 4, 3, 0, -2, 4, 3],\n'
            '  "description": "one line describing the vibe"\n'
            "}\n"
            "Rules: progression must list 4-8 Roman numerals, one chord per bar, "
            f"all valid in {key_root} {mode} (use lowercase for minor degrees, "
            "uppercase for major). motif must be 8-16 integers: scale-step "
            "contour relative to the chord root (0 = root, 2 = two scale steps "
            "up, -3 = three steps down), keep values between -5 and 5. "
            "description is a single short sentence."
        )
        text, provider = self.client.chat(system, user, temperature)
        data = extract_json(text)
        if not isinstance(data, dict):
            raise ValueError("LLM idea is not a JSON object")

        progression = self._validate_degrees(data.get("progression"), key_root, mode)
        motif = self._validate_motif(data.get("motif"))
        description = str(data.get("description") or "").strip()[:200]
        return {
            "progression": progression,
            "motif": motif,
            "description": description,
            "provider": provider,
        }

    @staticmethod
    def _validate_degrees(degrees, key_root: str, mode: str) -> list:
        if not isinstance(degrees, list):
            raise ValueError("missing progression")
        valid = []
        for degree in degrees:
            if not isinstance(degree, str):
                continue
            try:
                roman_chord(key_root, mode, degree)
            except Exception:  # noqa: BLE001 - music21 rejects invalid numerals
                continue
            valid.append(degree)
        if len(valid) < MIN_DEGREES:
            raise ValueError(f"too few valid degrees ({len(valid)})")
        return valid[:MAX_DEGREES]

    @staticmethod
    def _validate_motif(motif) -> list:
        if not isinstance(motif, list):
            raise ValueError("missing motif")
        valid = []
        for value in motif:
            try:
                step = int(value)
            except (TypeError, ValueError):
                continue
            if -12 <= step <= 12:
                valid.append(step)
        if len(valid) < MIN_MOTIF:
            raise ValueError(f"too few motif steps ({len(valid)})")
        return valid[:MAX_MOTIF]

    def idea_to_prompt_dump(self, idea: dict) -> str:
        """Compact human-readable form for the result page."""
        return json.dumps(
            {
                "progression": idea["progression"],
                "motif": idea["motif"],
                "description": idea["description"],
            },
            ensure_ascii=False,
        )
