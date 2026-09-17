# Some directories and lists necessary for deployment of lua tables and not
# only for that.
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
import os

font_dir = texmf_font_dir("type1/public/amsfonts/cyrillic")
dest_dir = xdvipsk_cmap_dir("type1/public/amsfonts/cyrillic")
lua_tables = [ "wncyr10.lua", ]

lua_tables_copy = {
    "wncyr10.lua": [ "wncyb10", "wncyi10", "wncysc10", "wncyss10" ],
}
