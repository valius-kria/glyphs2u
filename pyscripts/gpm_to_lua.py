#!/usr/bin/env python3
"""Derivation B: <font>.gpm.json -> <font>.lua, the glyphs2u side.

glyphs2u tables are restricted to what Unicode can say, so each glyph resolves
to codepoints in this order:

  1. an explicit ['uni'] in the record            -> used verbatim
  2. base + properties has a precomposed character -> that character
  3. it has not                                    -> the BASE ALONE, and the
     glyph is listed in the report

Case 3 is the ceiling this whole arrangement exists to work around: the htf
side keeps the properties in mathvariant, the glyphs2u side cannot, and drops
them.  Nothing is invented -- every dropped combination is printed, and
--report writes them to a file so they can be reviewed as a set (an explicit
['uni'] in the record overrides any of them).

Writes in the glyphs2u table format, glyph names as keys, with the Unicode
name as the trailing comment.

Usage: gpm_to_lua.py <font> [--out FILE] [--report FILE] [--all]
"""
import argparse, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G
from gpm_ladder import Ladder

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("--data", default=G.DATA)
ap.add_argument("--gpm")
ap.add_argument("--out")
ap.add_argument("--report", help="write the dropped-property list here")
ap.add_argument("--builtin", help="glyphs2u/builtin-glyph-map.json -- entries it "
                                  "already covers identically are left out")
ap.add_argument("--keep-covered", action="store_true",
                help="emit those too, for comparison")
ap.add_argument("--metrics", help="default: <font>.metrics.json -- the size cuts "
                                  "are ranked from it, so without it the variation "
                                  "selectors cannot be derived")
ap.add_argument("--all", action="store_true",
                help="emit every row, the ones the consumer can already derive "
                     "from the glyph name included (implies --keep-covered)")
a = ap.parse_args()
if a.all:                       # 'every row' has to mean the covered ones too,
    a.keep_covered = True       # or the prunes below would still hide them
gpm = a.gpm or f"{a.font}.gpm.json"
out = a.out or f"{a.font}.lua"

rec = G.load(gpm)
var = G.Variants(a.data)

# The size cut of a stretchable glyph -- which of a delimiter's or accent's
# several heights this one is -- is not in the record and cannot be read off the
# codepoint: uni0302.s1 and uni0302.s2 are both U+0302.  It is written as a
# VARIATION SELECTOR after the character, and the rank it encodes is MEASURED
# from the font metrics, not taken from the '.sN' in the name: the suffix numbers
# are the font's own and need not start where the ladder does.  Ladder does the
# measuring (see gpm_ladder.py); without the metrics file there is nothing to
# measure, and a row would silently lose its selector, so say so rather than
# quietly emit a table that is wrong.
mfile = a.metrics or f"{a.font}.metrics.json"
ladder = None
if os.path.exists(mfile):
    ladder = Ladder(a.font, data=a.data, metrics=mfile)
else:
    print(f"  WARNING: {mfile} missing -- size cuts will be emitted WITHOUT their "
          f"variation selectors (run `make {mfile}`)", file=sys.stderr)

# A stem two of whose cuts measure the SAME is not a size ladder, and a selector
# would be a guess: the two glyphs would come out as one character, at one rank.
# It happens for the horizontally assembled brackets -- uni23B4.l and .r are the
# left and right halves of one top square bracket, equal in width, and uni23DE
# has .l/.m/.r/.x pieces of a curly one.  Ladder finds assembly pieces by their
# shared ADVANCE, which sorts the vertical delimiters correctly but says nothing
# about these, whose pieces share a HEIGHT instead.  Rather than invent a second
# heuristic here, the whole stem is left without selectors and named below, so
# the ones that need a rule in gpm_ladder.py are visible.
ambiguous = set()
if ladder is not None:
    for _gname in rec["glyphs"]:
        _stem = _gname.split(".")[0]
        if _stem in ambiguous:
            continue
        _sizes = [s for s, _n in ladder.cuts(_stem)]
        if len(_sizes) != len(set(_sizes)):
            ambiguous.add(_stem)

def uni_name(codes):
    parts = []
    for c in codes:
        try:
            parts.append(unicodedata.name(chr(c)))
        except ValueError:
            parts.append(f"U+{c:04X}")
    return "/".join(parts)

# What xdvipsk already knows: an entry whose name and codepoints match the
# built-in list adds nothing, and glyphs2u prunes such rows anyway
# (find-unneeded-glyphs.py).  A RENAME is the exception -- it is the whole point
# of the row, since Acrobat Distiller truncates a glyph name at the first dot
# before consulting the AGL, so a dotted name must be renamed whatever its
# codepoints are.
builtin = {}
if a.builtin:
    for name, codes in G.load(a.builtin).items():
        builtin[name] = [int(c, 16) if isinstance(c, str) else int(c) for c in codes]

# The same argument without needing a file: an ALGORITHMIC AGL name states its
# own codepoints, and xdvipsk decodes it as such, so a row that repeats them says
# nothing.  These names are deliberately absent from glyphlist_table.lua (which
# lists named glyphs only) -- their absence there is not a gap to be filled.
# This is the inverse of glyphs2u's name_from_codes() (glyph_maps.py), but
# permissive where that is canonical: it writes 'uniXXXX' for a BMP character and
# 'uXXXXXX' for an astral one, while xdvipsk reads either form for either, so a
# 'u0302' row is just as redundant as a 'uni0302' one.
#
# The name is read UP TO THE FIRST DOT.  'uni0302.s1' states U+0302 as surely as
# 'uni0302' does -- the suffix picks one cut of that character, it does not make
# the name opaque -- so a row repeating just U+0302 adds nothing and only a row
# saying something MORE does: the selector that says which cut (0302 FE01), or a
# rename, both of which differ from the stem and are kept by the tests below.
#
# This is the check against the reference: with the stem read this way, seven of
# the nine fonts in glyphs2u's lua_tables_not_needed come out with no rows at all
# -- stix-mathrm, -mathrm-bold, -mathbb, -mathbb-bold, -mathfrak, -mathfrak-bold,
# -mathtt.  Comparing the whole name instead left each of them holding rows that
# merely restated their own glyph names.
ALGORITHMIC = re.compile(r"u(?:ni(?:[0-9A-Fa-f]{4})+|[0-9A-Fa-f]{4,6})\Z")

def agl_codes(gname):
    """The codepoints the glyph name states, or None if it states none.

    Read from the part before the first dot: the suffix names a cut or a piece of
    that character, not a different character.
    """
    stem = gname.split(".")[0]
    if not ALGORITHMIC.match(stem):
        return None
    if stem.startswith("uni"):
        body = stem[3:]
        return [int(body[i:i + 4], 16) for i in range(0, len(body), 4)]
    return [int(stem[1:], 16)]

rows, dropped, unknown, covered, algorithmic, dtls, sized = [], [], [], [], [], [], []
unranked = set()
dtls_renamed = []
for gname, g in sorted(rec["glyphs"].items()):
    codes, kind, lost = G.uni_codes(rec, g, var, gname)
    if kind == "unknown":
        unknown.append(gname)
        continue
    eff = G.effective(rec, g)
    tok = G.mv_token(eff)
    # Both kinds cost properties, and the report distinguishes them: 'base' gave
    # up the whole combination, 'partial' only the axes in 'lost' -- so a partial
    # row still carries the right character, and only what 'lost' names is
    # missing from it.
    if kind in ("base", "partial") and tok:
        dropped.append((gname, g.get("base"), tok, codes, kind, lost))
    # A dotless cut is not a failed derivation but a decided one, so it is
    # counted apart: dtls-policy.json chose between the dot and the font view.
    if kind == "dtls":
        dtls.append((gname, codes, "dot" if lost else "font view"))
    # Read the rename BEFORE any prune: both prunes below ask whether the row
    # says anything Unicode does not, and a rename does -- it is the row's whole
    # purpose, not a decoration on its codepoints.  Asking afterwards dropped 20
    # rows across the stix fonts (the .s1..s5 accent sizes, uni221A.s4/.t/.x,
    # uni2305/uni2306): each is a dotted name whose value IS its base and which
    # carries no properties, so it met this prune exactly and never reached the
    # built-in one that already guards renames.
    # The size cut, when this glyph is one.  Not applied over an explicit
    # ['uni']: that is a hand decision and outranks every derivation.
    if ladder is not None and kind != "override":
        prop = ladder.proposal(gname, g)
        if prop and gname.split(".")[0] in ambiguous:
            unranked.add(gname.split(".")[0])
            prop = None
        if prop:
            codes = [int(c, 16) for c in prop["codes"]]
            kind, lost = "size", ()
            sized.append((gname, codes, prop["selector"], prop["rank"], prop["of"]))
    ren = g.get("rename")
    # A dotless cut must be published under a dot-free name, because Distiller
    # truncates at the first dot and would otherwise read 'u1D48A.dtls' as
    # 'u1D48A' -- the letter WITH its dot, which is not what the row says.  The
    # rename belongs to the same decision as the codepoint, so the policy states
    # it; where a record says something else, the policy wins and says so.
    if kind == "dtls":
        pren = var.dtls_target(g.get("base"), eff)[2]
        if pren != ren:
            dtls_renamed.append((gname, ren, pren))
        ren = pren
    # 'value equals its base, carrying no properties' is not by itself a reason
    # to drop the row.  That only follows if the CONSUMER can work the codepoints
    # out from the NAME -- which is what the two prunes below decide -- and the
    # old condition did not ask.  It cost 104 rows across the stix fonts that
    # nothing else states: the brace pieces (uni23B4.l), the .var variants, and
    # uniE059, all suffixed or private-use names that neither the built-in list
    # nor the naming algorithm can resolve.  Published stix-mathbbit has uniE059
    # at U+2274, which is exactly what this dropped.
    derivable = builtin.get(gname) == codes or agl_codes(gname) == codes
    if not a.all and kind == "base" and not tok and not ren and derivable:
        continue
    if not ren and not a.keep_covered:
        if builtin.get(gname) == codes:
            covered.append(gname)      # the built-in list already says this
            continue
        if agl_codes(gname) == codes:
            algorithmic.append(gname)  # the name itself already says it
            continue
    rows.append((gname, codes, ren))

with open(out, "w", encoding="utf-8") as f:
    f.write("return {\n")
    for gname, codes, ren in rows:
        vals = ", ".join(f"0x{c:04X}" for c in codes)
        if ren:
            vals += f", '{ren}'"
        f.write(f"  ['{gname}'] = {{ {vals} }},-- {uni_name(codes)}\n")
    f.write("  }\n")

if covered:
    print(f"  {len(covered)} row(s) left out: the built-in list already has them "
          f"with the same codepoints (--keep-covered to emit anyway)")
if algorithmic:
    print(f"  {len(algorithmic)} row(s) left out: the glyph name is algorithmic and "
          f"states those codepoints itself (--keep-covered to emit anyway)")
# Count the selectors that reach the table, by where they came from: a record's
# own ['uni'] is a hand decision and is used as it stands, so a font like
# stix-mathex -- which carries 143 of them -- would otherwise be reported as
# having none, which reads as a table that lost its size information.
n_sel = sum(1 for _g, c, _r in rows if any(0xFE00 <= x <= 0xFE0F for x in c))
if n_sel:
    print(f"  {n_sel} row(s) carry a variation selector for their size cut: "
          f"{len(sized)} ranked from {os.path.basename(mfile)}, "
          f"{n_sel - len(sized)} from an explicit ['uni'] in the record")
if unranked:
    print(f"  {len(unranked)} stem(s) left WITHOUT selectors -- two of their cuts "
          f"measure the same, so the rank would be a guess: "
          f"{', '.join(sorted(unranked))}")
if dtls:
    kept_view = sum(1 for d in dtls if d[2] == "dot")
    print(f"  {len(dtls)} dotless i/j cut(s) resolved by dtls-policy.json: "
          f"{kept_view} kept the font view and gave up the dot, "
          f"{len(dtls) - kept_view} the reverse")
    for gname, codes, gave in dtls:
        print(f"    {gname}: U+{'+'.join(f'{c:04X}' for c in codes)} (gave up the {gave})")
for gname, was, now in dtls_renamed:
    if now:
        print(f"  {gname}: published as '{now}'"
              f"{f' (the record says {was!r})' if was else ' -- a dot-free name is required for a dotless cut'}")
    else:
        print(f"  {gname}: the record's rename {was!r} is dropped -- this row states "
              f"the letter with its dot, which is what the truncated name already means")
n_partial = sum(1 for d in dropped if d[4] == "partial")
print(f"gpm_to_lua: {out}  rows={len(rows)}  "
      f"properties dropped (no unicode)={len(dropped)}"
      f"{f' ({n_partial} of them only in part)' if n_partial else ''}  "
      f"unrecognised={len(unknown)}")
for gname, base, tok, codes, kind, lost in dropped[:20]:
    f_codes = "+".join(f"{c:04X}" for c in codes)
    how = f"kept all but {'+'.join(lost)}" if kind == "partial" else "base alone"
    print(f"  {gname}: no unicode for '{base}' + {tok} -> U+{f_codes} ({how})")
if len(dropped) > 20:
    print(f"  ... {len(dropped) - 20} more")
if unknown:
    print(f"  unrecognised (base still '?'): {len(unknown)}, "
          f"e.g. {unknown[:5]} -- run the editor")

if a.report:
    with open(a.report, "w", encoding="utf-8") as f:
        for gname, base, tok, codes, kind, lost in dropped:
            f.write(f"{gname}\t{base}\t{tok}\t"
                    f"{'+'.join(f'{c:04X}' for c in codes)}\t"
                    f"{kind}\t{'+'.join(lost)}\n")
    print(f"  -> {a.report}")
