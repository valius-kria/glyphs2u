#!/usr/bin/env python 
# Load psfonts-map-data, transforms them to pfb-to-tfm map and saves in json file

from io_data import load_dict_from_json, save_data_to_json
import os

# --- Configuration ---
INPUT_DATA_FILE = os.path.join(os.environ['project_dir'], 'pfb-tfm-map.json')
OUTPUT_JSON_FILE = 'enc-pfb-map.json'
# --- End Configuration ---

# Load psfonts.map data
pfb_dict = load_dict_from_json(INPUT_DATA_FILE)

# Set the initial value of the resulting map
enc_pfb = {}
# Iterate over the dictionary
for pfb, tfm_dict in pfb_dict.items():
    for tfm, enc in tfm_dict.items():
        if enc in enc_pfb.keys():
            enc_pfb[enc] = enc_pfb.get(enc, []) + [pfb,]
        else:
            enc_pfb[enc] = [pfb,]

# Save dictionary to JSON file
save_data_to_json(enc_pfb, OUTPUT_JSON_FILE)
