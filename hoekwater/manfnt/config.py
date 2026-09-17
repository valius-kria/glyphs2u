# Some directories and lists necessary for deployment of lua tables and not noly for that
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
import os
font_dir = texmf_font_dir("type1/hoekwater/manfnt-font")
dest_dir = xdvipsk_cmap_dir("type1/hoekwater/manfnt-font")
lua_tables = [ "manfnt.lua", ]
