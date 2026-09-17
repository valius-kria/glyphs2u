#!/usr/bin/env python
from io_data import load_list_from_json, path_file

import shutil

list_fname='fls-files-list.json'
fls_dir = 'fls-files'
file_list = load_list_from_json(list_fname)
total = len(file_list)

print(f"Total number of files to copy: {total}.")
num = 0
for source in file_list:
    destination = path_file(source, dname = fls_dir)
    shutil.copy(source, destination)
    num += 1
    if num % 100 == 0:
    # Update progress
        progress = (num + 1) / total * 100
        print(f"\rProgress: {progress:.1f}%", end="")
print("\nDone!")
