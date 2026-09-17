# Script callable from fontforge
from config import font_dir
import os
import sys
import fontforge
import json

arg = os.sys.argv[1]
basename, _ = os.path.splitext(os.path.basename(arg))
json_fname = basename + '-glyphs.json'
if os.path.isfile(json_fname):
    print(f"File {json_fname} exists; exiting... ")
    sys.exit(0)

pfb_file = os.path.join(font_dir, arg)
font = fontforge.open(pfb_file)
image_dir = basename
glyphs = []
if not os.path.exists(image_dir):
    os.makedirs(image_dir)

for glyph in font:
    if font[glyph].isWorthOutputting():
        gname = font[glyph].glyphname
        gfname = os.path.join(image_dir, gname + ".png")
        if not os.path.isfile(gfname):
            font[glyph].export(gfname)
        glyphs.append(gname)
print(f"Glyph images are saved in {image_dir}/ as .png files")

with open(json_fname, 'w', encoding='utf-8') as f:
    json.dump(glyphs, f, indent=4, ensure_ascii=False)
print(f"Glyph list successfully saved to JSON file: {json_fname}")
