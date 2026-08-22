"""Procedural fallback letterforms for a-z / 0-9.

These are used for any character you did NOT supply a reference image for.
They are simple geometric "monoline" strokes (think single-line engraving /
signage lettering) built out of straight segments and arcs, which then get
"stroked" to a filled outline in glyphbuild.py using the font's configured
stroke width / slant / roundness. They are deliberately simple and
consistent rather than fancy -- the point is a legible, uniform placeholder
that fills in gaps in your hand-drawn set, not a replacement for it.

Coordinate system (font units, 1000 units/em):
    baseline   y = BASE = 0
    x-height   y = XH   = 500   (top of a, c, e, m, n, o, r, s, u, v, w, x, z)
    cap-height y = CAP  = 700   (top of b, d, f, h, k, l, t, ascenders, digits)
    descender  y = DESC = -200  (bottom of g, j, p, q, y)

Each glyph is defined in its own local box from x=0 to x=<its natural
width>; glyphbuild.py positions/scales/spaces these when assembling the
final font.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .geometry import Point, Polyline, arc, circle, line

BASE = 0.0
XH = 500.0
CAP = 700.0
DESC = -200.0

# Natural (ymin, ymax) ink extent for each glyph -- used both to scale
# procedural glyphs consistently and to normalize traced reference images
# onto the right baseline/height for their letter class.
GLYPH_METRICS: Dict[str, Tuple[float, float]] = {}


def _stem(x: float, y0: float, y1: float) -> Polyline:
    return line((x, y0), (x, y1))


def _dome(x0: float, x1: float, y: float, bulge: float) -> Polyline:
    """Top arch spanning [x0, x1] with both ends at height y, apex at y+bulge."""
    cx = (x0 + x1) / 2.0
    rx = (x1 - x0) / 2.0
    return arc(cx, y, rx, bulge, 0, 180)


def _cup(x0: float, x1: float, y: float, depth: float) -> Polyline:
    """Bottom arch (valley) spanning [x0, x1] with both ends at height y, floor at y-depth."""
    cx = (x0 + x1) / 2.0
    rx = (x1 - x0) / 2.0
    return arc(cx, y, rx, depth, 180, 360)


def _diag(p0: Point, p1: Point) -> Polyline:
    return line(p0, p1)


# name -> (strokes, advance width, natural (ymin, ymax))
_DEFS: Dict[str, Tuple[List[Polyline], float, Tuple[float, float]]] = {}


def _add(char: str, strokes: List[Polyline], width: float, ymin: float, ymax: float) -> None:
    _DEFS[char] = (strokes, width, (ymin, ymax))


# ---- lowercase letters -----------------------------------------------------

R = 210.0  # standard bowl radius (~0.42 * x-height)

# a: bowl + right stem
_add("a", [circle(0.40 * 520, XH * 0.5, R), _stem(0.82 * 520, 0, XH)], 520, 0, XH)

# b: full-height stem + bottom-right bowl
_add("b", [_stem(90, 0, CAP), circle(90 + R, XH * 0.5, R)], 560, 0, CAP)

# c: open circle, gap on the right
_add("c", [arc(500 * 0.5, XH * 0.5, XH * 0.45, XH * 0.45, 45, 315)], 500, 0, XH)

# d: full-height stem (right) + bottom-left bowl
_add("d", [_stem(560 - 90, 0, CAP), circle(560 - 90 - R, XH * 0.5, R)], 560, 0, CAP)

# e: circle with a crossbar, small gap top-right
cx_e, cy_e, r_e = 520 * 0.5, XH * 0.5, XH * 0.45
_add("e", [arc(cx_e, cy_e, r_e, r_e, 15, 345), line((cx_e - r_e, cy_e), (cx_e + r_e * 0.95, cy_e))], 520, 0, XH)

# f: stem + crossbar + small top hook
_add(
    "f",
    [
        _stem(0.42 * 380, 0, CAP - 30),
        line((0.15 * 380, XH), (0.80 * 380, XH)),
        arc(0.42 * 380 + 120, CAP - 120, 120, 120, 90, 180),
    ],
    380,
    0,
    CAP,
)

# g: bowl + descending stem with a hook tail
_add(
    "g",
    [
        circle(0.40 * 560, XH * 0.5, R),
        _stem(0.82 * 560, DESC * 0.55, XH),
        arc(0.82 * 560 - R * 0.9, DESC * 0.55, R * 0.9, R * 0.9, 0, 180),
    ],
    560,
    DESC,
    XH,
)

# h: tall stem + short stem + connecting dome near top
_add("h", [_stem(90, 0, CAP), _stem(560 - 90, 0, XH), _dome(90, 560 - 90, XH * 0.62, XH * 0.38)], 560, 0, CAP)

# i: stem + dot
_add("i", [_stem(0.5 * 240, 0, XH * 0.72), circle(0.5 * 240, XH * 0.92, 55)], 240, 0, XH)

# j: descending stem with hook + dot
_add(
    "j",
    [
        _stem(0.5 * 260, DESC * 0.55, XH * 0.72),
        arc(0.5 * 260 - 90, DESC * 0.55, 90, 90, 0, 90),
        circle(0.5 * 260, XH * 0.92, 55),
    ],
    260,
    DESC,
    XH,
)

# k: stem + two diagonals
_add(
    "k",
    [_stem(90, 0, CAP), _diag((90, XH * 0.55), (520 - 60, XH)), _diag((90, XH * 0.55), (520 - 60, 0))],
    520,
    0,
    CAP,
)

# l: single stem
_add("l", [_stem(0.5 * 220, 0, CAP)], 220, 0, CAP)

# m: three stems + two domes
_x0, _x1, _x2 = 90, 400, 710
_add("m", [_stem(_x0, 0, XH), _stem(_x1, 0, XH), _stem(_x2, 0, XH), _dome(_x0, _x1, XH * 0.62, XH * 0.38), _dome(_x1, _x2, XH * 0.62, XH * 0.38)], 800, 0, XH)

# n: two stems + one dome
_add("n", [_stem(90, 0, XH), _stem(560 - 90, 0, XH), _dome(90, 560 - 90, XH * 0.62, XH * 0.38)], 560, 0, XH)

# o: full ellipse
_add("o", [arc(560 * 0.5, XH * 0.5, 560 * 0.42, XH * 0.5, 0, 360)], 560, 0, XH)

# p: descending stem + bowl
_add("p", [_stem(90, DESC * 0.55, XH), circle(90 + R, XH * 0.5, R)], 560, DESC, XH)

# q: descending stem (right) + bowl
_add("q", [_stem(560 - 90, DESC * 0.55, XH), circle(560 - 90 - R, XH * 0.5, R)], 560, DESC, XH)

# r: stem + small top arm
_add("r", [_stem(90, 0, XH), arc(90, XH - 120, 120, 120, -20, 90)], 380, 0, XH)

# s: two stacked open circles (touching)
_r_s = XH * 0.27
_add("s", [arc(460 * 0.5, XH - _r_s, _r_s, _r_s, 30, 270), arc(460 * 0.5, _r_s, _r_s, _r_s, 210, 450)], 460, 0, XH)

# t: stem + crossbar
_add("t", [_stem(0.42 * 360, 0, CAP * 0.85), line((0.12 * 360, XH), (0.85 * 360, XH))], 360, 0, CAP * 0.85)

# u: two stems + bottom cup
_add("u", [_stem(90, R, XH), _stem(560 - 90, R, XH), _cup(90, 560 - 90, R, R)], 560, 0, XH)

# v: two diagonals meeting at bottom
_add("v", [_diag((0, XH), (520 * 0.5, 0)), _diag((520 * 0.5, 0), (520, XH))], 520, 0, XH)

# w: four diagonals (double v)
_add(
    "w",
    [
        _diag((0, XH), (760 * 0.25, 0)),
        _diag((760 * 0.25, 0), (760 * 0.5, XH * 0.6)),
        _diag((760 * 0.5, XH * 0.6), (760 * 0.75, 0)),
        _diag((760 * 0.75, 0), (760, XH)),
    ],
    760,
    0,
    XH,
)

# x: two crossing diagonals
_add("x", [_diag((0, XH), (500, 0)), _diag((0, 0), (500, XH))], 500, 0, XH)

# y: two diagonals meeting mid, one continuing into the descender
_add("y", [_diag((0, XH), (500 * 0.55, XH * 0.35)), _diag((500, XH), (500 * 0.3, DESC))], 500, DESC, XH)

# z: top bar + diagonal + bottom bar
_add("z", [line((480 * 0.1, XH), (480 * 0.9, XH)), _diag((480 * 0.9, XH), (480 * 0.1, 0)), line((480 * 0.1, 0), (480 * 0.9, 0))], 480, 0, XH)

# ---- digits (full cap height) ----------------------------------------------

DW = 520.0
RD = CAP * 0.235

_add("0", [arc(DW * 0.5, CAP * 0.5, DW * 0.32, CAP * 0.45, 0, 360)], DW, 0, CAP)
_add("1", [_stem(DW * 0.5, 0, CAP), _diag((DW * 0.5 - 80, CAP - 110), (DW * 0.5, CAP))], DW, 0, CAP)

_2_top = _dome(DW * 0.15, DW * 0.85, CAP - RD, RD)
_add("2", [_2_top, _diag((DW * 0.85, CAP - RD), (DW * 0.15, 0)), line((DW * 0.15, 0), (DW * 0.85, 0))], DW, 0, CAP)

_add("3", [arc(DW * 0.5, CAP - RD, RD, RD, -60, 195), arc(DW * 0.5, RD, RD, RD, 165, 420)], DW, 0, CAP)

_add(
    "4",
    [_diag((DW * 0.78, CAP), (DW * 0.15, CAP * 0.35)), line((DW * 0.15, CAP * 0.35), (DW * 0.85, CAP * 0.35)), _stem(DW * 0.78, 0, CAP)],
    DW,
    0,
    CAP,
)

_add(
    "5",
    [line((78, CAP), (442, CAP)), _stem(78, 385, CAP), circle(195, 210, 210)],
    DW,
    0,
    CAP,
)

_add(
    "6",
    [circle(260, RD, RD), arc(290, 420, 270, 270, 60, 230)],
    DW,
    0,
    CAP,
)

_add("7", [line((DW * 0.12, CAP), (DW * 0.88, CAP)), _diag((DW * 0.88, CAP), (DW * 0.35, 0))], DW, 0, CAP)

_add("8", [circle(DW * 0.5, CAP * 0.745, CAP * 0.235), circle(DW * 0.5, CAP * 0.255, CAP * 0.235)], DW, 0, CAP)

_9_bowl_cx, _9_bowl_cy, _9_bowl_r = 260.0, CAP - RD, RD
_9_stem_x = _9_bowl_cx + _9_bowl_r
_add(
    "9",
    [
        circle(_9_bowl_cx, _9_bowl_cy, _9_bowl_r),
        _stem(_9_stem_x, _9_bowl_cy, 60),
        arc(_9_stem_x - 90, 60, 90, 90, 0, 180),
    ],
    DW,
    0,
    CAP,
)

for _c, (_strokes, _w, _ymm) in _DEFS.items():
    GLYPH_METRICS[_c] = _ymm

SKELETONS: Dict[str, Tuple[List[Polyline], float]] = {c: (s, w) for c, (s, w, _) in _DEFS.items()}
