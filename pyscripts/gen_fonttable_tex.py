#!/usr/bin/env python3
"""Write (to stdout) a fonttable specimen .tex for ONE font: an xmlforge
\\vtxmlDebugFont \\fonttable{<font>} document.  Its .uni carries the per-glyph
tex/htf/idx debug info that uni_to_html.py turns into a glyph<->unicode page --
so <font>.fonttable.tex -> .fonttable.uni -> .fonttable.uni.html.

The font is loaded by name by \\fonttable (\\font\\x=<name>), so <font> is the
tfm/htf name; the tfm must be findable by kpsewhich.

Usage: gen_fonttable_tex.py <font-name>   > <font>.fonttable.tex
"""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("font")
a = ap.parse_args()

print(r"\IfFileExists{xmlforge.sty}{\RequirePackage{xmlforge}}{}")
print(r"\documentclass{article}")
print(r"\usepackage{fonttable}")
print(r"\nodecimals")
print(r"\nohexoct")
print(r"\vtxmlDebugFont")
print(r"\pagestyle{empty}")
print(r"\begin{document}")
print(rf"\fonttable{{{a.font}}}")
print(r"\end{document}")
