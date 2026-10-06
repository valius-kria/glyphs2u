# Script callable from fontforge
# Saves the default encoding in the pfb file
import os
import sys
import fontforge
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff_glyph import real, draws
import json

pfb_name = os.sys.argv[1]
json_fname = pfb_name + '.enc.json'
# Do not extract if already exists
if os.path.isfile(json_fname):
    print(f"File {json_fname} exists; exiting... ")
    sys.exit(0)

path_fname = pfb_name + ".path"
with open(path_fname, "r", encoding="utf-8") as f:
    pfb_file = f.read()

# A slot that draws nothing AND stands for a printing character is a hole wearing
# a name, and it is recorded as such rather than as a glyph -- see ff_glyph for
# why neither isWorthOutputting() nor the bounding box answers this alone, and
# why 'space' has to survive the test.
#
# The empty ones are listed apart instead of being dropped, because slot -> name
# is a fact about the font's encoding and stays true whether the glyph draws or
# not.  gpm_init skips them the way it skips '.notdef', and anything wanting the
# whole encoding still has it.
font = fontforge.open(pfb_file)
slots, empty = {}, {}
for slot in range(256):
    try:
        g = font[slot]
        if g is not None:
            name = g.glyphname
            if name and name != ".notdef":
                (slots if real(g) else empty)[str(slot)] = name
    except (TypeError, KeyError):
        pass
font.close()

# The .enc.json stays a FLAT slot -> name map.  Nesting the two lists under
# 'slots' and 'empty' would have been tidier and would have broken every reader
# of it -- gpm_init, cmp_classify, enc_to_lua, uni_to_html all iterate it
# directly -- for a fact that belongs beside the file rather than inside it.
with open(json_fname, "w", encoding="utf-8") as f:
    json.dump(slots, f, ensure_ascii=False)
if empty:
    empty_fname = pfb_name + ".empty.json"
    with open(empty_fname, "w", encoding="utf-8") as f:
        json.dump(empty, f, ensure_ascii=False, indent=1)
    print(f"{len(slots)} slot(s) draw something; {len(empty)} named slot(s) are "
          f"empty -> {os.path.basename(empty_fname)}.  They are left out of the "
          f"encoding, so nothing downstream considers them: one degenerate "
          f"contour each, which isWorthOutputting() calls a glyph and the "
          f"bounding box does not.")
