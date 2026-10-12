#!/usr/bin/env python3
"""Thin glyphs-dataset/ by dropping samples that teach the classifier nothing.

The dataset carries every size cut of every font: eight of lmr, seven of
MnSymbol, and so on.  A size cut is a real design -- cmr5 is not cmr10 scaled,
or there would be no second font -- but the question for recognition is not
whether two glyphs differ, it is whether they differ ENOUGH to be worth
searching separately.  Most do not, and every redundant vector is scanned on
every query: the index is brute force at 328 dimensions, so query time falls
in step with the sample count.

So the test here is on the feature vectors rather than on the font names.
Within each codepoint sequence, a sample is kept only when it is farther than
--tau from every sample already kept, in the same feature space the index
searches.  That keeps the cuts that genuinely look different and drops the
ones that do not, which is what going by name could not do.  Selection is
farthest-first, so what survives spans the spread of shapes for that codepoint
rather than clustering wherever the scan happened to start.

Choosing --tau: measured on the current dataset, two samples of the SAME
codepoint sit a median 1.97 apart (10th percentile 0.77), while samples of
DIFFERENT codepoints sit a median 5.02 apart (10th percentile 3.47).  Anything
below about 3 therefore merges only like with like.  The default 0.75 halves
the dataset; 0.25 trims the outright duplicates alone.

Vectors come from the existing knn-index.joblib, so the features are exactly
the ones the index was built with and nothing is recomputed.  That makes the
order:

    make index      # build the index (or rebuild it, if the dataset moved on)
    make dedup      # prune, using the index's own vectors
    make index      # rebuild over what is left

Use --dry-run to see the effect without touching disk.
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("project_dir") or
                   Path(__file__).resolve().parent.parent)
DEFAULT_DATASET = PROJECT_DIR / "glyphs-dataset"


def farthest_first(vectors, tau):
    """Indices to keep: each one farther than tau from all already kept."""
    import numpy as np
    kept = [0]
    for j in range(1, len(vectors)):
        if np.linalg.norm(vectors[kept] - vectors[j], axis=1).min() > tau:
            kept.append(j)
    return kept


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", default=str(DEFAULT_DATASET))
    ap.add_argument("--index", default=None,
                    help="k-NN bundle to take vectors from "
                         "(default: <dataset>/knn-index.joblib)")
    ap.add_argument("--tau", type=float, default=0.75,
                    help="keep a sample only if it is farther than this from "
                         "every sample already kept for its codepoint "
                         "(default: 0.75)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be removed, but don't touch disk")
    a = ap.parse_args()

    try:
        import joblib
        import numpy as np
    except ImportError:
        sys.exit("dedup_dataset: needs joblib and numpy "
                 "(pip install joblib numpy)")

    root = Path(a.dataset)
    index_path = Path(a.index) if a.index else root / "knn-index.joblib"
    labels_path, metrics_path = root / "labels.json", root / "metrics.json"
    if not index_path.is_file():
        sys.exit(f"{index_path} not found -- run `make index' first, so the "
                 "vectors to compare are the ones the index searches.")
    if not labels_path.is_file():
        sys.exit(f"labels.json not found under {root}")

    bundle = joblib.load(index_path)
    X, seqs, names = bundle["features"], bundle["codepoint_seqs"], bundle["names"]
    with open(labels_path, encoding="utf-8") as f:
        labels = json.load(f)

    if len(names) != len(labels):
        print(f"dedup_dataset: the index has {len(names)} samples and "
              f"labels.json {len(labels)} -- the index is stale.  Rebuild it "
              "with `make index' first.", file=sys.stderr)
        sys.exit(1)

    groups = defaultdict(list)
    for i, s in enumerate(seqs):
        groups[tuple(s)].append(i)

    keep = set()
    for idx in groups.values():
        if len(idx) == 1:
            keep.add(idx[0])
            continue
        for j in farthest_first(X[idx], a.tau):
            keep.add(idx[j])

    drop = [i for i in range(len(names)) if i not in keep]
    print(f"samples {len(names)}, codepoint sequences {len(groups)}")
    print(f"tau {a.tau}: keep {len(keep)} ({100*len(keep)/len(names):.1f}%), "
          f"drop {len(drop)}")

    # The labels key is the file name without its directory or extension.
    def key(n):
        return Path(n).stem

    if a.dry_run:
        worst = sorted(groups.items(),
                       key=lambda kv: -(len(kv[1]) - sum(1 for i in kv[1] if i in keep)))
        print("\nmost thinned codepoints:")
        for s, idx in worst[:10]:
            k = sum(1 for i in idx if i in keep)
            print(f"   {' '.join('U+%04X' % c for c in s):22} "
                  f"{len(idx):4} -> {k}")
        print("\n(dry run: nothing removed)")
        return

    with open(metrics_path, encoding="utf-8") as f:
        metrics = json.load(f) if metrics_path.is_file() else {}

    removed = 0
    for i in drop:
        png = root / names[i]
        if png.is_file():
            png.unlink()
            removed += 1
        labels.pop(key(names[i]), None)
        metrics.pop(key(names[i]), None)

    with open(labels_path, "w", encoding="utf-8") as f:
        json.dump(labels, f, ensure_ascii=False, indent=1, sort_keys=True)
    if metrics_path.is_file():
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=1, sort_keys=True)

    print(f"removed {removed} image(s); labels.json now holds {len(labels)}")
    print("the index is now stale -- rebuild it with `make index'")


if __name__ == "__main__":
    main()
