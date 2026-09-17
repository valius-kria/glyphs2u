#!/usr/bin/env python
# Compare glyph-value sets saved in 'lua-table-glyph-values.json'

from io_data import load_dict_from_json, save_data_to_json
from compare_glyph_sets import font_gs_rels

# 1. Read data
json_input = "lua-table-glyph-values.json"
lua_tables_data = load_dict_from_json(json_input)

rels_fname = 'lua-tables-rels.txt'
with open(rels_fname, mode='w') as f:
    f.writelines(font_gs_rels(lua_tables_data))
print(f"Comparison of glyph-value sets of lua tables saved to the file: {rels_fname}")
