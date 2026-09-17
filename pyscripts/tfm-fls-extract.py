#!/usr/bin/env python
from io_data import save_data_to_json
import os
import sys
import re

fls_dir = 'fls-files'
tfm_list_fname = 'prod-tfm-list.json'

tfm_set = set({})
num = 0
rexp = re.compile("/([^/]+\\.tfm)")
with os.scandir(fls_dir) as d:
    for fls in d:
        if fls.is_file() and fls.name.endswith('.fls'):
            num += 1
            with open(fls.path, mode='r', encoding='utf-8') as fls_file:
                for line in fls_file:
                    match_data = rexp.search(line)
                    if match_data:
                        tfm_set.add(match_data.group(1))
            if num % 1000 == 0:
                print(f"\rRead file: {fls.name}", end="")
tfm_list = list(tfm_set)
tfm_list.sort()
save_data_to_json(tfm_list, tfm_list_fname)
print(f"\nCollected tfm names saved in file '{tfm_list_fname}'.")
