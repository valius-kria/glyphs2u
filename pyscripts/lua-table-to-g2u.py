#!/usr/bin/env python3
# Parses lua table to dictionary and saves to g2u table format
from io_glyph_data import read_lua_table_in_dict, lua_dict_to_g2u_list, write_g2u_list
import sys
import os

lua_fname = sys.argv[1]

# Read lua table into a dictionary
lua_table_dict = read_lua_table_in_dict(lua_fname)
if lua_table_dict == {}:
    print('Something went wrong, dictionary is empty for %s.' % lua_fname)
else:
    g2u_fname = os.path.basename(lua_fname).split(".")[0] + ".g2u"
    write_g2u_list(lua_dict_to_g2u_list(lua_table_dict), g2u_fname)
