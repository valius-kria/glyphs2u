#!/usr/bin/env python 
# Saves the path for the given htf file
from io_data import load_data_from_json
import os
import sys

# Read htf file name
htf_name = os.sys.argv[1]
# Set the output file name
path_fname = htf_name + '.htf.path'

# Read htf_db.  'tests_dir' was the variable back when these scripts lived in
# xmlforge/tests; nothing has exported it since they moved here, so this raised
# KeyError however it was called.  htf_db.json is derived from a TeX tree, so it
# is only true of one branch and now lives under it -- map_path knows both that
# and how to find the branch when data_dir is not exported (run by hand).
from gpm_io import map_path

htf_db_fname = map_path('htf_db.json')
htf_db_dict = load_data_from_json(htf_db_fname)

# Find paths in db
try:
    paths = htf_db_dict[htf_name + '.htf']
except KeyError:
    paths = None

# Find the actual htf path
if paths:
    i = len(paths)
    if i == 1:
        i += -1
    else:
        while i > 0:
            i += -1
            if not 'alias' in paths[i]:
                break
    htf_path =  paths[i]
    with open(path_fname, "w", encoding="utf-8") as f:
        f.write(htf_path)
    print(f"The  path to {htf_name}.htf saved into '{path_fname}'.")
else:
    print(f"No suitable path was found to {htf_name}.htf.")
