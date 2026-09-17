#!/usr/bin/env python3
# Transforming the lua tables to glyph value tree, to investigate differences

from io_data import save_data_to_json, load_dict_from_json

# 1. Read data
json_input = "font_glyph_dict.json"
lua_tables_data = load_dict_from_json(json_input)

# 2. Construct a tree
glyph_uni_tree = {}

for font, glyph_dict in lua_tables_data.items():
    for glyph in glyph_dict.keys():
        values = glyph_dict[glyph]
        if glyph in glyph_uni_tree.keys():
            glyph_inst_list = glyph_uni_tree[glyph]
            included = False
            for variant in glyph_inst_list:
                if included:
                    continue
                else:
                    found = True
                    for i, val in enumerate(values):
                        if not variant[i] == val:
                            found = False
                    if found:
                        included = True
                        variant.extend([font,])
            if not included:
                glyph_inst_list += [ (values + [font,]),]
        else:
            glyph_uni_tree[glyph] = [ (values + [font,]), ]

# 3. Save data 
json_output = "glyph-uni-tree.json"
save_data_to_json(glyph_uni_tree, json_output)
