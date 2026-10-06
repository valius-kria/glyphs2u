#!/usr/bin/env python3
"""Collect the characters a SIZE CUT can apply to, from the MathML operator
dictionary -> stretchy-chars.json.

Which glyphs in a font are cuts of one character is not worth deciding by
measuring every glyph: the set of characters that expand at all is small,
known, and listed.  MathML's dictionary marks

  stretchy   the delimiters, braces, brackets, arrows -- and, with 'accent',
             the expandable accents, which is where that list is authoritative
  largeop    the integrals and the big operators, which come in text and
             display cuts

so the union is the answer, and everything outside it needs no size analysis.
The dictionary says WHICH characters expand, never how far or in what steps --
that stays a question for the font metrics, and only for these characters.

Reads mathml-ops.csv (tab-separated, as saved from the MathML spec).

Usage: mathml_stretchy.py [--ops mathml-ops.csv] [--out stretchy-chars.json]
"""
import argparse, csv, json, os, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.dirname(HERE)
ap = argparse.ArgumentParser()
ap.add_argument("--ops", default=os.path.join(DATA, "mathml-ops.csv"))
ap.add_argument("--out", default=os.path.join(DATA, "stretchy-chars.json"))
a = ap.parse_args()

def props(row):
    return {p.strip() for p in (row.get("Properties") or "").split(",") if p.strip()}

chars = {}
with open(a.ops, encoding="utf-8") as f:
    for row in csv.DictReader(f, delimiter="\t"):
        g = row.get("Glyph") or ""
        if len(g) != 1:
            continue
        p = props(row)
        if not (p & {"stretchy", "largeop"}):
            continue
        cp = ord(g)
        e = chars.setdefault(f"U+{cp:04X}", {
            "char": g, "name": row.get("Name") or "",
            "stretchy": False, "largeop": False, "accent": False,
            "fence": False, "symmetric": False,
        })
        for k in ("stretchy", "largeop", "accent", "fence", "symmetric"):
            e[k] = e[k] or (k in p)

kinds = {"accents": sum(1 for e in chars.values() if e["accent"]),
         "delimiters": sum(1 for e in chars.values()
                           if e["stretchy"] and not e["accent"] and not e["largeop"]),
         "big operators": sum(1 for e in chars.values() if e["largeop"])}
with open(a.out, "w", encoding="utf-8") as f:
    json.dump({"source": os.path.basename(a.ops), "counts": kinds,
               "chars": chars}, f, ensure_ascii=False, indent=1)
    f.write("\n")
print(f"mathml_stretchy: {len(chars)} character(s) that can take a size cut -> {a.out}")
for k, n in kinds.items():
    print(f"  {k:16} {n}")
