# Paths and tools for the font-investigation rules in mk/font.mk.
#
# This file came from the htf-fonts project, where it also configured an
# overlay texmf tree and the xmlforge test pipeline.  Neither of those is part
# of this project, so what is left is the font side: where the work dirs are,
# where the generated maps go, and which TeX Live tree to read.

this_cfg    := $(lastword $(MAKEFILE_LIST))
project_dir := $(abspath $(dir $(this_cfg))/..)
script_dir  := $(project_dir)/pyscripts
tfm_dir     := $(project_dir)/tfm
std_dir     ?= $(project_dir)

PYTHON      ?= python3

# The TeX Live tree is located through kpathsea, as everywhere in this project.
# Override to work against another installation:
#   make <target> KPSEWHICH=/usr/local/texlive/2026/bin/x86_64-linux/kpsewhich
KPSEWHICH   ?= kpsewhich
export KPSEWHICH
TEXMFDIST   := $(shell $(KPSEWHICH) -var-value=TEXMFDIST)

# Maps derived from the distribution are kept per release, so that regenerating
# against a newer tree can be compared with what an older one produced -- the
# same arrangement as glyphlists/sources/.  The release is the directory name
# above texmf-dist, e.g. 2026.
TL_BRANCH   ?= $(notdir $(patsubst %/,%,$(dir $(TEXMFDIST))))
data_rel    ?= $(TL_BRANCH)
data_dir    ?= $(project_dir)/$(data_rel)
export data_dir

# tex4ht's .htf files, the source the glyph property maps are seeded from.
# Later roots win, so a local or personal tree can override the distribution.
HTF_DIRS    ?= $(TEXMFDIST)/tex4ht/ht-fonts

# The built-in glyph list, from this project's own root.
builtin_glyph_map ?= $(project_dir)/builtin-glyph-map.json

# In htf-fonts this pointed at a glyphs2u checkout elsewhere.  Here the two are
# one project, so it is simply the project root; mk/font.mk still asks for it by
# name.
glyphs2u_dir ?= $(project_dir)

# Standard TeX Live tools.  dvilualatex renders the one-glyph-per-page specimen
# whose pages dvipng turns into rasters for the font-pair comparison.
texdvi      ?= dvilualatex
dvipng      ?= dvipng
