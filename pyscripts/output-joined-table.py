#!/usr/bin/env python3
# For ouputting joined lua tables from data in 'font_glyph_maps.json' wrt
# comparison results in 'lua-tables-partition-map.json' plus from aliases data

from io_data import load_dict_from_json, save_data_to_json, path_file
import os

# 1. Define your project root
project_root = os.environ['project_dir']
# 2. Input data
tables_data_fname = "font_glyph_maps.json"
comparison_data_fname = "lua-tables-partition-map.json"
aliases_data_fname = "lua_tables_aliases_dict.json"
tables_data = load_dict_from_json(tables_data_fname)
comparison_data = load_dict_from_json(comparison_data_fname)
aliases_data = load_dict_from_json(aliases_data_fname)

# 3. Compose aliases data with comparison data
aliases_map = { name: comparison_data[aliases_data[name]]
                for name in aliases_data.keys() }
# 4. Collect tables-representatives
aliases_values = sorted(set(aliases_map.values()))

# 5. Save results
output_fname = path_file("font_glyph_maps.lua", dname = project_root)
with open(output_fname, mode='w', encoding='utf-8') as outfile:
    outfile.write("font_glyphs_maps = {\n")
    for table_name in aliases_values:
        outfile.write("  [\'" + table_name + "\'] = {\n")
        lines = tables_data[table_name]
        for line in lines:
            outfile.write("  " + line)
        outfile.write("  },\n")
    outfile.write("}\nfont_maps_alias = {\n")
    for table_name in sorted(aliases_map.keys()):
        outfile.write("  [\'" + table_name + "\'] = \'" + \
                      aliases_map[table_name] + "\',\n")
    outfile.write("}\n")
    print(f"Joined lua tables and aliases successfully saved to file: {output_fname}")
