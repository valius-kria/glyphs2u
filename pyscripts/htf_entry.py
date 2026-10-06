#!/usr/bin/env python3
"""The htf entry as it should stand in the table -- an ['alias'] where that says
everything, a full ['chars'] table where it does not.

An alias is a CONCLUSION, not a starting point.  luarealchar lets one entry lend
its characters to another (and only its characters: the declaration is read from
the entry the font resolves to, never through the alias -- vtex-dist c6836522d),
so a cut whose characters are identical to another's needs no table of its own,
only its own ['font'].  Whether they ARE identical is a question with an answer,
and this step asks it before writing anything.

The comparison is against the owner's NEW values, from its own <tfm>.gpm.map.json
-- not against the characters the owner holds in the table today.  Those are
still the old uncomposed letters, so comparing with them would report every
position as different and conclude that every cut needs its own table, which is
the opposite of the truth: bbmbx's 58 composed values are identical to bbm's, so
bbmbx is an alias carrying weight=bold and nothing else.

Writes <entry>.htf.lua either way, named for the htf TARGET rather than the tfm,
since that is the name the block is pasted over.  For the full char table of a
font regardless of what an alias could do -- which is what you compare, and what
this step compares for you -- ask for <font>.htf.lua by name.

Usage:  htf_entry.py <font> [--against MAP] [--data DIR] [--out FILE]
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("--data", default=G.DATA)
ap.add_argument("--map", help="default: <font>.gpm.map.json")
ap.add_argument("--against", help="the owner's map, for the comparison "
                                  "(default: found from the family dir)")
ap.add_argument("--out", help="default: <entry>.htf.lua")
a = ap.parse_args()

mp = a.map or f"{a.font}.gpm.map.json"
try:
    m = json.load(open(mp, encoding="utf-8"))
except OSError:
    sys.exit(f"htf_entry: no {mp} -- run `make {a.font}.gpm.map.json` first")

# The entry to WRITE comes from tfm-htf-map.json, through htf_target -- the same
# resolution `make htf-entry` and htf_mfont_apply --as use, and the one that was
# asked for: an htf name can be a prefix of the font's or a name from elsewhere,
# so it is looked up rather than derived.
#
# The map's own htf_entry is the record's largest-prefix answer against
# htf_data.lua, and the two DISAGREE where the .htf tree has an entry that
# htf_data.lua lacks.  Taking the map's answer here made stix-mathtt-bold write
# stix-mathtt.htf.lua -- the same filename stix-mathtt writes, so the second run
# silently overwrote the first and 22 fonts produced 22 files of which two were
# one.  htf_target is the authority; the map's value is the fallback for a font
# no tfm resolves to.
entry = None
_rep = subprocess.run([sys.executable, os.path.join(HERE, "htf_target.py"),
                       a.font, "--data", a.data], capture_output=True, text=True)
if _rep.returncode == 0 and _rep.stdout.strip():
    entry = _rep.stdout.strip()
entry = entry or m.get("htf_entry") or m["font"]
owner = m.get("htf_owner")
mine = {p: e["new_value"] for p, e in m["positions"].items()
        if e.get("new_value") is not None}
out = a.out or f"{entry}.htf.lua"

def chars_form(why):
    """Hand the full table to htf_mfont_apply, which owns that writing."""
    print(f"  {why} -- writing the full ['chars'] table")
    r = subprocess.run([sys.executable, os.path.join(HERE, "htf_mfont_apply.py"),
                        "--cmp", mp, "--block", a.font, "--as", entry,
                        "--full", "--no-compare", "--out", out,
                        "--data", a.data])
    sys.exit(r.returncode)

if not owner or owner == entry:
    chars_form(f"['{entry}'] owns its characters")

# The owner's own map: its work dir is a sibling under the family directory, and
# htf_target --rep-of says which tfm holds it.
against = a.against
if not against:
    rep = subprocess.run([sys.executable, os.path.join(HERE, "htf_target.py"),
                          "--rep-of", owner, "--data", a.data],
                         capture_output=True, text=True)
    if rep.returncode == 0:
        cand = os.path.join("..", rep.stdout.strip(),
                            f"{rep.stdout.strip()}.gpm.map.json")
        if os.path.exists(cand):
            against = cand
if against:
    theirs = {p: e["new_value"] for p, e in
              json.load(open(against, encoding="utf-8"))["positions"].items()
              if e.get("new_value") is not None}
    src = os.path.basename(against)
else:
    # No map for the owner means it has not been investigated, so nothing is
    # going to rewrite its table -- and an alias makes this font read that table
    # AS IT STANDS.  Its current values are therefore exactly what the alias
    # would deliver, which makes them the right thing to compare with here, not
    # a second-best.  Giving up instead wrote a full ['chars'] table for every
    # entry owned by one of htf_data's 17 synthetic 'lm-rep-*' groupings --
    # cmr, cmbx, cmss, cmsl, cmtt, cmcsc -- and no font is NAMED lm-rep-cmrm, so
    # no work dir for it can ever exist and the branch was unreachable by
    # design.  cmr10's 127 values are identical to lm-rep-cmrm's and the alias
    # is right.
    #
    # This is NOT the hazard the docstring warns about.  That one is comparing
    # an INVESTIGATED owner's stale values -- bbm's old uncomposed letters
    # against bbmbx's composed ones -- which can only call cuts different and
    # hand each its own table.  Here there is no new version to be stale
    # against.
    owner_chars = (G.read_htf().get(owner) or {}).get("chars") or {}
    if not owner_chars:
        chars_form(f"no record for the owner ['{owner}'], and its entry holds "
                   f"no values either, so nothing to compare against")
    theirs = dict(owner_chars)
    src = "as the table holds it today"
# Compared by MEANING, not by spelling: the same character is written '&#x2124;'
# or as itself depending on --chars, and a raw string compare called 11 of bbm's
# 58 values different from bbmbx's when every one was identical.
diff = [p for p in set(mine) | set(theirs)
        if not G.same_value(mine.get(p), theirs.get(p))]
if diff:
    chars_form(f"{len(diff)} of {len(mine)} value(s) differ from ['{owner}'] "
               f"({src}), so the alias cannot express this font")

# Identical: the alias says it all, and the declaration is this entry's own.
decl = m.get("decl_wanted") or {}
block = [f'\t["{entry}"] = \n', "\t{\n", f'\t\t["alias"] = "{owner}",\n']
if decl:
    block += ['\t\t["font"] = \n', "\t\t{\n"]
    for ax in ("family", "weight", "variant", "style"):
        if ax in decl:
            block.append(f'\t\t\t["{ax}"] = "{decl[ax]}",\n')
    block.append("\t\t},\n")
block.append("\t},\n")
with open(out, "w", encoding="utf-8") as f:
    f.writelines(block)
print(f"mode=entry/alias  {out}  {len(block)} line(s)")
print(f"  all {len(mine)} value(s) identical to ['{owner}'] "
      f"({src}) -- an ['alias'] says it, and no table of "
      f"its own is needed")
print(f"  the ['font'] declaration stays this entry's: {decl or '(none)'} -- "
      f"luarealchar reads it from the resolving entry, never through the alias")
