"""Shared font/glyph rendering helpers used by inference scripts.

Sibling of predicted_helpers.py (HTML helpers); these helpers handle the
FontForge-side: locating a font in the working dir's font_dir, rasterizing
a single glyph through the same normalization pipeline as render_dataset.py,
and iterating glyphs with the project's keying convention (PostScript glyph
names for PFB, GIDs as strings for OTF/TTF).
"""
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
from skimage.feature import hog

# render_dataset.normalize_bitmap is the canonical normalizer; reuse it so the
# query images go through exactly the same path as the training images.
PROJECT_DIR = Path(os.environ.get("project_dir") or
                   Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(PROJECT_DIR / "pyscripts"))
from render_dataset import normalize_bitmap, glyph_em_metrics  # noqa: E402

FONT_EXTS = (".pfb", ".otf", ".ttf")


def rasterize(glyph, pixelsize, size, margin):
    """Render a FontForge Glyph to a normalized float32 array in [0,1].

    Returns None if the glyph rasterizes to nothing (empty bitmap).
    """
    with tempfile.TemporaryDirectory() as td:
        tmp = os.path.join(td, "g.png")
        try:
            glyph.export(tmp, pixelsize)
        except Exception:
            return None
        if not os.path.exists(tmp):
            return None
        img = normalize_bitmap(tmp, size, margin)
    if img is None:
        return None
    return np.asarray(img, dtype=np.float32) / 255.0


def resolve_font(arg, font_dir):
    """Accept a bare name, filename, or absolute path; try .pfb/.otf/.ttf."""
    p = Path(arg)
    if p.is_absolute() and p.is_file():
        return p
    cand = font_dir / arg
    if cand.is_file():
        return cand
    for ext in FONT_EXTS:
        cand = font_dir / (arg + ext)
        if cand.is_file():
            return cand
    return None


def is_pfb(path):
    return Path(path).suffix.lower() == ".pfb"


def iter_labelled_glyphs(font, by_gid):
    """Yield (key, Glyph) — key is GID string for OTF/TTF, glyph name for PFB.

    For OTF/TTF the font is switched to Original encoding so GIDs are stable.
    """
    if by_gid:
        font.encoding = "Original"
        for gid in range(len(font)):
            try:
                yield str(gid), font[gid]
            except (TypeError, KeyError):
                continue
    else:
        for gname in font:
            yield gname, font[gname]


def query_feature(arr, font, glyph, hog_params, size_weight):
    """Build the index-compatible feature vector for one rasterized glyph.

    Returns shape (1, D) so it can be passed directly to nn.kneighbors().
    If size_weight is falsy or <= 0, only HOG is used (matches old indexes
    built before em-metrics were added).
    """
    feat = hog(arr, **hog_params)
    if size_weight and size_weight > 0:
        m = np.asarray(glyph_em_metrics(font, glyph), dtype=np.float32)
        feat = np.concatenate([feat, m * float(size_weight)])
    return feat.reshape(1, -1)
