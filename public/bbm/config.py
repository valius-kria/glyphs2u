# Some paths and lists necessary for deployment of lua tables and not noly for that
# import os # just for the case when 'lua_tables' list is made by reading the
# directory content as in the following line:
# lua_tables = [each for each in os.listdir(r"./") if each.endswith('.lua')]
from texmf_paths import font_dir_from_env, xdvipsk_cmap_dir
# These fonts are not distributed with TeX Live; set BBM_FONT_DIR
# to the directory holding them.
font_dir = font_dir_from_env("BBM_FONT_DIR")
dest_dir = xdvipsk_cmap_dir("type1/public/bbm")

# List all deployable tables in the current working directory
lua_tables = ["bbm10.lua", ]
# For each table, copyable to more than one file, list other names where to copy
lua_tables_copy = {
     "bbm10.lua": [
         "bbm12", "bbm17", "bbm5", "bbm6", "bbm7", "bbm8", "bbm9", "bbmb10",
         "bbmbx10", "bbmbx12", "bbmbx5", "bbmbx6", "bbmbx7", "bbmbx8", "bbmbx9",
         "bbmbxsl1", "bbmbxsl10", "bbmdunh1", "bbmdunh10", "bbmfib8", "bbminch",
         "bbmsl10", "bbmsl12", "bbmsl8", "bbmsl9", "bbmsltt1", "bbmsltt10",
         "bbmss10", "bbmss12", "bbmss17", "bbmss8", "bbmss9",
         "bbmssbx1", "bbmssbx10", "bbmssdc1", "bbmssdc10",
         "bbmssi10", "bbmssi12", "bbmssi17", "bbmssi8", "bbmssi9",
         "bbmssq8", "bbmssqi8",
         "bbmtt10", "bbmtt12", "bbmtt8", "bbmtt9", "bbmvtt10" ],
}
# lua_tables_not_needed = []
lua_tables_tocheck = []
