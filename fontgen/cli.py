from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compile import compile_ttf
from .config import FontConfig
from .ufobuild import CHARS, build_font

EXAMPLE_CONFIG = """\
# Font identity
family_name: "My Handwriting"
style_name: "Regular"

# Free-text style description. Keywords like bold/thin/light/heavy,
# italic/slanted/cursive/handwritten, sharp/angular/geometric/rounded,
# and condensed/wide/expanded are picked up automatically to steer any
# letters you did NOT supply a reference image for. Explicit settings
# below always take precedence over these keyword guesses.
description: "casual, slightly bold, a little rounded"

# --- Explicit overrides (optional; delete a line to let 'description' decide) ---
# stroke_width: 65        # thickness of generated (non-traced) strokes, in font units (1000/em)
# slant: 0                # degrees, positive leans right (italic-style)
# round_joins: true        # rounded vs sharp corners on generated strokes
# letter_spacing: 40       # extra side bearing added to every glyph
# weight_delta: 0          # grow(+)/shrink(-) traced glyphs, in font units
# uppercase_from_lowercase: true   # A-Z reuse the a-z shapes when no other source has them

# --- Optional: base an existing font's letterforms instead of generating from scratch ---
# Any character without a reference image in refs/ is sourced from this font
# (including real A-Z capitals, if it has them) before falling back to a
# generated letterform. Then puffiness/roughness restyle those shapes --
# e.g. to turn a clean blackletter font into a puffy, hand-cut looking one.
# base_font: "path/to/SomeFont.ttf"
# puffiness: 0             # outward round expand, in font units -- makes strokes chunkier/bubblier
# roughness: 0              # organic edge noise amplitude, in font units -- uneven/hand-cut look
# roughness_wavelength: 70  # spacing of the roughness texture, in font units
"""

REFS_README = """\
Drop one reference image per character here, named exactly by the character:

    a.png  b.png  c.png ... z.png
    0.png  1.png  2.png ... 9.png

(.jpg / .jpeg also work.) Any character you don't provide a file for is
generated automatically from font.yaml's style description.

Guidelines for reference images:
  - Dark ink/pencil/marker on a light, evenly-lit background.
  - One character per image, reasonably centered, with a bit of margin.
  - A plain photo or scan is fine -- it doesn't need to be pre-cleaned,
    but avoid heavy shadows or background clutter near the letter.
"""


def cmd_init(args: argparse.Namespace) -> None:
    root = Path(args.dir)
    refs = root / "refs"
    refs.mkdir(parents=True, exist_ok=True)
    config_path = root / "font.yaml"
    refs_readme = refs / "README.txt"

    if not config_path.exists():
        config_path.write_text(EXAMPLE_CONFIG)
        print(f"Wrote {config_path}")
    else:
        print(f"Skipped {config_path} (already exists)")

    if not refs_readme.exists():
        refs_readme.write_text(REFS_README)
        print(f"Wrote {refs_readme}")

    print(f"Created {refs}/ -- add your reference images there, then run:\n  python -m fontgen build")


def cmd_build(args: argparse.Namespace) -> None:
    cfg = FontConfig.load(args.config)

    refs_dir = Path(args.refs)
    ref_images = {}
    if refs_dir.exists():
        for char in CHARS:
            for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
                candidate = refs_dir / f"{char}{ext}"
                if candidate.exists():
                    ref_images[char] = candidate
                    break

    font, report = build_font(cfg, ref_images)

    out_path = Path(args.out)
    compile_ttf(font, out_path)

    traced = sorted(report["traced"])
    base_font = sorted(set(report["base_font"]))
    generated = sorted(set(report["generated"]))
    duplicated = sorted(report["duplicated"])
    fallback = sorted(report["fallback"])

    print(f"\nBuilt {out_path}  ({cfg.family_name} {cfg.style_name})")
    print(f"  Traced from your images  ({len(traced):2d}): {' '.join(traced) or '-'}")
    if cfg.base_font:
        print(f"  From base font           ({len(base_font):2d}): {' '.join(base_font) or '-'}")
    print(f"  Generated from style     ({len(generated):2d}): {' '.join(generated) or '-'}")
    if duplicated:
        print(f"  A-Z duplicated from a-z  ({len(duplicated):2d}): {' '.join(duplicated)}")
    if fallback:
        print(f"  A source failed, used a fallback instead: {' '.join(fallback)}")
    print("\nInstall on macOS: double-click the .ttf file, then click 'Install Font' in Font Book")
    print(f"(or: open '{out_path}' from Finder).")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="fontgen",
        description="Build an installable .ttf font from your own hand-drawn a-z/0-9 reference images and/or a style description.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Scaffold a refs/ folder and example font.yaml")
    p_init.add_argument("--dir", default=".", help="Where to scaffold (default: current directory)")
    p_init.set_defaults(func=cmd_init)

    p_build = sub.add_parser("build", help="Build the .ttf font")
    p_build.add_argument("--config", default="font.yaml", help="Path to font config YAML (default: font.yaml)")
    p_build.add_argument("--refs", default="refs", help="Folder of reference images (default: refs)")
    p_build.add_argument("--out", default="build/MyFont.ttf", help="Output .ttf path (default: build/MyFont.ttf)")
    p_build.set_defaults(func=cmd_build)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
