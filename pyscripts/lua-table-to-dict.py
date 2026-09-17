#!/usr/bin/env python
# Parses lua table, which contains a glyph to unicode map, to dictionary form
# for convenient use with python scripts and saves in json file
from io_glyph_data import read_lua_table_in_dict
from io_data import save_data_to_json
import sys

lua_fname = sys.argv[1]
json_fname = sys.argv[2]

# Read lua table into a dictionary
lua_table_dict = read_lua_table_in_dict(lua_fname)

if lua_table_dict == {}:
    print('Something went wrong, dictionary is empty for %s.' % lua_fname)
else:
    save_data_to_json(lua_table_dict, json_fname)

