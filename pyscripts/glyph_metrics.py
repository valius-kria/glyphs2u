# Script callable from fontforge.
# Saves each glyph's real metrics in <font>.metrics.json.
#
# The exported PNGs are NOT usable for this: fontforge's glyph.export() without
# a pixel size does not render at a fixed em scale, so two glyphs' image
# heights are not in proportion to their real heights -- stix-mathex's text
# white parenthesis (932 units) exports 101px while its 'big' cut (1230 units)
# exports 193px, a ratio of 1.9 where the truth is 1.3.  Image sizes do keep the
# ORDER, so they can rank cuts, but any statement about how much bigger a cut is
# has to come from here.
#
# Heights are written in font units and as a fraction of the em, so two fonts
# can be compared (Type 1 has em=1000, OpenType commonly 2048).
import os
import sys
import json
import fontforge
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff_glyph import real, draws

pfb_name = os.sys.argv[1]
basename, _ = os.path.splitext(os.path.basename(pfb_name))
json_fname = basename + '.metrics.json'

path_fname = pfb_name + ".path"
with open(path_fname, "r", encoding="utf-8") as f:
    pfb_file = f.read()

font = fontforge.open(pfb_file)
em = font.em or 1000
glyphs = {}
for name in font:
    g = font[name]
    # Zero-area bounding box as well as not-worth-outputting: a slot holding one
    # degenerate contour passes isWorthOutputting() and measures as nothing, so
    # it would enter the metrics as a real glyph of no size (198 of bbmssbx10's
    # 256).  The size ladder ranks by these numbers, and a run of zero-height
    # entries would rank as the smallest cuts of every stretchy symbol.
    if not real(g):                    # see ff_glyph: ink, or blank by design
        continue
    x0, y0, x1, y1 = g.boundingBox()
    glyphs[name] = {
        # x0/x1 as well as the width: a glyph can be the right SIZE and in the
        # wrong PLACE, and only the horizontal extent shows it.  bbmssbx10's
        # Acircumflex measures 808 wide like its A and sits at x0=-539 with an
        # advance of 881, so two thirds of it is left of the origin -- the base
        # letter's outline displaced, which fontforge's GUI shows at a glance and
        # no number here used to.
        "h": round(y1 - y0, 1), "w": round(x1 - x0, 1),
        "x0": round(x0, 1), "x1": round(x1, 1),
        "y0": round(y0, 1), "y1": round(y1, 1),
        "adv": g.width,
        "h_em": round((y1 - y0) / em, 4),
    }
out = {"font": basename, "em": em, "glyphs": glyphs}
font.close()

with open(json_fname, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"Metrics for {len(glyphs)} glyphs saved to {json_fname} (em={em})")
