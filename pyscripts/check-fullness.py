#!/usr/bin/env python
# Check if all necessary glyphs are defined in the table

import os
import sys
from io_glyph_data import read_lua_table_in_dict
from io_data import save_data_to_json
from glyph_maps import wanted_glyphs

# 1. Read lua table into a dictionary
lua_fname = sys.argv[1]
lua_table_gset = set(read_lua_table_in_dict(lua_fname).keys())
# 2. Find definable glyphs of the font
font_name = os.path.splitext(lua_fname)[0]
wanted_gset = set(wanted_glyphs(font_name))
# 3. Compute the set difference
maybe_mis_glyphs = list(wanted_gset - lua_table_gset)
# 4. Output the results
num = len(maybe_mis_glyphs)
if num == 0:
    print(f"File {lua_fname} maps all necessary glyphs from font {font_name}.")
else:
    json_fname = font_name + '-undef.json'
    save_data_to_json(maybe_mis_glyphs, json_fname)
    print(f"Some glyphs from {json_fname} may be missing in {lua_fname}.")
