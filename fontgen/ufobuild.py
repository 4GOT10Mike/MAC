"""Assembles a full UFO font source: one glyph per a-z / 0-9 (traced from
your reference images where supplied, procedurally generated otherwise),
plus A-Z duplicated from the lowercase shapes, space, and .notdef."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import ufoLib2
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

from . import skeletons
from .config import FontConfig
from .glyphbuild import build_skeleton_glyph, build_traced_glyph
from .trace import PotraceNotFound

LOWER = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
CHARS = list(LOWER + DIGITS)


def _draw_shape(glyph, shape: BaseGeometry) -> None:
    if shape.is_empty:
        return
    polys = list(shape.geoms) if isinstance(shape, MultiPolygon) else [shape]
    pen = glyph.getPen()
    for poly in polys:
        poly = orient(poly, sign=1.0)  # CCW exterior, CW holes (UFO convention)
        rings = [poly.exterior, *poly.interiors]
        for ring in rings:
            coords = list(ring.coords)
            if len(coords) > 1 and coords[0] == coords[-1]:
                coords = coords[:-1]
            if len(coords) < 3:
                continue
            pen.moveTo(coords[0])
            for pt in coords[1:]:
                pen.lineTo(pt)
            pen.closePath()


def build_font(cfg: FontConfig, ref_images: Dict[str, Path]) -> Tuple["ufoLib2.Font", dict]:
    """Build the UFO source. `ref_images` maps a single character ('a'..'z',
    '0'..'9') to the reference image file to trace for it; any character not
    present is generated procedurally. Returns (font, report) where report
    lists which characters were traced vs. generated vs. fell back after a
    tracing error."""

    font = ufoLib2.Font()
    info = font.info
    info.familyName = cfg.family_name
    info.styleName = cfg.style_name
    info.unitsPerEm = int(cfg.units_per_em)
    info.ascender = int(skeletons.CAP + 60)
    info.descender = int(skeletons.DESC - 60)
    info.xHeight = int(skeletons.XH)
    info.capHeight = int(skeletons.CAP)
    info.italicAngle = -cfg.slant if cfg.slant else 0
    info.versionMajor = 1
    info.versionMinor = 0
    if cfg.description:
        info.openTypeNameDescription = cfg.description

    report = {"traced": [], "generated": [], "fallback": []}

    potrace_available = True
    potrace_warning_shown = False

    glyph_order: List[str] = [".notdef", "space"]

    for char in CHARS:
        image_path = ref_images.get(char)
        shape = None
        advance = None

        if image_path is not None and potrace_available:
            try:
                shape, advance = build_traced_glyph(char, image_path, cfg)
                report["traced"].append(char)
            except PotraceNotFound as e:
                potrace_available = False
                if not potrace_warning_shown:
                    print(f"Warning: {e}\nFalling back to generated letterforms for all remaining reference images.")
                    potrace_warning_shown = True
            except Exception as e:
                print(f"Warning: couldn't trace '{char}' from {image_path} ({e}); using a generated letterform instead.")
                report["fallback"].append(char)

        if shape is None:
            shape, advance = build_skeleton_glyph(char, cfg)
            if char not in report["fallback"]:
                report["generated"].append(char)

        glyph = font.newGlyph(char)
        glyph.unicodes = [ord(char)]
        glyph.width = round(advance)
        _draw_shape(glyph, shape)
        glyph_order.append(char)

    if cfg.uppercase_from_lowercase:
        for lc in LOWER:
            uc = lc.upper()
            src = font[lc]
            glyph = font.newGlyph(uc)
            glyph.unicodes = [ord(uc)]
            glyph.width = src.width
            src.draw(glyph.getPen())
            glyph_order.append(uc)

    space = font.newGlyph("space")
    space.unicodes = [0x20]
    space.width = round(skeletons.XH * 0.55 + cfg.letter_spacing * 2)

    notdef = font.newGlyph(".notdef")
    notdef.width = 500
    ndpen = notdef.getPen()
    ndpen.moveTo((60, 0))
    ndpen.lineTo((440, 0))
    ndpen.lineTo((440, 700))
    ndpen.lineTo((60, 700))
    ndpen.closePath()
    ndpen.moveTo((100, 40))
    ndpen.lineTo((400, 40))
    ndpen.lineTo((400, 660))
    ndpen.lineTo((100, 660))
    ndpen.closePath()

    font.glyphOrder = glyph_order
    return font, report
