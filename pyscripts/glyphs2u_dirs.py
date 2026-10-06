#!/usr/bin/env python3
"""font -> the glyphs2u working directory that carries its table.

Why a map and not a lookup at the moment of use.  LUA_DIR has been passed by
hand on every gpm-seed line, and the Makefile's two examples are both under
public/, so a family filed elsewhere is easy to get wrong -- Computer Modern
sits in amsfonts/cm, and seeding it with no LUA_DIR at all succeeds in silence
and simply takes nothing from glyphs2u.

Why THIS source.  Two other routes were tried and both are worse:

  glyphs2u's config-list.json lists the family directories outright, but it is
  a checked-in list that can fall out of step with the directories themselves.

  The .pfb path mirrors the directory for 22 of the 28 families, and the six
  exceptions need corrections that are conventions rather than rules: the
  'public/' level is dropped for the five amsfonts families, and three
  directories lose a '-type1'/'-font' suffix (wasy vs wasy-type1).  It also has
  to search EVERY tree, because a .pfb can be in more than one -- lmr10 is in
  vtex-dist as public/lmodern and in texmf-dist as public/lm, and only the
  second has a glyphs2u counterpart, so a first-hit lookup answers wrongly.

  Each family's own config.py, by contrast, NAMES the fonts it serves, in the
  three lists glyphs2u_config already reads: lua_tables (a table of its own),
  lua_tables_copy (one table serving several fonts) and lua_tables_not_needed
  (no table wanted, every glyph named uXXXX).  Inverting those needs no
  correction, no tree search and nothing to keep in step -- the directories are
  read as they are.

Usage:  glyphs2u_dirs.py [--glyphs2u DIR] [--out FILE] [--check]
        --check reports without writing, and exits non-zero on a conflict.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import glyphs2u_config as C

# glyphs2u is this project, so the default is its root -- two levels up
# from this script.
DEFAULT_G2U = (os.environ.get("glyphs2u_dir")
               or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ap = argparse.ArgumentParser()
ap.add_argument("--glyphs2u", default=DEFAULT_G2U, help="the glyphs2u checkout")
ap.add_argument("--out", default="glyphs2u-dirs.json")
ap.add_argument("--check", action="store_true",
                help="report only; exit 1 if one font maps to two directories")
ap.add_argument("--font", metavar="NAME",
                help="print the ABSOLUTE directory for this font and stop -- "
                     "reads the map when it exists, and falls back to the "
                     "config.py walk so a stale or missing map cannot make the "
                     "answer wrong, only slower.  Prints nothing and exits 0 "
                     "when the font has no table: absent is a normal state, and "
                     "a make rule reading this must not be handed an error for "
                     "it.")
ap.add_argument("--map", metavar="FILE",
                help="the generated map to consult for --font")
a = ap.parse_args()


def families(root):
    """Every directory under the checkout that carries a config.py."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "__pycache__", "memory")]
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        # The checkout ROOT has a config.py of its own -- the project's
        # settings, not a family's, and not a table of literal assignments --
        # so reading it only produces a syntax complaint about a file that was
        # never meant to be read this way.
        if C.CONFIG in filenames and rel != ".":
            out.append(rel)
    return sorted(out)


def fonts_of(cfg):
    """The font names a config.py accounts for, from all three lists.

    Names appear with and without the '.lua' suffix, so the stem is taken
    either way -- glyphs2u_config.stem is the same rule its own table_for uses.
    """
    names = set()
    for entry in (cfg.get("lua_tables") or []):
        names.add(C.stem(entry))
    copies = cfg.get("lua_tables_copy") or {}
    for table, served in (copies.items() if isinstance(copies, dict) else copies):
        names.add(C.stem(table))
        for f in (served or []):
            names.add(C.stem(f))
    for entry in (cfg.get("lua_tables_not_needed") or []):
        names.add(C.stem(entry))
    return names


root = os.path.abspath(a.glyphs2u)
if not os.path.isdir(root):
    sys.exit(f"glyphs2u_dirs: no such checkout: {root}")

if a.font:
    rel = None
    if a.map and os.path.exists(a.map):
        try:
            with open(a.map, encoding="utf-8") as f:
                rel = json.load(f).get("fonts", {}).get(a.font)
        except (OSError, ValueError):
            rel = None
    if rel is None:                     # no map, or not in it: ask the configs
        for cand in families(root):
            cfg = C.load(os.path.join(root, cand))
            if cfg is not None and a.font in fonts_of(cfg):
                rel = cand
                break
    if rel:
        print(os.path.join(root, rel))
    sys.exit(0)

fonts, dirs, conflicts = {}, {}, []
for rel in families(root):
    cfg = C.load(os.path.join(root, rel))
    if cfg is None:
        continue
    names = fonts_of(cfg)
    dirs[rel] = len(names)
    for n in sorted(names):
        if n in fonts and fonts[n] != rel:
            conflicts.append((n, fonts[n], rel))
        else:
            fonts[n] = rel

rec = {
    "_comment": [
        "font -> the glyphs2u directory holding its table, RELATIVE to the",
        "checkout (glyphs2u_dir).  Generated by pyscripts/glyphs2u_dirs.py from",
        "each family's own config.py, which names the fonts it serves; nothing",
        "here is derived from a .pfb path or from config-list.json, and see that",
        "script for why both were rejected.",
        "",
        "'dirs' is the same information the other way round -- directory to the",
        "number of fonts it accounts for -- so a family that has stopped being",
        "read, or one newly added, is visible without diffing the whole map.",
        "",
        "A font absent from here has no glyphs2u table and none is expected: the",
        "seed then takes its base characters from the built-in xdvipsk list",
        "alone, which is a normal state and not a failure.",
    ],
    "fonts": dict(sorted(fonts.items())),
    "dirs": dict(sorted(dirs.items())),
}

print(f"glyphs2u_dirs: {len(dirs)} family dir(s), {len(fonts)} font(s)")
if conflicts:
    print(f"  {len(conflicts)} font(s) claimed by two directories:", file=sys.stderr)
    for n, first, second in conflicts[:8]:
        print(f"    {n}: {first} and {second}", file=sys.stderr)

if a.check:
    sys.exit(1 if conflicts else 0)

with open(a.out, "w", encoding="utf-8") as f:
    json.dump(rec, f, indent=1, ensure_ascii=False)
    f.write("\n")
print(f"  -> {a.out}")
