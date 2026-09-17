#!/usr/bin/env python3
# Coverage inventory: walk every working dir in config-list.json, classify each
# covered font name by whether tex4ht has a pfb-maps entry for it.
#
# Uses the precomputed tex4ht-data/pfb-maps/<pfb>.json, so this is now a thin
# reporter — all resolution work happened in tex4ht-tfm-map.py / tex4ht-pfb-maps.py.
#
# Reads:
#   $project_dir/config-list.json
#   $project_dir/tex4ht-data/pfb-maps/      one .json per in-scope PFB
#   <working_dir>/config.py                 lua_tables, lua_tables_copy, ...
#
# Writes:
#   $project_dir/tex4ht-inventory.json

import importlib.util
import json
import os
import sys
from pathlib import Path


def stem(name):
    return os.path.splitext(name)[0]


def load_config(working_dir):
    cfg_path = Path(working_dir) / "config.py"
    spec = importlib.util.spec_from_file_location(
        f"cfg_{abs(hash(str(working_dir)))}", cfg_path
    )
    mod = importlib.util.module_from_spec(spec)
    saved_path = sys.path[:]
    saved_cwd = os.getcwd()
    sys.path.insert(0, str(working_dir))
    try:
        os.chdir(working_dir)
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = saved_path
        os.chdir(saved_cwd)
    return mod


def covered_set(cfg):
    lua_tables = getattr(cfg, "lua_tables", [])
    lua_tables_copy = getattr(cfg, "lua_tables_copy", {})
    lua_tables_not_needed = getattr(cfg, "lua_tables_not_needed", [])
    lua_tables_tocheck = getattr(cfg, "lua_tables_tocheck", [])
    s = {stem(t) for t in lua_tables}
    for copies in lua_tables_copy.values():
        s.update(copies)
    s.update(lua_tables_not_needed)
    s.update(lua_tables_tocheck)
    return s


def main():
    project_dir = Path(os.environ["project_dir"])
    pfb_maps_dir = project_dir / "tex4ht-data" / "pfb-maps"
    if not pfb_maps_dir.is_dir():
        raise SystemExit(
            f"{pfb_maps_dir} missing — run `make tex4ht-pfb-maps` first."
        )

    all_dirs = json.loads((project_dir / "config-list.json").read_text())
    # Set of PFB stems for which we have a tex4ht map.
    covered_pfbs = {p.stem for p in pfb_maps_dir.glob("*.json")}

    working_dirs_out = []
    matched_pfbs = set()
    for d in sorted(all_dirs):
        try:
            cfg = load_config(d)
        except Exception as exc:
            working_dirs_out.append({
                "path": str(Path(d).relative_to(project_dir)),
                "error": f"failed to load config.py: {exc}",
            })
            continue
        covered = sorted(covered_set(cfg))
        covered_both = []
        ours_only = []
        for name in covered:
            if name in covered_pfbs:
                covered_both.append(name)
                matched_pfbs.add(name)
            else:
                ours_only.append(name)
        working_dirs_out.append({
            "path": str(Path(d).relative_to(project_dir)),
            "font_dir": getattr(cfg, "font_dir", None),
            "covered_count": len(covered),
            "covered_by_both_count": len(covered_both),
            "ours_only_count": len(ours_only),
            "covered_by_both": covered_both,
            "ours_only": ours_only,
        })

    theirs_only = sorted(covered_pfbs - matched_pfbs)
    out = {
        "kpsewhich": os.environ.get("KPSEWHICH", "kpsewhich"),
        "tex4ht_pfb_maps_total": len(covered_pfbs),
        "tex4ht_pfb_maps_matched_by_us": len(matched_pfbs),
        "tex4ht_pfb_maps_unmatched": len(theirs_only),
        "working_dirs": working_dirs_out,
        "theirs_only_pfbs": theirs_only,
    }
    out_file = project_dir / "tex4ht-inventory.json"
    out_file.write_text(json.dumps(out, indent=1, ensure_ascii=False, sort_keys=False))

    total_cov = sum(w.get("covered_count", 0) for w in working_dirs_out)
    total_both = sum(w.get("covered_by_both_count", 0) for w in working_dirs_out)
    print(f"wrote {out_file}")
    print(f"working dirs:               {len(working_dirs_out)}")
    print(f"project font names total:   {total_cov}")
    print(f"  covered by tex4ht too:    {total_both}")
    print(f"  ours only:                {total_cov - total_both}")
    print(f"tex4ht pfb-maps:            {len(covered_pfbs)}")
    print(f"  matched by us:            {len(matched_pfbs)}")
    print(f"  unmatched (theirs_only):  {len(theirs_only)}")


if __name__ == "__main__":
    main()
