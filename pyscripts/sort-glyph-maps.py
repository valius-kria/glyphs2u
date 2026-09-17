#!/usr/bin/env python3
# For sorting dictionaries of joined lua tables for better comparison
from io_data import save_data_to_json, load_list_from_json, path_file
import sys
import re

lua_fname = sys.argv[1]
new_lua_fname = sys.argv[2]

result_dict = {}
level1_line = None
level1_dict = {}
level1_list = []
level2_line = None
level2_list = []
rexp1 = r"^[a-z_]+ = "
rexp2 = r"^  \[.+\{"
rexp3 = r"^  \}"
rexp4 = r"    \["
rexp5 = r"^\}"
rexp6 = r"^  \[[^{}]+$"
with open(lua_fname, 'r', encoding='utf-8') as file:
    content = file.read().splitlines()
    for ln in content:
        m1 = re.search(rexp1, ln)
        m2 = re.search(rexp2, ln)
        m3 = re.search(rexp3, ln)
        m4 = re.search(rexp4, ln)
        m5 = re.search(rexp5, ln)
        m6 = re.search(rexp6, ln)
        if m4:
            level2_list.append(ln)
        elif m2:
            level2_line = ln
        elif m6:
            level1_list.append(ln)
        elif m1:
            level1_line = ln
        elif m3:
            level2_list.append(ln)
            level1_dict[level2_line] = level2_list
            level2_list = []
        elif m5:
            if level1_list == []:
                result_dict[level1_line] = level1_dict
                level1_dict = {}
            else:
                result_dict[level1_line] = level1_list
                level1_list == []

tables_dict = result_dict["font_glyphs_maps = {"]

with open(new_lua_fname, mode='w', encoding='utf-8') as outfile:
    outfile.write("font_glyphs_maps = {\n")
    for tname in sorted(tables_dict.keys()):
        outfile.write(tname + '\n')
        for line in tables_dict[tname]:
            outfile.write(line + '\n')
    outfile.write('}\n')
    outfile.write("font_maps_alias = {\n")
    for line in result_dict["font_maps_alias = {"]:
        outfile.write(line + '\n')
    outfile.write('}\n')
print(f"Lua table successfully saved to file: {new_lua_fname}")

