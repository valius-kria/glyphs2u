# Some directories and lists necessary for deployment of lua tables and not noly for that
# import os # just for the case when 'lua_tables' list is made by reading the
# directory content as in the following line:
# lua_tables += [each for each in os.listdir(r"./") if each.endswith('.lua')]

# Parameters actual for deployment
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
font_dir = texmf_font_dir("type1/public/niceframe-type1")
dest_dir = xdvipsk_cmap_dir("type1/public/niceframe-type1")
lua_tables = ["bbding10.lua",]
lua_tables_tocheck = [ "umranda", "umrandb", "dingbat", "karta15", ]
