#!/usr/bin/env python
# Copies values from another table
from io_glyph_data import read_lua_table_in_list, write_lua_table_list, \
    hex_codes_from_string, UNKNOWN_UNICODE
from io_data import load_dict_from_json
import os
import sys

if len(sys.argv) < 3:
    print("Source variable not given. Call like 'make source=path/some.lua copy-...-from'.")
    sys.exit(1)

# 1. Find font glyp list
json_fname = 'fonts-glyphs-dict.json'
fg_dict = load_dict_from_json(json_fname)

lua_fname = sys.argv[1]
font = os.path.splitext(os.path.basename(lua_fname))[0]
glyph_list = fg_dict[font]
# 2. Read lua tables in maps
list_one = read_lua_table_in_list(lua_fname)
list_two = read_lua_table_in_list(sys.argv[2])
map_one = { tupl[0]: tupl[1:] for tupl in list_one if not type(tupl) is str }
map_two = { tupl[0]: tupl[1:] for tupl in list_two if not type(tupl) is str }
# 3. Update the first map
is_changed = False
trivial = [UNKNOWN_UNICODE]
for glyph in glyph_list:
    if glyph in map_two.keys():
        codes2 = hex_codes_from_string(map_two[glyph][0])
        if glyph in map_one.keys():
            codes1 = hex_codes_from_string(map_one[glyph][0])
            if (codes1 == trivial and not codes2 == trivial):
                map_one[glyph] = map_two[glyph]
                is_changed = True
        else:
            if not codes2 == trivial:
                map_one[glyph] = map_two[glyph]
                is_changed = True
# 4. Write/report the results
if is_changed:
    list_one = ["return {",] + \
        [(glyph, ) + map_one[glyph] for glyph in map_one] + \
        ["}",]
    write_lua_table_list(list_one, lua_fname)
    print(f"Table '{lua_fname}' is updated.")
else:
    print(f"Nothing is changed in table '{lua_fname}'.")
