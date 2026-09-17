#!/usr/bin/env python
# Inserts proposed new glyph names into <font>.lua for the renaming clashes
# recorded in <font>-duplicates.json (produced by rename-info.py).  For every
# glyph that must be renamed, a ready-made replacement line is inserted right
# after the original entry, commented out with a '-->' marker and carrying the
# proposed name already placed among the codes, e.g.
#
#     ['uniE234'] = { 0x210B },-- SCRIPT CAPITAL H
#     --> ['uniE234'] = { 0x210B, 'uni210B.alt1' },-- SCRIPT CAPITAL H
#
# To apply a proposal by hand: delete (or comment) the original line and remove
# the '--> ' marker from the replacement.  The script is idempotent: it first
# drops any '-->' lines it inserted before, then regenerates them, and skips
# entries that already carry the proposed name.
from io_glyph_data import is_hex_string
from io_data import load_data_from_json
import os
import re
import sys

MARKER = '--> '
# indent, quote, glyph name, brace contents, trailing (comment) after '},'
ENTRY_RE = re.compile(r"^(\s*)\[(['\"])([^'\"]+)\2\] *= *\{([^{}]+)\},(.*)$")


def rename_map(duplicates: dict) -> dict:
    """Flatten {contested: {keep, rename:{orig: proposed}}} to {orig: proposed},
    dropping entries with no proposal (left for manual naming)."""
    result = {}
    for group in duplicates.values():
        for orig, proposed in group.get('rename', {}).items():
            if proposed:
                result[orig] = proposed
    return result


def replacement_line(m, proposed: str) -> str:
    indent, quote, name, inner, trailing = m.groups()
    codes = [t for t in re.split(r'[ ,]+', inner) if is_hex_string(t)]
    new_inner = ' ' + ', '.join(codes + ["'%s'" % proposed]) + ' '
    return '%s%s[%s%s%s] = {%s},%s' % (
        indent, MARKER, quote, name, quote, new_inner, trailing)


def has_name(inner: str, proposed: str) -> bool:
    """True if this entry already carries 'proposed' as its explicit name."""
    return any(t.strip('\'"') == proposed
               for t in re.split(r'[ ,]+', inner) if t and not is_hex_string(t))


if __name__ == "__main__":
    lua_fname = sys.argv[1]
    json_fname = os.path.basename(lua_fname).split(".")[0] + "-duplicates.json"
    if not os.path.exists(json_fname):
        print(f"No {json_fname}; run 'make {json_fname}' first.")
        sys.exit(0)

    renames = rename_map(load_data_from_json(json_fname))
    with open(lua_fname, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    out, inserted = [], 0
    for ln in lines:
        if ln.lstrip().startswith(MARKER.strip()):  # drop our earlier proposals
            continue
        out.append(ln)
        m = ENTRY_RE.match(ln)
        if m:
            name, inner = m.group(3), m.group(4)
            proposed = renames.get(name)
            if proposed and not has_name(inner, proposed):
                out.append(replacement_line(m, proposed))
                inserted += 1

    with open(lua_fname, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    print(f"Inserted {inserted} proposed rename(s) into {lua_fname}.")
