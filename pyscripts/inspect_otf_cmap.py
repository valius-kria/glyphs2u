#!/usr/bin/env python3
"""Inspect the cmap of one or more OTF/TTF files for sentinel codepoints.

Reports, per font, whether each project-relevant codepoint is present in
the cmap (primary `glyph.unicode` plus `glyph.altuni` alternates), plus the
total number of cmap entries.  Use before ingesting a font into
glyphs-dataset/ to confirm its Unicode conventions agree with the project's
PFB Lua tables.

The chosen sentinels surface common math-vs-text disagreement:

  U+0041   A                  — basic Latin, should always be present
  U+1D434  math italic A      — math-aware fonts; absence => text-style cmap
  U+1D538  math bb A          — Mathematical Alphanumeric Symbols block
  U+1D6FC  math italic α      — Greek math italics
  U+2211   ∑ N-ary summation  — basic math operator
  U+2260   ≠ not equal        — pre-composed negation
  U+0338   combining solidus  — used to build negated symbols

Usage:
    inspect_otf_cmap.py FILE [FILE ...]
    inspect_otf_cmap.py --dir DIR [--dir DIR ...]
"""
import argparse
import os
import sys
from pathlib import Path

import fontforge

SENTINELS = [
    (0x0041,  "A"),
    (0x1D434, "1D434"),
    (0x1D538, "1D538"),
    (0x1D6FC, "1D6FC"),
    (0x2211,  "2211"),
    (0x2260,  "2260"),
    (0x0338,  "0338"),
]


def cmap_set(font_path):
    """Return the set of all codepoints reachable via cmap + altuni."""
    font = fontforge.open(str(font_path))
    have = set()
    try:
        font.encoding = "Original"
        for gid in range(len(font)):
            try:
                g = font[gid]
            except (TypeError, KeyError):
                continue
            if g.unicode is not None and g.unicode != -1:
                have.add(int(g.unicode))
            if g.altuni:
                for alt in g.altuni:
                    if alt[0] != -1:
                        have.add(int(alt[0]))
    finally:
        font.close()
    return have


def report(paths):
    name_w = max(28, max((len(p.name) for p in paths), default=28))
    cols = [lbl for _, lbl in SENTINELS]
    header = (f"{'font':<{name_w}}  "
              + "  ".join(f"{c:>5}" for c in cols)
              + "   count")
    print(header)
    print("-" * len(header))
    for p in paths:
        try:
            have = cmap_set(p)
        except Exception as e:
            print(f"{p.name:<{name_w}}  ERROR: {e}")
            continue
        marks = "  ".join(f"{'yes' if cp in have else '-':>5}"
                          for cp, _ in SENTINELS)
        print(f"{p.name:<{name_w}}  {marks}  {len(have):6d}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", default=[],
                    help="OTF/TTF files to inspect")
    ap.add_argument("--dir", action="append", default=[],
                    help="Directory to scan recursively for .otf/.ttf "
                    "(may be repeated)")
    args = ap.parse_args()

    paths = [Path(f) for f in args.files]
    for d in args.dir:
        d = Path(d)
        if not d.is_dir():
            print(f"warn: {d} is not a directory; skipping", file=sys.stderr)
            continue
        paths.extend(sorted(p for p in d.rglob("*")
                            if p.suffix.lower() in (".otf", ".ttf")))
    if not paths:
        ap.error("provide font files or --dir")
    report(paths)


if __name__ == "__main__":
    main()
