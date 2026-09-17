#!/usr/bin/env python3
"""
export-csv.py -- Export glyph-to-Unicode tables as CSV files.

Usage:
    python3 export-csv.py <glyphlists-dir>

Produces in <glyphlists-dir>:
  agl.csv, pdftex.csv, luaotf.csv, ntx.csv, pdf.csv, tex.csv,
  cmr.csv, cmex.csv, cs.csv   -- one CSV per source table
  glyphs-descriptions-sources.csv  -- combined table: all (name, unicode)
                                       pairs across all sources, with Unicode
                                       descriptions and source lists
"""

import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

# ── Loaders ───────────────────────────────────────────────────────────────────

_ENTRY = re.compile(r'^\s*\["([^"]+)"\]\s*=\s*\{([^}]+)\}')
_HEX   = re.compile(r'0x([0-9A-Fa-f]+)')

def load_lua(path):
    """Load a Lua table → list of (name, cps), preserving file order."""
    entries = []
    seen = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        m = _ENTRY.match(line)
        if not m:
            continue
        name = m.group(1)
        cps  = [int(h, 16) for h in _HEX.findall(m.group(2))]
        if cps and name not in seen:
            seen[name] = True
            entries.append((name, cps))
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

def hex_str(cps):
    return ' '.join(f'{cp:04X}' for cp in cps)

def unicode_desc(cp):
    try:
        return unicodedata.name(chr(cp))
    except ValueError:
        if 0xD800 <= cp <= 0xDB7F:
            return '<Non Private Use High Surrogate>'
        if 0xDB80 <= cp <= 0xDBFF:
            return '<Private Use High Surrogate>'
        if 0xDC00 <= cp <= 0xDFFF:
            return '<Low Surrogate>'
        if (0xE000 <= cp <= 0xF8FF or
                0xF0000 <= cp <= 0xFFFFF or
                0x100000 <= cp <= 0x10FFFF):
            return '<Private Use>'
        if (0x0000 <= cp <= 0x001F or
                0x007F <= cp <= 0x009F):
            return '<control>'
        return '<Unknown>'

def desc_str(cps):
    return '/'.join(unicode_desc(cp) for cp in cps)

# ── Per-source export ─────────────────────────────────────────────────────────

PER_SOURCE_HEADER = """\
# Format: two comma-delimited fields:
#   (1) glyph name--upper/lowercase letters and digits
#   (2) Unicode scalar values, space-separated if more than one
"""

# (csv_stem, lua_file, multimap)
SOURCES = [
    ('tex',    'tex.lua',    True),
    ('pdftex', 'pdftex.lua', False),
    ('pdf',    'pdf.lua',    False),
    ('luaotf', 'luaotf.lua', False),
    ('ntx',    'ntx.lua',    False),
    ('cs',     'cs.lua',     False),
    ('cmr',    'cmr.lua',    False),
    ('cmex',   'cmex.lua',   False),
    ('agl',    'agl.lua',    False),
]

def export_per_source(gldir):
    for stem, lua_file, multimap in SOURCES:
        srcpath = gldir / lua_file
        if not srcpath.exists():
            print(f'  SKIP  {lua_file} (not found)')
            continue

        entries = load_lua_multimap(srcpath) if multimap else load_lua(srcpath)
        entries_sorted = sorted(entries, key=lambda x: x[0])

        outpath = gldir / f'{stem}.csv'
        lines = [PER_SOURCE_HEADER.rstrip()]
        for name, cps in entries_sorted:
            lines.append(f'{name},{hex_str(cps)}')
        outpath.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'  {stem}.csv: {len(entries)} entries')

# ── Combined export ───────────────────────────────────────────────────────────

COMBINED_HEADER = """\
# Format: four comma-delimited fields:
#   (1) glyph name--upper/lowercase letters and digits
#   (2) Unicode scalar values, space-separated if more than one
#   (3) Unicode descriptions, /-separated if more than one
#   (4) List of sources, space-separated if more than one
"""

def export_combined(gldir):
    # combined: (name, cps_tuple) -> [source, ...]  in SOURCES order
    combined = defaultdict(list)

    for stem, lua_file, multimap in SOURCES:
        srcpath = gldir / lua_file
        if not srcpath.exists():
            continue
        entries = load_lua_multimap(srcpath) if multimap else load_lua(srcpath)
        seen_keys = set()
        for name, cps in entries:
            key = (name, tuple(cps))
            if key not in seen_keys:
                combined[key].append(stem)
                seen_keys.add(key)

    # Sort by (name, cps) — plain lexicographic on name, then numeric on cps
    rows = sorted(combined.items(), key=lambda x: (x[0][0], x[0][1]))

    outpath = gldir / 'glyphs-descriptions-sources.csv'
    lines = [COMBINED_HEADER.rstrip()]
    for (name, cps), sources in rows:
        lines.append(f'{name},{hex_str(list(cps))},{desc_str(list(cps))},{" ".join(sources)}')
    outpath.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'  glyphs-descriptions-sources.csv: {len(rows)} entries')

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    gldir = Path(sys.argv[1])

    print('Per-source CSVs:')
    export_per_source(gldir)
    print('Combined CSV:')
    export_combined(gldir)

if __name__ == '__main__':
    main()
