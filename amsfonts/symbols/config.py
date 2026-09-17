# Some paths and lists necessary for deployment of lua tables and not noly for that
# import os
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
font_dir = texmf_font_dir("type1/public/amsfonts/symbols")
dest_dir = xdvipsk_cmap_dir("type1/public/amsfonts/symbols")
# List all deployable tables in the current working directory
lua_tables = ['msam10.lua', 'msbm10.lua']
# lua_tables += [each for each in os.listdir(r"./") if each.endswith('.lua')]
# For tables to copy to more than one file, list other names where to copy (no extension)
lua_tables_copy = {
    "msam10.lua": ["msam9", "msam8", "msam7", "msam6", "msam5"],
    "msbm10.lua": ["msbm9", "msbm8", "msbm7", "msbm6", "msbm5"]}
