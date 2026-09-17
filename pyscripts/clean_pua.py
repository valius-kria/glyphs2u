#!/usr/bin/env python3
"""Remove glyphs-dataset/ entries whose primary codepoint is in a Private
Use Area.

Walks glyphs-dataset/labels.json, finds entries where values[0] is in
U+E000..F8FF, U+F0000..FFFFD, or U+100000..10FFFD, deletes the
corresponding PNG from images/, and drops the entry from both labels.json
and metrics.json.  Pure cleanup — does not re-render anything.

Use with --dry-run to see what would be removed without touching disk.
Re-run `make index` afterwards to rebuild the k-NN index from the pruned
dataset.
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


def is_pua(cp):
    return (0xE000 <= cp <= 0xF8FF
            or 0xF0000 <= cp <= 0xFFFFD
            or 0x100000 <= cp <= 0x10FFFD)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default=str(DEFAULT_DATASET))
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would be removed, but don't touch disk")
    args = ap.parse_args()

    root = Path(args.dataset)
    labels_path = root / "labels.json"
    metrics_path = root / "metrics.json"
    images_dir = root / "images"
    if not labels_path.is_file():
        sys.exit(f"labels.json not found under {root}")
    with open(labels_path, encoding="utf-8") as f:
        labels = json.load(f)
    metrics = {}
    if metrics_path.is_file():
        with open(metrics_path, encoding="utf-8") as f:
            metrics = json.load(f)

    to_remove = []
    contributors = Counter()
    for name, codes in labels.items():
        if not codes:
            continue
        try:
            cp = int(codes[0], 16)
        except (TypeError, ValueError):
            continue
        if is_pua(cp):
            to_remove.append(name)
            contributors[name.split("_", 1)[0]] += 1

    print(f"PUA-primary entries: {len(to_remove)} / {len(labels)} "
          f"({100 * len(to_remove) / max(1, len(labels)):.1f}%)")
    if not to_remove:
        return
    print("Contributors:")
    for stem, n in contributors.most_common():
        print(f"  {n:6d}  {stem}")
    if args.dry_run:
        print("\n[dry-run] no files modified")
        return

    deleted_pngs = 0
    missing_pngs = 0
    for name in to_remove:
        png = images_dir / f"{name}.png"
        try:
            png.unlink()
            deleted_pngs += 1
        except FileNotFoundError:
            missing_pngs += 1
        labels.pop(name, None)
        metrics.pop(name, None)

    tmp = labels_path.with_suffix(labels_path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=0, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, labels_path)
    if metrics_path.is_file() or metrics:
        tmp = metrics_path.with_suffix(metrics_path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=0, sort_keys=True, ensure_ascii=False)
        os.replace(tmp, metrics_path)
    print(f"\nDeleted {deleted_pngs} PNGs"
          + (f" ({missing_pngs} already missing)" if missing_pngs else ""))
    print(f"labels.json now has {len(labels)} entries; "
          f"metrics.json has {len(metrics)}")


if __name__ == "__main__":
    main()
