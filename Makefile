# Makefile for managing tasks in the root directoy of the project

script_dir = pyscripts
# Define the Python interpreter (good practice)
PYTHON = python3 $(script_dir)#
# The project root: the directory holding this Makefile.  Derived, so the
# project works wherever it is checked out.
export project_dir := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
export UNICODE_DIR := $(project_dir)

# The TeX Live tree is located through kpathsea, i.e. whichever TeX Live the
# `kpsewhich' on your PATH belongs to.  Override on the command line to work
# against a different installation, e.g.
#   make <target> KPSEWHICH=/usr/local/texlive/2024/bin/x86_64-linux/kpsewhich
KPSEWHICH ?= kpsewhich
export KPSEWHICH

# Source data locations, resolved from that tree.
TEXMFDIST := $(shell $(KPSEWHICH) -var-value=TEXMFDIST)
psfonts_map := $(shell $(KPSEWHICH) psfonts.map)

# To start with some new pfb font directory, we need to know at least one pfb
# font from it.  Ususally you know the name of the font, and the first
# question is: has the project already some working directory for this pfb
# font directory.  Each config.py file contains definition of variable
# 'font_dir' with the path to the corresponding pfb font directory.  The
# following target allow to find already existing project directory.
print-%-dir:
	$(PYTHON)/find-working-dir-for-pfb.py $(dir $(shell $(KPSEWHICH) -a $*.pfb))

# In case there is not yet a corresponding project directory, call
# make <dirname>/config.py font_path=/path/to/directory/where/pfb/file/located
# with font_path value copied from what was written by the call of the
# previous target, and some initial configuration for the new directory
# <dirname> will be done.
%/config.py:
	$(PYTHON)/make-working-dir.py $* ${font_path}

# Renew the unicode data dictionary in case new version of UnicodeData is downloaded
UnicodeData.pkl: unicode-data/UnicodeData.txt
	$(PYTHON)/unicodedata-to-dict.py

# Present unicode data dictionary in readable/editable json format.
UnicodeData.json: UnicodeData.pkl
	$(PYTHON)/unicode-dict-to-json.py

# Renew the psfonts.map data dictionary in case the file is chnaged
psfonts-map.pkl: $(psfonts_map)
	$(PYTHON)/psfonts-map-to-dict.py $<

# Transform data from psfonts.map to dictionary with pfb font names as keys
pfb-tfm-map.json: psfonts-map.pkl
	$(PYTHON)/psfonts-data-to-pfb-map.py

# Find tfm to encoding map from psfonts.map as dictionary
tfm-enc-map.json: psfonts-map.pkl
	$(PYTHON)/psfonts-tfm-enc.py

# Present encoding to pfb list map, to find sets where renaming conflicts can occur.
enc-pfb-map.json: pfb-tfm-map.json
	$(PYTHON)/psfonts-data-to-enc-map.py

# Save the glyph list, which is build in xdvipsk, as a dictionary
builtin-glyph-map.json: glyphlists/glyphlist_table.lua
	$(PYTHON)/lua-table-to-dict.py $< $@

# Reversed map of size/style-variant name roots (radical, integral, hat, ...)
# and their variation-selector suffix families, derived from the built-in map.
# Used to propose new glyph names when renaming clashes are detected.
builtin-roots.json: builtin-glyph-map.json $(script_dir)/build-roots.py
	$(PYTHON)/build-roots.py $< $@

# Save lua table to dictionary for checking
%-lua.json: %.lua
	$(PYTHON)/lua-table-to-dict.py $< $@

# The Private Use Area replacement map, as a dictionary for the scripts.
# The Lua table is the source: it is the curated one, carrying the Unicode
# names as comments and the more exact values arrived at over time.  The
# dependency keeps the JSON from falling behind it.
adobe-private-lua.json: adobe-private/adobe-private.lua
	$(PYTHON)/lua-table-to-dict.py $< $@

# Scanning the production files for information about used tfm files.
# At first, find list of .fls files
fls-files-list.json:
	$(PYTHON)/find-fls-files.py

# Copy fls files to local directory
fls-files.copied: fls-files-list.json
	$(PYTHON)/copy-fls-files.py
	touch fls-files.copied

# Read tfm file names from fls files
prod-tfm-list.json: $(script_dir)/tfm-fls-extract.py
prod-tfm-list.json: fls-files.copied
	$(PYTHON)/tfm-fls-extract.py

# Find pfb file names from tfm names from fls files
prod-pfb-dict.json: $(script_dir)/pfb-from-tfm.py
prod-pfb-dict.json: prod-tfm-list.json pfb-tfm-map.json
	$(PYTHON)/pfb-from-tfm.py

# Group pfb files by directories
prod-pfb-dirs.json: $(script_dir)/pfb-dirs.py
prod-pfb-dirs.json: prod-pfb-dict.json
	$(PYTHON)/pfb-dirs.py

# List config files
config-list.json: $(script_dir)/list-config-files.py
	$(PYTHON)/list-config-files.py

# Join lua tables from config files; also outputs 'lua_tables_aliases_dict.json'
font_glyph_maps.json: config-list.json
font_glyph_maps.json: $(script_dir)/join-lua-tables.py
	$(PYTHON)/join-lua-tables.py

# Transform joined lua tables data into nested dictionary
font_glyph_dict.json: font_glyph_maps.json
font_glyph_dict.json: $(script_dir)/lua-data-to-dict.py
	$(PYTHON)/lua-data-to-dict.py

# Bild glyph tree
glyph-uni-tree.json: font_glyph_dict.json
glyph-uni-tree.json: $(script_dir)/glyph-uni-tree.py
	$(PYTHON)/glyph-uni-tree.py

# Build set-like structure for joined lua tables
lua-table-glyph-values.json: font_glyph_dict.json
lua-table-glyph-values.json: $(script_dir)/lua-table-glyph-values.py
	$(PYTHON)/lua-table-glyph-values.py

# Compare lua tables by equality and save the map to representatives
lua-tables-partition-map.json: lua-table-glyph-values.json
lua-tables-partition-map.json: $(script_dir)/partition-lua-tables.py
	$(PYTHON)/partition-lua-tables.py

# Output joined lua tables wrt comparison
font_glyph_maps.lua: lua-tables-partition-map.json font_glyph_maps.json
font_glyph_maps.lua: lua_tables_aliases_dict.json
font_glyph_maps.lua: $(script_dir)/output-joined-table.py
	$(PYTHON)/output-joined-table.py

# Compare glyph-values of lua tables
lua-tables-rels.txt: lua-table-glyph-values.json
lua-tables-rels.txt: $(script_dir)/compare-lua-tables.py
	$(PYTHON)/compare-lua-tables.py

# Put joined lua tables in table name order
font_glyph_maps_sorted.lua: font_glyph_maps_ST.lua
font_glyph_maps_sorted.lua: $(script_dir)/sort-glyph-maps.py
	$(PYTHON)/sort-glyph-maps.py font_glyph_maps_ST.lua font_glyph_maps_sorted.lua

## ML glyph classifier — repo-wide dataset and model
# Build/refresh the labeled glyph-image dataset for ONE working directory.
# Usage: make dataset DIR=public/lm
# Output lands under glyphs-dataset/<codepoint_hex>/<font>_<glyph>.png
dataset:
	@test -n "$(DIR)" || { echo "Usage: make dataset DIR=<working-dir-relative-to-project-root>" >&2; exit 1; }
	$(PYTHON)/render_dataset.py --working-dir $(project_dir)/$(DIR)

# Rebuild the entire dataset for every working dir listed in config-list.json.
dataset-all: config-list.json
	$(PYTHON)/render_dataset.py --all

# Add OTF/TTF training samples from a directory tree (uses each font's cmap as
# the label).  Usage: make dataset-otf DIR=/usr/local/texlive/2024/texmf-dist/fonts/opentype/public
dataset-otf:
	@test -n "$(DIR)" || { echo "Usage: make dataset-otf DIR=<otf-or-ttf-directory-tree>" >&2; exit 1; }
	$(PYTHON)/render_dataset.py --otf-dir $(DIR)

# Build the k-NN index for the unsupervised classifier.
# Writes glyphs-dataset/knn-index.joblib.
index:
	$(PYTHON)/build_index.py

glyphs-dataset/knn-index.joblib: $(script_dir)/build_index.py
	$(MAKE) index

# List unique fonts in the dataset (also persists glyphs-dataset/fonts.txt).
list-fonts:
	$(PYTHON)/list_dataset_fonts.py --output glyphs-dataset/fonts.txt

# Remove dataset entries whose primary codepoint is in a Private Use Area
# (font-specific, useless as labels).  Pass DRY_RUN=1 to preview without
# touching disk.  Re-run `make index` afterwards.
clean-pua:
	$(PYTHON)/clean_pua.py $(if $(DRY_RUN),--dry-run)

## Curated math-OTF directories from TeX Live.  Overridable on the command
## line: `make dataset-math-otf TLROOT=/path/to/texmf-dist/fonts/opentype/public`
## Latin Modern Math (lm-math) is intentionally omitted — its shapes already
## live in the dataset as PFB lm.  Edit MATH_OTF_DIRS below to add or drop a
## family.
TLROOT ?= $(TEXMFDIST)/fonts/opentype/public
MATH_OTF_DIRS = \
    $(TLROOT)/tex-gyre-math \
    $(TLROOT)/asana-math \
    $(TLROOT)/firamath \
    $(TLROOT)/erewhon-math \
    $(TLROOT)/garamond-math \
    $(TLROOT)/xcharter-math

# Report cmap coverage of sentinel codepoints for every font in the curated
# list.  Run this before dataset-math-otf to confirm Unicode conventions
# match the project's PFB Lua tables.  fontforge's noisy stderr warnings
# about glyph-name vs cmap mismatches are filtered out.
inspect-math-otf:
	@$(PYTHON)/inspect_otf_cmap.py $(addprefix --dir ,$(MATH_OTF_DIRS)) 2>/dev/null

# Ingest the curated math-OTF list into glyphs-dataset/.  After this, run
# `make index` to rebuild glyphs-dataset/knn-index.joblib.
dataset-math-otf:
	@for d in $(MATH_OTF_DIRS); do \
	    if test -d "$$d"; then \
	        echo "=== $$d ==="; \
	        $(PYTHON)/render_dataset.py --otf-dir $$d; \
	    else \
	        echo "skip $$d (not a directory)"; \
	    fi; \
	done

.PHONY: print-%-dir dataset dataset-all dataset-otf dataset-math-otf \
        inspect-math-otf index list-fonts clean-pua

.FORCE:
