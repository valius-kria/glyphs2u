#!/usr/bin/env python3
"""Report the size ladder of a font's stretchable glyphs, from font metrics.

A stretchable symbol -- delimiter, radical, big operator, wide accent -- is cut
at several sizes, and which cut a glyph is cannot be read off its codepoint:
uni222B and uni222B.dsp are both U+222B.  What does say it is how tall the
glyph is, so this measures that, from <font>.metrics.json (real bounding boxes)
rather than from the exported images, whose sizes are not in proportion.

Glyphs are grouped by STEM -- the name up to the first dot -- and the cuts of
one stem are ranked by height.  Rank is what transfers: absolute heights do not
compare between fonts, and even within one family the ladders start at
different rungs.

The canonical shape, for reference (Computer Modern, em=1000):

  cmr10   parenleft      1.00 em   text size
  cmex10  parenleftbig   1.20 em   FE01     the ladder is ARITHMETIC:
          parenleftBig   1.80 em   FE02     1.2, 1.8, 2.4, 3.0 = 2,3,4,5 x 0.6
          parenleftbigg  2.40 em   FE03
          parenleftBigg  3.00 em   FE04
          parenleftex    0.62 em   the extension piece -- the module itself

so 'big' is only a fifth taller than a text parenthesis.  stix-mathex repeats
it 2.5% larger (2,3,4,5 x 0.615 em).  stix-mathcal is a different thing: its
.sm/base/.dsp integrals are 0.88/1.14/2.27 em -- script, text and display
STYLE sizes of one character, not a growth ladder.

Only stems whose base character can expand at all are reported: that set comes
from MathML's operator dictionary via stretchy-chars.json (delimiters, accents,
big operators), not from measuring.  It is what keeps a dotless letter beside
its dotted form out of the size analysis -- u1D5C2.dtls shares an advance with
u1D5C2 and is shorter, which is the signature of an extension piece, but 'i'
is not a stretchable character so the question never arises.

Assembly pieces -- the top, extension and bottom a renderer stacks to build a
delimiter of any height -- are found by their shared ADVANCE width, not by
height: they are set on one advance so they stack in a column.  stix-mathex's
radical bottom is as tall as its first size cut, so height alone would rank it
as one.  The suffixes correspond to the built-in table's names: .x is 'ex'
(extension), .t is 'tp' (top), and the radical's .s4 is 'bt' (bottom).

Usage: gpm_sizes.py <font> [--all] [--metrics FILE]
"""
import argparse, collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G
from gpm_ladder import Ladder

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("--data", default=G.DATA)
ap.add_argument("--metrics", help="default: <font>.metrics.json")
ap.add_argument("--gpm", help="default: <font>.gpm.json (for the htf values)")
ap.add_argument("--all", action="store_true", help="list every stem, not just multi-cut ones")
a = ap.parse_args()
mf = a.metrics or f"{a.font}.metrics.json"
if not os.path.exists(mf):
    sys.exit(f"gpm_sizes: {mf} missing -- run `make {mf}` (fontforge)")
m = G.load(mf)
em, gm = m["em"], m["glyphs"]
L = Ladder(a.font, data=a.data, metrics=mf)

rec = None
gpm = a.gpm or f"{a.font}.gpm.json"
if os.path.exists(gpm):
    rec = G.load(gpm)

# Which characters can have a size cut at all -- from MathML's operator
# dictionary, not from measuring.  Everything outside this set is some other
# kind of multi-glyph stem (a dotless letter beside its dotted form, a variant
# shape) and has no size question to ask.

def stem_base(stem, names):
    """The character this stem's glyphs are cuts of, from the record."""
    if not rec:
        return None
    for n in [stem] + sorted(names):
        g = rec["glyphs"].get(n)
        if g and G.has_base(g) and g.get("base"):
            return g["base"][0]
    return None

def expandable(stem, names):
    if not L.stretchy or not rec:
        return True, None
    b = stem_base(stem, names)
    if b is None:
        return False, "base unknown"
    f = L.flags(b)
    return (True, f) if f else (False, f"{b!r} does not expand")

fam = collections.defaultdict(list)
for name, info in gm.items():
    fam[name.split(".")[0]].append((info["h_em"], name))


def measure(stem, name):
    """What the ladder ranks on -- its axis, not the height."""
    return L.size(name)


print(f"{m['font']}  em={em}   {len(gm)} glyphs, {len(fam)} stems")
multi = {k: v for k, v in fam.items() if len(v) > 1}
keep, skipped = {}, []
for stem, members in multi.items():
    ok, why = expandable(stem, [n for _, n in members])
    (keep.setdefault(stem, why) if ok else skipped.append((stem, why)))
print(f"{len(multi)} stem(s) with more than one cut; "
      f"{len(keep)} of a character that expands\n")
print("flags: s=stretchy L=largeop a=accent f=fence y=symmetric"
      "  |  +=added by hand  c=built from pieces, no ladder\n")
print(f"{'stem':14} {'flags':7} {'ax':3} {'cuts as height x width in em':50} pieces")
pieces_all = []
for stem in sorted(keep if not a.all else multi):
    ax = L.axis(stem)
    pieces = sorted(L.assembly(stem))
    ladder = sorted((measure(stem, n), n) for _, n in fam[stem] if n not in pieces)
    pieces_all += pieces
    # ordered by the ladder's axis, but shown as the real height x width
    txt = "  ".join(f"{n.split('.')[-1] if '.' in n else '(base)'}:"
                    f"{gm[n]['h_em']:.2f}x{gm[n]['w']/em:.2f}" for _, n in ladder)
    print(f"  {stem:12} {str(keep.get(stem) or '-'):7} {ax:3} {txt:50} "
          f"{' '.join(pieces) if pieces else ''}")

if skipped:
    print(f"\n{len(skipped)} multi-glyph stem(s) that are not a stretchable "
          f"character -- no size question to ask:")
    for stem, why in sorted(skipped):
        print(f"    {stem:14} {why}")

if pieces_all:
    print(f"\n{len(pieces_all)} assembly piece(s) -- parts of a construction, "
          f"not size cuts (shared advance width):\n  " + " ".join(sorted(pieces_all)))

# what the ladder steps look like, to compare against the 0.6 em module
steps = collections.Counter()
for stem in keep:
    pieces = L.assembly(stem)
    vs = sorted(measure(stem, n) for _, n in fam[stem] if n not in pieces)
    for i in range(1, len(vs)):
        d = round(vs[i] - vs[i-1], 2)
        if d:                      # 0 = the slanted/upright pair, not a step
            steps[d] += 1
if steps:
    print("\nstep sizes between consecutive cuts (em):",
          ", ".join(f"{s}x{n}" for s, n in steps.most_common(8)))
