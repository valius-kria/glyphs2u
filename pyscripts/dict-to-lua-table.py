#!/usr/bin/env python3
# Writes a glyph name -> Unicode values dictionary, held as JSON, out as a
# Lua table with the Unicode names spelled out as trailing comments.
#
#   dict-to-lua-table.py <input.json> <output.lua>
#
# The JSON is the form the scripts read; the Lua table is the same data made
# readable, so that a change to the JSON can be seen in terms of the
# characters it affects.  Keeping it a `make' target stops the two drifting
# apart.

import sys

from io_data import load_dict_from_json
from io_glyph_data import write_lua_table_list
from unicode_descriptions import unicode_descr_for_code


def lua_entries(glyph_map):
    """Turn {name: [code, ...]} into the tuple list write_lua_table_list wants."""
    entries = []
    for name in sorted(glyph_map):
        codes = glyph_map[name]
        if isinstance(codes, str):
            codes = [codes]
        codes = ['0x%04X' % int(c, 16) for c in codes]
        descr = '/'.join(unicode_descr_for_code(c) for c in codes)
        entries.append((name, ' ' + ', '.join(codes) + ' ', '-- ' + descr))
    return entries


def main():
    if len(sys.argv) != 3:
        sys.exit('usage: dict-to-lua-table.py <input.json> <output.lua>')
    json_fname, lua_fname = sys.argv[1], sys.argv[2]
    glyph_map = load_dict_from_json(json_fname)
    lua_list = ['return {'] + lua_entries(glyph_map) + ['}']
    write_lua_table_list(lua_list, lua_fname)


if __name__ == '__main__':
    main()
