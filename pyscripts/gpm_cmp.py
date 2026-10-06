#!/usr/bin/env python3
"""Step 3: merge a font-pair raster comparison into one axis of the record.

<font>.cmp.map.json (cmp_classify.py) compares this font against the sibling
that differs by exactly one property -- stix-mathcal-bold vs stix-mathcal,
axis 'weight=bold'.  A position whose two rasters differ really carries that
property; a position whose rasters are identical does not, whatever the
font-level declaration claims.  That is the whole point of the comparison: it
settles ONE axis per glyph, mechanically, for every position at once.

Positions the comparison left out (already unicode-matched) keep what
gpm_unicode gave them.  Confirmed values are never overwritten.

Review the verdicts in <font>.cmp.html before running this; the html is built
from the same map, and its `wrap` flags can be edited by hand first.

Usage: gpm_cmp.py <font> [--map FILE] [--gpm FILE]
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("--map")
ap.add_argument("--gpm")
a = ap.parse_args()
gpm = a.gpm or f"{a.font}.gpm.json"
mapf = a.map or f"{a.font}.cmp.map.json"

rec = G.load(gpm)
m = G.load(mapf)

axis, _, value = m["axis"].partition("=")
if axis not in G.AXES:
    sys.exit(f"gpm_cmp: '{m['axis']}' is not one of the axes {G.AXES}")

by_pos = {g["pos"]: (name, g) for name, g in rec["glyphs"].items() if "pos" in g}

n_var = n_norm = n_same = n_confirmed = 0
kept, missing = [], []
for pos_s, p in m["positions"].items():
    hit = by_pos.get(int(pos_s))
    if hit is None:
        missing.append(pos_s)
        continue
    gname, g = hit
    # 'wrap' is the reviewable flag in the map (differ => true initially); the
    # html lets it be corrected by hand, so honour it over the raw verdict.
    carries = bool(p.get("wrap", p.get("verdict") == "differ"))
    want = value if carries else "normal"
    r = G.set_axis(g, axis, want, "cmp")
    if r == "kept":
        kept.append((gname, g["props"].get(axis), want))
    elif r == "set":
        n_var, n_norm = (n_var + 1, n_norm) if carries else (n_var, n_norm + 1)
    else:
        # 'same': the value is already what the rasters say, so set_axis returned
        # early and left the OLD provenance -- a position the comparison measured
        # stayed labelled as whatever had guessed it first, and no re-run could
        # correct that, the values still agreeing.  The comparison has looked at
        # every position in its map, agreement included, so 'cmp' is the truthful
        # provenance -- EXCEPT where the value was confirmed by eye or by hand.
        # set_axis checks CONFIRMED only on the disagreement path, so agreement
        # with a 'visual' value arrives here too, and stamping it would replace a
        # stronger provenance with a weaker one: 'visual' says a person looked at
        # this very glyph, which outranks 'measured' for the same answer.
        cur = g.get("status", {}).get(axis)
        if cur in G.CONFIRMED:
            n_confirmed += 1
        elif cur != "cmp":
            g.setdefault("status", {})[axis] = "cmp"
            n_same += 1

G.save(rec, gpm)
open_n = sum(1 for g in rec["glyphs"].values() if G.is_open(rec, g))
print(f"gpm_cmp: {gpm}  axis={axis}  {value}={n_var}  normal={n_norm}  "
      f"already agreed={n_same}  still open={open_n}")
if n_same:
    print(f"  {n_same} position(s) already held the measured value; their "
          f"provenance is now 'cmp' -- measured, not merely inherited")
if n_confirmed:
    print(f"  {n_confirmed} position(s) were already confirmed by eye or by hand "
          f"and the rasters agree -- provenance left as it was, not weakened")
if missing:
    print(f"  {len(missing)} compared position(s) not in the record "
          f"(e.g. {missing[:5]}) -- encoding and htf table disagree?")
for gname, have, want in kept:
    print(f"  kept confirmed {gname} {axis}={have} (comparison says {want})")
