"""Mise à l'échelle des sous-titres ASS (640x360 -> 1920x1080) : effets rares compris (v3.33).
Lancer : python3 -m unittest discover -s tests (Flask doit être installé)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import mouflanimexer as M  # noqa: E402

HEAD = """[Script Info]
PlayResX: 640
PlayResY: 360

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sign,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,1.5,0,1,2,1,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def scaled_text(event_text):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "a.ass"
        p.write_text(HEAD + f"Dialogue: 0,0:00:01.00,0:00:02.00,Sign,,0,0,0,,{event_text}\n", encoding="utf-8")
        M.scale_positioning_tags(p, (640, 360), (1920, 1080))
        line = [l for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("Dialogue:")][0]
        return line.split(",", 9)[9]


class AssScaling(unittest.TestCase):
    def test_rect_clip_et_iclip(self):
        self.assertEqual(scaled_text(r"{\clip(10,20,30,40)}a"), r"{\clip(30.00,60.00,90.00,120.00)}a")
        self.assertEqual(scaled_text(r"{\iclip(10,20,30,40)}a"), r"{\iclip(30.00,60.00,90.00,120.00)}a")

    def test_clip_vectoriel(self):
        self.assertEqual(scaled_text(r"{\clip(m 0 0 l 100 0 100 50)}a"), r"{\clip(m 0 0 l 300 0 300 150)}a")
        self.assertEqual(scaled_text(r"{\iclip(2,m 10 10 b 20 20 30 30 40 40)}a"), r"{\iclip(2,m 30 30 b 60 60 90 90 120 120)}a")

    def test_dessin_p1(self):
        self.assertEqual(scaled_text(r"{\pos(10,10)\p1}m 0 0 l 10 0 10 5{\p0}texte 12"),
                         r"{\pos(30.00,30.00)\p1}m 0 0 l 30 0 30 15{\p0}texte 12")

    def test_texte_normal_intact(self):
        self.assertEqual(scaled_text(r"m 0 0 l 10 0"), r"m 0 0 l 10 0")          # pas de \p : c'est du texte
        self.assertEqual(scaled_text(r"{\p1}m 0 0 l 1 1{\r}m 2 2"), r"{\p1}m 0 0 l 3 3{\r}m 2 2")

    def test_bordures_ombres_xy_espacement(self):
        self.assertEqual(scaled_text(r"{\xbord2\ybord1\xshad-1\yshad0.5\fsp2\pbo4\bord1}a"),
                         r"{\xbord6\ybord3\xshad-3\yshad1.5\fsp6\pbo12\bord3.00}a")

    def test_dans_animation_t(self):
        self.assertEqual(scaled_text(r"{\t(0,500,\iclip(0,0,10,10)\xbord3)}a"), r"{\t(0,500,\iclip(0.00,0.00,30.00,30.00)\xbord9)}a")

    def test_style_ssa_mis_a_l_echelle(self):
        ssa = """[Script Info]
ScriptType: v4.00
PlayResX: 640
PlayResY: 360

[V4 Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, TertiaryColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, AlphaLevel, Encoding
Style: Default,Arial,22,16777215,65535,65535,0,0,0,1,2,1,2,10,10,15,0,1

[Events]
Format: Marked, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: Marked=0,0:00:01.00,0:00:02.00,Default,,0000,0000,0000,,Bonjour
"""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.ssa"
            p.write_text(ssa, encoding="utf-8")
            M.patch_ass_style(p, (640, 360), apply_style_profiles=False)
            style = [l for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("Style:")][0]
        f = style[len("Style: "):].split(",")
        self.assertEqual((f[2], f[10], f[11], f[13], f[14], f[15]), ("66", "6", "3", "30", "30", "45"))

    def test_espacement_style_v4plus(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.ass"
            p.write_text(HEAD, encoding="utf-8")
            M.patch_ass_style(p, (640, 360), apply_style_profiles=False)
            style = [l for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("Style:")][0]
        f = style[len("Style: "):].split(",")
        self.assertEqual((f[2], f[13], f[16], f[17]), ("60", "4.5", "6", "3"))


if __name__ == "__main__":
    unittest.main()
