# Some directories and lists necessary for deployment of lua tables and not noly for that
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
import os
font_dir = texmf_font_dir("type1/public/amsfonts/latxfont")
dest_dir = xdvipsk_cmap_dir("type1/public/amsfonts/latxfont")
lua_tables = []
lua_tables += [each for each in os.listdir(r"./") if each.endswith('.lua')]
lua_tables_copy = {
    "lasy10.lua": [ "lasy5", "lasy6", "lasy7", "lasy8", "lasy9", "lasyb10" ],
    "line10.lua": [ "linew10", ],
    "lcircle1.lua": [ "lcirclew", ],
    "lcmss8.lua": [ "lcmssb8", "lcmssi8" ]
}
