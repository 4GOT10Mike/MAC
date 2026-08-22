"""Compiles the in-memory UFO source into a real, installable .ttf file."""

from __future__ import annotations

from pathlib import Path

import ufo2ft


def compile_ttf(font, out_path: Path) -> None:
    ttf = ufo2ft.compileTTF(font, removeOverlaps=True, dropImpliedOnCurves=True)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ttf.save(str(out_path))
