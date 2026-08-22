"""Low-level geometry helpers used to build letterforms and turn them into
filled, closed contours that a font outline needs.

Two kinds of glyph source flow through here:

  * "skeleton" glyphs: a handful of straight lines / arcs describing the
    stroke centerline of a character (see skeletons.py). These get turned
    into filled shapes by "stroking" them (like a marker of fixed width
    following the line) with `stroke_polylines`.
  * "traced" glyphs: outlines already extracted from a bitmap by potrace
    (see trace.py). Those are already filled shapes and just get scaled /
    positioned / unioned via the same helpers.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

from shapely.affinity import affine_transform
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import unary_union

Point = Tuple[float, float]
Polyline = List[Point]


def line(p0: Point, p1: Point) -> Polyline:
    return [p0, p1]


def arc(cx: float, cy: float, rx: float, ry: float, a0: float, a1: float, n: int = 20) -> Polyline:
    """Elliptical arc from angle a0 to a1 (degrees, 0=+x axis, 90=+y axis, CCW)."""
    pts: Polyline = []
    for i in range(n + 1):
        t = a0 + (a1 - a0) * i / n
        r = math.radians(t)
        pts.append((cx + rx * math.cos(r), cy + ry * math.sin(r)))
    return pts


def circle(cx: float, cy: float, r: float, n: int = 28) -> Polyline:
    return arc(cx, cy, r, r, 0, 360, n)


def chain(*parts: Sequence[Point]) -> Polyline:
    """Join polylines end-to-start into one continuous polyline, dropping
    duplicate join points. Parts must already share endpoints."""
    out: Polyline = []
    for part in parts:
        if out and part and _close(out[-1], part[0]):
            out.extend(part[1:])
        else:
            out.extend(part)
    return out


def _close(a: Point, b: Point, eps: float = 1e-6) -> bool:
    return abs(a[0] - b[0]) < eps and abs(a[1] - b[1]) < eps


def stroke_polylines(strokes: Iterable[Polyline], width: float, round_joins: bool = True) -> Polygon | MultiPolygon:
    """Turn a set of stroke centerlines into filled outline(s) of the given
    width, unioned into one shape."""
    cap = 1 if round_joins else 2  # shapely CAP_STYLE.round / .flat
    join = 1 if round_joins else 2  # shapely JOIN_STYLE.round / .mitre
    polys = []
    for pts in strokes:
        if len(pts) < 2:
            continue
        buf = LineString(pts).buffer(width / 2.0, cap_style=cap, join_style=join, quad_segs=8)
        if not buf.is_empty:
            polys.append(buf)
    if not polys:
        return Polygon()
    return unary_union(polys)


def slant(geom, angle_deg: float, base_y: float = 0.0):
    """Shear a shapely geometry horizontally (italic-style slant) about a
    baseline y."""
    if angle_deg == 0 or geom.is_empty:
        return geom
    k = math.tan(math.radians(angle_deg))
    # x' = x + k*(y - base_y); y' = y
    return affine_transform(geom, [1, k, 0, 1, -k * base_y, 0])


def grow(geom, amount: float):
    """Dilate (amount > 0) or erode (amount < 0) a filled shape, e.g. to make
    a traced glyph bolder/lighter. Keeps holes (counters) intact."""
    if amount == 0 or geom.is_empty:
        return geom
    return geom.buffer(amount, join_style=1, quad_segs=8)


def translate(geom, dx: float, dy: float):
    return affine_transform(geom, [1, 0, 0, 1, dx, dy])


def scale(geom, sx: float, sy: float, origin: Point = (0, 0)):
    ox, oy = origin
    return affine_transform(geom, [sx, 0, 0, sy, ox - sx * ox, oy - sy * oy])
