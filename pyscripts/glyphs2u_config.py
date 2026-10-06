#!/usr/bin/env python3
"""Read glyphs2u's per-family config.py -- which fonts have a lua table, and where.

Every glyphs2u working directory carries one, and it holds three facts no font
file can tell us:

  lua_tables            the deployable tables
  lua_tables_copy       one table serving several fonts: stix-mathex.lua is
                        copied to stix-mathex-bold, which therefore has no file
                        of its own to find
  lua_tables_not_needed fonts that deliberately need NO table, because every
                        glyph is named uXXXX/uniXXXX and xdvipsk decodes those
                        by the AGL algorithmic rule -- a rule that lives in
                        xdvipsk, not in glyphlist_table.lua, so nothing in this
                        project could deduce it

Without this, looking for '<font>.lua' and finding nothing is ambiguous: it may
mean the table is a copy of another, that none is wanted, or that one is
expected and absent.  Only the last is a problem, and it used to be silent.

Names in the lists appear with and without the '.lua' suffix: the convention is
that a MISSING table is written without one (lua_tables can also be built by
scanning the directory, where the files naturally carry it), so both are
accepted here.

Values are read with ast, not exec: the file is data, and nothing in it should
run just because we want to know what it says.

Usage:  glyphs2u_config.py <dir> [--font NAME]
"""
import ast, os, sys, argparse

CONFIG = "config.py"
KEYS = ("font_dir", "dest_dir", "lua_tables", "lua_tables_copy",
        "lua_tables_not_needed")

def stem(name):
    """'stix-mathex.lua' / 'stix-mathex' -> 'stix-mathex'."""
    return name[:-4] if name.endswith(".lua") else name

def load(dirname):
    """The config's literal assignments, or None when there is no config.py."""
    path = os.path.join(dirname, CONFIG)
    if not os.path.exists(path):
        return None
    try:
        tree = ast.parse(open(path, encoding="utf-8").read(), path)
    except SyntaxError as e:
        print(f"glyphs2u_config: {path}: {e}", file=sys.stderr)
        return None
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id in KEYS:
                try:
                    out[t.id] = ast.literal_eval(node.value)
                except ValueError:
                    pass                  # computed, not a literal -- skip it
    return out

def table_for(font, dirname):
    """(path or None, why) -- the .lua to read for this font, and the reason.

    'why' is one of: own, copy of <table>, not needed, expected but missing,
    not listed.  A caller can report the difference instead of treating every
    absence as the same silence.
    """
    own = os.path.join(dirname, font + ".lua")
    if os.path.exists(own):
        return own, "own"
    cfg = load(dirname) or {}
    for src, dests in (cfg.get("lua_tables_copy") or {}).items():
        if font in {stem(d) for d in dests}:
            p = os.path.join(dirname, stem(src) + ".lua")
            return (p if os.path.exists(p) else None,
                    f"copy of {stem(src)}.lua"
                    + ("" if os.path.exists(p) else " -- WHICH IS MISSING"))
    if font in {stem(x) for x in (cfg.get("lua_tables_not_needed") or ())}:
        return None, "not needed"
    if font in {stem(x) for x in (cfg.get("lua_tables") or ())}:
        return None, "expected but missing"
    return None, "not listed"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--font", help="report just this font's table")
    a = ap.parse_args()
    cfg = load(a.dir)
    if cfg is None:
        sys.exit(f"glyphs2u_config: no {CONFIG} in {a.dir}")
    if a.font:
        p, why = table_for(a.font, a.dir)
        print(f"{a.font}: {p or '(none)'}  [{why}]")
        return
    print(f"{os.path.join(a.dir, CONFIG)}")
    for k in ("font_dir", "dest_dir"):
        if cfg.get(k):
            print(f"  {k} = {cfg[k]}")
    for k in ("lua_tables", "lua_tables_not_needed"):
        v = cfg.get(k) or []
        print(f"  {k} ({len(v)}): {', '.join(stem(x) for x in sorted(v))}")
    for src, dests in (cfg.get("lua_tables_copy") or {}).items():
        print(f"  {stem(src)}.lua is also used as: "
              f"{', '.join(stem(d) for d in dests)}")
    missing = [stem(x) for x in (cfg.get("lua_tables") or [])
               if not os.path.exists(os.path.join(a.dir, stem(x) + ".lua"))]
    if missing:
        print(f"  LISTED BUT ABSENT: {', '.join(missing)}")

if __name__ == "__main__":
    main()
