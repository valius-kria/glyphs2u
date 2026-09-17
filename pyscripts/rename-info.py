#!/usr/bin/env python 
# Finds glyphs that will be renamed by xdvipsk
from io_data import save_data_to_json
from glyph_maps import find_duplicates
import sys
import os

if __name__ == "__main__":
    lua_fname = sys.argv[1]
    # Check if we need to check all tables and do search
    if lua_fname == "all-tables": # do for all tables
        from config import lua_tables
        json_fname = 'all-duplicates.json'
        lua_fname = 'all tables from config.py'
        duplicates = {}
        for fname in lua_tables:
            dups =  find_duplicates(fname)
            if not dups == {}:
                duplicates[fname] = dups
    else: # do just for one table
        json_fname = os.path.basename(lua_fname).split(".")[0] \
            + "-duplicates.json"
        duplicates = find_duplicates(lua_fname)

    # Output results
    if len(duplicates) > 0:
        save_data_to_json(duplicates, json_fname)
        print(f"Duplicate renames of {lua_fname} saved in {json_fname}.")
    else:
        print(f"No duplicate renames found in {lua_fname}.")
