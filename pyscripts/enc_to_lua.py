#!/usr/bin/env python
## Generate a lua table from enc dictionary.
# The Lua table is like ones obtained from htf files.
from io_data import load_data_from_json
import os
import sys

# 1. Get enc file name
enc_name = sys.argv[1]
# 2. Read encoding dictionary
enc_dict = load_data_from_json(enc_name + ".enc.json")
# 3. Define output dictionary format
lua_lines = [ 'return\n', '{\n', '''\t["''' + enc_name + '''"] =\n''',
              '\t{\n', '''\t\t["chars"] =\n''', '\t\t{\n' ] + \
            [ '''\t\t\t["''' + ind + '''"] =\n\t\t\t{\n\t\t\t\t["value"] = "''' + \
              enc_dict[ind] + '",\n\t\t\t},\n'
              for ind in  enc_dict.keys() ] + \
            [ '\t\t},\n', '\t},\n', '},\n', ]

# 4. Define output file name
lua_fname = enc_name + ".enc.lua"
with open(lua_fname, mode='w', encoding='utf-8') as outfile:
    outfile.writelines(lua_lines)
print(f"Encoding {enc_name} data written in file {lua_fname} as a lua table.")
