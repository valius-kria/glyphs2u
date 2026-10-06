#!/usr/bin/env python3
"""Step 3b: carry the paired font's properties across, minus the axis they differ by.

A bold cut of a font is the same design at a different weight: it does not
become upright, or sans-serif, or stop being small-caps.  So once the plain
sibling has been settled -- 157 style decisions confirmed by eye in
stix-mathit, say -- doing the same work again in stix-mathit-bold is answering
questions that have already been answered.

This copies the sibling's per-glyph axis values into this record, EXCEPT the one
axis the pair differs by, which is the comparison's job (gpm_cmp) and the only
thing the two fonts genuinely disagree about.

MATCHED BY POSITION, not by glyph name.  The names diverge exactly where the
characters do -- stix-mathit has 'u1D44D' where stix-mathit-bold has 'u1D468',
because italic Z and bold-italic Z are different characters -- so only 150 of
256 names are shared, while all 256 positions line up.  Position is also what
the raster comparison already assumes: it compares page N of both fonts.

NOT COPIED: 'base', and 'uni' except for size cuts.  Those say WHICH CHARACTER a
glyph is, and that does change with weight -- position N is U+1D44E in the plain
and U+1D468 in the bold.  Each font's own htf value settles them (gpm_unicode).

The exception is a SIZE CUT, where the character is the same in both fonts and
only a variation selector is added: Unicode has no bold parenthesis, so
'parenleft.s1' is 0028 FE01 in stix-mathex and in stix-mathex-bold alike.  Those
are settled one confirmation per glyph in `gpm_edit --sizes`, and stix-mathex
holds 143 of them, so not carrying them meant answering all 143 again in the bold
cut.  Carried only when the sibling's value is this glyph's own character
followed by selectors, so the character itself can never change -- see
size_cut_uni().

FILLS GAPS ONLY.  A value this glyph already carries of its own is left alone,
whatever set it: the sibling is an inference about another font, so anything this
record already says about ITSELF outranks it.  Where the two disagree it is
reported, because a conflict between what a font says about itself and what its
pair says is worth a look rather than a silent overwrite.  --overwrite replaces
values that were set automatically (never "visual"/"manual"/"name").

Inheritance is respected, not confused with a value: a glyph with no own value
for an axis is a gap even when the font level has one, which is the whole point
-- an upright integral confirmed in the plain font must be able to say so in the
bold font that declares style=italic font-wide.

The values land with status "sibling", which is deliberately not in CONFIRMED: an
inference from the other font, not something seen in this one, so any step that
looks at this font may overrule it.

Usage: gpm_sibling.py <font> [--from PATH] [--axis AX] [--overwrite] [--dry-run]
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G
from font_pairs import pair_of

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("--gpm")
ap.add_argument("--from", dest="src",
                help="the sibling's record (default: ../<plain>/<plain>.gpm.json)")
ap.add_argument("--axis", help="the axis NOT to carry (default: from the pairing)")
ap.add_argument("--overwrite", action="store_true",
                help="also replace values this font set automatically "
                     "(visual/manual/name are still never touched)")
ap.add_argument("--dry-run", action="store_true", help="report, change nothing")
a = ap.parse_args()

gpm = a.gpm or f"{a.font}.gpm.json"
plain, differs = pair_of(a.font)
if not plain and not a.src:
    sys.exit(f"gpm_sibling: no comparison pair for '{a.font}' -- name one in the "
             f"family's 'pairs' file, or give --from")
axis = a.axis or (differs.partition("=")[0] if differs else None)
if not axis:
    sys.exit(f"gpm_sibling: pair '{a.font}' <- '{plain}' does not say which axis "
             f"they differ by; add a third column to the 'pairs' entry")
if axis not in G.AXES:
    sys.exit(f"gpm_sibling: '{axis}' is not one of the axes {G.AXES}")

src = a.src or os.path.join("..", plain, f"{plain}.gpm.json")
if not os.path.exists(src):
    sys.exit(f"gpm_sibling: {src} not found -- settle {plain} first "
             f"(make -C ../{plain} {plain}.gpm.uni)")

rec, other = G.load(gpm), G.load(src)
# position is the key; a record may hold it as int or str depending on the step
by_pos = {}
for gname, g in other["glyphs"].items():
    if g.get("pos") is not None:
        by_pos[str(g["pos"])] = (gname, g)

VS = range(0xFE00, 0xFE10)              # the variation selectors, FE00..FE0F

def size_cut_uni(og, g):
    """The sibling's ['uni'] when it is THIS glyph's character plus a size cut.

    'uni' is not carried in general, and for a good reason (see the module
    docstring): it says which character a glyph is, and that changes with weight
    -- position N is U+1D44E in the plain font and U+1D468 in the bold.

    A SIZE CUT is the exception, because there the character does not change.
    Unicode has no bold parenthesis, so stix-mathex's 'parenleft.s1' and
    stix-mathex-bold's are both 0028 FE01: the same character, the same rung.
    Those values are settled by measuring, one confirmation per glyph, and
    stix-mathex holds 143 of them -- asking for all of them again in the bold cut
    is the duplicated work this whole step exists to avoid.

    Carried only when the sibling's value is exactly this glyph's own character
    followed by selectors, so which character this glyph is can never change: a
    letter, whose codepoint really does differ between the two fonts, never
    matches and is never touched.
    """
    val = og.get("uni")
    if not val:
        return None
    codes = [int(str(c), 16) if isinstance(c, str) else int(c) for c in val]
    body = [c for c in codes if c not in VS]
    if len(body) == len(codes):          # no selector: an ordinary character
        return None
    mine = G.char_at(g)
    if not mine or [ord(c) for c in mine] != body:
        return None                      # a different character -- leave it alone
    return val

carried = [ax for ax in G.AXES if ax != axis]
n_set = n_same = 0
n_uni = n_uni_same = 0
uni_kept = []
kept, differ, unmatched = [], [], []
for gname, g in rec["glyphs"].items():
    pos = g.get("pos")
    hit = by_pos.get(str(pos)) if pos is not None else None
    if not hit:
        unmatched.append(gname)
        continue
    oname, og = hit
    su = size_cut_uni(og, g)
    if su is not None:
        own = g.get("uni")
        if own is None or a.overwrite:
            g["uni"] = list(su)
            g.setdefault("status", {})["uni"] = "sibling"
            n_uni += 1
        elif own == su:
            n_uni_same += 1
        else:
            uni_kept.append((gname, own, su, g.get("status", {}).get("uni", "?")))
    for ax in carried:
        val = og.get("props", {}).get(ax)
        if not val:
            continue                      # the sibling has nothing to say either
        # The glyph's OWN value, not the effective one: inheriting the font-level
        # value is a gap to fill, and filling it is exactly how an upright glyph
        # states itself inside a font that declares style=italic font-wide.
        own = g.get("props", {}).get(ax)
        if own is not None and not a.overwrite:
            if own == val:
                n_same += 1
            else:
                differ.append((gname, ax, own,
                               g.get("status", {}).get(ax, "?"), val, oname))
            continue
        r = G.set_axis(g, ax, val, "sibling")
        if r == "set":
            n_set += 1
        elif r == "same":
            n_same += 1
        else:                             # confirmed here already: leave it
            kept.append((gname, ax, g["props"].get(ax), val, oname))

if not a.dry_run:
    G.save(rec, gpm)

undet = sum(1 for g in rec["glyphs"].values() if G.unset_axes(rec, g))
print(f"gpm_sibling: {gpm}{' (dry run)' if a.dry_run else ''}  from {src}\n"
      f"  carried {', '.join(carried)} (not '{axis}' -- that is what the "
      f"comparison settles)\n"
      f"  filled={n_set}  already agreed={n_same}  "
      f"kept (this font already said so)={len(differ) + len(kept)}  "
      f"no counterpart={len(unmatched)}\n"
      f"  {undet} glyph(s) still have axes nothing has spoken about")
if n_uni or n_uni_same or uni_kept:
    print(f"  size cuts: {n_uni} ['uni'] carried across (same character, same "
          f"rung), {n_uni_same} already agreed, {len(uni_kept)} kept")
    for gname, own, want, st in uni_kept[:5]:
        f_own = "+".join(str(c) for c in own); f_want = "+".join(str(c) for c in want)
        print(f"  kept {gname} uni={f_own} ({st}) -- sibling says {f_want}")
    if len(uni_kept) > 5:
        print(f"  ... {len(uni_kept) - 5} more; --overwrite to take the sibling's")
for gname, ax, have, st, want, oname in differ[:10]:
    print(f"  kept {gname} {ax}={have} ({st}) -- sibling {oname} says {want}")
if len(differ) > 10:
    print(f"  ... {len(differ) - 10} more disagreement(s); --overwrite to take "
          f"the sibling's value where this font's was automatic")
for gname, ax, have, want, oname in kept[:5]:
    print(f"  kept confirmed {gname} {ax}={have} (sibling {oname} says {want})")
if unmatched:
    print(f"  no counterpart at that position: {len(unmatched)}, "
          f"e.g. {unmatched[:5]}")
