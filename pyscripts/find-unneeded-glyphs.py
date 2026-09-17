#!/usr/bin/env python

# Finds and writes glyphs that are correctly defined in buil-in lua table and
# which are not in the font (may be were copied from other table)

from io_glyph_data import read_lua_table_in_dict
from io_data import save_data_to_json
import sys
import os

lua_fname = sys.argv[1]
json_fname = sys.argv[2]
# Read lua table into a dictionary
lua_map = read_lua_table_in_dict(lua_fname)
font_name = os.path.splitext(os.path.basename(lua_fname))[0]

if lua_map == {}:
    print('Something went wrong, dictionary is empty for %s.' % lua_fname)
else:
    from io_data import save_data_to_json
    from glyph_maps import unneeded_glyphs

    rm_glyphs = unneeded_glyphs(lua_map, font_name)
    if rm_glyphs == {}:
        print(f'No maps to remove in {lua_fname} found.')
    else:
        save_data_to_json(rm_glyphs, json_fname)
        print(f'The removal candidates from {lua_fname} are saved in {json_fname}.')
