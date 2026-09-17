# Some directories and lists necessary for deployment of lua tables and not noly for that
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
import os # just for the case when 'lua_tables' list is made by reading the
# directory content as in the following line:
lua_tables = [each for each in os.listdir(r"./") if each.endswith('.lua')]

# Parameters actual for deployment
font_dir = texmf_font_dir("type1/public/old-arrows")
dest_dir = xdvipsk_cmap_dir("type1/public/old-arrows")
lua_tables_copy = {
    "oasy10.lua": [ "oasy5", "oasy6", "oasy7", "oasy8", "oasy9",
                    "oabsy10", "oabsy5", "oabsy7", ],
}
