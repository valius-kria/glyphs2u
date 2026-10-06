#!/usr/bin/env python 
# Calls kpsewhich to find path to the file
from io_tex_data import apply_kpsewhich
import sys

# 1. Read file name from argument
file_name = sys.argv[1]
# 2. Find path
file_path = apply_kpsewhich(file_name)
# 3. Set save file name 
output = file_name + ".path"
# 4. Write the path to the output
with open(output, "w", encoding="utf-8") as f:
    f.write(file_path)
