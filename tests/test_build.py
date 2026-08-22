"""Smoke test: build an all-procedural font (no reference images) and check
the resulting .ttf is well-formed and installable."""

import string
import tempfile
import unittest
from pathlib import Path

from fontTools.ttLib import TTFont

from fontgen.compile import compile_ttf
from fontgen.config import FontConfig
from fontgen.ufobuild import build_font


class TestBuild(unittest.TestCase):
    def test_all_procedural_font_is_well_formed(self):
        cfg = FontConfig(family_name="Test Font", style_name="Regular", description="bold rounded")
        font, report = build_font(cfg, ref_images={})

        self.assertEqual(len(report["traced"]), 0)
        self.assertEqual(sorted(report["generated"]), sorted(string.ascii_lowercase + string.digits))

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "Test.ttf"
            compile_ttf(font, out)
            self.assertTrue(out.exists())

            ttf = TTFont(str(out))
            cmap = ttf.getBestCmap()

            expected_chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + " "
            missing = [c for c in expected_chars if ord(c) not in cmap]
            self.assertEqual(missing, [], f"missing glyphs for: {missing}")

            glyf = ttf["glyf"]
            for name in ttf.getGlyphOrder():
                glyf[name].expand(glyf)  # raises on malformed outlines

            self.assertGreaterEqual(ttf["maxp"].numGlyphs, 2 + 36 + 26)
            self.assertEqual(ttf["name"].getDebugName(1), "Test Font")


if __name__ == "__main__":
    unittest.main()
