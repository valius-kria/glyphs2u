#!/usr/bin/env python 
# Load psfonts-map-data, extracts tfm-to-enc map and saves in a json file.
# Needed for finding glyph names in htf files

from io_tex_data import parse_psfonts_map
from io_data import save_data_to_json
import sys
import os

# --- Configuration ---
INPUT_MAP_FILE = sys.argv[1]
OUTPUT_JSON_FILE = 'psfonts-map-tfm-data.json'
# --- End Configuration ---

# Parse MAP and construct dictionary
psfont_dict = parse_psfonts_map(INPUT_MAP_FILE)

# Set the initial value of the resulting map
tfm_data = {}

# Iterate over the dictionary
for tfm, val_dict in psfont_dict.items():
    if 'psfont' in val_dict.keys():
        pfb = val_dict['psfont']
        tfm_data[tfm] = { "pfb": pfb }
        if 'enc' in val_dict.keys():
            tfm_data[tfm]['enc'] = val_dict['enc']

# Save dictionary to JSON file
save_data_to_json(tfm_data, OUTPUT_JSON_FILE)
