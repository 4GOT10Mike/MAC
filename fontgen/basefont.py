"""Sources glyph shapes from an existing font file (e.g. a blackletter/Old
English TTF) instead of a reference image or a procedural skeleton, so you
can reuse its letterforms as a base and then restyle them (see `roughen`/
`grow` in geometry.py) to match a different reference's texture."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry


class _FlattenPen(BasePen):
    """Records each contour as a flat polyline, sampling curves at `steps`
    points per segment."""

    def __init__(self, glyphSet, steps: int = 10):
        super().__init__(glyphSet)
        self.steps = steps
        self.contours = []
        self._pts = []

    def _moveTo(self, pt):
        self._pts = [pt]

    def _lineTo(self, pt):
        self._pts.append(pt)

    def _curveToOne(self, p1, p2, p3):
        p0 = self._pts[-1]
        n = self.steps
        for i in range(1, n + 1):
            t = i / n
            mt = 1 - t
            x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
            y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
            self._pts.append((x, y))

    def _qCurveToOne(self, p1, p2):
        p0 = self._pts[-1]
        n = self.steps
        for i in range(1, n + 1):
            t = i / n
            mt = 1 - t
            x = mt**2 * p0[0] + 2 * mt * t * p1[0] + t**2 * p2[0]
            y = mt**2 * p0[1] + 2 * mt * t * p1[1] + t**2 * p2[1]
            self._pts.append((x, y))

    def _closePath(self):
        if len(self._pts) > 2:
            self.contours.append(self._pts)
        self._pts = []

    def _endPath(self):
        self._closePath()


def _contours_to_shape(contours) -> BaseGeometry:
    """Combine raw flattened contours into one filled shape, treating a
    contour nested inside an odd number of *larger* contours as a hole. This
    doesn't assume any particular winding-direction convention (different
    font tools disagree on whether outer contours are clockwise or
    counter-clockwise), just actual geometric nesting.

    Containment is only ever tested against larger-area contours: a small
    hole's representative point can easily fall, purely by coincidence,
    inside the region a much bigger contour silhouettes (e.g. a letter's
    outer shell's own representative point often lands inside one of its
    own counters) -- testing in both directions would misread that as the
    hole containing the shell.
    """
    polys = []
    for c in contours:
        p = Polygon(c)
        if not p.is_valid:
            p = p.buffer(0)
        if not p.is_empty:
            polys.append(p)
    if not polys:
        return Polygon()

    order = sorted(range(len(polys)), key=lambda i: -polys[i].area)

    result = Polygon()
    for rank, i in enumerate(order):
        p = polys[i]
        rp = p.representative_point()
        depth = sum(1 for j in order[:rank] if polys[j].contains(rp))
        if depth % 2 == 0:
            result = p if result.is_empty else result.union(p)
        else:
            result = result.difference(p)
    return result


class BaseFont:
    """A loaded reference font you can pull glyph shapes out of."""

    def __init__(self, path: str):
        self.ttfont = TTFont(path)
        self.units_per_em = self.ttfont["head"].unitsPerEm
        self.cmap = self.ttfont.getBestCmap()
        self.glyph_set = self.ttfont.getGlyphSet()
        self._cache: Dict[str, Tuple[Optional[BaseGeometry], Optional[float]]] = {}

    def has_char(self, char: str) -> bool:
        return ord(char) in self.cmap

    def get_shape(self, char: str, steps: int = 10) -> Tuple[Optional[BaseGeometry], Optional[float]]:
        """Returns (shape, advance_width) in this font's own units, or
        (None, None) if the font has no glyph for `char`."""
        if char in self._cache:
            return self._cache[char]
        if not self.has_char(char):
            self._cache[char] = (None, None)
            return None, None

        glyph_name = self.cmap[ord(char)]
        pen = _FlattenPen(self.glyph_set, steps=steps)
        self.glyph_set[glyph_name].draw(pen)

        shape = _contours_to_shape(pen.contours)
        width = self.ttfont["hmtx"][glyph_name][0]
        self._cache[char] = (shape, width)
        return shape, width
