# Some directories and lists necessary for deployment of lua tables and not noly for that
# import os # just for the case when 'lua_tables' list is made by reading the
# directory content as in the following line:
# lua_tables += [each for each in os.listdir(r"./") if each.endswith('.lua')]

from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
font_dir = texmf_font_dir("type1/public/marvosym")
dest_dir = xdvipsk_cmap_dir("type1/public/marvosym")
lua_tables = [ "marvosym.lua", ]
