# fontgen -- build your own installable Mac font

A small command-line tool that builds a real, installable `.ttf` font file
covering `a-z` and `0-9` (plus `A-Z`, reusing the lowercase shapes by
default) from:

- **your own reference images** -- a photo or scan of hand-drawn/lettered
  characters, one image per character, traced into vector outlines, and/or
- **a plain-English style description** -- used to procedurally generate any
  character you didn't supply an image for, so gaps in your reference set
  still come out looking consistent with the rest.

The output is a standard TrueType font (`.ttf`). That's the real,
double-click-installable file format on macOS -- Font Book (or a
double-click) installs it directly; a plain text file isn't a valid font
container.

## 1. Install prerequisites

```bash
brew install potrace          # traces your reference images into vector shapes
python3 -m pip install -r requirements.txt
```

(On Linux, `sudo apt-get install potrace` instead of the `brew` line.)

You only need `potrace` if you're supplying reference images. A
description-only font doesn't need it.

## 2. Scaffold a project

```bash
python3 -m fontgen init
```

This creates `font.yaml` (your style config) and a `refs/` folder in the
current directory.

## 3. Add reference images (optional but recommended)

Drop images into `refs/`, one per character, named exactly by the
character: `a.png`, `b.png`, ... `z.png`, `0.png`, ... `9.png` (`.jpg` /
`.jpeg` also work). See `refs/README.txt` for photo guidelines -- in short:
dark ink on a light background, one character per image, reasonably
centered.

Any character you don't provide an image for is generated automatically
from your style description in `font.yaml`.

## 4. Edit `font.yaml`

```yaml
family_name: "My Handwriting"
style_name: "Regular"
description: "casual marker lettering, a little bold, slightly rounded"
```

The `description` is scanned for keywords (bold/thin/light/heavy,
italic/slanted/cursive/handwritten, sharp/angular/geometric/rounded,
condensed/wide/expanded/airy, ...) that steer the procedurally-generated
letters. You can also set any of these explicitly to override the
keyword guesses -- see `examples/font.example.yaml` for the full list
(`stroke_width`, `slant`, `round_joins`, `letter_spacing`, `weight_delta`,
`uppercase_from_lowercase`).

## 5. Build

```bash
python3 -m fontgen build --out build/MyFont.ttf
```

This prints a summary of which characters were traced from your images vs.
generated from the description, then writes the `.ttf`.

## 6. Install on macOS

Double-click `build/MyFont.ttf` in Finder, then click **Install Font** in
the Font Book window that opens. It'll then show up as a regular font in
any Mac app (Pages, Preview, Photoshop, etc.) under the `family_name` you
set.

## How it works

- **Traced glyphs**: each reference image is thresholded to black-and-white
  and traced into vector outlines with [potrace](http://potrace.sourceforge.net/),
  then scaled/positioned onto the font's baseline and x-height/cap-height
  according to the character's class (x-height letter, ascender, descender,
  or digit).
- **Generated glyphs**: characters without a reference image are built from
  simple geometric stroke skeletons (`fontgen/skeletons.py`) -- straight
  lines and arcs describing each letterform's centerline -- which are then
  "stroked" to a filled outline at the configured width/slant/roundness
  (`fontgen/geometry.py`), the same way a single-line engraving font is
  built. This keeps ungenerated letters legible and visually consistent
  with each other, though it won't match your actual handwriting the way a
  traced image does -- for the closest match to your own lettering, supply
  a reference image for every character you care about.
- Both paths produce plain polygon outlines, which are assembled into a UFO
  font source (`fontgen/ufobuild.py`, via [ufoLib2](https://github.com/fonttools/ufoLib2))
  and compiled to `.ttf` with [ufo2ft](https://github.com/fonttools/ufo2ft) /
  [fontTools](https://github.com/fonttools/fonttools).

## Project layout

```
fontgen/
  cli.py         command-line entry point (init / build)
  config.py      font.yaml loading + description keyword heuristics
  skeletons.py   procedural letterform definitions for a-z, 0-9
  geometry.py    stroke / slant / scale helpers (shapely-based)
  trace.py       reference image -> vector outline (potrace)
  glyphbuild.py  per-character outline construction (traced or generated)
  ufobuild.py    assembles the full UFO font source
  compile.py     UFO -> .ttf
examples/font.example.yaml   annotated example config
tests/test_build.py          smoke test (build + validate an all-generated font)
```

## Tests

```bash
python3 -m unittest tests.test_build -v
```

## Troubleshooting

- **"potrace is required..."** -- install it (`brew install potrace` on
  macOS), or remove the reference image for that character to fall back to
  a generated letterform.
- **A traced letter looks wrong / tracing failed** -- check the image has
  clear dark ink on a light, evenly-lit background with no stray marks;
  `fontgen` will print a warning and fall back to a generated letterform
  for that character rather than failing the whole build.
- **Font looks right in this tool's specimen but wrong in an app** -- make
  sure you're not confusing two installed fonts with the same
  `family_name`; bump `style_name` or `family_name` between builds while
  iterating, or remove the old one from Font Book first.
