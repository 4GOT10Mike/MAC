"""Smoke tests: build fonts through each glyph source path and check the
resulting .ttf is well-formed and installable."""

import string
import tempfile
import unittest
from pathlib import Path

from fontTools.ttLib import TTFont

from fontgen.compile import compile_ttf
from fontgen.config import FontConfig
from fontgen.ufobuild import build_font

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_FONT_FIXTURE = REPO_ROOT / "examples" / "references" / "OldEnglishFive.ttf"


def _assert_well_formed(test, ttf_path, expected_family):
    ttf = TTFont(str(ttf_path))
    cmap = ttf.getBestCmap()

    expected_chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + " "
    missing = [c for c in expected_chars if ord(c) not in cmap]
    test.assertEqual(missing, [], f"missing glyphs for: {missing}")

    glyf = ttf["glyf"]
    for name in ttf.getGlyphOrder():
        glyf[name].expand(glyf)  # raises on malformed outlines

    test.assertGreaterEqual(ttf["maxp"].numGlyphs, 2 + 36 + 26)
    test.assertEqual(ttf["name"].getDebugName(1), expected_family)


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
            _assert_well_formed(self, out, "Test Font")

    def test_base_font_puffy_rough_font_is_well_formed(self):
        if not BASE_FONT_FIXTURE.exists():
            self.skipTest(f"fixture not present: {BASE_FONT_FIXTURE}")

        cfg = FontConfig(
            family_name="Test Base Font",
            style_name="Regular",
            base_font=str(BASE_FONT_FIXTURE),
            puffiness=20,
            roughness=18,
            roughness_wavelength=140,
        )
        font, report = build_font(cfg, ref_images={})

        self.assertEqual(len(report["traced"]), 0)
        self.assertEqual(len(report["fallback"]), 0)
        self.assertEqual(sorted(report["base_font"]), sorted(string.ascii_lowercase + string.ascii_uppercase + string.digits))

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "TestBase.ttf"
            compile_ttf(font, out)
            self.assertTrue(out.exists())
            _assert_well_formed(self, out, "Test Base Font")


if __name__ == "__main__":
    unittest.main()
