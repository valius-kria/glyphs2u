#!/usr/bin/env python3
# Parses g2u table to list, transforms to lua table dictionary and saves
from io_glyph_data import read_g2u_table_in_list, g2u_list_to_lua_dict, \
    write_lua_table_list, lua_dict_to_list
import sys
import os

g2u_fname = sys.argv[1]

# Read g2u table into a list of pairs
g2u_list = read_g2u_table_in_list(g2u_fname)
if g2u_list == []:
    print('Something went wrong, g2u list is empty for %s.' % g2u_fname)
else:
    lua_fname = os.path.basename(g2u_fname).split(".")[0] + ".lua"
    if os.path.isfile(lua_fname):
        print("There is a file with name '%s'. Re(move|name) to regenerate it."
              % lua_fname)
    else:
        write_lua_table_list(lua_dict_to_list(g2u_list_to_lua_dict(g2u_list)),
                             lua_fname)
