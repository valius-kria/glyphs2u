# Some directories and lists necessary for deployment of lua tables and not
# only for that.  This file, Makefile and lua tables are copied from ../lm
# directory. Names of lua tables are modified adding the 'm' in the
# beginning.  It is assumed that glyphs sets of the respective fonts are the
# same as in the lmodern set.
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
import os
font_dir = texmf_font_dir("type1/public/mlmodern")
dest_dir = xdvipsk_cmap_dir("type1/public/mlmodern")
# list all tables in the current working directory
lua_tables = []
lua_tables += [each for each in os.listdir(r"./") if each.endswith('.lua')]
lua_tables_copy = {
    "mlmr10.lua": [ # all text fonts with 822 or 815 glyphs
        "mlmr17", "mlmr12", "mlmr9", "mlmr8", "mlmr7", "mlmr6", "mlmr5", "mlmb10",
        "mlmbo10", "mlmbx10", "mlmbx12", "mlmbx5", "mlmbx6", "mlmbx7", "mlmbx8",
        "mlmbx9", "mlmbxi10", "mlmbxo10", "mlmcsco10", "mlmcsc10", "mlmdunh10",
        "mlmduno10", "mlmri10", "mlmri12", "mlmri7", "mlmri8", "mlmri9", "mlmro10",
        "mlmro12", "mlmro17", "mlmro8", "mlmro9", "mlmss10", "mlmss12", "mlmss17",
        "mlmss8", "mlmss9", "mlmssbo10", "mlmssbx10", "mlmssdc10", "mlmssdo10",
        "mlmsso10", "mlmsso12", "mlmsso17", "mlmsso8", "mlmsso9", "mlmu10",
        "mlmvtk10", "mlmvtko10", "mlmvtl10", "mlmvtlo10", "mlmvtt10", "mlmvtto10" ],
    "mlmssq8.lua": ["mlmssqbo8", "mlmssqbx8", "mlmssqo8"], # text fonts with 825 glyphs
    "mlmtt10.lua": [ # text fonts with 785 or 786 glyphs
        "mlmtcsc10", "mlmtcso10", "mlmtk10", "mlmtko10", "mlmtl10", "mlmtlc10",
        "mlmtlco10", "mlmtlo10", "mlmtt12", "mlmtt8", "mlmtt9", "mlmtti10",
        "mlmtto10" ],
    "mlmsy10.lua": ["mlmsy9", "mlmsy8", "mlmsy7", "mlmsy6", "mlmsy5"],
    "mlmbsy10.lua": ["mlmbsy7", "mlmbsy5"],
    "mlmmi10.lua": ["mlmmi12", "mlmmi9", "mlmmi8", "mlmmi7", "mlmmi6", "mlmmi5"],
    "mlmmib10.lua": ["mlmmib7", "mlmmib5"]
    # no additional copies for mlmex10.lua
}
