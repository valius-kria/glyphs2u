#!/usr/bin/env python
# Removes the glyphs from lua table that are in the same way defined in
# buil-in lua table
from io_glyph_data import read_lua_table_in_list, write_lua_table_list
from io_data import load_dict_from_json, path_file
import sys
import os
import shutil

lua_fname = sys.argv[1]
uglyhs_fname = sys.argv[2]

# Read lua table into a dictionary
lua_list = read_lua_table_in_list(lua_fname)
if lua_list == []:
    print('Something went wrong, list is empty for %s.' % lua_fname)
elif os.path.isfile(uglyhs_fname):
    shutil.copyfile(lua_fname, lua_fname + '.unclean')
    # Import unneeded glyph list
    uglyphs = load_dict_from_json(uglyhs_fname)
    # Filter the lua list
    new_lua_list = [ elm for elm in lua_list
                     if type(elm) is str or not elm[0] in uglyphs.keys() ]
    write_lua_table_list(new_lua_list, lua_fname)
else:
    print('Not changing %s, no file found with removable maps.' % lua_fname)
