# Some paths and lists necessary for deployment of lua tables and not noly for that
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
import os # just for the case when 'lua_tables' list is made by reading the
# directory content as in the following line:
lua_tables = [each for each in os.listdir(r"./") if each.endswith('.lua')]
font_dir = texmf_font_dir("type1/public/mathpazo")
dest_dir = xdvipsk_cmap_dir("type1/public/mathpazo")

# List all deployable tables in the current working directory
# For each table, copyable to more than one file, list other names where to copy
# lua_tables_copy = {}
# lua_tables_not_needed = []
# lua_tables_tocheck = []
