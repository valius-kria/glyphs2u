# Some directories and lists necessary for deployment of lua tables and not
# only for that.
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
import os

font_dir = texmf_font_dir("type1/public/amsfonts/euler")
dest_dir = xdvipsk_cmap_dir("type1/public/amsfonts/euler")
lua_tables = []
lua_tables += [each for each in os.listdir(r"./") if each.endswith('.lua')]
lua_tables_copy = {
    "eufm10.lua": [ "eufm5", "eufm7" ],
    "eufb10.lua": [ "eufb5", "eufb7" ],
    "eurm10.lua": [ "eurm5", "eurm7" ],
    "eurb10.lua": [ "eurb5", "eurb7" ],
    "eusm10.lua": [ "eusm5", "eusm7" ],
    "eusb10.lua": [ "eusb5", "eusb7" ],
    "euex10.lua": [ "euex7", "euex8", "euex9" ]
}
