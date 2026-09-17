#!/usr/bin/env python 
# Compute glyph-set differences between groups saved in 'groups-by-glyphs.json'
from io_data import load_list_from_json, save_data_to_json

group_list_fname = 'groups-by-glyphs.json'
group_list = load_list_from_json(group_list_fname)
group_dict = { i : group_list[i] for i in range(len(group_list)) }
diffs_dict = group_dict
for i, group in diffs_dict.items():
    for j, group2 in diffs_dict.items():
        
