#!/usr/bin/env python3
"""
compare-glyphlists.py -- Compare glyph-to-Unicode tables.

Two modes:

  diff-all   (called by 'make diff-all'):
    python3 compare-glyphlists.py <glyphlists-dir> <main-table.lua>

    For every source Lua table in <glyphlists-dir> computes the set
    difference  source − main-table  and writes <source>-not-main.lua.
    tex.lua is handled as a multi-map: if a name appears in the main
    table, all occurrences of that name are removed from the result.

  check-changes  (called by 'make check-changes'):
    python3 compare-glyphlists.py --check-changes <generated.lua> <authoritative.lua>

    Compares the generated table with the authoritative glyphlist_table.lua
    and reports: names only in generated, names only in authoritative, and
    names present in both but with different Unicode values.
"""

import re
import sys
from pathlib import Path

# ── Loaders ───────────────────────────────────────────────────────────────────

_ENTRY = re.compile(r'^\s*\["([^"]+)"\]\s*=\s*\{([^}]+)\}')
_HEX   = re.compile(r'0x([0-9A-Fa-f]+)')
PUA    = [(0xE000, 0xF8FF), (0xF0000, 0xFFFFF), (0x100000, 0x10FFFF)]

def is_pua(cps):
    return any(any(lo <= cp <= hi for lo, hi in PUA) for cp in cps)

def load_lua(path):
    """Load a Lua table file → dict {name: [codepoints]}."""
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

# ── Formatting ────────────────────────────────────────────────────────────────

def lua_line(name, cps):
    vals = ', '.join(f'0x{cp:04X}' for cp in cps)
    mark = '  -- pua' if is_pua(cps) else ''
    return f'  ["{name}"] = {{ {vals} }},{mark}'

def write_diff(outpath, varname, entries, header):
    lines = [f'-- {header}', f'-- {len(entries)} entries', '']
    if varname == 'tex':
        lines += [
            '-- Multi-map: duplicate keys are intentional.',
            '-- This file is NOT a valid Lua table.',
            '',
        ]
        for name, cps in entries:
            lines.append(lua_line(name, cps))
    else:
        lines.append(f'{varname}_not_main = {{')
        for name, cps in entries:
            lines.append(lua_line(name, cps))
        lines.append('}')
    Path(outpath).write_text('\n'.join(lines) + '\n', encoding='utf-8')

# ── diff-all mode ─────────────────────────────────────────────────────────────

SOURCES = [
    ('agl',    'agl.lua',    False),
    ('pdftex', 'pdftex.lua', False),
    ('luaotf', 'luaotf.lua', False),
    ('ntx',    'ntx.lua',    False),
    ('pdf',    'pdf.lua',    False),
    ('tex',    'tex.lua',    True),   # multi-map, never subtractor
    ('cmr',    'cmr.lua',    False),
    ('cmex',   'cmex.lua',   False),
    ('cs',     'cs.lua',     False),
]

def diff_all(gldir, main_path):
    main = load_lua(main_path)
    main_names = set(main.keys())

    print(f'Main table: {len(main_names)} entries  ({main_path})')

    for name, filename, multimap in SOURCES:
        srcpath = gldir / filename
        if not srcpath.exists():
            print(f'  SKIP  {filename} (not found)')
            continue

        outpath = gldir / f'{name}-not-main.lua'
        header  = f'{filename} − {main_path.name}'

        if multimap:
            # tex: remove ALL occurrences of any name that is in main
            src = load_lua_multimap(srcpath)
            diff = [(n, cps) for n, cps in src if n not in main_names]
            write_diff(outpath, 'tex', diff, header)
        else:
            src  = load_lua(srcpath)
            diff = [(n, cps) for n, cps in src.items() if n not in main_names]
            write_diff(outpath, name, diff, header)

        print(f'  {filename:30s}  {len(src):5d} source  '
              f'{len(diff):5d} not in main  → {outpath.name}')

# ── check-changes mode ────────────────────────────────────────────────────────

def check_changes(generated_path, authoritative_path):
    gen  = load_lua(generated_path)
    auth = load_lua(authoritative_path)

    gen_names  = set(gen.keys())
    auth_names = set(auth.keys())

    only_gen  = sorted(gen_names  - auth_names)
    only_auth = sorted(auth_names - gen_names)
    both      = gen_names & auth_names
    diffvals  = sorted(n for n in both if gen[n] != auth[n])

    print(f'Generated:     {len(gen_names):5d} entries  ({generated_path})')
    print(f'Authoritative: {len(auth_names):5d} entries  ({authoritative_path})')
    print()

    if only_gen:
        print(f'Only in generated ({len(only_gen)}):')
        for n in only_gen:
            vals = ', '.join(f'0x{cp:04X}' for cp in gen[n])
            print(f'  ["{n}"] = {{ {vals} }}')
    else:
        print('Only in generated: (none)')

    print()
    if only_auth:
        print(f'Only in authoritative ({len(only_auth)}):')
        for n in only_auth:
            vals = ', '.join(f'0x{cp:04X}' for cp in auth[n])
            print(f'  ["{n}"] = {{ {vals} }}')
    else:
        print('Only in authoritative: (none)')

    print()
    if diffvals:
        print(f'Same name, different values ({len(diffvals)}):')
        for n in diffvals:
            gv = ', '.join(f'0x{cp:04X}' for cp in gen[n])
            av = ', '.join(f'0x{cp:04X}' for cp in auth[n])
            print(f'  ["{n}"]  generated={{{gv}}}  authoritative={{{av}}}')
    else:
        print('Same name, different values: (none)')

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    if args[0] == '--check-changes':
        if len(args) != 3:
            print('Usage: compare-glyphlists.py --check-changes <generated> <authoritative>')
            sys.exit(1)
        check_changes(Path(args[1]), Path(args[2]))
    else:
        if len(args) != 2:
            print('Usage: compare-glyphlists.py <glyphlists-dir> <main-table.lua>')
            sys.exit(1)
        diff_all(Path(args[0]), Path(args[1]))

if __name__ == '__main__':
    main()
