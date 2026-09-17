#!/usr/bin/env python
# Compare glyph sets saved in 'fonts-glyphs-dict.json' with differences
# outside of built-in table.  Also should be removed glyph names starting
# with 'uni' and 'u'.
from io_data import load_dict_from_json, save_data_to_json
import os
from glyph_maps import glyph_list_to_add, fg_dict
from compare_glyph_sets import font_gs_rels

rels_fname = 'font-gs-rels-nobuilt.txt'
fglyphs_dict = { font: [ glyph for glyph in fg_dict[font]
                         if not glyph_list_to_add(glyph) == [] ]
                 for font in fg_dict.keys() }
save_data_to_json( fglyphs_dict, 'font-gsets-nobuilt.json')

with open(rels_fname, mode='w') as f:
    f.writelines(font_gs_rels(fglyphs_dict))
print(f"Comparison of glyph sets saved to the file: {rels_fname}")
