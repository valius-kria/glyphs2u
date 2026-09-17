#!/usr/bin/env python3
# For joining separate lua tables into one with a deeper structure

import importlib.util # for reading config.py files
from io_data import save_data_to_json, load_list_from_json, path_file
from io_glyph_data import write_lua_table_list
import pathlib
from pathlib import Path
import re
import sys
import os

# 1. Define your project root
project_root = os.environ['project_dir']
# 2. Get config file directories for public fonts
config_dirs = load_list_from_json(
    path_file("config-list.json", dname = project_root))

# 3. Define function to remove '.lua' extension and number sufix
def basic_font_name(fname: str) -> str:
    return re.sub(r'[0-9]*\.lua$', '', fname)

# 4. Define procedure to read data from one working directory
def read_tables_from_config(wd_path: Path):
    global lua_tables_dict
    global font_table_aliases_dict
    config_path = path_file("config.py", dname = wd_path)
    spec = None  # Initialize spec to None for the cleanup in except block
    os.chdir(wd_path) # to read the right dir for lua tables
    try:
        # Safely load the config.py file as a Python module
        spec = importlib.util.spec_from_file_location(
            name=f"config_{wd_path}",
            location=str(config_path))
        config_module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = config_module
        spec.loader.exec_module(config_module)

        # Safely get the 'lua_tables' and 'lua_tables_copy' attributes
        lua_tables = getattr(config_module, 'lua_tables', [])
        lua_tables_copy = getattr(config_module, 'lua_tables_copy', {})
        del sys.modules[spec.name]
        # Initialize local variables
        font_aliases =  {}
        tables_dict = {}
        # Read lua tables
        for lua_fname in lua_tables:
            with open(path_file(lua_fname, dname = wd_path)) as f:
                glyph_map_list = f.readlines()
            font_name = basic_font_name(lua_fname)
            font_noext = re.sub(r'\.lua$', '', lua_fname)
            if font_name in tables_dict.keys():
                if font_noext in tables_dict.keys():
                    print(f"! Keys {font_name} and {font_noext} are already in table list!")
                else:
                    font_name = font_noext
            tables_dict[font_name] = glyph_map_list
            font_aliases[font_noext] = font_name
            if lua_fname in lua_tables_copy.keys():
                copies = lua_tables_copy[lua_fname]
                for font in copies:
                    font_aliases[font] = font_name
            lua_tables_dict.update(tables_dict)
            font_table_aliases_dict.update(font_aliases)
    except Exception as e:
        print(f"Error processing {config_path}: {e}")
    finally:
        # Ensure the temporary module is removed from the system cache
        if spec and spec.name in sys.modules:
            del sys.modules[spec.name]

if __name__ == "__main__":
    # 5. Initialize global variables
    lua_tables_dict = {}
    font_table_aliases_dict = {}
    # 6. Update from all config.py
    for config_dir in config_dirs:
        read_tables_from_config(config_dir)
    # 7. Save results
    output_fname = path_file("font_glyph_maps.lua", dname = project_root)
    lua_tables_data = \
        { font: [ line for line in lua_tables_dict[font] if "[" in line ]
          for font in lua_tables_dict.keys() }
    # in the form of json for further investigation and optimization
    json_fname = path_file(output_fname, ext = ".json")
    save_data_to_json(lua_tables_data, json_fname)
    # in the form of aliases
    aliases_fname = path_file("lua_tables_aliases_dict.json",
                              dname = project_root)
    save_data_to_json(font_table_aliases_dict, aliases_fname)
