#!/usr/bin/env python3
"""Set values in a glyph property record from the command line.

The editor is for deciding things by looking at glyphs; this is for writing
down an answer already known -- most often the font-level family that nothing
declares but the whole font has (stix-mathbb is double-struck, stix-mathtt is
monospace), which otherwise has to be clicked once per font.

  gpm_set.py stix-mathbb family=double-struck --rest  # font level + exceptions
  gpm_set.py stix-mathcal family=script weight=normal
  gpm_set.py stix-mathex --glyph uni222B weight=bold  # one glyph
  gpm_set.py stix-mathbb --show                       # what is set and whence

--rest is what makes a font-level property safe to state.  Setting
family=double-struck alone would have every glyph inherit it, symbols included
-- and in these fonts the property belongs to the alphabet only, the
non-alphabetical symbols being spread across the family to cover what maths
needs.  --rest writes family=normal onto every glyph that has no value of its
own, so the font-level property covers the letters (which got theirs from their
codepoints) and the symbols say plainly that they do not have it.

Explicit assignments land with status "manual" -- a human said so, so the
automatic steps leave them alone.  The --rest fills land with status "default":
a blanket assumption, which a later comparison or a look at the glyph may still
correct.  --status overrides both.
"""
import argparse, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("assignments", nargs="*", metavar="axis=value")
ap.add_argument("--gpm")
ap.add_argument("--glyph", help="set on this glyph instead of the font level")
ap.add_argument("--pos", type=int,
                help="same, naming the glyph by its htf position -- what the "
                     "comparison and review pages show")
ap.add_argument("--status", default="manual", help="provenance to record")
ap.add_argument("--base", metavar="CHAR",
                help="set the glyph's base character -- the character it IS, "
                     "before font properties.  Needs --glyph or --pos.  Accepts "
                     "the character itself or codepoints (0x03F5)")
ap.add_argument("--rename", metavar="NAME",
                help="set the glyph's published name (empty string removes it).  "
                     "Needs --glyph or --pos: a rename belongs to one glyph.  It "
                     "is a hand fact like any other here -- the name a dotted "
                     "glyph must be published under, because Distiller truncates "
                     "at the first dot")
ap.add_argument("--rest", action="store_true",
                help="also mark every glyph with no value of its own for these "
                     "axes as 'normal' (status 'default'), so the font-level "
                     "value covers only the glyphs that really carry it")
ap.add_argument("--rest-status", default="default", help="provenance for --rest fills")
ap.add_argument("--reviewed", nargs="?", const="gpm.html", metavar="WHAT",
                help="record at FONT LEVEL that this record has been read and "
                     "found right -- optionally naming what was read (default "
                     "'gpm.html').  Checking a whole font from the review page "
                     "is one act, so it is written down once here rather than "
                     "promoted onto every glyph's status.  It changes no value: "
                     "it says the record was looked over, so it need not be "
                     "looked over again.  Repeat with --except to note the rows "
                     "that were NOT right.")
ap.add_argument("--except", dest="skip", default="",
                help="with --reviewed: positions the review found wrong, so the "
                     "note says what is still open")
ap.add_argument("--show", action="store_true", help="print the record's properties")
a = ap.parse_args()
gpm = a.gpm or f"{a.font}.gpm.json"
rec = G.load(gpm)

if a.show:
    print(f"{a.font}: font level")
    for ax in G.AXES:
        print(f"  {ax:8} = {rec.get('props', {}).get(ax, 'normal'):14} "
              f"({rec.get('status', {}).get(ax, G.UNKNOWN)})")
    n = len(rec["glyphs"])
    own = sum(1 for g in rec["glyphs"].values() if g.get("props"))
    print(f"  {own} of {n} glyph(s) carry properties of their own")
    rv = rec.get("reviewed")
    if rv:
        print(f"  reviewed: {rv.get('what')}"
              + (f"   open: {rv['open']}" if rv.get("open") else "")
              + (f"   ({rv['note']})" if rv.get("note") else ""))
    else:
        print("  reviewed: not yet -- `gpm_set.py <font> --reviewed` after "
              "reading <font>.gpm.html")
    sys.exit(0)

if a.reviewed:
    rv = {"what": a.reviewed}
    if a.skip:
        rv["open"] = sorted(G.parse_positions(a.skip))
    rec["reviewed"] = rv
    G.save(rec, gpm)
    print(f"gpm_set: {gpm} font level  reviewed = {rv}")
    if not a.assignments:
        sys.exit(0)

if not a.assignments and a.rename is None and a.base is None:
    sys.exit("gpm_set: nothing to set (give axis=value, --base, --rename, "
             "--reviewed, or --show)")

if a.pos is not None and not a.glyph:
    hit = [n for n, g in rec["glyphs"].items()
           if g.get("pos") == a.pos or a.pos in [x["pos"] for x in g.get("alt", [])]]
    if not hit:
        sys.exit(f"gpm_set: no glyph at position {a.pos} in {gpm}")
    a.glyph = hit[0]

if a.rename is not None and not a.glyph and a.pos is None:
    sys.exit("gpm_set: --rename needs --glyph or --pos -- a rename is per-glyph")
if a.base is not None and not a.glyph and a.pos is None:
    sys.exit("gpm_set: --base needs --glyph or --pos -- a base is per-glyph")

target = rec
if a.glyph:
    if a.glyph not in rec["glyphs"]:
        sys.exit(f"gpm_set: no glyph '{a.glyph}' in {gpm}")
    target = rec["glyphs"][a.glyph]

if a.base is not None:
    # Read either the character or its codepoints, as the editor does: a base is
    # usually typed, but a Greek symbol form is easier to name by number.
    # Either the character itself or its codepoint: a Greek symbol form is far
    # easier to name by number than to type, and mistaking one for the other is
    # the whole reason a base needs fixing here.
    val = a.base
    if len(val) > 1 and re.fullmatch(r"(?:0[xX]|[uU]\+)?[0-9A-Fa-f]{4,6}", val):
        val = chr(int(re.sub(r"^(?:0[xX]|[uU]\+)", "", val), 16))
    was = target.get("base", "(unset)")
    src = target.get("status", {}).get("base", G.UNKNOWN)
    target["base"] = val
    target.setdefault("status", {})["base"] = a.status
    print(f"gpm_set: glyph {a.glyph} base = {val!r} "
          f"(U+{ord(val[0]):04X}) ({a.status})   was {was!r} ({src})")

if a.rename is not None:
    was = target.get("rename", "(unset)")
    src = target.get("status", {}).get("rename", G.UNKNOWN)
    if a.rename == "":
        target.pop("rename", None)
        target.get("status", {}).pop("rename", None)
        print(f"gpm_set: glyph {a.glyph} rename removed   was {was} ({src})")
    else:
        target["rename"] = a.rename
        target.setdefault("status", {})["rename"] = a.status
        print(f"gpm_set: glyph {a.glyph} rename = {a.rename} ({a.status})   "
              f"was {was} ({src})")

for item in a.assignments:
    ax, _, val = item.partition("=")
    if ax not in G.AXES:
        sys.exit(f"gpm_set: '{ax}' is not an axis {G.AXES}")
    if val not in G.AXIS_VALUES[ax]:
        sys.exit(f"gpm_set: '{val}' is not a {ax} value {G.AXIS_VALUES[ax]}")
    was = target.get("props", {}).get(ax, "(unset)")
    src = target.get("status", {}).get(ax, G.UNKNOWN)
    target.setdefault("props", {})[ax] = val
    target.setdefault("status", {})[ax] = a.status
    where = f"glyph {a.glyph}" if a.glyph else "font level"
    print(f"gpm_set: {where} {ax} = {val} ({a.status})   was {was} ({src})")

    if a.rest and not a.glyph:
        # every glyph that has not been given this axis says 'normal' outright,
        # instead of quietly inheriting the font-level value
        filled = carried = 0
        for g in rec["glyphs"].values():
            if ax in g.get("props", {}):
                carried += 1
                continue
            g.setdefault("props", {})[ax] = "normal"
            g.setdefault("status", {})[ax] = a.rest_status
            filled += 1
        print(f"  --rest: {filled} glyph(s) marked {ax}=normal "
              f"({a.rest_status}); {carried} already carried a value of "
              f"their own")

G.save(rec, gpm)
tok = G.mv_token({ax: rec.get("props", {}).get(ax, "normal") for ax in G.AXES})
print(f"-> {gpm}   font-level mathvariant now: {tok or '(none)'}"
      + ("" if G.mv_valid(tok) else "   WARNING: no MathML token for this"))
