#!/usr/bin/env python3
"""Render labeled glyph images for ML training.

For one working dir, read its config.py to find `font_dir` and any
`lua_tables_copy` mapping.  For every per-font Lua table, merge with the
global glyphlist_table.lua base; for each PFB in `font_dir` that the table
applies to, rasterize every glyph that has a known codepoint sequence and
save it as a normalized NxN PNG under

    glyphs-dataset/images/<font>_<glyphname>.png  (PFB)
    glyphs-dataset/images/<font>_<gid>.png        (OTF/TTF via --otf-dir)

The full codepoint sequence (e.g. ["0x003D", "0x0338"] for notequal) is
written to glyphs-dataset/labels.json keyed by filename without extension.
Multi-codepoint sequences matter for negated symbols, small caps with
accents, etc.

Use --all to iterate every dir listed in config-list.json.
Use --clean to wipe images/ and labels.json before rebuilding.
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import fontforge
import numpy as np
from PIL import Image

PROJECT_DIR = Path(os.environ.get("project_dir") or
                   Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(PROJECT_DIR / "pyscripts"))
from io_glyph_data import read_lua_table_in_dict  # noqa: E402

BASE_TABLE = PROJECT_DIR / "glyphlists" / "glyphlist_table.lua"
DEFAULT_OUT = PROJECT_DIR / "glyphs-dataset"
CONFIG_LIST = PROJECT_DIR / "config-list.json"
EXCLUDED_DIR_NAMES = {"Pothana2000"}


def load_working_dir_config(working_dir):
    """Return (font_dir Path or None, lua_tables_copy dict)."""
    cfg_path = working_dir / "config.py"
    if not cfg_path.is_file():
        return None, {}
    spec = importlib.util.spec_from_file_location("wd_config", cfg_path)
    mod = importlib.util.module_from_spec(spec)
    cwd = os.getcwd()
    os.chdir(working_dir)
    try:
        spec.loader.exec_module(mod)
    finally:
        os.chdir(cwd)
    fd = getattr(mod, "font_dir", None)
    return (Path(fd) if fd else None,
            dict(getattr(mod, "lua_tables_copy", {}) or {}))


def hex_codes(codes):
    """Normalize a list of code strings to canonical 0xXXXX hex strings.

    Drops any non-hex entries (e.g. quoted glyph-name renames inside { ... }).
    Returns [] if nothing valid remains.
    """
    out = []
    for c in codes:
        try:
            n = int(c, 16)
        except (TypeError, ValueError):
            continue
        out.append(f"0x{n:04X}")
    return out


def normalize_bitmap(src_png, size, margin):
    """Crop to ink bbox, scale-preserving, paste centered on size x size.

    Returns black-on-white grayscale PIL Image, or None if the bitmap is empty.
    """
    im = Image.open(src_png).convert("L")
    arr = 255 - np.asarray(im)
    ys, xs = np.where(arr > 0)
    if len(xs) == 0:
        return None
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    cropped = arr[y0:y1, x0:x1]
    h, w = cropped.shape
    target = max(1, size - 2 * margin)
    if h >= w:
        new_h = target
        new_w = max(1, round(w * target / h))
    else:
        new_w = target
        new_h = max(1, round(h * target / w))
    resized = Image.fromarray(cropped).resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("L", (size, size), 0)
    canvas.paste(resized, ((size - new_w) // 2, (size - new_h) // 2))
    return Image.fromarray(255 - np.asarray(canvas))


def safe_filename(name):
    """File-system safe form of a glyph name."""
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


def glyph_em_metrics(font, glyph):
    """Em-relative size metrics: [w_em, h_em, cy_em, cx_em], roughly in [0,1].

    w_em, h_em — bbox width/height as a fraction of the horizontal em-square
                 (font.em) and the vertical em (ascent+descent), respectively.
                 Distinguishes degree (small) from O (large) and minus
                 (narrow) from em-dash (wide).
    cy_em      — vertical center of ink, 0 at top of ascender, 1 at bottom of
                 descender; captures subscript/superscript/baseline position.
    cx_em      — horizontal center of ink relative to em.

    Returned floats are NOT clipped to [0,1]; math glyphs and accents can fall
    slightly outside, which is fine since these become features for k-NN.
    """
    em = max(float(font.em), 1.0)
    em_v = max(float(font.ascent) + float(font.descent), 1.0)
    try:
        xmin, ymin, xmax, ymax = glyph.boundingBox()
    except Exception:
        return [0.0, 0.0, 0.5, 0.5]
    if xmax <= xmin or ymax <= ymin:
        return [0.0, 0.0, 0.5, 0.5]
    return [
        (xmax - xmin) / em,
        (ymax - ymin) / em_v,
        (float(font.ascent) - (ymin + ymax) / 2) / em_v,
        (xmin + xmax) / (2 * em),
    ]


def render_font(pfb_path, glyph_to_codes, images_dir, font_stem,
                size, margin, pixelsize, labels, metrics):
    """Render every glyph in `glyph_to_codes` from one PFB.

    Mutates `labels` (basename -> list[hex_str]) and `metrics`
    (basename -> [w_em, h_em, cy_em, cx_em]).
    Returns (rendered, skipped).
    """
    font = fontforge.open(str(pfb_path))
    rendered = 0
    skipped = 0
    try:
        with tempfile.TemporaryDirectory() as td:
            tmp_png = os.path.join(td, "g.png")
            for gname, codes in glyph_to_codes.items():
                if gname not in font:
                    skipped += 1
                    continue
                g = font[gname]
                if not g.isWorthOutputting():
                    skipped += 1
                    continue
                if os.path.exists(tmp_png):
                    os.remove(tmp_png)
                try:
                    g.export(tmp_png, pixelsize)
                except Exception as e:
                    print(f"  export failed {font_stem}/{gname}: {e}",
                          file=sys.stderr)
                    skipped += 1
                    continue
                if not os.path.exists(tmp_png):
                    skipped += 1
                    continue
                img = normalize_bitmap(tmp_png, size, margin)
                if img is None:
                    skipped += 1
                    continue
                basename = f"{font_stem}_{safe_filename(gname)}"
                img.save(images_dir / f"{basename}.png")
                labels[basename] = codes
                metrics[basename] = glyph_em_metrics(font, g)
                rendered += 1
    finally:
        font.close()
    return rendered, skipped


def merged_glyph_map(base_map, per_font_map):
    """Per-glyph codepoint *sequence* (hex strings). Per-font overrides base."""
    out = {}
    for name, codes in base_map.items():
        hex_seq = hex_codes(codes)
        if hex_seq:
            out[name] = hex_seq
    for name, codes in per_font_map.items():
        hex_seq = hex_codes(codes)
        if hex_seq:
            out[name] = hex_seq
    return out


def render_working_dir(working_dir, out_root, size, margin, pixelsize,
                       labels, metrics):
    if working_dir.name in EXCLUDED_DIR_NAMES:
        print(f"[skip] {working_dir}: excluded")
        return
    font_dir, lua_copy = load_working_dir_config(working_dir)
    if not font_dir or not font_dir.is_dir():
        print(f"[skip] {working_dir}: no usable font_dir")
        return

    base_map = read_lua_table_in_dict(str(BASE_TABLE)) or {}
    pfbs = {p.stem: p for p in font_dir.glob("*.pfb")}
    lua_files = sorted(working_dir.glob("*.lua"))
    if not lua_files:
        print(f"[skip] {working_dir}: no Lua tables")
        return

    images_dir = out_root / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    total_r = total_s = 0
    for lua in lua_files:
        per_font = read_lua_table_in_dict(str(lua)) or {}
        merged = merged_glyph_map(base_map, per_font)
        applies_to = [lua.stem] + list(lua_copy.get(lua.name, []))
        for font_stem in applies_to:
            pfb = pfbs.get(font_stem)
            if pfb is None:
                continue
            r, s = render_font(pfb, merged, images_dir, font_stem,
                               size, margin, pixelsize, labels, metrics)
            total_r += r
            total_s += s
            print(f"  {font_stem} ({lua.name}): rendered={r} skipped={s}")
    print(f"[done] {working_dir.name}: rendered={total_r} skipped={total_s}")


def render_all(out_root, size, margin, pixelsize, labels, metrics):
    if not CONFIG_LIST.is_file():
        sys.exit(f"config-list.json not found at {CONFIG_LIST}")
    with open(CONFIG_LIST, encoding="utf-8") as f:
        dirs = json.load(f)
    for d in dirs:
        render_working_dir(Path(d).resolve(),
                           out_root, size, margin, pixelsize,
                           labels, metrics)


def is_pua(cp):
    """True iff `cp` lies in a Unicode Private Use Area."""
    return (0xE000 <= cp <= 0xF8FF
            or 0xF0000 <= cp <= 0xFFFFD
            or 0x100000 <= cp <= 0x10FFFD)


def glyph_codepoints(g):
    """Codepoints from a fontforge Glyph: primary cmap then altuni, as hex.

    Codepoints in any Private Use Area are filtered out — PUA assignments
    are font-specific and meaningless as ML labels.  If a glyph's only
    mapping is in PUA, this returns [] and the caller skips the glyph.
    """
    out = []
    if g.unicode is not None and g.unicode != -1 and not is_pua(int(g.unicode)):
        out.append(f"0x{int(g.unicode):04X}")
    if g.altuni:
        for alt in g.altuni:
            cp = alt[0]
            if cp != -1 and not is_pua(int(cp)):
                h = f"0x{int(cp):04X}"
                if h not in out:
                    out.append(h)
    return out


def render_otf_font(font_path, images_dir, size, margin, pixelsize,
                    labels, metrics):
    """Render one OTF/TTF using cmap as labels. Returns (rendered, skipped)."""
    font = fontforge.open(str(font_path))
    font_stem = font_path.stem
    rendered = 0
    skipped = 0
    try:
        font.encoding = "Original"
        with tempfile.TemporaryDirectory() as td:
            tmp_png = os.path.join(td, "g.png")
            for gid in range(len(font)):
                try:
                    g = font[gid]
                except (TypeError, KeyError):
                    skipped += 1
                    continue
                if not g.isWorthOutputting():
                    skipped += 1
                    continue
                codes = glyph_codepoints(g)
                if not codes:
                    skipped += 1
                    continue
                if os.path.exists(tmp_png):
                    os.remove(tmp_png)
                try:
                    g.export(tmp_png, pixelsize)
                except Exception as e:
                    print(f"  export failed {font_stem}/gid{gid}: {e}",
                          file=sys.stderr)
                    skipped += 1
                    continue
                if not os.path.exists(tmp_png):
                    skipped += 1
                    continue
                img = normalize_bitmap(tmp_png, size, margin)
                if img is None:
                    skipped += 1
                    continue
                basename = f"{font_stem}_{gid}"
                img.save(images_dir / f"{basename}.png")
                # For OTF, the cmap's primary is the label; altuni siblings are
                # separate Unicode encodings of the same glyph (rare for math
                # fonts), not a decomposition - so keep just the primary.
                labels[basename] = codes[:1]
                metrics[basename] = glyph_em_metrics(font, g)
                rendered += 1
    finally:
        font.close()
    return rendered, skipped


def render_otf_dir(otf_root, out_root, size, margin, pixelsize,
                   labels, metrics):
    otf_root = Path(otf_root).resolve()
    if not otf_root.is_dir():
        print(f"[skip] {otf_root}: not a directory")
        return
    fonts = sorted([p for p in otf_root.rglob("*")
                    if p.suffix.lower() in (".otf", ".ttf")])
    if not fonts:
        print(f"[skip] {otf_root}: no .otf/.ttf files")
        return
    images_dir = out_root / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    total_r = total_s = 0
    for p in fonts:
        if p.parent.name in EXCLUDED_DIR_NAMES:
            continue
        r, s = render_otf_font(p, images_dir, size, margin, pixelsize,
                               labels, metrics)
        total_r += r
        total_s += s
        print(f"  {p.name}: rendered={r} skipped={s}")
    print(f"[done] {otf_root}: rendered={total_r} skipped={total_s}")


def load_labels(out_root):
    p = out_root / "labels.json"
    if not p.is_file():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_labels(out_root, labels):
    p = out_root / "labels.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=0, sort_keys=True, ensure_ascii=False)


def load_metrics(out_root):
    p = out_root / "metrics.json"
    if not p.is_file():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_metrics(out_root, metrics):
    p = out_root / "metrics.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=0, sort_keys=True, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--working-dir", default=os.environ.get("working_dir"),
                   help="Path to one PFB working dir (default: $working_dir)")
    g.add_argument("--all", action="store_true",
                   help="Iterate every dir in config-list.json (PFB only)")
    ap.add_argument("--otf-dir", action="append", default=[],
                    help="OTF/TTF directory tree (cmap is the label source). "
                    "May be repeated.")
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help="Dataset output root (default: %(default)s)")
    ap.add_argument("--size", type=int, default=64)
    ap.add_argument("--margin", type=int, default=4)
    ap.add_argument("--pixelsize", type=int, default=64,
                    help="FontForge rasterization em-pixel size")
    ap.add_argument("--clean", action="store_true",
                    help="Delete images/ and labels.json before rebuilding")
    args = ap.parse_args()

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    if args.clean:
        imgs = out_root / "images"
        if imgs.is_dir():
            shutil.rmtree(imgs)
        for fname in ("labels.json", "metrics.json"):
            sidecar = out_root / fname
            if sidecar.is_file():
                sidecar.unlink()
        # Also remove any stale codepoint-hex dirs from the previous layout.
        import re
        for child in out_root.iterdir():
            if child.is_dir() and re.fullmatch(r"[0-9A-F]+", child.name):
                shutil.rmtree(child)
        print(f"[clean] wiped {imgs}, labels.json, metrics.json, "
              f"and any stale hex dirs")
    (out_root / "images").mkdir(parents=True, exist_ok=True)

    labels = load_labels(out_root)
    metrics = load_metrics(out_root)
    if args.all:
        render_all(out_root, args.size, args.margin, args.pixelsize,
                   labels, metrics)
    elif args.working_dir:
        render_working_dir(Path(args.working_dir).resolve(),
                           out_root, args.size, args.margin, args.pixelsize,
                           labels, metrics)
    elif not args.otf_dir:
        ap.error("provide --working-dir, --all, or --otf-dir")
    for d in args.otf_dir:
        render_otf_dir(d, out_root, args.size, args.margin, args.pixelsize,
                       labels, metrics)
    save_labels(out_root, labels)
    save_metrics(out_root, metrics)
    print(f"[labels]  {len(labels)} entries -> {out_root/'labels.json'}")
    print(f"[metrics] {len(metrics)} entries -> {out_root/'metrics.json'}")


if __name__ == "__main__":
    main()
