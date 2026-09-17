#!/usr/bin/env python3
"""List unique fonts currently in glyphs-dataset/, with sample counts.

Reads <root>/labels.json, parses the `<font_stem>_<key>` basename of each
entry, and reports unique font stems sorted by sample count.  Useful before
adding a new font to confirm it isn't already represented in the dataset.

Output (one line per font):

    <count>  <font_stem>

With --output FILE, also persists the same text so future-you can grep it
without re-running.
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("project_dir") or
                   Path(__file__).resolve().parent.parent)
DEFAULT_DATASET = PROJECT_DIR / "glyphs-dataset"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default=str(DEFAULT_DATASET),
                    help="Dataset root (default: %(default)s)")
    ap.add_argument("--output", default=None,
                    help="Also write the listing to this file")
    ap.add_argument("--sort", default="count",
                    choices=["count", "name"],
                    help="Sort by sample count (default) or alphabetical")
    args = ap.parse_args()

    root = Path(args.dataset)
    labels_path = root / "labels.json"
    if not labels_path.is_file():
        sys.exit(f"labels.json not found at {labels_path}")
    with open(labels_path, encoding="utf-8") as f:
        labels = json.load(f)

    counts = Counter(basename.split("_", 1)[0] for basename in labels)
    items = counts.most_common() if args.sort == "count" \
        else sorted(counts.items())

    header = (f"# {len(counts)} fonts, {sum(counts.values())} total samples "
              f"in {labels_path}")
    out_lines = [header]
    for stem, n in items:
        out_lines.append(f"{n:6d}  {stem}")
    body = "\n".join(out_lines)
    print(body)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(body + "\n")
        print(f"\nWrote {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
