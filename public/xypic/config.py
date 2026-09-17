# Some directories and lists necessary for deployment of lua tables and not
# only for that.
# import os

from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
font_dir = texmf_font_dir("type1/public/xypic")
dest_dir = xdvipsk_cmap_dir("type1/public/xypic")

lua_tables = [
    "xyatip10.lua", # left-hand side arrow tips in "technical style",
                    # unicodes present arrows of near directions
    "xycirc10.lua", # 1/8 circle segments at various sizes and directions,
                    # without meaningful unicodes, just 'Arc' code for all
    "xybsql10.lua", # quarter circles for hooks and squiggles at one size,
                    # but at many directions, just 'Arc' code for all
    "xydash10.lua", # dashes at various directions, unicodes present
                    # line-form symbols of as near as possible directions
]
# lua_tables += [each for each in os.listdir(r"./") if each.endswith('.lua')]
lua_tables_copy = {
    "xyatip10.lua": [
        "xybtip10", # right-hand side arrow tips in technical style
        # one-side arrow tips in "Computer Modern style"
        "xycmat10", "xycmat11", "xycmat12", "xycmbt10", "xycmbt11", "xycmbt12",
        # one-side arrow tips in "Euler style"
        "xyeuat10", "xyeuat11", "xyeuat12", "xyeubt10", "xyeubt11", "xyeubt12",
        # one-side arrow tips in Lucida arrow style
        "xyluat10", "xyluat11", "xyluat12", "xylubt10", "xylubt11", "xylubt12",
    ],
}
