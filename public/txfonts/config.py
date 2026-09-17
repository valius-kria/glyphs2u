# Some paths and lists necessary for deployment of lua tables and not noly for that
# import os # just for the case when 'lua_tables' list is made by reading the
# directory content as in the following line:
# lua_tables = [each for each in os.listdir(r"./") if each.endswith('.lua')]
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
font_dir = texmf_font_dir("type1/public/txfonts")
dest_dir = xdvipsk_cmap_dir("type1/public/txfonts")

# List all deployable tables in the current working directory
lua_tables = [
    "rtcxr.lua", "rtxb.lua", "rtxbi.lua", "rtxbmi.lua", "rtxbsc.lua", 
    "rtxmi.lua", "rtxr.lua", "rtxsc.lua", "t1xtt.lua", "t1xttsc.lua", 
    "tcxtt.lua", "txbmia.lua", "txbsy.lua", "txbtt.lua", "txbttsc.lua",
    "txex.lua", "txexa.lua", "txmia.lua", "txsy.lua", "txsya.lua",
    "txsyb.lua", "txsyc.lua", "txtt.lua", "txttsc.lua", 
]
# For each table, copyable to more than one file, list other names where to copy
lua_tables_copy = {
    "rtcxr.lua": [ "rtcxb", "rtcxbi", "rtcxi", "rtcxbss", "rtcxss", ],
    "rtxb.lua": [ "rtxbss", ],
    "rtxr.lua": [ "rtxi", "rtxss", ],
    "rtxsc.lua": [ "rtxsssc", ],
    "rtxbsc.lua": [ "rtxbsssc", ],
    "t1xtt.lua": [ "t1xbtt", ],
    "t1xttsc.lua": [ "t1xbttsc", ],
    "tcxtt.lua": [ "tcxbtt", ],
    "txex.lua": [ "txbex", ],
    "txexa.lua": [ "txbexa", ],
    "txsya.lua":[ "txbsya", ],
    "txsyb.lua":[ "txbsyb", ],
    "txsyc.lua": [ "txbsyc", ],
}
# lua_tables_not_needed = []
# lua_tables_tocheck = []
