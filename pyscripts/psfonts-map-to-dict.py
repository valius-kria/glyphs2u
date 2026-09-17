#!/usr/bin/env python 
# Load psfonts.map and saves the parsed data into a dictionary

from io_tex_data import parse_psfonts_map
from io_data import save_dict_to_binary, save_data_to_json
import sys # To exit gracefully on error
import os

# --- Configuration ---
INPUT_MAP_FILE = sys.argv[1]
OUTPUT_JSON_FILE = 'psfonts-map.json'
OUTPUT_BINARY_FILE = 'psfonts-map.pkl'
# --- End Configuration ---

# Parse MAP and construct dictionary
psfont_dict = parse_psfonts_map(INPUT_MAP_FILE)

# Save dictionary to JSON file
if psfont_dict is not None: # Ensure parsing was successful before saving
     save_dict_to_binary(psfont_dict, OUTPUT_BINARY_FILE)
     save_data_to_json(psfont_dict, OUTPUT_JSON_FILE)
