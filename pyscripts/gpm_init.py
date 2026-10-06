#!/usr/bin/env python3
"""Step 1: write the skeleton <font>.gpm.json for one tfm work dir.

Joins what is already known without looking at a single glyph image:
  - position -> glyph name, from the font's encoding (<font>.pfb.enc.json for a
    pfb's built-in encoding, or <enc>.enc.json when psfonts.map names one);
  - the htf value currently at that position (htf_data.lua, alias resolved);
  - the font-level ['font'] declaration, kept at the top of the record.
Everything else is left to be filled: base = "?", no per-glyph axes.

Refuses to overwrite an existing <font>.gpm.json unless --force (the file is
hand-edited and filled in by later steps -- like glyphs2u refusing to
regenerate a <font>.lua).  --merge keeps the existing per-glyph work and only
adds glyphs/positions that were missing.

Usage: gpm_init.py <font> [--enc FILE] [--merge|--force]
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("--data", default=G.DATA, help="directory of generated JSON maps")
ap.add_argument("--enc", help="encoding json (default: <font>.pfb.enc.json)")
ap.add_argument("--htf-lua", default=None,
                help="a single htf lua to read instead of the pair "
                     "htf_data.lua + user_htf.lua")
ap.add_argument("--out")
ap.add_argument("--merge", action="store_true", help="keep existing entries, add missing")
ap.add_argument("--force", action="store_true", help="overwrite an existing record")
a = ap.parse_args()
# Left as None when not given, so read_htf_lua takes BOTH htf_data.lua and
# user_htf.lua.  Collapsing it to HTF_LUA here meant the overlay was never read,
# and every font defined only there -- bbm and its aliases -- looked as though it
# had no htf entry at all.
out = a.out or f"{a.font}.gpm.json"

if os.path.exists(out) and not (a.merge or a.force):
    sys.exit(f"gpm_init: {out} exists -- use --merge to add missing glyphs, "
             f"--force to start over")

# --- encoding: slot(0-based) -> glyph name ---------------------------------
enc_file = a.enc or G.enc_json_for(a.font, a.data)
if not os.path.exists(enc_file):
    sys.exit(f"gpm_init: no encoding json for '{a.font}' -- "
             f"run `make {enc_file}` first, or pass --enc")
enc = G.load(enc_file)

# --- glyphs excluded BY HAND ------------------------------------------------
# <font>.exclude, one glyph name per line, '#' starting a comment.  For a slot
# the font names and fills with something that is not a glyph: bbmssbx10 holds
# nine circumflex composites that ARE drawn -- so no emptiness test rejects them
# -- but drawn as the base letter's outline displaced left of the origin, two
# thirds of it outside the advance width.  Whether that is a glyph is a judgement
# about the font, so it is written down rather than derived.
#
# A sidecar file rather than a key in the record, because the record is rebuilt
# from the encoding: --merge would carry a key across, --force would not, and a
# decision should not depend on which was used.  Same reason 'plain' and the
# family 'pairs' live beside their records.
exclude_file = f"{a.font}.exclude"
excluded = set()
if os.path.exists(exclude_file):
    for line in open(exclude_file, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if line:
            excluded.add(line)

# --- htf: chars from the alias target, declaration from the font itself -----
# Read htf_data.lua AND user_htf.lua, the files the pipeline loads and
# htf_mfont_apply rewrites -- not htf_data.json, which comes from the .htf
# sources and drifts from them.  The overlay matters: bbm and its seven aliases
# exist only there, tex4ht's .htf tree knowing nothing of them, and for this
# workflow they are htf data like any other.
htf_data = G.read_htf(a.htf_lua)

def resolve(name, seen=None):
    """Follow the alias chain to the entry that owns ['chars']."""
    seen = seen or set()
    e = htf_data.get(name)
    if e is None or name in seen:
        return None
    if e.get("chars"):
        return name
    seen.add(name)
    return resolve(e.get("alias"), seen) if e.get("alias") else None

# The entry serving this font is found by name, or by the LARGEST PREFIX of it,
# which is how luarealchar.lua does it: bbm10, bbm12 and every other size are all
# served by the one entry called 'bbm', so demanding an exact match found nothing
# for any of them and seeded a record with no htf values at all.
htf_name = G.htf_entry_for(a.font, htf_data)
entry = htf_data.get(htf_name) if htf_name else None
if entry is None:
    print(f"gpm_init: WARNING no htf entry named '{a.font}' or any prefix of it",
          file=sys.stderr)
    entry = {}
elif htf_name != a.font:
    print(f"gpm_init: htf entry '{htf_name}' serves '{a.font}' "
          f"(largest-prefix rule)", file=sys.stderr)
base_htf = resolve(htf_name) if htf_name else None
chars = htf_data.get(base_htf, {}).get("chars", {}) if base_htf else {}

# An alias says which table of chars to use, not what this font looks like:
# ptmr8r (Times roman) aliases pcrro8r (Courier oblique) because they share the
# 8r encoding, and inheriting its style=oblique would be plainly wrong.  So the
# declaration is the entry's own, as htf_mfont_targets.py also reads it.
decl = {k: v for k, v in entry.get("font", {}).items() if k in G.AXES}

# --- pfb ---------------------------------------------------------------------
pfb = None
try:
    pfb = G.load_map("psfonts-map-tfm-data.json", a.data).get(a.font, {}).get("pfb")
except FileNotFoundError:
    pass

# --- build ------------------------------------------------------------------
old = G.load(out) if (a.merge and os.path.exists(out)) else {}
old_glyphs = old.get("glyphs", {})

rec = {
    "font": a.font,
    "pfb": pfb,
    "enc": enc_file,
    "htf": base_htf or a.font,
    # The entry SERVING this font, as against the one owning ['chars'].  They
    # differ two different ways and the htf side must not confuse them:
    #   htf_entry != font   reached by the largest-prefix rule -- there is no
    #                       entry of this font's own name at all, so writing one
    #                       would serve this tfm only and leave bbm12, bbm17 and
    #                       the rest on the old table.  The entry to write is
    #                       htf_entry.
    #   htf != htf_entry    the entry exists and ALIASES another for its chars,
    #                       which is the case that needs the alias removed.
    "htf_entry": htf_name or a.font,
    # Every axis gets a font-level status: "decl" where the htf declaration
    # speaks, "?" where nothing does -- those are the questions gpm_edit asks
    # once for the whole font (stix-mathsf declares no family, yet it is
    # sans-serif throughout).
    # what htf_data.lua declares right now, kept apart from the truth below:
    # the declaration can be wrong (stix-mathscr says variant=small-caps where
    # its letters are script), and the htf output has to know both to decide
    # whether keeping the declaration is even an option
    "htf_decl": dict(decl),
    # What the tfm says it defines: positions outside [bc, ec] are unreachable,
    # whatever the .pfb encoding lists.  Recorded rather than looked up again by
    # every later step, so the derivation stays deterministic even where the tfm
    # is not resolvable, and so a record seeded before this existed keeps working
    # -- G.addressable() treats a missing range as 'no bound known'.
    **({"tfm_range": dict(zip(("bc", "ec"), G.tfm_range(a.font)))}
       if G.tfm_range(a.font) else {}),
    "props": old.get("props", dict(decl)),
    "status": old.get("status", {ax: ("decl" if ax in decl else G.UNKNOWN)
                                 for ax in G.AXES}),
    "glyphs": {},
}
# Anything else the old record carried at font level -- 'reviewed', and whatever
# a later step adds -- rides across untouched.  This rebuild names the keys it
# derives from the encoding and the htf table, so without this line every merge
# silently drops the rest, exactly as it once dropped the per-glyph 'rename'.
# A merge must lose nothing it does not deliberately recompute.
for _k, _v in old.items():
    if _k not in rec:
        rec[_k] = _v
# The htf table is 1-based over the 0-based encoding slots (cf. cmp_classify).
OFFSET = 1
kept = added = novalue = 0
dups = []
for slot_s, gname in sorted(enc.items(), key=lambda kv: int(kv[0])):
    slot = int(slot_s)
    pos = slot + OFFSET
    value = chars.get(str(pos))
    if gname == ".notdef":            # a hole in the encoding, not a glyph
        continue
    if gname in excluded:             # a decision, not a derivation: see below
        continue
    if gname in rec["glyphs"]:
        # an encoding may put one glyph at more than one slot (8r.enc has
        # hyphen twice); the record is keyed by name, so the extra positions
        # ride along and the htf derivation writes them all
        rec["glyphs"][gname].setdefault("alt", []).append(
            {"slot": slot, "pos": pos, "htf_value": value})
        dups.append((gname, pos))
        continue
    if value is None:
        novalue += 1
    if gname in old_glyphs:
        g = old_glyphs[gname]
        kept += 1
    else:
        g = {"base": G.UNKNOWN, "props": {}, "status": {"base": G.UNKNOWN}}
        added += 1
    g["slot"], g["pos"], g["htf_value"] = slot, pos, value
    g.pop("alt", None)                # rebuilt from this encoding below
    # Keep the ordering readable: position first, work-in-progress after -- and
    # use the SHARED key list, plus anything not in it.  This used to name the
    # keys here, and the list had gone stale: it omitted 'rename', so every merge
    # silently dropped the xdvipsk renames gpm_unicode had carried in from the
    # glyphs2u tables.  A merge must lose nothing it does not deliberately
    # rebuild, whatever key a later step adds.
    rec["glyphs"][gname] = {k: g[k] for k in G.GLYPH_KEYS if k in g} | \
                           {k: v for k, v in g.items() if k not in G.GLYPH_KEYS}

# glyphs the old record had that this encoding does not mention: keep them, they
# may have been added by hand.
for gname, g in old_glyphs.items():
    if gname not in rec["glyphs"]:
        rec["glyphs"][gname] = g
        kept += 1

G.save(rec, out)
print(f"gpm_init: {out}  glyphs={len(rec['glyphs'])} (added {added}, kept {kept})  "
      f"decl={decl or '(none)'}  htf={rec['htf']}  no-htf-value={novalue}")
if dups:
    print(f"  {len(dups)} glyph(s) at more than one slot, carried as 'alt': "
          + ", ".join(f"{n}@{p}" for n, p in dups[:6]))
# Unreachable positions.  A WARNING and not an exclusion: the rule is right
# often enough to be worth saying and not always enough to act on by itself.
# On bbmssbx10 it names nine glyphs gpm_exclude had already proposed on the
# geometry (outlines outside the advance width) and a tenth, sfthyphen, that
# geometry did not see -- so it agrees with a human reading, which is the case
# for reporting it and not for deleting anything.  The decision belongs in
# <font>.exclude, where a looked-at judgement is already recorded.
_r = rec.get("tfm_range")
if _r:
    _bc, _ec = _r["bc"], _r["ec"]
    _prim = sorted((g["slot"], n) for n, g in rec["glyphs"].items()
                   if isinstance(g, dict) and "slot" in g
                   and not (_bc <= g["slot"] <= _ec))
    _alt = sorted((x["slot"], n) for n, g in rec["glyphs"].items()
                  if isinstance(g, dict)
                  for x in (g.get("alt") or []) if not (_bc <= x["slot"] <= _ec))
    if _prim or _alt:
        print(f"  tfm defines {_bc}..{_ec}; OUTSIDE that: "
              f"{len(_prim)} glyph(s) at their only slot, "
              f"{len(_alt)} duplicate slot(s) -- unreachable, and the htf "
              f"derivation skips them")
        if _prim:
            print("    only slot unreachable (nothing addresses this glyph): "
                  + ", ".join(f"{n}@{s}" for s, n in _prim[:8]))
        if _alt:
            print("    duplicate slots (the designer's, not TeX's): "
                  + ", ".join(f"{n}@{s}" for s, n in _alt[:8]))
if base_htf and base_htf != a.font:
    print(f"  chars come through the alias {a.font} -> {rec['htf']}; the "
          f"['font'] declaration is this font's own")
