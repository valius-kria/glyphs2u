#!/usr/bin/env python 
# Load UnicodeData.txt saves data into the dictionary

from io_glyph_data import parse_csv_to_dict
from io_data import save_dict_to_binary, save_data_to_json
import sys # To exit gracefully on error

# --- Configuration ---
INPUT_CSV_FILE = 'unicode-data/UnicodeData.txt'
OUTPUT_JSON_FILE = 'UnicodeData.json'
OUTPUT_BINARY_FILE = 'UnicodeData.pkl'
CSV_DELIMITER = ';'            # <<< The delimiter used in your CSV
# --- End Configuration ---

# Parse CSV and construct dictionary
unidata = parse_csv_to_dict(INPUT_CSV_FILE, delimiter=CSV_DELIMITER)

# Save dictionary to JSON file
if unidata is not None: # Ensure parsing was successful before saving
     save_dict_to_binary(unidata, OUTPUT_BINARY_FILE)
     save_data_to_json(unidata, OUTPUT_JSON_FILE)
