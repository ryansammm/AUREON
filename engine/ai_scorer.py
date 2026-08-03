"""Phase 5 — LLM-assisted candidate scoring.

Scores every generated candidate in a single LLM call (each candidate is
reduced to a few compact stats) so the model acts as a second opinion on
top of the deterministic ensemble score. Optional: without a configured
key the web/CLI simply skip this layer.

The returned 0-10 rating is blended into the ranking as a small bonus so
it breaks ties without overriding the rule-based heuristics.
"""

from .llm import LLMClient, extract_json

PERCUSSION_ROLES = {"drum", "drum_layers"}
DISSONANT_INTERVALS = {1, 6, 11}
BEATS_PER_BAR = 4.0
MAX_CANDIDATES_PER_CALL = 8


class AIScorer:
    """Scores candidate summaries via one LLM chat call."""

    def __init__(self, config: dict, client: LLMClient = None):
        self.config = config
        self.client = client or LLMClient()

    def available(self) -> bool:
        return self.client.available()

    def score_candidates(
        self,
        summaries: list,
        key_root: str,
        mode: str,
        temperature: float = 0.2,
    ) -> dict:
        """Return ``{index: {"score": float, "reason": str}}``.

        Raises:
            LLMError / ValueError: on provider or parse failure so the
            caller can keep the pure ensemble ranking.
        """
        if not summaries:
            return {}
        if len(summaries) > MAX_CANDIDATES_PER_CALL:
            summaries = summaries[:MAX_CANDIDATES_PER_CALL]
        system = (
            "You are a music producer judging candidate arrangements. "
            "Return ONLY valid JSON. No markdown, no commentary, no code fences."
        )
        blocks = []
        for s in summaries:
            roles = ", ".join(
                f"{r['role']}({r['notes']}n, avg_pitch={r['avg_pitch']}, "
                f"leap={r['mean_leap']:.1f}, dis={r['dissonance_rate']:.2f})"
                for r in s.get("roles", [])
            )
            blocks.append(f'  {{"candidate": {s["index"]}, "roles": "{roles}", '
                          f'"progression": "{s.get("progression", "")}"}}')
        user = (
            f"Judge these {self.config['genre']} candidates in {key_root} {mode}. "
            "Each candidate is one arrangement.\n[\n"
            + ",\n".join(blocks)
            + "\n]\n"
            "Rate each candidate 0-10 (10 = best) for musical quality: "
            "interesting but coherent, good balance, fitting for the genre. "
            'Return ONLY a JSON array:\n'
            '[{"candidate": 1, "score": 7, "reason": "short reason"}, ...]'
        )
        text, provider = self.client.chat(system, user, temperature)
        data = extract_json(text)
        if not isinstance(data, list):
            raise ValueError("LLM scoring is not a JSON array")
        result = {}
        for item in data:
            if not isinstance(item, dict) or "candidate" not in item:
                continue
            try:
                score = max(0.0, min(10.0, float(item.get("score"))))
            except (TypeError, ValueError):
                continue
            result[int(item["candidate"])] = {
                "score": score,
                "reason": str(item.get("reason") or "").strip()[:200],
            }
        return result, provider


def build_candidate_summary(tracks: list, progression: list, index: int) -> dict:
    """Compact stats for one candidate (melodic roles only)."""
    roles = []
    for track in tracks:
        if getattr(track, "role", "") in PERCUSSION_ROLES:
            continue
        notes = sorted(track.notes, key=lambda n: n.start_beat)
        if len(notes) < 2:
            roles.append({
                "role": track.role, "notes": len(notes),
                "avg_pitch": 0, "mean_leap": 0.0, "dissonance_rate": 0.0,
            })
            continue
        intervals = [
            abs(notes[i + 1].pitch - notes[i].pitch)
            for i in range(len(notes) - 1)
        ]
        dissonance = sum(
            1 for i in range(len(notes) - 1)
            if (abs(notes[i + 1].pitch - notes[i].pitch) % 12) in DISSONANT_INTERVALS
        ) / len(intervals)
        roles.append({
            "role": track.role,
            "notes": len(notes),
            "avg_pitch": round(sum(n.pitch for n in notes) / len(notes), 1),
            "mean_leap": round(sum(intervals) / len(intervals), 2),
            "dissonance_rate": round(dissonance, 2),
        })
    return {
        "index": index,
        "roles": roles,
        "progression": " -> ".join(c.degree for c in progression),
    }
