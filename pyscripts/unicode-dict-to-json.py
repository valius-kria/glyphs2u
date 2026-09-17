#!/usr/bin/env python 
# LaParses UnicodeData.txt (in case it is renewed) and saves the dictionary

from io_data import load_dict_from_binary, save_data_to_json

# --- Configuration ---
INPUT_BINARY_FILE = 'UnicodeData.pkl'
OUTPUT_JSON_FILE = 'UnicodeData.json'
# --- End Configuration ---

# Load dictionary
unidata = load_dict_from_binary(INPUT_BINARY_FILE)

# Save dictionary to JSON file
if unidata is not None: # Ensure parsing was successful before saving
     save_data_to_json(unidata, OUTPUT_JSON_FILE)

