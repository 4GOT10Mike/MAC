"""Font style configuration: explicit YAML knobs plus lightweight keyword
heuristics applied to your free-text `description`, so a description alone
can drive the look of any procedurally-generated (non-traced) glyphs."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any, Dict

import yaml

_KEYWORDS = {
    "thin": dict(stroke_width=38, weight_delta=-18),
    "light": dict(stroke_width=42, weight_delta=-14),
    "fine": dict(stroke_width=40, weight_delta=-16),
    "delicate": dict(stroke_width=38, weight_delta=-18),
    "bold": dict(stroke_width=95, weight_delta=16),
    "thick": dict(stroke_width=100, weight_delta=18),
    "heavy": dict(stroke_width=105, weight_delta=20),
    "marker": dict(stroke_width=100, weight_delta=16, round_joins=True),
    "chunky": dict(stroke_width=110, weight_delta=22, round_joins=True),
    "black": dict(stroke_width=125, weight_delta=26),
    "fat": dict(stroke_width=120, weight_delta=24),
    "italic": dict(slant=9.0),
    "slanted": dict(slant=9.0),
    "leaning": dict(slant=7.0),
    "cursive": dict(slant=10.0, round_joins=True),
    "script": dict(slant=10.0, round_joins=True),
    "handwritten": dict(slant=5.0, round_joins=True),
    "sharp": dict(round_joins=False),
    "angular": dict(round_joins=False),
    "geometric": dict(round_joins=False),
    "stencil": dict(round_joins=False),
    "blocky": dict(round_joins=False),
    "rounded": dict(round_joins=True),
    "playful": dict(round_joins=True),
    "friendly": dict(round_joins=True),
    "condensed": dict(letter_spacing=10.0),
    "narrow": dict(letter_spacing=15.0),
    "tight": dict(letter_spacing=15.0),
    "wide": dict(letter_spacing=90.0),
    "expanded": dict(letter_spacing=95.0),
    "airy": dict(letter_spacing=85.0),
    "loose": dict(letter_spacing=80.0),
}


@dataclasses.dataclass
class FontConfig:
    family_name: str = "My Custom Font"
    style_name: str = "Regular"
    description: str = ""
    units_per_em: int = 1000
    stroke_width: float = 65.0
    slant: float = 0.0
    weight_delta: float = 0.0
    round_joins: bool = True
    letter_spacing: float = 40.0
    uppercase_from_lowercase: bool = True
    version: str = "1.0"

    @classmethod
    def load(cls, path: str | Path) -> "FontConfig":
        raw: Dict[str, Any] = {}
        p = Path(path)
        if p.exists():
            raw = yaml.safe_load(p.read_text()) or {}
        valid = {f.name for f in dataclasses.fields(cls)}
        unknown = set(raw) - valid
        if unknown:
            raise ValueError(f"Unknown option(s) in {path}: {', '.join(sorted(unknown))}")
        cfg = cls(**raw)
        cfg._apply_description_keywords(explicit=set(raw))
        return cfg

    def _apply_description_keywords(self, explicit: set) -> None:
        text = self.description.lower()
        for word, effects in _KEYWORDS.items():
            if word not in text:
                continue
            for field_name, value in effects.items():
                if field_name not in explicit:
                    setattr(self, field_name, value)
