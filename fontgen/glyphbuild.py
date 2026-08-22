"""Turns either a reference image or a procedural skeleton into a final,
positioned glyph outline (a shapely geometry in font units, left sidebearing
already applied) plus its advance width."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from shapely.affinity import affine_transform
from shapely.geometry.base import BaseGeometry

from . import skeletons
from .basefont import BaseFont
from .config import FontConfig
from .geometry import grow, roughen, scale, slant, stroke_polylines, translate
from .trace import trace_image


def build_skeleton_glyph(char: str, cfg: FontConfig) -> Tuple[BaseGeometry, float]:
    strokes, natural_width = skeletons.SKELETONS[char]
    shape = stroke_polylines(strokes, cfg.stroke_width, round_joins=cfg.round_joins)
    if cfg.slant:
        shape = slant(shape, cfg.slant, base_y=0)
    minx, miny, maxx, maxy = shape.bounds
    shape = translate(shape, cfg.letter_spacing - minx, 0)
    advance = (maxx - minx) + 2 * cfg.letter_spacing
    return shape, advance


def build_basefont_glyph(char: str, base_font: BaseFont, cfg: FontConfig) -> Tuple[BaseGeometry, float]:
    shape, width = base_font.get_shape(char)
    if shape is None or shape.is_empty:
        raise ValueError(f"'{char}' has no glyph (or an empty outline) in the base font {cfg.base_font!r}.")

    factor = cfg.units_per_em / base_font.units_per_em
    if factor != 1.0:
        shape = scale(shape, factor, factor, origin=(0, 0))
        width *= factor

    if cfg.puffiness:
        shape = grow(shape, cfg.puffiness)
    if cfg.roughness:
        shape = roughen(shape, cfg.roughness, cfg.roughness_wavelength, seed=cfg.roughness_seed + ord(char))
    if cfg.slant:
        shape = slant(shape, cfg.slant, base_y=0)

    shape = translate(shape, cfg.letter_spacing, 0)
    advance = width + 2 * cfg.letter_spacing
    return shape, advance


def build_traced_glyph(char: str, image_path: Path, cfg: FontConfig) -> Tuple[BaseGeometry, float]:
    shape_px, (img_w, img_h) = trace_image(image_path)
    if shape_px.is_empty:
        raise ValueError(
            f"Tracing {image_path} produced no ink. Make sure it's a dark drawing on a light background."
        )

    # Image space is y-down from the top-left; font space is y-up from the baseline.
    shape = affine_transform(shape_px, [1, 0, 0, -1, 0, img_h])

    minx, miny, maxx, maxy = shape.bounds
    ink_h = maxy - miny
    if ink_h <= 0:
        raise ValueError(f"Tracing {image_path} produced a degenerate (zero-height) shape.")

    ymin, ymax = skeletons.GLYPH_METRICS.get(char, (0.0, skeletons.XH))
    target_h = ymax - ymin
    s = target_h / ink_h
    shape = translate(shape, -minx, -miny)
    shape = scale(shape, s, s, origin=(0, 0))
    shape = translate(shape, 0, ymin)

    if cfg.slant:
        shape = slant(shape, cfg.slant, base_y=0)
    if cfg.weight_delta:
        shape = grow(shape, cfg.weight_delta)

    minx, miny, maxx, maxy = shape.bounds
    shape = translate(shape, cfg.letter_spacing - minx, 0)
    advance = (maxx - minx) + 2 * cfg.letter_spacing
    return shape, advance
