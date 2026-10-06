# Script callable from fontforge
import os
import sys
import fontforge
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff_glyph import real, draws
import json

pfb_name = os.sys.argv[1]
basename, _ = os.path.splitext(os.path.basename(pfb_name))
json_fname = basename + '-glyphs.json'
if os.path.isfile(json_fname):
    print(f"File {json_fname} exists; exiting... ")
    sys.exit(0)

path_fname = pfb_name + ".path"
with open(path_fname, "r", encoding="utf-8") as f:
    pfb_file = f.read()

font = fontforge.open(pfb_file)
image_dir = basename
glyphs = []
if not os.path.exists(image_dir):
    os.makedirs(image_dir)

# See ff_glyph: ink where there is ink, and where there is none, whether the
# character the glyph stands for is meant to be invisible.
skipped = 0
for glyph in font:
    g = font[glyph]
    if not g.isWorthOutputting():
        continue
    if not draws(g):
        skipped += 1
        continue
    gname = g.glyphname
    gfname = os.path.join(image_dir, gname + ".png")
    if not os.path.isfile(gfname):
        g.export(gfname)
    glyphs.append(gname)
print(f"Glyph images are saved in {image_dir}/ as .png files")
if skipped:
    print(f"{skipped} named slot(s) draw nothing (one degenerate contour each) "
          f"-- no image written and no entry in the glyph list")

with open(json_fname, 'w', encoding='utf-8') as f:
    json.dump(glyphs, f, indent=4, ensure_ascii=False)
print(f"Glyph list successfully saved to JSON file: {json_fname}")
