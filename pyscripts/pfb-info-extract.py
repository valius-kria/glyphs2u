# fontforge script: dump per-PFB info for tex4ht-data.
#
# Invoked as:
#   fontforge -script pfb-info-extract.py <pfb_path> <glyphs_out> <enc_out>
# Writes:
#   <glyphs_out>: { "source": <pfb_path>,
#                   "glyphs": ["glyph0", "glyph1", ...] }   # full CharStrings universe
#   <enc_out>:    { "source": <pfb_path>,
#                   "slots": ["", "Gamma", ..., ""] }       # 256-entry slot->name vector
#
# The two outputs come from one fontforge open call.  enc_out uses
# font.encoding = "Original" to force the PFB's internal /Encoding (slots 0..255).
# Empty / .notdef slots are written as "".  glyphs_out is the full glyph-name
# set (in iteration order, may exceed 256 for fonts with extra CharStrings
# entries like MnSymbol).
#
# Either output path may be passed as the literal "-" to skip producing it.

import json
import os
import sys

import fontforge

if len(sys.argv) < 4:
    sys.stderr.write(
        "usage: pfb-info-extract.py <pfb> <glyphs_out|-> <enc_out|->\n"
    )
    sys.exit(2)

pfb_path, glyphs_out, enc_out = sys.argv[1], sys.argv[2], sys.argv[3]

if not os.path.isfile(pfb_path):
    sys.stderr.write(f"pfb not found: {pfb_path}\n")
    sys.exit(1)

font = fontforge.open(pfb_path)

# Full glyph universe (CharStrings names).  Iteration on the font yields glyphs
# in the current encoding order; some PFBs hold more glyphs than fit in the
# default /Encoding, in which case the trailing tail comes from CharStrings
# entries reachable only via alternative encodings.
if glyphs_out != "-":
    all_glyphs = []
    for g in font.glyphs():
        name = g.glyphname
        if name and name != ".notdef":
            all_glyphs.append(name)
    with open(glyphs_out, "w", encoding="utf-8") as f:
        json.dump(
            {"source": pfb_path, "glyphs": all_glyphs},
            f, ensure_ascii=False,
        )

# 256-entry positional slot -> name vector via the PFB's internal /Encoding.
# fontforge.open loads a PFB with encoding="Custom" reflecting the file's own
# /Encoding array (slot N matches the .pfb's `dup N /name put` directives).
# Do NOT set font.encoding = "Original" — that inserts a .notdef at slot 0 and
# shifts every subsequent slot by 1.
if enc_out != "-":
    slots = [""] * 256
    for slot in range(256):
        try:
            g = font[slot]
            if g is not None:
                name = g.glyphname
                if name and name != ".notdef":
                    slots[slot] = name
        except (TypeError, KeyError):
            pass
    with open(enc_out, "w", encoding="utf-8") as f:
        json.dump({"source": pfb_path, "slots": slots}, f, ensure_ascii=False)

font.close()
