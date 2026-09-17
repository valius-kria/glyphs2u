#!/usr/bin/env python
# Reads the glyph list from pfb file, removes some part of glyphs common with
# the builtin table, map them to some default values.
#
# Usage:
#   initial-lua.py <font>.lua        smart initial table (only glyphs needing
#                                    attention, unknowns get the sentinel)
#   initial-lua.py <font>.lua all    every glyph mapped to the sentinel, for
#                                    fonts with wrong/meaningless glyph names

import os
import sys
lua_fname = sys.argv[1]
all_sentinels = len(sys.argv) > 2 and sys.argv[2] == 'all'

if os.path.isfile(lua_fname):
    print(f"File {lua_fname} exists; exiting... ")
else:
    from io_glyph_data import write_lua_dict
    from glyph_maps import initial_lua, sentinel_lua
    lua_dict = sentinel_lua(lua_fname) if all_sentinels else initial_lua(lua_fname)
    write_lua_dict(lua_dict, lua_fname)
    kind = "all-sentinel" if all_sentinels else "initial"
    print(f"File {lua_fname} created ({kind}) with {len(lua_dict)} glyphs.")
