#!/usr/bin/env python3
# For each PFB stem in tex4ht-inventory.json["theirs_only_pfbs"], run
#   kpsewhich <stem>.pfb
# and collect the directory portion of the result.  Output the deduplicated,
# sorted directory list.
#
# Reads:
#   $project_dir/tex4ht-inventory.json
# Writes:
#   $project_dir/tex4ht-theirs-only-dirs.json   (sorted unique dirs + diagnostics)

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(os.environ["project_dir"])
# The TeX Live tree is whichever this kpsewhich belongs to.
KPSEWHICH = os.environ.get("KPSEWHICH", "kpsewhich")

def kpsewhich(name):
    try:
        out = subprocess.check_output(
            [KPSEWHICH, name],
            text=True, stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    out = out.strip()
    return out.splitlines()[0] if out else None


if __name__ == "__main__":
    inv = json.loads((PROJECT_DIR / "tex4ht-inventory.json").read_text())
    theirs_only = inv.get("theirs_only_pfbs", [])
    print(f"Have read list with {len(theirs_only)} members")
    dirs = []
    not_found = []
    font_list = list(theirs_only)
    while font_list:
        stem = font_list[0]
        pfb_path = kpsewhich(f"{stem}.pfb")
        if not pfb_path:
            not_found.append(stem)
            font_list = font_list[1:]
            continue
        dir_path = os.path.dirname(pfb_path)
        print(dir_path)
        font_list1 = [os.path.splitext(fn)[0]
                      for fn in sorted(os.listdir(dir_path))
                      if fn.endswith(".pfb")]
        font_list = [nm for nm in font_list if nm not in font_list1]
        dirs.append({dir_path: len(font_list1)})

    n = len(theirs_only)
    out = {
        "kpsewhich": KPSEWHICH,
        "theirs_only_pfb_count": n,
        "directory_count": len(dirs),
        "not_found_count": len(not_found),
        "directories": dirs,
    }
    if not_found:
        out["not_found_pfbs"] = sorted(not_found)
    (PROJECT_DIR / "tex4ht-theirs-only-dirs.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(f"theirs_only PFBs queried: {n}")
    print(f"unique directories:       {len(dirs)}")
    print(f"kpsewhich not found:      {len(not_found)}")
