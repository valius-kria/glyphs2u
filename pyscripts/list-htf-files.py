#!/usr/bin/env python 
# Finds all htf files in the given directory
from io_data import load_data_from_json, save_data_to_json
import sys
import os

# Get directory name
top_dir = sys.argv[1]

# Get the data base file
htf_db_fname = 'htf_db.json'
if os.path.isfile(htf_db_fname):
    htf_db_dict = load_data_from_json(htf_db_fname)
else:
    htf_db_dict = {}

# Add files
for loop_root, _, fnames in os.walk(top_dir):
    for fn in fnames:
        if fn.endswith('.htf'):
            if fn in htf_db_dict.keys():
                htf_db_dict[fn].append(loop_root)
            else:
                htf_db_dict[fn] = [loop_root,]

# Save the result
save_data_to_json(htf_db_dict, htf_db_fname)
