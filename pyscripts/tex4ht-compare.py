#!/usr/bin/env python3
# Compare a font's project lua table to tex4ht's per-PFB glyph -> codepoint map.
#
# Invoked from a working dir as:   tex4ht-compare.py <font-stem>
# Writes:  <font-stem>-tex4ht.diff in the working dir.
#
# Uses tex4ht-data/pfb-maps/<font-stem>.json (already-computed glyph -> codepoint
# map from tex4ht), compares against the project's <font>.lua + builtin map.

import importlib.util
import json
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(os.environ["project_dir"])
WORKING_DIR = Path(os.environ.get("working_dir", os.getcwd()))

sys.path.insert(0, str(PROJECT_DIR / "pyscripts"))
from io_glyph_data import read_lua_table_in_dict


def hex_list_to_ints(xs):
    return [int(x, 16) for x in xs]


def load_lua(path):
    raw = read_lua_table_in_dict(str(path))
    return {n: hex_list_to_ints(v) for n, v in raw.items()}


def load_builtin():
    raw = json.loads((PROJECT_DIR / "builtin-glyph-map.json").read_text())
    return {n: hex_list_to_ints(v) for n, v in raw.items()}


def project_unicode(name, lua, builtin):
    if name in lua:
        return lua[name]
    if name in builtin:
        return builtin[name]
    return None


def fmt_cps(cps):
    return "+".join(f"U+{c:04X}" for c in cps) if cps else "(none)"


def main():
    if len(sys.argv) < 2:
        print("usage: tex4ht-compare.py <font-stem>", file=sys.stderr)
        sys.exit(2)
    font_stem = sys.argv[1]
    lua_path = WORKING_DIR / f"{font_stem}.lua"
    if not lua_path.exists():
        print(f"{lua_path} not found", file=sys.stderr)
        sys.exit(1)

    pfb_map_path = PROJECT_DIR / "tex4ht-data" / "pfb-maps" / f"{font_stem}.json"
    if not pfb_map_path.exists():
        out_path = WORKING_DIR / f"{font_stem}-tex4ht.diff"
        out_path.write_text(
            f"# tex4ht has no pfb-maps entry for {font_stem}\n"
            f"# (no TFM referencing {font_stem}.pfb resolves to a tex4ht .htf)\n",
            encoding="utf-8",
        )
        print(f"wrote {out_path}  (no tex4ht coverage)")
        return

    lua = load_lua(lua_path)
    builtin = load_builtin()
    pfb_map = json.loads(pfb_map_path.read_text())
    their_glyphs = pfb_map.get("glyphs", {})
    sources = pfb_map.get("sources", [])
    conflicts = pfb_map.get("conflicts", {})

    n_agree = 0
    disagree = []
    missing_project = []
    only_project = []

    for name, theirs in sorted(their_glyphs.items()):
        ours = project_unicode(name, lua, builtin)
        if ours is None:
            missing_project.append((name, theirs))
        elif ours == theirs:
            n_agree += 1
        else:
            disagree.append((name, ours, theirs))

    # Glyphs the project has a codepoint for but tex4ht doesn't.
    project_names = set(lua) | set(builtin)
    for name in sorted(project_names - their_glyphs.keys()):
        if name in lua:
            only_project.append((name, lua[name]))

    lines = [
        f"# tex4ht compare for {font_stem}.lua",
        f"working dir: {WORKING_DIR}",
        f"pfb-map:     {pfb_map_path.relative_to(PROJECT_DIR)}",
        f"tex4ht sources used for this PFB ({len(sources)}):",
    ]
    for s in sources:
        lines.append(f"  TFM={s['tfm']!r}  enc={s['enc']!r}  htf={s['htf']}  matched_by={s['matched_by']}")
    lines.append("")
    lines.append(
        f"glyphs in tex4ht map: {len(their_glyphs)}  agree={n_agree}  "
        f"disagree={len(disagree)}  project-missing={len(missing_project)}"
    )
    lines.append("")
    if disagree:
        lines.append("## Disagreements (project differs from tex4ht):")
        for name, ours, theirs in disagree:
            lines.append(f"  /{name:30s}  ours={fmt_cps(ours):20s}  theirs={fmt_cps(theirs)}")
        lines.append("")
    if missing_project:
        lines.append("## Glyphs in tex4ht map but unmapped in project (.lua + builtin):")
        for name, theirs in missing_project:
            lines.append(f"  /{name:30s}  theirs={fmt_cps(theirs)}")
        lines.append("")
    if conflicts:
        lines.append(f"## tex4ht internal conflicts (glyphs where multiple sources disagreed): {len(conflicts)}")
        for name, options in sorted(conflicts.items()):
            lines.append(f"  /{name}")
            for opt in options:
                src = opt.get("source", "?")
                src_str = "(first)" if src == "(first writer)" else f"{src.get('tfm','?')}/{src.get('htf','?')}"
                lines.append(f"     {fmt_cps(opt['codepoints']):20s}  via {src_str}")
        lines.append("")

    out_path = WORKING_DIR / f"{font_stem}-tex4ht.diff"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_path}")
    print(f"  agree={n_agree}  disagree={len(disagree)}  project-missing={len(missing_project)}")


if __name__ == "__main__":
    main()
