# Some directories and lists necessary for deployment of lua tables and not noly for that

# Parameters actual for deployment
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
font_dir = texmf_font_dir("type1/public/yhmath")
dest_dir = xdvipsk_cmap_dir("type1/public/yhmath")
lua_tables = [ "yhcmex.lua", ]
