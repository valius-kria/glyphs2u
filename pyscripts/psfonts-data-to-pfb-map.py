#!/usr/bin/env python 
# Load psfonts-map-data, transforms them to pfb-to-tfm map and saves in json file

from io_data import load_dict_from_binary, save_data_to_json
import os

# --- Configuration ---
INPUT_DATA_FILE = os.path.join(os.environ['project_dir'], 'psfonts-map.pkl')
OUTPUT_JSON_FILE = 'pfb-tfm-map.json'
# --- End Configuration ---

# Load psfonts.map data
psfont_dict = load_dict_from_binary(INPUT_DATA_FILE)

# Set the initial value of the resulting map
pfb_tfm = {}

# Iterate over the dictionary
for tfm, val_dict in psfont_dict.items():
    if 'psfont' in val_dict.keys():
        pfb = val_dict['psfont']
        enc = val_dict.get('enc')
        if pfb in pfb_tfm.keys():
            pfb_tfm[pfb][tfm] = enc
        else:
            pfb_tfm[pfb] = { tfm: enc }


# Save dictionary to JSON file
save_data_to_json(pfb_tfm, OUTPUT_JSON_FILE)
