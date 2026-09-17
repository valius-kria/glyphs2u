# Some directories and lists necessary for deployment of lua tables and not
# only for that.
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
import os
font_dir = texmf_font_dir("type1/public/amsfonts/cm")
dest_dir = xdvipsk_cmap_dir("type1/public/amsfonts/cm")
lua_tables = [ "cmmi10.lua", # only tex-specific changes and old style digits
               "cmmib10.lua", # bold math italic, both latin and greek
               "cmsy10.lua", #  math script letters and tex-specific changes
               "cmbsy10.lua", # unicodes for bold script letters
               "cmr10.lua", # only dotlessj set
               "cmbx10.lua", # in bold fonts math codes for greek bold are added
               "cmbxsl10.lua", # bold italic/slanted greek gets math codes
               "cmtex10.lua", # some arrow corrected
               "cmex10.lua", # only private area values from builtin
              ]
lua_tables_copy = {
    "cmmi10.lua": [ "cmmi12", "cmmi5", "cmmi6", "cmmi7", "cmmi8", "cmmi9" ],
    "cmsy10.lua": [ "cmsy5", "cmsy6", "cmsy7", "cmsy8", "cmsy9" ],
    "cmr10.lua": [ "cmr12", "cmr17", "cmr5", "cmr6", "cmr7", "cmr8", "cmr9",
                   "cmss10", "cmss12", "cmss17", "cmss8", "cmss9", "cmssi10",
                   "cmssi12", "cmssi17", "cmssi8", "cmssi9", "cmti10",
                   "cmti12", "cmti7", "cmti8", "cmti9", "cmsl10", "cmsl12",
                   "cmsl8", "cmsl9", "cmtt10", "cmtt12", "cmtt8", "cmtt9",
                   "cmff10", "cmfi10", "cmcsc10", "cmdunh10", "cmitt10",
                   "cmsltt10", "cmssq8", "cmssqi8", "cmtcsc10", "cmu10",
                   "cmvtt10" ],
    "cmbx10.lua": [ "cmbx12", "cmbx5", "cmbx6", "cmbx7", "cmbx8", "cmbx9",
                    "cmfib8", "cmb10", "cmssbx10", "cmssdc10" ],
    "cmbxsl10.lua": [ "cmbxti10", ],
    "cmtex10.lua": [ "cmtex8", "cmtex9" ],
}
lua_tables_not_needed = [ "cminch", ]
