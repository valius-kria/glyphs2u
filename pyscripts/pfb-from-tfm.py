#!/usr/bin/env python
from io_data import load_list_from_json, load_dict_from_json, save_data_to_json
import os

tfm_list_fname = 'prod-tfm-list.json'
pfb_dict_fname = 'prod-pfb-dict.json'
pfb_tfm_map_fname = 'pfb-tfm-map.json'

pfb_tfm_map = load_dict_from_json(pfb_tfm_map_fname)
tfm_pfb_map = { tfm: pfb for pfb, tfms in pfb_tfm_map.items()
                for tfm in tfms }
tfm_list = [ os.path.splitext(tfm_fn)[0]
             for tfm_fn in load_list_from_json(tfm_list_fname) ]

pfb_dict = {}
for tfm in tfm_list:
    pfb = tfm_pfb_map.get(tfm, None)
    if not pfb == None:
        pfb_dict[pfb] = pfb_dict.get(pfb, []) + [tfm, ]

save_data_to_json(pfb_dict, pfb_dict_fname)
print(f"PFB map to production tfm's is saved in file '{pfb_dict_fname}'.")
