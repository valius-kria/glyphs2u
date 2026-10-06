#!/usr/bin/env python3
"""Which slots this font names and fills with something that is not a glyph.

Two kinds get past every emptiness test, because they DRAW:

  displaced   the base letter's outline placed left of the origin, most of it
              outside the advance width.  bbmssbx10's Acircumflex measures 808
              wide like its A and sits at x0=-539 against an advance of 881 --
              the same symbol, in the wrong place, which is what fontforge's GUI
              shows at a glance.
  overflowing ink reaching well past the advance on either side.

Whether such a slot holds a glyph is a judgement about the font, so this only
PROPOSES: --seed writes <font>.exclude with every candidate COMMENTED OUT, and
uncommenting one is the decision.  Nothing is excluded until you say so, and
nothing you have said is overwritten -- a re-seed keeps every line already there,
the way rename-stems.json and the family 'pairs' file are kept.

gpm_init reads <font>.exclude and skips those glyphs as it skips '.notdef'.

Usage:  gpm_exclude.py <font> [--seed] [--metrics FILE] [--margin 0.5]
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("--metrics", help="default: <font>.metrics.json")
ap.add_argument("--seed", action="store_true",
                help="write/extend <font>.exclude with the candidates, commented out")
ap.add_argument("--margin", type=float, default=0.5,
                help="how much of a glyph may lie outside the advance before it "
                     "is a candidate (default 0.5 -- more than half)")
a = ap.parse_args()

mf = a.metrics or f"{a.font}.metrics.json"
try:
    met = json.load(open(mf, encoding="utf-8"))["glyphs"]
except OSError:
    sys.exit(f"gpm_exclude: no {mf} -- run `make {a.font}.metrics.json` first")
if not any("x0" in g for g in met.values()):
    sys.exit(f"gpm_exclude: {mf} has no x0 -- it predates the horizontal extent "
             f"being recorded; rebuild it (`rm {mf}` and re-make)")

out = f"{a.font}.exclude"
kept, said = [], set()
if os.path.exists(out):
    for line in open(out, encoding="utf-8"):
        kept.append(line.rstrip("\n"))
        bare = line.split("#", 1)[0].strip()
        if bare:
            said.add(bare)

cands = []
for name, g in sorted(met.items()):
    x0, x1, adv = g.get("x0"), g.get("x1"), g.get("adv") or 0
    if x0 is None or x1 is None or adv <= 0:
        continue
    span = x1 - x0
    if span <= 0:
        continue
    outside = max(0.0, -x0) + max(0.0, x1 - adv)
    if outside / span > a.margin:
        cands.append((name, x0, x1, adv, outside / span))

print(f"{a.font}: {len(cands)} slot(s) with more than "
      f"{a.margin:.0%} of the glyph outside the advance width")
for name, x0, x1, adv, frac in cands:
    mark = "  (already listed)" if name in said else ""
    print(f"  {name:<16} x0={x0:<8} x1={x1:<8} adv={adv:<6} outside={frac:.0%}{mark}")

if not a.seed:
    if cands:
        print(f"  --seed writes them into {out}, commented out, for you to "
              f"uncomment the ones that are not glyphs")
    sys.exit(0)

new = [n for n, *_ in cands if n not in said and f"# {n}" not in "\n".join(kept)]
with open(out, "w", encoding="utf-8") as f:
    if not kept:
        f.write(f"# Glyphs of {a.font} that are NOT glyphs -- one name per line.\n"
                f"# gpm_init skips these as it skips '.notdef'.\n"
                f"# Seeded by gpm_exclude.py with candidates COMMENTED OUT:\n"
                f"# uncomment the ones you have looked at and rejected.\n"
                f"# Nothing here is overwritten by a re-seed.\n")
    for line in kept:
        f.write(line + "\n")
    for n in new:
        g = met[n]
        f.write(f"# {n}\t# x0={g['x0']} adv={g.get('adv')} -- outline outside "
                f"the advance width\n")
print(f"  -> {out}: {len(new)} candidate(s) added, commented out; "
      f"{len(said)} already decided")
