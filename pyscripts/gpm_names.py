#!/usr/bin/env python3
"""Fill properties a font states in its GLYPH NAMES.

A font may hold two cuts of the same character -- stix-mathcal has the usual
slanted integral at uni222B and the upright one at uni222B.up -- and Unicode
has one codepoint for both.  Nothing derived from codepoints can tell them
apart, and a raster comparison against a sibling font will not either: the
difference is inside the font, not between two fonts.  What does say it is the
glyph name, so that is where this reads it from.

Names are taken as dot-separated components (uni222B.upsm = upright + small)
and looked up in gpm_name_rules.json, which keys the rules by a regular
expression on the font name.  There is no general convention across families --
each names its variant cuts its own way -- so that file holds only what has
been observed, family by family.  Survey a new one with --list and add it
there (or pass --rule for a one-off).

Values land with status "name": better than an assumption, weaker than having
looked at the glyph, so a later visual or manual value is left alone and this
step never overwrites one.

  gpm_names.py stix-mathcal --list          # what would be set, and on what
  gpm_names.py stix-mathcal
  gpm_names.py <font> --rule upr:style=normal --rule sl:style=italic

To make an upright/slanted distinction actually readable, the glyphs that are
NOT upright have to say so too -- the font-level style, or gpm_set --rest:
  gpm_names.py stix-mathcal                 # .up* -> style=normal
  gpm_set.py  stix-mathcal style=italic --rest   # the rest, skipping those
"""
import argparse, collections, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("--data", default=G.DATA)
ap.add_argument("--gpm")
ap.add_argument("--rules", default="gpm_name_rules.json",
                help="rule file, relative to --data")
ap.add_argument("--rule", action="append", default=[],
                metavar="suffix:axis=value[,axis=value]",
                help="add or replace a rule for one name component")
ap.add_argument("--no-defaults", action="store_true", help="use only --rule rules")
ap.add_argument("--list", action="store_true",
                help="report the name components in this font and what the "
                     "rules would do, without writing")
ap.add_argument("--status", default="name")
a = ap.parse_args()
gpm = a.gpm or f"{a.font}.gpm.json"
rec = G.load(gpm)

rules, matched = {}, []
if not a.no_defaults:
    # gpm_name_rules.json is hand-maintained and lives at the project root,
    # not with the tree-derived maps, so resolve it the way every other map
    # is resolved: data_dir first, then the root.
    path = G.map_path(a.rules, a.data)
    if os.path.exists(path):
        for pattern, table in G.load(path).items():
            if pattern.startswith("_") or not re.search(pattern, a.font):
                continue
            matched.append(pattern)
            for sfx, props in table.items():
                if sfx.startswith("_"):
                    continue
                for ax, val in props.items():
                    if ax == "base":
                        if not isinstance(val, dict):
                            sys.exit(f"gpm_names: {a.rules}: {pattern}/{sfx}: "
                                     f"'base' must map old character to new")
                    elif ax == "selector":
                        try:
                            ok = G.is_selector(int(str(val), 16))
                        except ValueError:
                            ok = False
                        if not ok:
                            sys.exit(f"gpm_names: {a.rules}: {pattern}/{sfx}: "
                                     f"'{val}' is not a variation selector")
                    elif ax not in G.AXES:
                        sys.exit(f"gpm_names: {a.rules}: {pattern}/{sfx}: "
                                 f"'{ax}' is not an axis {G.AXES}")
                    elif val not in G.AXIS_VALUES[ax]:
                        sys.exit(f"gpm_names: {a.rules}: {pattern}/{sfx}: "
                                 f"'{val}' is not a {ax} value")
                rules[sfx] = props
    else:
        print(f"gpm_names: no rule file at {path}", file=sys.stderr)

for r in a.rule:
    sfx, _, rest = r.partition(":")
    props = {}
    for item in rest.split(","):
        ax, _, val = item.partition("=")
        if ax not in G.AXES:
            sys.exit(f"gpm_names: '{ax}' is not an axis {G.AXES}")
        if val not in G.AXIS_VALUES[ax]:
            sys.exit(f"gpm_names: '{val}' is not a {ax} value {G.AXIS_VALUES[ax]}")
        props[ax] = val
    if not props:
        sys.exit(f"gpm_names: rule '{r}' sets nothing")
    rules[sfx.lstrip(".")] = props

seen = collections.Counter()
for name in rec["glyphs"]:
    for part in name.split(".")[1:]:
        seen[part] += 1

if not rules:
    print(f"gpm_names: no rules apply to '{a.font}' -- glyph-name conventions "
          f"are per family.\n  Survey it with --list, then add a section to "
          f"{a.rules} (or pass --rule).", file=sys.stderr)
    if not a.list:
        sys.exit(1)

if a.list:
    print(f"{a.font}: name components and what the rules say"
          + (f"  (rules: {', '.join(matched)})" if matched else ""))
    for part, n in seen.most_common():
        what = rules.get(part)
        print(f"  .{part:8} {n:4} glyph(s)   "
              + (", ".join(f"{k}={v}" for k, v in what.items()) if what
                 else "(no rule -- not a font property)"))
    if not seen:
        print("  (no suffixed glyph names in this font)")
    sys.exit(0)

n_set = 0
by_rule = collections.Counter()
kept, unmapped = [], []
for name, g in rec["glyphs"].items():
    for part in name.split(".")[1:]:
        table = rules.get(part, {})
        for ax, val in table.items():
            if ax in ("base", "selector"):
                continue
            r = G.set_axis(g, ax, val, a.status)
            if r == "set":
                n_set += 1
                by_rule[f".{part} {ax}={val}"] += 1
            elif r == "kept":
                kept.append((name, ax, g["props"].get(ax), val))
        # a size cut: the name says this is the larger drawing of the same
        # character, which Unicode spells as the character plus a variation
        # selector.  Nothing in the codepoint says it -- uni222B and
        # uni222B.dsp carry the same U+222B -- so the name is the only source.
        sel = table.get("selector")
        if sel:
            base = g.get("base", G.UNKNOWN)
            if base == G.UNKNOWN:
                unmapped.append((name, "?"))
            else:
                codes = ([f"0x{ord(c):04X}" for c in base]
                         + [f"0x{int(str(sel), 16):04X}"])
                r = G.set_uni(g, codes, a.status)
                if r == "set":
                    n_set += 1
                    by_rule[f".{part} uni +{sel}"] += 1
                elif r == "kept":
                    kept.append((name, "uni", g.get("uni"), codes))

        # a base substitution: the name says which cut of the character this
        # is, where the codepoint at the position knows only the character
        sub = table.get("base")
        if sub:
            cur = g.get("base")
            if cur in sub:
                r = G.set_base(g, sub[cur], a.status)
                if r == "set":
                    n_set += 1
                    by_rule[f".{part} base {cur}->{sub[cur]}"] += 1
                elif r == "kept":
                    kept.append((name, "base", cur, sub[cur]))
            elif cur and cur != G.UNKNOWN:
                unmapped.append((name, cur))

G.save(rec, gpm)
print(f"gpm_names: {gpm}  {n_set} value(s) set from glyph names")
for what, n in by_rule.most_common():
    print(f"  {what:28} {n:4} glyph(s)")
for name, ax, have, want in kept:
    print(f"  kept confirmed {name} {ax}={have} (the name says {want})")
for name, cur in unmapped:
    print(f"  no substitution for {name}: base is {cur!r} -- set it in the editor")
unruled = [f".{p}" for p in seen if p not in rules]
if unruled:
    print(f"  no rule for: {' '.join(sorted(unruled))}  (--list to review)")
