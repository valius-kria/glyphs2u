#!/usr/bin/env python3
"""Task 3: classify a font-variant comparison from the per-font rasters and
write <variant>.cmp.map.json.

Compares <plain>.pos/NNN.png vs <variant>.pos/NNN.png (page NNN = \\char NNN-1)
position by position.  For each non-blank position NOT already covered by a
variant unicode (base_fonts matches), records the verdict (differ|identical)
and an INITIAL 'wrap' decision (differ => true) as a value to confirm.

Offset: the .uni index (0-based \\char position) maps to the 1-based htf key
(cf. uni_to_html.py's int(ind)+1), so htf_key = char_code + 1.  A sanity check
warns if any matched htf key does not land on a non-blank glyph.

The verdict itself is offset-independent (same \\char compared in both fonts).
Usage: cmp_classify.py <variant> [--targets PATH] [--lua PATH]
"""
import json, sys, os, re, argparse, unicodedata as u
from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("data_dir") or os.path.dirname(HERE)      # generated maps live in data_dir (parent of pyscripts)
sys.path.insert(0, HERE)
import gpm_io as G

ap = argparse.ArgumentParser()
ap.add_argument("variant")
ap.add_argument("--data", default=DATA, help="directory of generated JSON maps")
ap.add_argument("--targets", default=None, help="htf_mfont_targets.json (default: <data>/...)")
# Through gpm_io, not a literal path: the htf table this project reads and
# rewrites lives in the OVERLAY now (mk/config.mk exports htf_path), and a
# hardcoded distribution path would have classified against the file the
# pipeline no longer loads.
ap.add_argument("--lua", default=G.HTF_LUA)
a = ap.parse_args()
# Through gpm_io's resolver, not a bare join: the tree-derived maps live under
# the branch now, so a bare <data>/ join finds nothing when data_dir is not
# exported -- which is every hand run.
a.targets = a.targets or G.map_path("htf_mfont_targets.json", a.data)

data = json.load(open(a.targets, encoding="utf-8"))
# Not read straight from comparison_pairs: a family may override the derivation
# in tfm/<supplier>/<family>/pairs, which is the only way to fix a pairing the
# declarations get wrong or miss entirely.  font_pairs.pair_of consults that
# first (searching upward from the work dir) and falls back to the derived pairs.
from font_pairs import pair_of
plain, axis = pair_of(a.variant, ".", a.data)
if not plain:
    sys.exit(f"cmp_classify: no comparison pair for '{a.variant}' "
             f"(derived none, and no 'pairs' entry above this dir)")
if not axis or "=" not in axis:
    sys.exit(f"cmp_classify: pair '{a.variant}' <- '{plain}' has no axis; "
             f"the third column must say what they differ by, e.g. weight=bold")
bf = data["base_fonts"].get(a.variant, {})
matched_keys = {int(m["pos"]) for m in bf.get("matches", []) if m.get("pos")}

# mathvariant as an ordered LIST of atomic tokens from the variant's font-level
# declaration (else the axis value).  ORDER is the canonical MathML order, so
# '-'.join(list) is a valid mathvariant (e.g. ['bold','italic']->'bold-italic',
# ['bold','script']->'bold-script').
ORDER = ["family", "weight", "variant", "style"]
NAME = {"weight:bold": "bold", "weight:light": "light", "style:italic": "italic",
        "style:oblique": "oblique", "family:sans-serif": "sans-serif",
        "family:monospace": "monospace",
        # the mathscr fonts declare small-caps at font level where 'script' is
        # meant (their letters get 'script' from their unicodes); relabel so the
        # token is a valid MathML mathvariant rather than the non-MathML
        # 'small-caps'.
        "variant:small-caps": "script"}
def vlist(d): return [NAME.get(f"{k}:{d[k]}", d[k]) for k in ORDER if k in d]
mathvariant = vlist(bf.get("font", {})) or [axis.split("=")[1]]

# Both fonts' rasters have to be HERE, in the variant's work dir.  Say so before
# comparing rather than after: a missing dir makes img() return None for every
# page, and the run then completes with every count zero and no positions --
# a map and a review page that look finished and hold nothing.  That is not a
# comparison with no differences, it is no comparison at all, and the two are
# indistinguishable in the output.
for _f in (a.variant, plain):
    _d = f"{_f}.pos"
    if not os.path.isdir(_d) or not any(n.endswith(".png") for n in os.listdir(_d)):
        sys.exit(f"cmp_classify: {_d}/ has no rasters -- both fonts are rendered "
                 f"in this dir, so run `make {_f}.pos.dvi` here first "
                 f"(comparing {a.variant} against {plain})")

def img(font, c):                       # <font>.pos/{c+1:03d}.png  (page = char+1)
    p = f"{font}.pos/{c+1:03d}.png"
    return Image.open(p).convert("L") if os.path.exists(p) else None
def ink(im): return sum(im.histogram()[:250]) if im else 0

def font_values(name):
    """htf position(int) -> the value the table holds there, for THIS font.

    The owner comes from 2024/tfm-htf-map.json, which already records it: for
    cmss10 the entry is 'cmss' by the largest-prefix rule and the OWNER of the
    characters is 'lm-rep-cmrm' at the end of its alias chain.  Asking for the
    exact font name found neither -- there is no entry called cmss10, and cmss
    holds no chars of its own -- so this returned {} and every position of the
    map came out with htf_value null and codepoint and name empty.  That is most
    fonts, and was all three pairs in cm.

    Through the map rather than walking prefix and alias here: that resolution
    is generated once and read by htf_target and gpm_init already, and a second
    copy of it would be a second thing to keep right.
    """
    owner = (G.load_map("tfm-htf-map.json", a.data).get(name) or {}).get("htf")
    if not owner:
        return {}
    chars = (G.read_htf(a.lua if os.path.exists(a.lua) else None).get(owner) or {}).get("chars") or {}
    return {int(k): v for k, v in chars.items() if v is not None}
vvals = font_values(a.variant)

def cp_name(v):
    """'U+003C', 'LESS-THAN SIGN' -- through the shared decoder.

    This used to decode the value itself and knew only '&#xHHHH;', so a value
    spelled as a NAMED entity resolved to nothing: '&lt;' and '&gt;' produced
    rows with an empty codepoint and an empty name, which read as blank lines in
    the review page.  htf tables must spell '<' and '>' that way -- the value is
    markup -- and htf_data holds 753 such values.
    """
    if not v: return "", ""
    # An <mfont> wrapper is the htf value's way of carrying a mathvariant the
    # character could not: the CHARACTER is inside it.  Reading the whole string
    # found no codepoint, so every wrapped value left the codepoint and name
    # columns blank -- 31 of cmmi's 128, and all 128 of cmbsy's, which is the
    # whole review page for a font whose values are wrapped throughout.
    inner = re.match(r'^<mfont\s+[^>]*>(.*)</mfont>$', v)
    if inner:
        v = inner.group(1)
    cp = G.to_cp(v)
    try: nm = u.name(chr(cp)) if cp else ""
    except ValueError: nm = ""
    return (f"U+{cp:04X}" if cp else ""), nm

OFFSET = 1                              # htf_key = char_code + 1
nonblank = {c for c in range(256) if ink(img(a.variant, c)) > 0}
bad = sorted(k for k in matched_keys if (k - OFFSET) not in nonblank)
if bad:
    sys.stderr.write(f"cmp_classify: WARNING {len(bad)} matched htf keys land on blank "
                     f"glyphs at offset {OFFSET} (offset may be wrong): {bad[:8]}\n")

positions = {}
n_diff = n_id = n_blank = 0
for c in range(256):
    A, B = img(plain, c), img(a.variant, c)
    if A is None or B is None: continue
    ia, ib = ink(A), ink(B)
    if ia == 0 and ib == 0: n_blank += 1; continue
    same = (A.size == B.size and ImageChops.difference(A, B).getbbox() is None)
    n_id, n_diff = (n_id + 1, n_diff) if same else (n_id, n_diff + 1)
    htf = c + OFFSET
    if htf in matched_keys: continue    # already unicode-handled
    v = vvals.get(htf); cpn, nm = cp_name(v)
    positions[str(htf)] = {"char_code": c, "htf_value": v, "codepoint": cpn,
                           "name": nm, "verdict": "identical" if same else "differ",
                           "base": v, "wrap": not same}

# Carry over a review.  The 'wrap' flags are initial values to be confirmed in
# <variant>.cmp.html, so regenerating the map -- by hand or because make thinks
# the rasters are newer -- must not throw that away.  A reviewed position is one
# whose wrap disagrees with its own verdict (rasters differ, yet the reader
# judged them the same glyph), or whose base was edited away from the htf value;
# both are carried forward wherever the fresh verdict still agrees with the old.
if os.path.exists(f"{a.variant}.cmp.map.json"):
    old = json.load(open(f"{a.variant}.cmp.map.json", encoding="utf-8"))
    kept_flip = kept_base = 0
    for htf, p in positions.items():
        o = old.get("positions", {}).get(htf)
        if not o or o.get("verdict") != p["verdict"]:
            continue                      # the comparison itself changed; re-review
        if o.get("wrap") != (o.get("verdict") == "differ"):
            p["wrap"] = o["wrap"]; kept_flip += 1
        if o.get("base") and o["base"] != o.get("htf_value"):
            p["base"] = o["base"]; kept_base += 1
    if kept_flip or kept_base:
        print(f"cmp_classify: kept {kept_flip} reviewed wrap flag(s) and "
              f"{kept_base} edited base(s) from the previous map")

out = {"font": a.variant, "plain": plain, "axis": axis, "mathvariant": mathvariant,
       "offset": OFFSET,
       "counts": {"differ": n_diff, "identical": n_id, "blank": n_blank,
                  "unicode_matched": len(matched_keys), "remainder": len(positions)},
       "positions": positions}
json.dump(out, open(f"{a.variant}.cmp.map.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"cmp_classify: {a.variant}.cmp.map.json  offset={OFFSET}  "
      f"differ={n_diff} identical={n_id} blank={n_blank} matched={len(matched_keys)} "
      f"remainder-in-map={len(positions)}")
