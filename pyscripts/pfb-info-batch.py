# fontforge batch script: extract per-PFB info for many PFBs in one process.
#
# Invoked as:
#   fontforge -script pfb-info-batch.py <jobs.json>
#
# jobs.json is a list of triples: [pfb_path, glyphs_out, enc_out]
# Either output path can be "-" to skip it (e.g. when only the glyph list is
# needed, pass "-" for enc_out).
#
# Output formats match pfb-info-extract.py:
#   glyphs_out: {"source": <pfb>, "glyphs": [name, name, ...]}
#   enc_out:    {"source": <pfb>, "slots":  [name|"" x 256]}
#
# Existing output files are skipped (caller is responsible for invalidating
# stale caches if the source PFB or this script changed).

import json
import os
import sys

import fontforge

if len(sys.argv) < 2:
    sys.stderr.write("usage: fontforge -script pfb-info-batch.py <jobs.json>\n")
    sys.exit(2)

with open(sys.argv[1], "r", encoding="utf-8") as f:
    jobs = json.load(f)

n_glyphs = n_enc = n_skip = n_err = 0
for pfb_path, glyphs_out, enc_out in jobs:
    need_glyphs = glyphs_out != "-" and not os.path.isfile(glyphs_out)
    need_enc = enc_out != "-" and not os.path.isfile(enc_out)
    if not need_glyphs and not need_enc:
        n_skip += 1
        continue
    if not os.path.isfile(pfb_path):
        sys.stderr.write(f"pfb missing: {pfb_path}\n")
        n_err += 1
        continue
    try:
        font = fontforge.open(pfb_path)
    except Exception as exc:
        sys.stderr.write(f"open failed for {pfb_path}: {exc}\n")
        n_err += 1
        continue
    try:
        if need_glyphs:
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
            n_glyphs += 1
        if need_enc:
            # See pfb-info-extract.py: keep encoding 'Custom' (default after
            # open) — that is the PFB's /Encoding.  Do NOT set "Original".
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
                json.dump(
                    {"source": pfb_path, "slots": slots},
                    f, ensure_ascii=False,
                )
            n_enc += 1
    finally:
        font.close()

sys.stderr.write(
    f"pfb-info-batch: glyph files written={n_glyphs}, "
    f"enc files written={n_enc}, skipped={n_skip}, errors={n_err}\n"
)
