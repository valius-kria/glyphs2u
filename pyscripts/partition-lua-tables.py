#!/usr/bin/env python
# Partition by equality glyph-value sets saved in 'lua-table-glyph-values.json'

from io_data import load_dict_from_json, save_data_to_json
from compare_glyph_sets import group_equal_sets

# 1. Read data
json_input = "lua-table-glyph-values.json"
lua_tables_data = load_dict_from_json(json_input)
# 2. Partition sets by equality
map_fname = 'lua-tables-partition-map.json'
partition_map = { elm: group[1] for group in group_equal_sets(lua_tables_data)
                  for elm in group[1:] }
# 3. Save results
save_data_to_json(partition_map, map_fname)
