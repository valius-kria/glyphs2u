"""Locating font directories and table deployment directories in TeX trees.

Every working directory has a `config.py` saying where its fonts live and
where its Lua tables should be deployed.  Both vary between installations,
so neither is written as a fixed path here.

Fonts
-----
Most of the fonts covered by this project are distributed with TeX Live, and
are found relative to `texmf-dist`, which is located through kpathsea:

    font_dir = texmf_font_dir("type1/public/lm")

Some freely available font families are *not* part of TeX Live (bbm, for
instance).  Those need an explicit path, which is best taken from the
environment so that the working directory stays portable:

    font_dir = font_dir_from_env("BBM_FONT_DIR")

Deployment
----------
`xdvipsk` always reads its built-in table and the convoluted table
`font_glyph_maps.lua`.  Per-font tables are additional: they only have to be
somewhere kpathsea will find them.  That can be the system-wide tree, your
personal tree, or even the directory holding the manuscript being typeset --
which is why the choice belongs to each working directory.  The default here
is your personal tree (TEXMFHOME), because it is writable without root:

    dest_dir = xdvipsk_cmap_dir("type1/public/lm")

Point it at another tree by passing `tree=`, or by setting
GLYPHS2U_DEPLOY_TREE in the environment.
"""

import functools
import os
import subprocess

# The TeX Live tree is whichever this kpsewhich belongs to.  Override with
# the KPSEWHICH environment variable to work against another installation.
KPSEWHICH = os.environ.get("KPSEWHICH", "kpsewhich")


@functools.lru_cache(maxsize=None)
def texmf_var(name):
    """Value of a kpathsea variable (TEXMFDIST, TEXMFHOME, ...), or None."""
    try:
        out = subprocess.check_output(
            [KPSEWHICH, f"-var-value={name}"], text=True,
            stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out or None


# Nothing here raises when fonts turn out to be absent.  A working directory
# must load whether or not its fonts are installed, because most of what the
# project does -- joining the tables, deploying them, checking them against
# the built-in table -- needs the tables only.  The fonts are needed just for
# rendering glyph images and for reading a font's glyph names, and those
# callers ask `fonts_available' first and skip what they cannot do.


def texmf_font_dir(subpath):
    """Directory of fonts shipped with TeX Live: <texmf-dist>/fonts/<subpath>.

    `subpath` is as it appears in the distribution, e.g. "type1/public/lm"
    or "type1/hoekwater/manfnt-font".  Returns "" if no TeX Live tree can be
    found at all.
    """
    dist = texmf_var("TEXMFDIST")
    if not dist:
        return ""
    return os.path.join(dist, "fonts", subpath)


def font_dir_from_env(varname, default=None):
    """Directory of fonts installed outside TeX Live.

    Not every freely available font family is part of TeX Live; such a family
    is installed wherever its user put it, so the path is taken from the
    environment variable `varname`.  Returns "" when the variable is unset,
    which is the ordinary case for someone who does not have these fonts.
    """
    return os.environ.get(varname) or default or ""


def fonts_available(font_dir):
    """True if the font files are actually there to be read."""
    return bool(font_dir) and os.path.isdir(font_dir)


def missing_fonts_note(font_dir, working_dir=None):
    """A line explaining that a step was skipped for want of the fonts."""
    where = f" for {working_dir}" if working_dir else ""
    if not font_dir:
        return (f"fonts not located{where}: the font directory is not set. "
                "The tables are usable without them; only rendering and "
                "glyph-name extraction need the font files.")
    return (f"fonts not found{where}: {font_dir} does not exist. "
            "The tables are usable without them; only rendering and "
            "glyph-name extraction need the font files.")


def xdvipsk_cmap_dir(subpath, tree=None):
    """Deployment directory: <tree>/fonts/cmap/xdvipsk/<subpath>.

    `tree` defaults to GLYPHS2U_DEPLOY_TREE if set, otherwise to your
    personal texmf tree (TEXMFHOME), which needs no root privileges.
    """
    if tree is None:
        tree = os.environ.get("GLYPHS2U_DEPLOY_TREE") or texmf_var("TEXMFHOME")
    if not tree:
        raise RuntimeError(
            "cannot determine a tree to deploy into; set GLYPHS2U_DEPLOY_TREE "
            "to the texmf tree that should hold the tables.")
    return os.path.join(tree, "fonts", "cmap", "xdvipsk", subpath)
