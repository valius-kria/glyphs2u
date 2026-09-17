#!/usr/bin/env python3
"""
build-glyphlist-table.py -- Build the unified glyph-to-Unicode table
by applying the unification algorithm documented in built-in-table.md.

Usage:
    python3 build-glyphlist-table.py <glyphlists-dir>

<glyphlists-dir>  directory containing the parsed .lua source files
                  produced by parse-glyphlists.py

Output: <glyphlists-dir>/glyphlist_table-generated.lua

The authoritative glyphlist_table.lua is never overwritten.
Manual corrections in that file are revealed by running
compare-glyphlists.py between the generated and authoritative tables.

Unification order (see built-in-table.md for rationale):
  1. AGL (agl.lua)    -- all values, including PUA
  2. pdftex           -- skip PUA; skip tfm:-prefixed names
  3. luaotf           -- skip PUA
  4. ntx              -- skip PUA
  5. cs               -- skip PUA; before cmr because of 'suppress'
  6. cmr              -- skip PUA; skip a<digits> and d<digits> names
  7. tex              -- all remaining entries not yet covered
"""

import re
import sys
from pathlib import Path

# ── Private Use Area ──────────────────────────────────────────────────────────

PUA_RANGES = [(0xE000, 0xF8FF), (0xF0000, 0xFFFFF), (0x100000, 0x10FFFF)]

def is_pua(cps):
    return any(any(lo <= cp <= hi for lo, hi in PUA_RANGES) for cp in cps)

# ── Loader for parsed .lua tables ─────────────────────────────────────────────

_ENTRY = re.compile(r'^\s*\["([^"]+)"\]\s*=\s*\{([^}]+)\}')
_HEX   = re.compile(r'0x([0-9A-Fa-f]+)')

def load_lua(path):
    """Load a parsed source Lua table → dict {name: [codepoints]}."""
    entries = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        m = _ENTRY.match(line)
        if not m:
            continue
        name = m.group(1)
        cps  = [int(h, 16) for h in _HEX.findall(m.group(2))]
        if cps:
            entries[name] = cps
    return entries

def load_lua_multimap(path):
    """Load a multi-map Lua file (tex.lua) → list of (name, cps) with duplicates."""
    entries = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        m = _ENTRY.match(line)
        if not m:
            continue
        name = m.group(1)
        cps  = [int(h, 16) for h in _HEX.findall(m.group(2))]
        if cps:
            entries.append((name, cps))
    return entries

# ── cmr exclusion pattern: a<digits> or d<digits> ────────────────────────────

_CMR_SKIP = re.compile(r'^[ad]\d+$')

# ── Output formatting ─────────────────────────────────────────────────────────

def lua_line(name, cps, source):
    vals = ', '.join(f'0x{cp:04X}' for cp in cps)
    return f'  ["{name}"] = {{ {vals}, }},  -- {source}'

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    gldir   = Path(sys.argv[1])
    outpath = gldir / 'glyphlist_table-generated.lua'

    table = {}   # name -> (cps, source)  — tracks what is already included
    lines = []   # output lines in insertion order

    def add(name, cps, source):
        if name not in table:
            table[name] = (cps, source)
            lines.append(lua_line(name, cps, source))

    # Step 1 — AGL: all values, including PUA
    agl = load_lua(gldir / 'agl.lua')
    for name, cps in agl.items():
        add(name, cps, 'AGL')
    print(f'  Step 1 AGL:    {len(agl):5d} source  →  {len(table):5d} total')

    prev = len(table)

    # Step 2 — pdftex: skip PUA and tfm:-prefixed names
    pdftex = load_lua(gldir / 'pdftex.lua')
    for name, cps in pdftex.items():
        if name.startswith('tfm:') or is_pua(cps):
            continue
        add(name, cps, 'pdftex')
    print(f'  Step 2 pdftex: {len(pdftex):5d} source  →  {len(table):5d} total  (+{len(table)-prev})')
    prev = len(table)

    # Step 3 — luaotf: skip PUA
    luaotf = load_lua(gldir / 'luaotf.lua')
    for name, cps in luaotf.items():
        if is_pua(cps):
            continue
        add(name, cps, 'luaotf')
    print(f'  Step 3 luaotf: {len(luaotf):5d} source  →  {len(table):5d} total  (+{len(table)-prev})')
    prev = len(table)

    # Step 4 — ntx: skip PUA
    ntx = load_lua(gldir / 'ntx.lua')
    for name, cps in ntx.items():
        if is_pua(cps):
            continue
        add(name, cps, 'ntx')
    print(f'  Step 4 ntx:    {len(ntx):5d} source  →  {len(table):5d} total  (+{len(table)-prev})')
    prev = len(table)

    # Step 5 — cs: skip PUA; must precede cmr because of 'suppress'
    cs = load_lua(gldir / 'cs.lua')
    for name, cps in cs.items():
        if is_pua(cps):
            continue
        add(name, cps, 'cs')
    print(f'  Step 5 cs:     {len(cs):5d} source  →  {len(table):5d} total  (+{len(table)-prev})')
    prev = len(table)

    # Step 6 — cmr: skip PUA and a<digits>/d<digits> names
    cmr = load_lua(gldir / 'cmr.lua')
    for name, cps in cmr.items():
        if _CMR_SKIP.match(name) or is_pua(cps):
            continue
        add(name, cps, 'cmr')
    print(f'  Step 6 cmr:    {len(cmr):5d} source  →  {len(table):5d} total  (+{len(table)-prev})')
    prev = len(table)

    # Step 7 — tex: all remaining entries not yet covered
    tex = load_lua_multimap(gldir / 'tex.lua')
    tex_src = len({name for name, _ in tex})
    for name, cps in tex:
        add(name, cps, 'tex')
    print(f'  Step 7 tex:    {tex_src:5d} source  →  {len(table):5d} total  (+{len(table)-prev})')

    # Write output
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('-- Generated by build-glyphlist-table.py\n')
        f.write('-- Compare with glyphlist_table.lua to identify manual corrections\n')
        f.write('--[[\n')
        f.write('   xxd -i -n glyphlist_table glyphlist_table.lua >glyphlist_table.h\n')
        f.write('--]]\n')
        f.write('glyphtounicode_main = {\n')
        for line in lines:
            f.write(line + '\n')
        f.write('}\n')

    print(f'\n  → {outpath}  ({len(table)} entries)')

if __name__ == '__main__':
    main()
