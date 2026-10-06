#!/usr/bin/env python3
"""Step 2: fill base + axes from the Unicode value already assigned.

Whatever a glyph's position currently renders as -- the codepoint in the htf
table, an <mfont> already written there, or the codepoints a glyphs2u table
gives for the same glyph name -- says something about the glyph without anyone
looking at it:

  a precomposed variant (MATHEMATICAL SANS-SERIF ITALIC SMALL A) decomposes,
  through char_to_properties.json, into base 'a' + family=sans-serif +
  style=italic;
  a plain character (LEFT ARROW WITH CIRCLED PLUS) gives the base only -- it
  says nothing about weight or style, which stay for the comparison and the
  visual steps to settle.

This settles far less than it looks: a base character for nearly every glyph,
but properties only where the assigned codepoint is a precomposed variant --
in practice the latin and greek alphabets.  Operators, delimiters and symbols
come out with a base and no properties at all, which is what the font-pair
comparison and the editor are for.  Nothing here is ever final: every value it
writes is overwritable by those later steps.

Three sources, in this order of authority:

  the htf value    what the htf table renders at that position -- the richest,
                   because a variant codepoint carries the properties with it.
  --lua / --lua-dir  the font's glyphs2u table, for glyphs the htf table says
                   nothing about.  Disagreements with the htf value are
                   reported, not resolved.
  --builtin        the AGL list xdvipsk carries (glyphs2u's
                   builtin-glyph-map.json).  Last, and base-only: it is
                   font-blind -- 'A' is plain A there even in a fraktur font,
                   which is exactly why glyphs2u needs no table for
                   stix-mathfrak.  Private-use values are not taken as a base.

Axes confirmed by eye or by hand ("visual"/"manual") are never overwritten;
each such disagreement is reported.

Usage: gpm_unicode.py <font> [--lua FILE | --lua-dir DIR] [--builtin FILE]
"""
import argparse, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G
import glyphs2u_config as g2u_cfg

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("--data", default=G.DATA)
ap.add_argument("--gpm")
ap.add_argument("--lua", help="a glyphs2u <font>.lua table")
ap.add_argument("--lua-dir", help="glyphs2u working dir; finds <pfb stem>.lua in it")
ap.add_argument("--builtin", help="glyph-name -> codepoints fallback "
                                  "(glyphs2u/builtin-glyph-map.json)")
a = ap.parse_args()
gpm = a.gpm or f"{a.font}.gpm.json"
rec = G.load(gpm)
var = G.Variants(a.data)

MFONT = re.compile(r'<mfont\s+mathvariant="([^"]+)">(.*)</mfont>', re.S)

def from_chars(s):
    """A decoded value -> (base, {axis: value}, uni).

    A variation selector is split off: it says which SIZE cut of a stretchy
    symbol this is (radical, brace, wide accent, big operator), not which
    character.  The base keeps the plain character and the whole sequence goes
    to ['uni'], so the glyphs2u side can emit it and the htf side need not.
    """
    core, had_sel = G.split_selectors(s)
    uni = ([f"0x{ord(c):04X}" for c in s] if had_sel or len(core) > 1 else None)
    if len(core) == 1:
        base, props = var.decompose(core)
    else:                       # a composed sequence (base + combining mark)
        base, props = core, {}
    return base, props, uni

def props_from_tokens(tokens):
    props = {}
    for t in tokens:
        ax = G.TOKEN_AXIS.get(t)
        if ax:
            props[ax] = t
    return props

def from_value(value):
    """htf value -> (base, {axis: value}, uni) or None if it says nothing.

    'uni' is set only for a value that is a codepoint SEQUENCE (a base plus a
    variation selector or a combining mark): no single character stands for it,
    so the sequence itself is what the glyphs2u side must emit.
    """
    m = MFONT.fullmatch(value.strip())
    if m:                                   # already converted by a former run
        base = G.to_chars(m.group(2)) or m.group(2)
        return base, props_from_tokens(m.group(1).split("-")), None
    s = G.to_chars(value)
    if s is None:
        return None
    if any(G.is_pua(ord(c)) for c in s):
        # the htf table has the font's own slot number here, not a character;
        # glyphs2u often has the real decomposition (U+E004 -> wave arrow +
        # combining long solidus overlay), so let the lua table answer instead
        return None
    return from_chars(s)

def find_lua():
    """The glyphs2u table for this font: named after the pfb, not the tfm.

    Asked of the family's config.py rather than guessed from the directory
    listing, because a missing '<font>.lua' has three quite different meanings
    and only one of them is a problem: the table may be a COPY of another
    (stix-mathex.lua serves stix-mathex-bold, which has no file of its own), no
    table may be WANTED (every glyph named uXXXX, which xdvipsk decodes by the
    AGL algorithmic rule), or one may be expected and absent.  Guessing treated
    all three as the same silence.
    """
    if a.lua:
        return a.lua
    if not a.lua_dir:
        return None
    stem = os.path.splitext(os.path.basename(rec.get("pfb") or a.font))[0]
    p, why = g2u_cfg.table_for(stem, a.lua_dir)
    if why != "own":
        print(f"  glyphs2u table for {stem}: {why}"
              + (f" -> {os.path.basename(p)}" if p else ""),
              file=sys.stderr if "missing" in why else sys.stdout)
    return p

lua_file = find_lua()
lua_entries = G.read_lua_entries(lua_file) if lua_file else {}
lua = {k: v["codes"] for k, v in lua_entries.items() if v["codes"]}

builtin = {}
if a.builtin:
    # a builtin entry pointing into a private-use area (small caps, oldstyle
    # figures, ...) is no more informative than '?'
    for name, codes in G.load(a.builtin).items():
        cps = [int(c, 16) if isinstance(c, str) else int(c) for c in codes]
        if cps and not any(G.is_pua(c) for c in cps):
            builtin[name] = cps

n_base = n_axis = n_plain = n_lua = n_builtin = n_ren = 0
n_uni_cleared = 0
kept, differ = [], []
def from_codes(codes):
    return from_chars("".join(chr(c) for c in codes))

for gname, g in rec["glyphs"].items():
    src, found = None, None
    value = g.get("htf_value")
    if value:
        found, src = from_value(value), "unicode"
    if found is None and gname in lua:        # glyphs2u investigated this one
        found, src = from_codes(lua[gname]), "lua"
        n_lua += 1
    if found is None and gname in builtin:    # generic AGL: a base, nothing more
        found, src = (from_codes(builtin[gname])[0], {}, None), "builtin"
        n_builtin += 1
    if found is None:
        continue
    # informational: the two sides of the same glyph, where both have an opinion
    if value and gname in lua:
        want = "".join(chr(c) for c in lua[gname])
        have = G.to_chars(value)
        if have is not None and have != want:
            differ.append((gname, have, want))
    base, props, uni = found
    if uni:
        G.set_uni(g, uni, src)
    elif g.get("uni") and g.get("status", {}).get("uni") == src:
        # This value needs no explicit sequence, and the one on record came from
        # THIS step -- so refresh it away rather than leave it standing.  Without
        # this a corrected reading is only half applied: '&gt;' used to decode
        # as the four letters '&','g','t',';' and left uni=[0x26,0x67,0x74,0x3B]
        # behind, which a re-run would keep because it now sets no uni at all.
        # A sequence any OTHER step arrived at is left alone.
        g.pop("uni", None)
        g.get("status", {}).pop("uni", None)
        n_uni_cleared += 1
    # xdvipsk renames a dotted glyph before Distiller truncates the name at the
    # dot, so the rename is part of what the table has to say -- carry it into
    # the record rather than leaving it only in the lua file
    ren = (lua_entries.get(gname) or {}).get("rename")
    if ren and not g.get("rename"):
        g["rename"] = ren
        n_ren += 1
    if not props:
        n_plain += 1
    r = G.set_base(g, base, src)
    n_base += (r == "set")
    if r == "kept":
        kept.append((gname, "base", g.get("base"), base))
    for ax, v in props.items():
        r = G.set_axis(g, ax, v, src)
        n_axis += (r == "set")
        if r == "kept":
            kept.append((gname, ax, g["props"].get(ax), v))

G.save(rec, gpm)
open_n = sum(1 for g in rec["glyphs"].values() if G.is_open(rec, g))
undetermined = sum(1 for g in rec["glyphs"].values() if G.unset_axes(rec, g))
if n_uni_cleared:
    print(f"  {n_uni_cleared} stale ['uni'] sequence(s) cleared "
          f"(this step had set them from a value it now reads differently)")
print(f"gpm_unicode: {gpm}  base set={n_base}  axes set={n_axis}  "
      f"plain-char (no properties implied)={n_plain}  still open={open_n}")
if lua_file:
    print(f"  from {os.path.basename(lua_file)}: {n_lua} glyph(s)"
          + (f", {n_ren} rename(s) carried over" if n_ren else ""))
if builtin:
    print(f"  from the builtin AGL list: {n_builtin} glyph(s) (base only)")
print(f"  {undetermined} glyph(s) have axes nothing has spoken about yet -- "
      f"the comparison and the editor settle those")
for gname, ax, have, want in kept:
    print(f"  kept confirmed {gname} {ax}={have} (unicode says {want})")
for gname, have, want in differ[:10]:
    print(f"  differs: {gname} htf={have!r} glyphs2u={want!r}")
if len(differ) > 10:
    print(f"  ... {len(differ) - 10} more disagreement(s)")
