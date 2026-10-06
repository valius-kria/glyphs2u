#!/usr/bin/env python 
# Parses enc file and saves in the json file
from io_tex_data import parse_enc_file
from io_data import save_data_to_json
import os
import sys

# 1. Read encoding name from argument
enc_name = sys.argv[1]
# 2. Find the path to the encoding
with open(enc_name + ".path", "r", encoding="utf-8") as f:
    enc_file_content = f.read()
# 3. Read encoding file
enc_dict = parse_enc_file(enc_file_content)
# 4. Save the list
save_data_to_json(enc_dict, enc_name + '.json')
