#!/usr/bin/env python3
# Transforming the data from lua tables to strings in the form glyph+values

from io_data import save_data_to_json, load_dict_from_json
from io_glyph_data import is_hex_string

# 1. Read data
json_input = "font_glyph_dict.json"
lua_tables_data = load_dict_from_json(json_input)

# 2. Construct font-glyph-map sets
font_glyph_values = {}

for font, glyph_dict in lua_tables_data.items():
    glyph_value_list = []
    for glyph in glyph_dict.keys():
        values = glyph_dict[glyph]
        codes = [item for item in values if is_hex_string(item)]
        glyph_values = ' '.join( [glyph,] + codes )
        glyph_value_list.extend([ glyph_values, ])
    font_glyph_values[font] = glyph_value_list

# 3. Save data
json_output = "lua-table-glyph-values.json"
save_data_to_json(font_glyph_values, json_output)
