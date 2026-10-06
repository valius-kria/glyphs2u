#!/usr/bin/env python3
"""Print the plain-sibling font name for a given variant font.

Kept as its own command because the makefiles call it by name (`make
<font>.tfmdir` writes its output into the work dir's 'plain' file).  The
lookup itself lives in font_pairs.py, which consults the hand-editable
tfm/<supplier>/<family>/pairs first and the derived comparison_pairs after.

Usage: cmp_sibling.py <variant-font-name>
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from font_pairs import pair_of

if len(sys.argv) < 2:
    sys.exit("cmp_sibling: missing variant font name")
variant = sys.argv[1]
plain, _differs = pair_of(variant)
if not plain:
    sys.exit(f"cmp_sibling: no comparison pair for '{variant}'")
print(plain)
