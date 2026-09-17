#!/usr/bin/env python3
"""Build a k-NN index over glyphs-dataset/ for unsupervised classification.

Reads <root>/images/*.png, <root>/labels.json, and <root>/metrics.json,
computes HOG features, concatenates 4 em-relative size metrics scaled by
--size-weight, and saves a single bundle containing:

    - the fitted sklearn NearestNeighbors object
    - the feature matrix (float32): [HOG | metrics * size_weight]
    - codepoint_seqs: parallel list of tuples (int codepoints) — multi-cp
      sequences kept intact (e.g. notequal -> (0x003D, 0x0338))
    - the relative filename array ("images/<name>.png")
    - the HOG params used
    - the size_weight used (so inference scripts can reproduce the feature
      vector for query glyphs)

The em-relative metrics (w_em, h_em, cy_em, cx_em) capture information HOG
discards by design: how big the glyph is inside its em-square and where it
sits.  Without them, a degree sign and an uppercase O look identical to HOG
once both are scale-fit to the canvas.

Used by classify_knn.py, predicted-knn-html.py, edit_knn.py.
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path

import joblib
import numpy as np
from PIL import Image
from skimage.feature import hog
from sklearn.neighbors import NearestNeighbors

PROJECT_DIR = Path(os.environ.get("project_dir") or
                   Path(__file__).resolve().parent.parent)
DEFAULT_DATASET = PROJECT_DIR / "glyphs-dataset"

HOG_PARAMS = dict(orientations=9,
                  pixels_per_cell=(16, 16),
                  cells_per_block=(2, 2),
                  block_norm="L2-Hys",
                  feature_vector=True)

# HOG produces 324 dims for a 64x64 image with these params; metrics are 4
# dims.  sqrt(324/4) ~= 9 gives the two groups equal influence in L2 distance.
DEFAULT_SIZE_WEIGHT = math.sqrt(324 / 4)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default=str(DEFAULT_DATASET))
    ap.add_argument("--out", default=None,
                    help="Output (default: <dataset>/knn-index.joblib)")
    ap.add_argument("--n-neighbors", type=int, default=20)
    ap.add_argument("--algorithm", default="auto",
                    choices=["auto", "ball_tree", "kd_tree", "brute"])
    ap.add_argument("--size-weight", type=float, default=DEFAULT_SIZE_WEIGHT,
                    help="Multiplier applied to the 4 em-relative metric "
                    "dims before concatenation with HOG features.  Default "
                    "balances HOG and metrics roughly equally in L2 "
                    "distance; pass 0 to disable metrics entirely.")
    args = ap.parse_args()

    root = Path(args.dataset)
    images_dir = root / "images"
    labels_path = root / "labels.json"
    metrics_path = root / "metrics.json"
    if not images_dir.is_dir():
        sys.exit(f"images/ not found under {root}")
    if not labels_path.is_file():
        sys.exit(f"labels.json not found under {root}")
    out = Path(args.out) if args.out else root / "knn-index.joblib"

    with open(labels_path, encoding="utf-8") as f:
        labels_map = json.load(f)
    metrics_map = {}
    if args.size_weight > 0:
        if not metrics_path.is_file():
            sys.exit(f"metrics.json not found under {root}; re-run "
                     f"`make dataset-all` or pass --size-weight 0")
        with open(metrics_path, encoding="utf-8") as f:
            metrics_map = json.load(f)
    sw = float(args.size_weight)

    print(f"Scanning {images_dir} (labels: {len(labels_map)}, "
          f"metrics: {len(metrics_map)}, size_weight: {sw:.3f}) ...",
          flush=True)
    feats = []
    seqs = []
    names = []
    skipped_no_metrics = 0
    for p in sorted(images_dir.glob("*.png")):
        label = labels_map.get(p.stem)
        if not label:
            continue
        cps = tuple(int(c, 16) for c in label)
        if not cps:
            continue
        m = metrics_map.get(p.stem) if sw > 0 else None
        if sw > 0 and m is None:
            skipped_no_metrics += 1
            continue
        arr = np.asarray(Image.open(p).convert("L"),
                         dtype=np.float32) / 255.0
        feat = hog(arr, **HOG_PARAMS)
        if sw > 0:
            feat = np.concatenate(
                [feat, np.asarray(m, dtype=np.float32) * sw])
        feats.append(feat)
        seqs.append(cps)
        names.append(f"images/{p.name}")
    if not feats:
        sys.exit("No samples found.")
    if skipped_no_metrics:
        print(f"  skipped {skipped_no_metrics} samples without metrics",
              file=sys.stderr)
    X = np.stack(feats).astype(np.float32)
    print(f"  {len(seqs)} samples, feature dim {X.shape[1]}", flush=True)
    print(f"Fitting NearestNeighbors (algorithm={args.algorithm}, "
          f"K={args.n_neighbors}) ...", flush=True)
    nn = NearestNeighbors(n_neighbors=args.n_neighbors,
                          algorithm=args.algorithm)
    nn.fit(X)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"index": nn, "features": X, "codepoint_seqs": seqs,
                 "names": names, "hog_params": HOG_PARAMS,
                 "size_weight": sw,
                 "default_k": args.n_neighbors}, out)
    print(f"Index saved to {out} ({out.stat().st_size/1e6:.1f} MB)",
          flush=True)


if __name__ == "__main__":
    main()
