#!/usr/bin/env python

from io_data import load_dict_from_json, save_data_to_json
from io_tex_data import apply_kpsewhich, KPSEWHICH
import os

cmd_prefix = KPSEWHICH + ' '
pfb_dict_fname = 'prod-pfb-dict.json'
font_dirs_fname = 'prod-pfb-dirs.json'

pfb_dict = load_dict_from_json(pfb_dict_fname)

font_dirs = {}
num = 0
for pfb in pfb_dict.keys():
    num += 1
    output = apply_kpsewhich(pfb)
    if output:
        path = os.path.dirname(output.splitlines()[0])
        font_dirs[path] = font_dirs.get(path, []) + [pfb, ]
    if num % 25 == 0:
        print(f"\rFinding file {pfb}", end="")

save_data_to_json(font_dirs, font_dirs_fname)
print(f"\nPFB directories are saved in file '{font_dirs_fname}'.")
