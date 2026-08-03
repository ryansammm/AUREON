"""Layer 3 — Arrangement Engine.

Maps a genre's section template onto a bar-by-bar plan with an energy
curve: each bar carries a section name plus density, register shift and
base velocity so the composition has shape (intro/build/drop/...)
instead of a flat loop.

Musical assumptions:
- ``section_template`` lists section names in performance order.
- ``section_bars`` maps section name -> number of bars (default 1).
- ``section_density`` (0-1) drives note density (default 1.0).
- ``section_register`` is an octave shift (default 0).
- ``section_velocity`` is the section's base MIDI velocity (default 92).
- When the requested bar count is not an exact multiple of the template,
  the template is tiled and truncated.
"""

from .models import SectionBar


class ArrangementEngine:
    """Builds section plans for a genre config."""

    def __init__(self, config: dict):
        self.config = config

    def total_bars(self) -> int:
        """Full length of the section template (in bars)."""
        template = self.config.get("section_template") or ["drop"]
        bars_map = self.config.get("section_bars") or {}
        return sum(bars_map.get(section, 1) for section in template)

    def build_plan(self, num_bars: int = None) -> list:
        """Return one :class:`SectionBar` per bar of the composition.

        Args:
            num_bars: requested length; ``None`` uses the full template.
        """
        if num_bars is None:
            num_bars = self.total_bars()
        if num_bars < 1:
            raise ValueError("num_bars must be >= 1")

        template = self.config.get("section_template") or ["drop"]
        bars_map = self.config.get("section_bars") or {}
        density_map = self.config.get("section_density") or {}
        register_map = self.config.get("section_register") or {}
        velocity_map = self.config.get("section_velocity") or {}

        names = []
        while len(names) < num_bars:
            for section in template:
                for _ in range(bars_map.get(section, 1)):
                    names.append(section)
                    if len(names) >= num_bars:
                        break
                if len(names) >= num_bars:
                    break

        return [
            SectionBar(
                bar=bar,
                name=name,
                density=float(density_map.get(name, 1.0)),
                register_shift=int(register_map.get(name, 0)),
                base_velocity=int(velocity_map.get(name, 92)),
            )
            for bar, name in enumerate(names)
        ]
