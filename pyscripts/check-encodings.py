#!/usr/bin/env python
# Find encoding files, read glyph names, find if lua tables maps them differently.

from io_data import load_dict_from_json, save_data_to_json
from io_tex_data import apply_kpsewhich, KPSEWHICH
from io_glyph_data import read_encoding_in_list
import os
from glyph_maps import renaming_maps

cmd_prefix = KPSEWHICH + ' '
enc_map_fname = 'common-encodings.json'
enc_map = load_dict_from_json(enc_map_fname)

# Read encodings and collect pfb names
enc_glyph_dict = {}
pfb_set = set({})
for enc, pfb_pairs in enc_map.items():
    enc_fname = apply_kpsewhich(enc).splitlines()[0]
    name_set = set(read_encoding_in_list(enc_fname)[1:]) # remove encoding name
    enc_glyph_dict[enc] = list(name_set) # duplicates of .notdef removed
    for pfb_pair in pfb_pairs:
        for pfb in pfb_pair:
            pfb_set.add(pfb)

pfb_map_dict = renaming_maps(pfb_set)

# Reexamine the encoding and pfb pairs for glyph mapping coincidence
dupl_encs = {}
for enc, pfb_pairs in enc_map.items():
    enc_glyphs = set(enc_glyph_dict[enc])
    for pfb_pair in pfb_pairs:
        glyph_map0 = pfb_map_dict[pfb_pair[0]]
        glyph_map1 = pfb_map_dict[pfb_pair[1]]
        common_glyphs = set(glyph_map0.keys()) | set(glyph_map1.keys())
        diff_glyphs = [ pfb for pfb in  common_glyphs
                        if ( ( not pfb in glyph_map1.keys() )
                             or ( not  pfb in glyph_map0.keys() )
                             or ( not glyph_map0[pfb] == glyph_map1[pfb] ) ) ]
        common_glyphs = enc_glyphs & set(diff_glyphs)
        if not len(common_glyphs) == 0:
            pfb_pair.extend(common_glyphs)
            if dupl_encs.get(enc, []) == []:
                dupl_encs[enc] = [pfb_pair,]
            else:
                dupl_encs[enc].append(pfb_pair)

if dupl_encs == {}:
    print("None encoding needs duplication.")
else:
    save_data_to_json(dupl_encs, 'dupl-encodings.json')
    print("Encodings to duplicate saved in 'dupl-encodings.json'.")
