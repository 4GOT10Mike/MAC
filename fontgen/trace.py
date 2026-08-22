"""Trace a hand-drawn reference image (one character per file) into vector
outlines using potrace.

Assumption: dark ink on a light background (a photo/scan of pencil or marker
lettering on paper works fine; a screenshot with a transparent background
does not -- flatten it onto white first).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple

from PIL import Image
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


class PotraceNotFound(RuntimeError):
    pass


class TraceError(RuntimeError):
    pass


def _find_potrace() -> str:
    exe = shutil.which("potrace")
    if not exe:
        raise PotraceNotFound(
            "potrace is required to trace your reference images but isn't installed.\n"
            "Install it with:\n"
            "  macOS:   brew install potrace\n"
            "  Linux:   sudo apt-get install potrace\n"
        )
    return exe


def trace_image(path: Path, threshold: int = 140, turdsize: int = 2, alphamax: float = 1.0) -> Tuple[BaseGeometry, Tuple[int, int]]:
    """Trace `path` into a shapely (Multi)Polygon in image pixel coordinates
    (origin top-left, y increasing downward), with holes (counters) already
    represented as polygon interiors. Returns (shape, (image_width, image_height)).
    """
    potrace = _find_potrace()
    img = Image.open(path).convert("L")
    w, h = img.size
    bw = img.point(lambda p: 255 if p >= threshold else 0).convert("1")

    with tempfile.TemporaryDirectory() as td:
        pbm = Path(td) / "in.pbm"
        geo = Path(td) / "out.json"
        bw.save(pbm)
        proc = subprocess.run(
            [potrace, str(pbm), "-b", "geojson", "-t", str(turdsize), "-a", str(alphamax), "-o", str(geo)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise TraceError(f"potrace failed on {path}: {proc.stderr.strip()}")
        data = json.loads(geo.read_text())

    polys = []
    for feat in data.get("features", []):
        coords = feat.get("geometry", {}).get("coordinates", [])
        if not coords:
            continue
        shell, *holes = coords
        if len(shell) < 3:
            continue
        try:
            p = Polygon(shell, holes)
            if not p.is_valid:
                p = p.buffer(0)
            if not p.is_empty:
                polys.append(p)
        except Exception:
            continue

    if not polys:
        return Polygon(), (w, h)
    return unary_union(polys), (w, h)
