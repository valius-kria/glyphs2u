#!/usr/bin/env python
# Used as a configuration file for other Python scripts called from this directory
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
import os

# The following list could be given explicitly, up to convenience
lua_tables = []
lua_tables += [fn for fn in os.listdir(r"./") if fn.endswith('.lua')]
font_dir = texmf_font_dir("type1/public/mnsymbol")
dest_dir = xdvipsk_cmap_dir("type1/public/mnsymbol")

# The following lists all pfb fonts from font_dir with the same glyph sets and
# the same unicode mappings
lua_tables_copy = {
    "MnSymbol10.lua": [
        "MnSymbol5", "MnSymbol6", "MnSymbol7", "MnSymbol8", "MnSymbol9",
        "MnSymbol12"
    ],
    "MnSymbol-Bold10.lua": [
        "MnSymbol-Bold5", "MnSymbol-Bold6", "MnSymbol-Bold7",
        "MnSymbol-Bold8", "MnSymbol-Bold9", "MnSymbol-Bold12"
    ],
}
