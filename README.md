# fontgen -- build your own installable Mac font

A small command-line tool that builds a real, installable `.ttf` font file
covering `a-z` and `0-9` (plus `A-Z` -- real capitals if your base font has
them, otherwise the lowercase shapes reused by default) from:

- **your own reference images** -- a photo or scan of hand-drawn/lettered
  characters, one image per character, traced into vector outlines,
- **an existing font file** -- reuse its letterforms as a base (e.g. a
  blackletter/display font whose overall shapes you like), optionally
  restyled with a puffy/rough texture to match a different reference's
  look, and/or
- **a plain-English style description** -- used to procedurally generate any
  character still uncovered, so gaps in your reference set still come out
  looking consistent with the rest.

Whichever sources you use, priority per character is: your reference image,
then the base font (if configured), then the procedural generator.

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
condensed/wide/expanded/airy, puffy/rough/distressed/jagged, ...) that steer
the procedurally-generated letters (and, for puffy/rough, a base font's
letters too -- see below). You can also set any of these explicitly to
override the keyword guesses -- see `examples/font.example.yaml` for the
full list (`stroke_width`, `slant`, `round_joins`, `letter_spacing`,
`weight_delta`, `uppercase_from_lowercase`).

### Reskinning an existing font (`base_font`)

If you want a specific existing typeface's letterforms (say, a blackletter
font whose overall shapes are close to what you want) restyled to look
hand-cut/worn/puffy instead of generating letters from scratch, point
`base_font` at it:

```yaml
base_font: "examples/references/OldEnglishFive.ttf"
puffiness: 20               # outward round expand, in font units -- chunkier strokes
roughness: 18                # organic edge noise amplitude, in font units
roughness_wavelength: 140    # spacing of the bumps -- bigger = fewer/chunkier, smaller = fine sawtooth
```

See `examples/saintsrow_style.example.yaml` for a full example (built from
the bundled `examples/references/OldEnglishFive.ttf`). Any character with a
reference image in `refs/` still takes priority over the base font; any
character the base font doesn't have falls back to the procedural
generator. `puffiness`/`roughness` only apply to base-font-sourced glyphs.

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
- **Base-font glyphs**: each character's outline is extracted straight from
  the given font file (`fontgen/basefont.py`, via `fontTools`), scaled to
  match your font's units-per-em. `puffiness` expands it outward with
  rounded joins (chunkier strokes); `roughness` perturbs its contours with
  smooth, seeded noise along their normal direction and rounds the result
  with Chaikin corner-cutting (`fontgen/geometry.py`'s `roughen`) for an
  organic, hand-cut/worn edge instead of a clean vector one.
- All three paths produce plain polygon outlines, which are assembled into
  a UFO font source (`fontgen/ufobuild.py`, via [ufoLib2](https://github.com/fonttools/ufoLib2))
  and compiled to `.ttf` with [ufo2ft](https://github.com/fonttools/ufo2ft) /
  [fontTools](https://github.com/fonttools/fonttools).

## Project layout

```
fontgen/
  cli.py         command-line entry point (init / build)
  config.py      font.yaml loading + description keyword heuristics
  skeletons.py   procedural letterform definitions for a-z, 0-9
  geometry.py    stroke / slant / scale / puff / roughen helpers (shapely-based)
  trace.py       reference image -> vector outline (potrace)
  basefont.py    existing font file -> vector outline (fontTools)
  glyphbuild.py  per-character outline construction (traced, base font, or generated)
  ufobuild.py    assembles the full UFO font source
  compile.py     UFO -> .ttf
examples/font.example.yaml              annotated example config
examples/saintsrow_style.example.yaml   example using base_font + puffiness/roughness
examples/references/                    bundled font(s) usable as a base_font
tests/test_build.py                     smoke tests (procedural + base-font builds)
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
