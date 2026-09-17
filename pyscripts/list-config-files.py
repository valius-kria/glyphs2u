#!/usr/bin/env python3

import importlib
find_config_mod = importlib.import_module("find-working-dir-for-pfb")
from io_data import save_data_to_json, path_file
import os

# --- How to Use It ---
if __name__ == "__main__":
    # 1. DEFINE YOUR PROJECT ROOT
    project_root = os.environ['project_dir']
    print(f"Searching under project root: '{project_root}'")
    working_dirs = find_config_mod.discover_working_dirs(project_root)
    print(f"Found {len(working_dirs)} potential dirs to check...")
    for d in working_dirs:
        print(f"  - {d.name}")
    print("-" * 20)
    save_data_to_json(list(map(str, working_dirs)),
                      path_file("config-list.json", dname = project_root))
