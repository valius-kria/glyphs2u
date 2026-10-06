#!/usr/bin/env python3
"""Print the encoding json <font>.gpm.json needs -- <enc>.enc.json when
psfonts.map names an encoding vector for this tfm, <font>.pfb.enc.json when it
does not and the pfb's built-in encoding applies.

Used by mk/font.mk as a second-expansion prerequisite, the way cmp_sibling.py
supplies the comparison sibling.

Usage: gpm_encfile.py <font>
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpm_io as G

if len(sys.argv) < 2:
    sys.exit("gpm_encfile: missing font name")
print(G.enc_json_for(sys.argv[1], os.environ.get("data_dir") or G.DATA))
