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

    # Section types that carry the main energy peak of a genre (the "drop").
    PEAK_SECTIONS = {"drop", "drop2", "chorus"}
    # Sections that build tension *into* a peak; they stay part of the
    # repeatable loop so long arrangements keep their build-up/drop shape.
    PREPEAK_SECTIONS = {"build", "buildup", "verse"}

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

        Short requests (up to one full pass of the template) tile the
        template and truncate. Longer requests use an expanded structure
        ``intro -> [peak loop] x N -> outro`` so a 3-5 minute track keeps
        the genre's build-up/drop shape instead of repeating the whole
        template (which would put the outro mid-song).
        """
        if num_bars is None:
            num_bars = self.total_bars()
        if num_bars < 1:
            raise ValueError("num_bars must be >= 1")

        template = self.config.get("section_template") or ["drop"]
        bars_map = self.config.get("section_bars") or {}
        names = self._expand_names(template, bars_map, num_bars)

        density_map = self.config.get("section_density") or {}
        register_map = self.config.get("section_register") or {}
        velocity_map = self.config.get("section_velocity") or {}

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

    # ------------------------------------------------------------------ #
    # Long-form expansion
    # ------------------------------------------------------------------ #
    def _split_template(self, template: list) -> tuple:
        """Split the template into ``(head, loop, tail)`` section lists.

        - ``head``: sections before the first peak (played once).
        - ``loop``: from the pre-peak build section up to the last peak;
          this is the repeatable energy cycle.
        - ``tail``: sections after the last peak (e.g. outro, played once).
        """
        peaks = [
            i for i, name in enumerate(template)
            if name in self.PEAK_SECTIONS
        ]
        if not peaks:
            return [], template, []
        first, last = peaks[0], peaks[-1]
        start = first
        while start > 0 and template[start - 1] in self.PREPEAK_SECTIONS:
            start -= 1
        return template[:start], template[start:last + 1], template[last + 1:]

    @staticmethod
    def _seq(sections: list, bars_map: dict) -> list:
        """Expand a section list into one entry per bar."""
        names = []
        for section in sections:
            names += [section] * bars_map.get(section, 1)
        return names

    def _expand_names(self, template: list, bars_map: dict, num_bars: int) -> list:
        """Produce the ordered section-name list for ``num_bars`` bars."""
        single_pass = sum(bars_map.get(section, 1) for section in template)
        if num_bars <= single_pass:
            return self._tile(template, bars_map, num_bars)

        head, loop, tail = self._split_template(template)
        head_bars = len(self._seq(head, bars_map))
        loop_bars = len(self._seq(loop, bars_map))
        tail_bars = len(self._seq(tail, bars_map))

        if loop_bars == 0 or head_bars + loop_bars + tail_bars > num_bars * 2:
            return self._tile(template, bars_map, num_bars)

        # Build the looped middle first so the outro always lands at the end.
        middle = self._seq(head, bars_map)
        remaining = num_bars - head_bars - tail_bars
        repeats = max(1, remaining // loop_bars)
        for _ in range(repeats):
            middle += self._seq(loop, bars_map)
        while len(middle) < num_bars - tail_bars:
            middle += self._tile(loop, bars_map, num_bars - tail_bars - len(middle))

        names = middle + self._seq(tail, bars_map)
        return names[:num_bars]

    @staticmethod
    def _tile(template: list, bars_map: dict, num_bars: int) -> list:
        """Repeat the template and truncate to exactly ``num_bars`` bars."""
        names = []
        while len(names) < num_bars:
            for section in template:
                for _ in range(bars_map.get(section, 1)):
                    names.append(section)
                    if len(names) >= num_bars:
                        break
                if len(names) >= num_bars:
                    break
        return names
