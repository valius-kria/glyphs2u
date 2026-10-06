#!/usr/bin/env python3
"""Write (to stdout) a LaTeX doc that renders all 256 positions of ONE font,
one glyph per page, so dvipng can rasterize each into <font>.pos/.

The font is loaded by name exactly as fonttable.sty does (\\font\\f=<name> at
<size>); page N (1-based, dvipng output) holds font position \\char N-1.

Usage: render_font_tex.py <font-name> [--size 60]   > <font>.pos/render.tex
"""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("--size", default="60")
a = ap.parse_args()

print(r"\documentclass{article}")
print(r"\pagestyle{empty}\newcount\c")
print(rf"\font\f={a.font} at {a.size}pt")
print(r"\begin{document}")
print(r"\f \c=0 \loop \setbox0=\hbox{\char\c}\shipout\box0 \ifnum\c<255 \advance\c by1 \repeat")
print(r"\end{document}")
