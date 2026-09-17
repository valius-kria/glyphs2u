# Some paths and lists necessary for deployment of lua tables and not noly for that
# import os # just for the case when 'lua_tables' list is made by reading the
# directory content as in the following line:
# lua_tables = [each for each in os.listdir(r"./") if each.endswith('.lua')]
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
font_dir = texmf_font_dir("type1/public/stix")
dest_dir = xdvipsk_cmap_dir("type1/public/stix")

# List all deployable tables in the current working directory
lua_tables = [
    "STIXGeneral-Regular.lua", "STIXGeneral-Bold.lua", "STIXGeneral-Italic.lua",
    "STIXGeneral-BoldItalic.lua", "stix-mathit.lua", "stix-mathit-bold.lua",
    "stix-mathsf.lua", "stix-mathsfit.lua", "stix-mathsfit-bold.lua",
    "stix-mathsf-bold.lua", "stix-mathbbit-bold.lua", "stix-mathbbit.lua",
    "stix-mathcal.lua", "stix-mathcal-bold.lua", "stix-mathex.lua",
    "stix-mathscr.lua", "stix-mathscr-bold.lua", ]
# For each table, copyable to more than one file, list other names where to copy
lua_tables_copy = {
     "stix-mathex.lua": ["stix-mathex-bold", ], }
lua_tables_not_needed = [
    "stix-mathrm", "stix-mathrm-bold", "stix-mathbb", "stix-mathbb-bold", 
    "stix-mathtt-bold", "stix-mathtt", "stix-mathfrak-bold", "stix-mathfrak" ]
# lua_tables_tocheck = []

