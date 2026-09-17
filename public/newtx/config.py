# Some directories and lists necessary for deployment of lua tables and not noly for that
# import os # just for the case when 'lua_tables' list is made by reading the
# directory content as in the following line:
# lua_tables += [each for each in os.listdir(r"./") if each.endswith('.lua')]

# Parameters actual for deployment
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
font_dir = texmf_font_dir("type1/public/newtx")
dest_dir = xdvipsk_cmap_dir("type1/public/newtx")
lua_tables = [
    "LibertineMathBMI.lua", "MinLibBol.lua", "MinLibBolIta.lua",
    "MinLibIta.lua", "MinLibReg.lua", "NewTXBMI.lua", "ebgBRM.lua",
    "fxlri-5letters.lua", "fxlzi-5letters.lua", "ntxbexb.lua",
    "ntxsups-Bold.lua", "ntxsups-BoldItalic.lua", "ntxsups-Italic.lua",
    "ntxsups-Regular.lua", "ntxsupsalt-Bold.lua", "ntxsupsalt-Regular.lua",
    "ntxsybalt.lua", "ntxsyralt.lua", "rntxbmi.lua", "rntxmi.lua",
    "rtxbmi-rev.lua", "rtxbmi5.lua", "rtxbmi7.lua", "txbexas.lua",
    "txbexs.lua", "txbmiaX.lua", "txbsy7.lua", "txbsym.lua", "txbsys.lua",
    "txex-bar.lua", "txexas.lua", "txexs.lua", "txmiaX.lua", "txsy7.lua",
    "txsym.lua", "txsys.lua", "ztmb.lua", "ztmbi.lua", "ztmr.lua",
    "ztmri.lua", "ztmrsl.lua", "zxlr.lua",
]
lua_tables_copy = {
    "LibertineMathBMI.lua": [ "LibertineMathBMI5", "LibertineMathBMI7", ],
    "NewTXBMI.lua": [ "NewTXBMI5", "NewTXBMI7", ],
    "fxlri-5letters.lua": [ "fxlri-7letters", ],
    "fxlzi-5letters.lua": [ "fxlzi-7letters", "rtxmi5", "rtxmi7", "zxlri",
                            "zxlz", "zxlzi", ],
    "ntxsups-BoldItalic.lua": [ "ntxsupsalt-BoldItalic", "ntxsupsalt-Italic", ],
    "rntxbmi.lua": [ "rntxbmi5", "rntxbmi7", ],
    "rntxmi.lua": [ "rntxmi5", "rntxmi7", ], 
    "rtxbmi-rev.lua": [ "rtxbmi5-rev", "rtxbmi7-rev", ],
    "txbsy7.lua": [ "txbsy5", ],
    "txex-bar.lua": [ "txbex-bar", ],
    "txsy7.lua": [ "txsy5", ],
    "ztmb.lua": [ "ztmbsl", ],
}
# For completeness check of all fonts in the font_dir all fonts should be
# mentioned.  But some fonts do not need an unicode maps, either because of
# glyph names starting with 'uni' or 'u', or because of glyph names included
# in the built-in table.
lua_tables_not_needed = [
    "Libertine-nu", "LibertineI-5nu", "LibertineI-7nu", "LibertineI-nu",
    "LibertineMathBRM", "LibertineMathMI", "LibertineMathMI5",
    "LibertineMathMI7", "LibertineMathRM", "LibertineTheta-Regular",
    "LibertineZ-nu", "LibertineZI-5nu", "LibertineZI-7nu", "LibertineZI-nu",
    "NewTXMI", "NewTXMI5", "NewTXMI7", "ebgBMI", "ebgMI", "ebgMRM",
    "fxlri-vw", "fxlri-vw5", "fxlri-vw7", "fxlzi-jv", "fxlzi-jv5",
    "fxlzi-jv7", "fxlzi-vw", "fxlzi-vw5", "fxlzi-vw7",
    "ntxbexmods", "ntxexb", "ntxexmods", "stxscr", "txbmiaSTbb",
    "txmiaSTbb", "ztmfigs-bsl", "ztmfigs-sl", "zxlr-5nums", "zxlr-7nums",
]
# Neither constructed, completed, or checked tables; to use in stages when
# there are fonts in font_dir not yet processed.
lua_tables_tocheck = [
]

