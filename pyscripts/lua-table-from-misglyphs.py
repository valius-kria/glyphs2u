#!/usr/bin/env python 
# Parses file about missing glyphs and outputs preliminary lua table
from io_glyph_data import parse_misglyphs_list, save_glist_to_lua

import sys
font = sys.argv[1]
mis_fname = sys.argv[2]

glyph_list = parse_misglyphs_list(font, mis_fname)

import os
path = os.path.split(mis_fname)[0]

if len(sys.argv) <= 3:
    lua_fname = "".join((path, font, ".lua"))
else:
    lua_fname = sys.argv[3]

save_glist_to_lua(glyph_list, lua_fname)
