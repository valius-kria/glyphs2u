#!/usr/bin/env python 
# Load psfonts-map-data, extracts tfm-to-enc map and saves in a json file.
# Needed for finding glyph names in htf files

from io_data import load_dict_from_binary, save_data_to_json
import os

# --- Configuration ---
INPUT_DATA_FILE = os.path.join(os.environ['project_dir'], 'psfonts-map.pkl')
OUTPUT_JSON_FILE = 'tfm-enc-map.json'
# --- End Configuration ---

# Load psfonts.map data
psfont_dict = load_dict_from_binary(INPUT_DATA_FILE)

# Set the initial value of the resulting map
tfm_enc = {}

# Iterate over the dictionary
for tfm, val_dict in psfont_dict.items():
    if 'psfont' in val_dict.keys():
        pfb = val_dict['psfont']
        enc = val_dict.get('enc')
        tfm_enc[tfm] = ( enc if 'enc' in val_dict.keys() else pfb )

# Save dictionary to JSON file
save_data_to_json(tfm_enc, OUTPUT_JSON_FILE)
