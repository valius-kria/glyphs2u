#!/usr/bin/env python3
"""
parse-glyphlists.py -- Parse TeX Live glyph-to-Unicode source files
into Lua tables for use in the glyphlists/ investigation workflow.

Usage:
    python3 parse-glyphlists.py <sources-dir> [<output-dir>]

<sources-dir>  directory of source files produced by 'make load-sources'
               (e.g. glyphlists/sources/2026/)
<output-dir>   where to write .lua output files (default: current directory)

Output files:
    agl.lua    -- Adobe Glyph List (glyphlist.txt)
    pdftex.lua -- pdftex glyphtounicode.tex
    luaotf.lua -- luaotfload-glyphlist.lua
    ntx.lua    -- glyphtounicode-ntx.tex
    pdf.lua    -- pdfglyphlist.txt
    tex.lua    -- texglyphlist.txt  (multi-map, not valid Lua)
    cmr.lua    -- glyphtounicode-cmr.tex
    cmex.lua   -- glyphtounicode-cmex.tex
    cs.lua     -- glyphtounicode-cs.tex

Private-area codepoints (U+E000-U+F8FF and supplementary PUA) are kept
but annotated with a trailing  -- pua  comment in every output file.
"""

import re
import sys
from pathlib import Path

# ── Private Use Area detection ────────────────────────────────────────────────

PUA_RANGES = [(0xE000, 0xF8FF), (0xF0000, 0xFFFFF), (0x100000, 0x10FFFF)]

def is_pua(cp):
    return any(lo <= cp <= hi for lo, hi in PUA_RANGES)

# ── UTF-16 surrogate pair → codepoint ────────────────────────────────────────

def decode_hex_list(parts):
    """Convert a list of hex strings (possibly with surrogate pairs) to codepoints."""
    result = []
    i = 0
    while i < len(parts):
        v = int(parts[i], 16)
        if 0xD800 <= v <= 0xDBFF and i + 1 < len(parts):
            low = int(parts[i + 1], 16)
            if 0xDC00 <= low <= 0xDFFF:
                result.append((v - 0xD800) * 0x400 + (low - 0xDC00) + 0x10000)
                i += 2
                continue
        result.append(v)
        i += 1
    return result

# ── Lua line formatting ───────────────────────────────────────────────────────

def lua_line(name, cps):
    vals = ', '.join(f'0x{cp:04X}' for cp in cps)
    mark = '  -- pua' if any(is_pua(cp) for cp in cps) else ''
    return f'  ["{name}"] = {{ {vals} }},{mark}'

# ── Parsers ───────────────────────────────────────────────────────────────────

def parse_txt(path):
    """glyphlist.txt / pdfglyphlist.txt: Name;HEX HEX ..."""
    entries = []
    for line in Path(path).read_text(encoding='latin-1').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ';' not in line:
            continue
        name, hexpart = line.split(';', 1)
        cps = decode_hex_list(hexpart.split())
        if cps:
            entries.append((name.strip(), cps))
    return entries

def parse_txt_multimap(path):
    """texglyphlist.txt: Name;HEX HEX,HEX HEX  (comma separates alternatives)"""
    entries = []
    for line in Path(path).read_text(encoding='latin-1').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ';' not in line:
            continue
        name, hexpart = line.split(';', 1)
        for alt in hexpart.split(','):
            cps = decode_hex_list(alt.split())
            if cps:
                entries.append((name.strip(), cps))
    return entries

def parse_tex(path):
    r"""glyphtounicode.tex and variants: \pdfglyphtounicode{Name}{HEX HEX}
    NTX uses \let\p\pdfglyphtounicode then \p{Name}{HEX}.
    """
    entries = []
    pattern = re.compile(r'\\(?:pdfglyphtounicode|p)\{([^}]+)\}\{([^}]*)\}')
    for m in pattern.finditer(Path(path).read_text(encoding='latin-1')):
        name = m.group(1).strip()
        hexpart = m.group(2).strip()
        if not hexpart:
            continue
        cps = decode_hex_list(hexpart.split())
        if cps:
            entries.append((name, cps))
    return entries

def parse_luaotf(path):
    """luaotfload-glyphlist.lua: ["GlyphName"]=<decimal integer>"""
    entries = []
    pattern = re.compile(r'\["([^"]+)"\]\s*=\s*(\d+)')
    for m in pattern.finditer(Path(path).read_text(encoding='utf-8')):
        name = m.group(1)
        cp = int(m.group(2))
        entries.append((name, [cp]))
    return entries

# ── Writer ────────────────────────────────────────────────────────────────────

def write_lua(outpath, varname, entries, source_desc, multimap=False):
    lines = [
        f'-- Generated from {source_desc}',
        '',
    ]
    if multimap:
        lines += [
            '-- Multi-map: duplicate keys are intentional.',
            '-- This file is NOT a valid Lua table; do not load with require().',
            '',
        ]
        for name, cps in entries:
            lines.append(lua_line(name, cps))
    else:
        lines.append(f'{varname} = {{')
        for name, cps in entries:
            lines.append(lua_line(name, cps))
        lines.append('}')

    Path(outpath).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'  {Path(outpath).name}: {len(entries)} entries')

# ── Source table ──────────────────────────────────────────────────────────────

# (output_lua, varname, filename_in_srcdir, parser_key, multimap)
SOURCES = [
    ('agl.lua',    'glyphs_agl',    'glyphlist.txt',              'txt',      False),
    ('pdftex.lua', 'glyphs_pdftex', 'glyphtounicode.tex',         'tex',      False),
    ('luaotf.lua', 'glyphs_luaotf', 'luaotfload-glyphlist.lua',   'luaotf',   False),
    ('ntx.lua',    'glyphs_ntx',    'glyphtounicode-ntx.tex',     'tex',      False),
    ('pdf.lua',    'glyphs_pdf',    'pdfglyphlist.txt',           'txt',      False),
    ('tex.lua',    'glyphs_tex',    'texglyphlist.txt',           'txmulti',  True),
    ('cmr.lua',    'glyphs_cmr',    'glyphtounicode-cmr.tex',     'tex',      False),
    ('cmex.lua',   'glyphs_cmex',   'glyphtounicode-cmex.tex',    'tex',      False),
    ('cs.lua',     'glyphs_cs',     'glyphtounicode-cs.tex',      'tex',      False),
]

PARSERS = {
    'txt':     parse_txt,
    'txmulti': parse_txt_multimap,
    'tex':     parse_tex,
    'luaotf':  parse_luaotf,
}

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    srcdir = Path(sys.argv[1])
    outdir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('.')

    print(f'Sources: {srcdir}')
    print(f'Output:  {outdir}')

    for outname, varname, srcfile, parser_key, multimap in SOURCES:
        srcpath = srcdir / srcfile
        if not srcpath.exists():
            print(f'  SKIP  {srcfile} (not found)')
            continue
        entries = PARSERS[parser_key](srcpath)
        write_lua(outdir / outname, varname, entries,
                  f'{srcdir}/{srcfile}', multimap)

if __name__ == '__main__':
    main()
