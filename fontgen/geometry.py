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
import random
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


def _densify_ring(coords: Polyline, max_seg_len: float) -> Polyline:
    pts: Polyline = []
    n = len(coords)
    for i in range(n):
        p0, p1 = coords[i], coords[(i + 1) % n]
        pts.append(p0)
        seg_len = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        steps = max(1, int(seg_len // max_seg_len))
        for s in range(1, steps):
            t = s / steps
            pts.append((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t))
    return pts


def _moving_average_smooth(values: List[float], passes: int = 1) -> List[float]:
    """Light 3-tap smoothing on a closed sequence -- just enough to keep
    adjacent jitter from being *completely* uncorrelated (which self-
    intersects constantly), while keeping the result jagged rather than a
    smooth wave."""
    n = len(values)
    for _ in range(passes):
        values = [(values[(i - 1) % n] + 2 * values[i] + values[(i + 1) % n]) / 4.0 for i in range(n)]
    return values


def _roughen_ring(coords: Polyline, amplitude: float, wavelength: float, seed: int) -> Polyline:
    if coords and coords[0] == coords[-1]:
        coords = coords[:-1]
    if len(coords) < 3:
        return coords

    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    amp = min(amplitude, diag * 0.15)  # never let noise be big enough to collapse a small ring (dots, counters)
    if amp <= 0:
        return coords

    dense = _densify_ring(coords, max(wavelength / 3.0, 3.0))
    n = len(dense)
    rng = random.Random(seed)
    # independent per-point jitter, lightly correlated with its neighbors --
    # jagged/chipped rather than a smooth periodic wave.
    jitter = _moving_average_smooth([rng.uniform(-1.0, 1.0) for _ in range(n)], passes=1)

    out: Polyline = []
    for i, (x, y) in enumerate(dense):
        x0, y0 = dense[(i - 1) % n]
        x1, y1 = dense[(i + 1) % n]
        tx, ty = x1 - x0, y1 - y0
        tl = math.hypot(tx, ty) or 1.0
        nx, ny = ty / tl, -tx / tl
        offset = amp * jitter[i]
        out.append((x + nx * offset, y + ny * offset))
    return out


def roughen(geom, amplitude: float, wavelength: float = 70.0, seed: int = 1):
    """Perturb a filled shape's contours with jagged, irregular jitter along
    their own normal direction -- a chipped/hand-cut edge, not a smooth wavy
    one. `wavelength` is roughly the grain size (in font units) of the
    texture (smaller = finer/tighter jaggedness, larger = coarser, more
    spread-out chips); `amplitude` is roughly how far it pushes in/out."""
    if amplitude == 0 or geom.is_empty:
        return geom

    polys = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    out = []
    for gi, poly in enumerate(polys):
        rings = [poly.exterior, *poly.interiors]
        new_rings = [_roughen_ring(list(r.coords), amplitude, wavelength, seed + gi * 1000 + ri) for ri, r in enumerate(rings)]
        try:
            p = Polygon(new_rings[0], new_rings[1:])
            if not p.is_valid:
                p = p.buffer(0)
        except Exception:
            p = poly
        if p.is_empty:
            continue
        pieces = list(p.geoms) if isinstance(p, MultiPolygon) else [p]
        # drop stray slivers self-intersection cleanup can leave behind, without risking real
        # small features (e.g. a dot) -- those are orders of magnitude bigger than this.
        out.extend(piece for piece in pieces if piece.area >= 25.0)

    if not out:
        return geom
    return out[0] if len(out) == 1 else unary_union(out)
