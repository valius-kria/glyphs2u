# Some directories and lists necessary for deployment of lua tables and not noly for that
# import os
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
font_dir = texmf_font_dir("type1/public/wasy-type1")
dest_dir = xdvipsk_cmap_dir("type1/public/wasy-type1")
lua_tables = ["wasy10.lua",
              "wasysl10.lua" # two glyphs named differently
              ]
# lua_tables += [each for each in os.listdir(r"./") if each.endswith('.lua')]
lua_tables_copy = {
    "wasy10.lua": ["wasy9", "wasy8", "wasy7", "wasy6", "wasy5", "wasyb10",],
    }
