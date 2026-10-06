#!/usr/bin/env python3
"""List the fonts of a family worth building a glyph property record for.

A font qualifies when it owns its ['chars'] in htf_data.lua (an alias font
shares another's table, so the htf side has to go through the owner) and
psfonts.map knows a pfb for it (no pfb, no glyph names, no encoding).

  gpm_family.py stix              # names matching 'stix'
  gpm_family.py stix --all        # include the alias fonts too
  gpm_family.py stix --why        # say why each candidate was left out

Usage from the top Makefile:  make gpm-seed FAMILY=stix
"""
import argparse, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpm_io as G

ap = argparse.ArgumentParser()
ap.add_argument("pattern", help="regular expression matched against the htf name")
ap.add_argument("--data", default=G.DATA)
ap.add_argument("--htf-lua", default=None, help="htf_data.lua to read")
ap.add_argument("--all", action="store_true", help="include fonts without own chars")
ap.add_argument("--why", action="store_true", help="report the ones left out")
a = ap.parse_args()

# Both tables by default, not htf_data.lua alone: bbm and its seven cuts are
# defined only in user_htf.lua, so restricting the read to htf_data.lua made
# `make gpm-seed FAMILY=bbm` expand to nothing at all and say nothing about why.
# read_htf_lua() with no argument reads htf_data.lua then user_htf.lua, which is
# the order luarealchar loads them in.
htf = G.read_htf(a.htf_lua)
pfbs = G.load_map("psfonts-map-tfm-data.json", a.data)
rx = re.compile(a.pattern)

# An htf name that is not itself a tfm.  bbm is served by bbm10, bbm12 and eight
# more sizes; there is no bbm.tfm and so no pfb under that name, and matching htf
# names alone rejected the whole family with "no pfb in psfonts.map".  So where a
# matched htf name has no pfb, the tfms that RESOLVE to it are looked up in
# tfm-htf-map.json and ONE is taken as the representative.
#
# One per entry, not one per size, because the sizes of a cut differ in metrics
# and not in glyph properties: their records would come out the same, and a
# record per size is eight copies of one decision to keep in step by hand.
#
# The 10pt cut is preferred.  There is no design-size-neutral tfm -- picking the
# shortest name gave bbm5 and bbmsl8, the SMALLEST sizes, which is neither the
# reference size nor what the work dirs already here use (bbm10, bbmss10,
# bbmtt10).  10 is the reference design size throughout TeX, so it is the one to
# open and look at.  Falls back to the shortest name where no 10pt cut exists
# (bbmssbx10 has no siblings at all), and --why names the choice either way.
try:
    t2h = G.load_map("tfm-htf-map.json", a.data)
except (OSError, ValueError):
    t2h = {}
by_entry = {}
for tfm, v in t2h.items():
    e = v.get("entry")
    if e and pfbs.get(tfm, {}).get("pfb"):
        by_entry.setdefault(e, []).append(tfm)

def represent(name):
    """A tfm standing for this htf entry, or None.  The 10pt cut for choice.

    10 is the basic design size, so it is what one opens to look at a cut.  Where
    a cut has no 10pt tfm the SMALLEST size present is taken -- some fonts go no
    higher than 8 -- and the size is read as a number, not off the length of the
    name, which had ranked bbmsl12 against bbmsl8 by how many characters they
    spell rather than by how big they are.
    """
    def size(t):
        m = re.search(r"(\d+)$", t)
        return int(m.group(1)) if m else 10 ** 6
    cands = sorted(by_entry.get(name, []), key=lambda t: (size(t) != 10, size(t), t))
    return cands[0] if cands else None

take, skip, stood = [], [], []
for name in sorted(htf):
    if not rx.search(name):
        continue
    own = bool(htf[name].get("chars"))
    pfb = pfbs.get(name, {}).get("pfb")
    if not pfb:
        rep = represent(name)
        if rep:
            # The alias test is about the ENTRY, which is what owns chars or does
            # not; the representative only says which tfm to open.
            if not own and not a.all:
                skip.append((name, f"aliases {htf[name].get('alias')} -- "
                                   f"build that one (its tfm is {rep})"))
            else:
                take.append(rep)
                stood.append((name, rep, len(by_entry.get(name, []))))
        else:
            skip.append((name, "no pfb in psfonts.map, and no tfm resolves to it"))
    elif not own and not a.all:
        skip.append((name, f"aliases {htf[name].get('alias')} -- build that one"))
    else:
        take.append(name)

print(" ".join(take))
if a.why:
    for name, rep, n in stood:
        print(f"# {name}: no tfm of that name -- taking {rep} to stand for it "
              f"({n} size(s) share the entry)", file=sys.stderr)
    for name, why in skip:
        print(f"# {name}: {why}", file=sys.stderr)
