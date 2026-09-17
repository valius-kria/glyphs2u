# Some directories and lists necessary for deployment of lua tables and not noly for that
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
import os
font_dir = texmf_font_dir("type1/public/lm")
dest_dir = xdvipsk_cmap_dir("type1/public/lm")
# list all tables in the current working directory
lua_tables = []
lua_tables += [each for each in os.listdir(r"./") if each.endswith('.lua')]
lua_tables_copy = {
    "lmr10.lua": [ # all text fonts with 822 or 815 glyphs
        "lmr17", "lmr12", "lmr9", "lmr8", "lmr7", "lmr6", "lmr5", "lmb10",
        "lmbo10", "lmbx10", "lmbx12", "lmbx5", "lmbx6", "lmbx7", "lmbx8",
        "lmbx9", "lmbxi10", "lmbxo10", "lmcsco10", "lmcsc10", "lmdunh10",
        "lmduno10", "lmri10", "lmri12", "lmri7", "lmri8", "lmri9", "lmro10",
        "lmro12", "lmro17", "lmro8", "lmro9", "lmss10", "lmss12", "lmss17",
        "lmss8", "lmss9", "lmssbo10", "lmssbx10", "lmssdc10", "lmssdo10",
        "lmsso10", "lmsso12", "lmsso17", "lmsso8", "lmsso9", "lmu10",
        "lmvtk10", "lmvtko10", "lmvtl10", "lmvtlo10", "lmvtt10", "lmvtto10" ],
    "lmssq8.lua": ["lmssqbo8", "lmssqbx8", "lmssqo8"], # text fonts with 825 glyphs
    "lmtt10.lua": [ # text fonts with 785 or 786 glyphs
        "lmtcsc10", "lmtcso10", "lmtk10", "lmtko10", "lmtl10", "lmtlc10",
        "lmtlco10", "lmtlo10", "lmtt12", "lmtt8", "lmtt9", "lmtti10",
        "lmtto10" ],
    "lmsy10.lua": ["lmsy9", "lmsy8", "lmsy7", "lmsy6", "lmsy5"],
    "lmbsy10.lua": ["lmbsy7", "lmbsy5"],
    "lmmi10.lua": ["lmmi12", "lmmi9", "lmmi8", "lmmi7", "lmmi6", "lmmi5"],
    "lmmib10.lua": ["lmmib7", "lmmib5"]
    # no additional copies for lmex10.lua
}
