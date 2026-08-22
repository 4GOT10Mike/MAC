"""Assembles a full UFO font source: one glyph per a-z / 0-9, sourced in
priority order -- traced from your reference images, then from a base font
(if configured), then procedurally generated -- plus A-Z (from the base
font if it has real capitals, otherwise duplicated from the lowercase
shapes), space, and .notdef."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ufoLib2
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

from . import skeletons
from .basefont import BaseFont
from .config import FontConfig
from .glyphbuild import build_basefont_glyph, build_skeleton_glyph, build_traced_glyph
from .trace import PotraceNotFound

LOWER = "abcdefghijklmnopqrstuvwxyz"
UPPER = LOWER.upper()
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


class _Resolver:
    """Tries each glyph source in priority order for a character: your
    reference image, then the base font, recording what happened in
    `report` and disabling tracing globally the first time potrace turns
    out to be missing."""

    def __init__(self, cfg: FontConfig, ref_images: Dict[str, Path], base_font: Optional[BaseFont], report: dict):
        self.cfg = cfg
        self.ref_images = ref_images
        self.base_font = base_font
        self.report = report
        self.potrace_available = True
        self.potrace_warned = False

    def resolve(self, char: str) -> Tuple[Optional[BaseGeometry], Optional[float]]:
        image_path = self.ref_images.get(char)
        if image_path is not None and self.potrace_available:
            try:
                shape, advance = build_traced_glyph(char, image_path, self.cfg)
                self.report["traced"].append(char)
                return shape, advance
            except PotraceNotFound as e:
                self.potrace_available = False
                if not self.potrace_warned:
                    print(f"Warning: {e}\nFalling back to other sources for all remaining reference images.")
                    self.potrace_warned = True
            except Exception as e:
                print(f"Warning: couldn't trace '{char}' from {image_path} ({e}); trying other sources.")
                self.report["fallback"].append(char)

        if self.base_font is not None and self.base_font.has_char(char):
            try:
                shape, advance = build_basefont_glyph(char, self.base_font, self.cfg)
                self.report["base_font"].append(char)
                return shape, advance
            except Exception as e:
                print(f"Warning: couldn't use the base font's '{char}' glyph ({e}); trying other sources.")
                if char not in self.report["fallback"]:
                    self.report["fallback"].append(char)

        return None, None


def build_font(cfg: FontConfig, ref_images: Dict[str, Path]) -> Tuple["ufoLib2.Font", dict]:
    """Build the UFO source. `ref_images` maps a single character ('a'..'z',
    '0'..'9') to the reference image file to trace for it. `cfg.base_font`
    (if set) is used as a second-choice source for any character without a
    reference image. Anything still uncovered is generated procedurally (or,
    for A-Z, duplicated from the matching lowercase shape). Returns
    (font, report) describing which source was used for each character."""

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

    base_font = BaseFont(cfg.base_font) if cfg.base_font else None

    report = {"traced": [], "base_font": [], "generated": [], "duplicated": [], "fallback": []}
    resolver = _Resolver(cfg, ref_images, base_font, report)

    glyph_order: List[str] = [".notdef", "space"]

    for char in CHARS:
        shape, advance = resolver.resolve(char)
        if shape is None:
            shape, advance = build_skeleton_glyph(char, cfg)
            if char not in report["fallback"]:
                report["generated"].append(char)

        glyph = font.newGlyph(char)
        glyph.unicodes = [ord(char)]
        glyph.width = round(advance)
        _draw_shape(glyph, shape)
        glyph_order.append(char)

    for lc in LOWER:
        uc = lc.upper()
        shape, advance = resolver.resolve(uc)
        if shape is not None:
            glyph = font.newGlyph(uc)
            glyph.unicodes = [ord(uc)]
            glyph.width = round(advance)
            _draw_shape(glyph, shape)
            glyph_order.append(uc)
        elif cfg.uppercase_from_lowercase:
            src = font[lc]
            glyph = font.newGlyph(uc)
            glyph.unicodes = [ord(uc)]
            glyph.width = src.width
            src.draw(glyph.getPen())
            glyph_order.append(uc)
            report["duplicated"].append(uc)

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
