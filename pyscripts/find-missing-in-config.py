#!/usr/bin/env python
# Find what fonts are missing in config.py
from io_data import load_dict_from_json, save_data_to_json
import os
import config

# The following variables might be not defined in config.py
lua_tables_copy = getattr(config, 'lua_tables_copy', {})
lua_tables_not_needed = getattr(config, 'lua_tables_not_needed', [])
lua_tables_tocheck = getattr(config, 'lua_tables_tocheck', [])

misfont_fname = 'config-missing-fonts.json'
fglyphs_dict_fname = 'fonts-glyphs-dict.json'
font_set = set(load_dict_from_json(fglyphs_dict_fname).keys())

config_tables = [ os.path.splitext(lua_table)[0]
                  for lua_table in config.lua_tables ]
if not lua_tables_copy == {}:
    for lua_table, font_list in lua_tables_copy.items():
        config_tables.extend(font_list)

if not lua_tables_not_needed == []:
    config_tables.extend(lua_tables_not_needed)
if not lua_tables_tocheck == []:
    config_tables.extend(lua_tables_tocheck)

misfonts = font_set - set(config_tables)
num = len(misfonts)
if num == 0:
    print("All fonts are mentioned in 'config.py' file.")
else:
    save_data_to_json(list(misfonts), misfont_fname)
    print(f"{num} font()s are missing in 'config.py': look at {misfont_fname}.")
