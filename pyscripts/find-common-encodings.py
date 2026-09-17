#!/usr/bin/env python
# Find encodings that are common to tables with distinct maps for the same
# glyphs.  Don't consider glyph names in encodings and lua tables, at least
# at the beginning.

from config import lua_tables
from io_data import load_dict_from_json, save_data_to_json
import os

# 1. Define file name map function
def lua2pfb(lua_fname: str) -> str:
    return os.path.splitext(lua_fname)[0] + '.pfb'

# 2. Define pfb file name list
pfb_list = list(map(lua2pfb, lua_tables))
# 3. Read dictionary, made from psfonts.map
pfb_map_fname = os.path.join(os.environ['project_dir'], 'pfb-tfm-map.json')
pfb_map = load_dict_from_json(pfb_map_fname)
# 4. Construct a map from pfb names to encoding lists
pfb_enc_map = {
    pfb_name: set(pfb_map.get(pfb_name, {}).values())
    for pfb_name in pfb_list }

# 5. Find common encodings
common_encs = {}
l = len(pfb_list)
for i in range(l):
    enc_set1 = pfb_enc_map[pfb_list[i]]
    if not enc_set1 == {None}:
        for j in range(i + 1, l):
            enc_set2 = pfb_enc_map[pfb_list[j]]
            if not enc_set2 == {None}:
                common = enc_set1 & enc_set2
                if not common == {}:
                    for enc in common:
                        val = [pfb_list[i], pfb_list[j]]
                        if common_encs.get(enc, []) == []:
                            common_encs[enc] = [ val,]
                        else:
                            common_encs[enc].append(val)

if common_encs == {}:
    print("No common encodings were found.")
else:
    save_data_to_json(common_encs, 'common-encodings.json')
    print("Saved common encodings in file 'common-encodings.json'.")
