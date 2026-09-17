# Some directories and lists necessary for deployment of lua tables and not
# only for that.
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
import os
font_dir = texmf_font_dir("type1/public/cjhebrew")
dest_dir = xdvipsk_cmap_dir("type1/public/cjhebrew")
lua_tables = ["cjheblsm.lua",]
lua_tables_copy = {
    "cjheblsm.lua": ["cjhebltx"],
}

