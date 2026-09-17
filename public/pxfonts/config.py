# Some paths and lists necessary for deployment of lua tables and not noly for that
# import os # just for the case when 'lua_tables' list is made by reading the
# directory content as in the following line:
# lua_tables = [each for each in os.listdir(r"./") if each.endswith('.lua')]
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
font_dir = texmf_font_dir("type1/public/pxfonts")
dest_dir = xdvipsk_cmap_dir("type1/public/pxfonts")

# List all deployable tables in the current working directory
lua_tables = [
    "pxbmia.lua", "pxbsy.lua", "pxex.lua", "pxexa.lua", "pxmia.lua",
    "pxsy.lua", "pxsya.lua", "pxsyb.lua", "pxsyc.lua",
    "rpcxr.lua", "rpxb.lua", "rpxbi.lua", "rpxbmi.lua", "rpxbsc.lua",
    "rpxmi.lua", "rpxr.lua", "rpxsc.lua",
]
# For each table, copyable to more than one file, list other names where to copy
lua_tables_copy = {
    "pxex.lua": [ "pxbex", ],
    "pxexa.lua": [ "pxbexa", ],
    "pxsya.lua": [ "pxbsya", ],
    "pxsyb.lua": [ "pxbsyb", ],
    "pxsyc.lua": [ "pxbsyc", ],
    "rpcxr.lua": [ "rpcxb", "rpcxbi", "rpcxi", ],
    "rpxr.lua": [ "rpxi", ],
}
# lua_tables_not_needed = []
# lua_tables_tocheck = []
