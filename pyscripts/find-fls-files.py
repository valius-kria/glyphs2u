#!/usr/bin/env python
from io_data import save_data_to_json
import os

prod_dir = '/media/X/files_db'
list_fname = 'fls-files-list.json'

file_list = [ os.path.join(path, f) for path, _, files in os.walk(prod_dir)
              for f in files if f.endswith('.fls') ]

save_data_to_json(file_list, list_fname)
print(f"Fls file list successfully saved to file: '{list_fname}'.")
