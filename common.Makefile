# The common makefile for scripts managing tasks for building lua (and g2u)
# tables.  Makefiles in working directores do include this file with
# 'include' directive

# Export the working directtory, from which 'make' is called; enables import
# of config.py to other python scripts
export working_dir := $(abspath ./)
# The project root: the directory holding this common.Makefile, derived so
# that a working directory can live anywhere relative to it.
export project_dir := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
# The TeX Live tree is located through kpathsea; override to target another
# installation (see the root Makefile).
KPSEWHICH ?= kpsewhich
export KPSEWHICH
export PYTHONPATH = ${CURDIR}
export script_dir = $(project_dir)/pyscripts
# Define the Python interpreter (good practice)
PYTHON = python3 $(script_dir)# Or just python, or /usr/bin/python3, etc.

fonttable_dir := $(project_dir)/fonttable
export UNICODE_DIR := $(project_dir)

# Sometimes we need to obtain lua table from g2u table
%.lua:: %.g2u
	$(PYTHON)/g2u-to-lua.py $*.g2u

# Another way to obtain initial lua table: take pfb glyph list, remove ones
# from the builtin table, but not those, which in the biltin table are mapped
# to private area codes or need TeX font corrections.
# Initial Lua table for non-pfb fonts: include all without unicodes
%.lua:: fonts-glyphs-dict.json $(project_dir)/builtin-glyph-map.json \
 $(project_dir)/tex-specific.lua
	@ test -f $@ || $(PYTHON)/initial-lua.py $*.lua

# Create <font>.lua with EVERY glyph mapped to the unknown sentinel (0xFFFD),
# for fonts whose glyph names are wrong/meaningless so each glyph must be
# recognised visually with edit_knn.py.  Refuses to overwrite an existing
# <font>.lua.  Then run: make edit-<font>.lua
sentinels-%: fonts-glyphs-dict.json
	@ test -f $*.lua || $(PYTHON)/initial-lua.py $*.lua all

# Find unicodes by image analysis.
%-unicode: %.png $(script_dir)/get_unicode.py
	$(PYTHON)/get_unicode.py $*.png


# Copy values from another lua table.  Call as
# make source=another.lua copy-to-one
copy-to-%: fonts-glyphs-dict.json %.lua
	$(PYTHON)/copy-from.py $*.lua ${source}

# Remove unneeded glyph maps
%.cleaned: %-unneeded.json
	$(PYTHON)/remove-unneeded.py $*.lua $<
	touch $*.cleaned

# Detect glyphs that are in the built-in table with the same codes and ones
# not in the font (maybe were copied from other table)
%-unneeded.json: %.lua $(project_dir)/builtin-glyph-map.json \
 fonts-glyphs-dict.json $(script_dir)/find-unneeded-glyphs.py
	$(PYTHON)/find-unneeded-glyphs.py $*.lua $@

# Update or add (as comments, started with "-- ") unicode descriptions of
# codes used in the respective lines of the lua table.  We overwrite the same
# file, so the target is not a file name.
%.descr: %.lua $(UNICODE_DIR)/UnicodeData.pkl
	$(PYTHON)/lua-table-add-uni-descr.py $<
	touch $*.descr

# Obtain g2u table from .lua table with the same name
%.g2u: %.lua
	$(PYTHON)/lua-table-to-g2u.py $<

# Save Unicode data for the future use
%/UnicodeData.pkl:
	cd $(UNICODE_DIR) && $(MAKE) UnicodeData.pkl

# Save psfonts.map data for the future use
%/psfonts-map.pkl:
	cd $(project_dir) && $(MAKE) psfonts-map.pkl

# Transform data from psfonts.map to dictionary with pfb font names as keys
%/pfb-tfm-map.json: $(project_dir)/psfonts-map.pkl
	cd $(project_dir) && $(MAKE) pfb-tfm-map.json

# Generate font table(s) for a pfb font; call like
# make ../fonttable/mtms.tex
%.tex:
	$(PYTHON)/generate_fonttable_tex.py $(basename $(notdir $*))

# Compile the fonttable to a web PDF
# Ghostscript; call like
# make mtms.pdf
# The pdf file fill be copied to working dir from 'fonttable' folder
%.pdf: $(fonttable_dir)/%.tex %.lua
	cd $(fonttable_dir) && $(MAKE) $(basename $*).pdf
	mv $(fonttable_dir)/$*.pdf ./

# Testing diffs between dvips and xdvispk results
%-diff.pdf: %.lua $(fonttable_dir)/%.tex
	@ rm -f $(fonttable_dir)/$*-diff.pdf $*-diff.pdf
	@ cd $(fonttable_dir) && $(MAKE) $(basename $*)-diff.pdf && \
	{ echo "No diffs found!"; } || { mv $*-diff.pdf $(working_dir)/ }

# target:
# SVN_INFO := $(shell svn info . 1>&2 2> /dev/null; echo $$?)
# ifneq ($(SVN_INFO),0)
#     $(error "Not an SVN repo...")
# endif

# For checking files we need to compile them all, so prepare batch
# compilation variables:
all_lua := $(wildcard *.lua)
all_fontables := $(patsubst %.lua,%.pdf,$(all_lua))
# Now,
fonttables: $(all_fontables)
	echo "Built all font tables in PDF format!"

# Checking for missing unicodes
%-unimis.txt: %.pdf $(script_dir)/pdf-investigate.py
	$(PYTHON)/pdf-investigate.py $< $@

## fonftable directory cleaning
tex-%-clean:
	cd $(fonttable_dir) && $(MAKE) $*-clean

tex-clean:
	cd $(fonttable_dir) && $(MAKE) clean

# Test something in directory where fonttable resides (change the respective
# target test: in the Makefile of that directory)
test-tex:
	cd $(fonttable_dir) && $(MAKE) test

test-tex-%-lua: %.lua
	cd $(fonttable_dir) && $(MAKE) test-$*

# Finds glyph-set intersection of a lua table with the built-in lua table and
# check uniqueness of unicodes in the intersection set.  To check all lua
# tables, call make all-duplicates.json
%-duplicates.json:  %.lua $(project_dir)/builtin-glyph-map.json \
 $(script_dir)/rename-info.py
	$(PYTHON)/rename-info.py $*.lua

all-duplicates.json: (script_dir)/rename-info.py
all-duplicates.json: $(project_dir)/builtin-glyph-map.json config.py
	$(PYTHON)/rename-info.py all-tables

# Insert proposed new glyph names for the clashes in <font>-duplicates.json into
# <font>.lua, as ready-made '-->' comment lines, for later manual editing.
%-renames: %-duplicates.json $(project_dir)/builtin-roots.json \
 $(script_dir)/propose-renames.py
	$(PYTHON)/propose-renames.py $*.lua

# Check if all necessary glyphs have unicodes
%-undef.json: %.lua fonts-glyphs-dict.json \
 $(project_dir)/builtin-glyph-map.json
	$(PYTHON)/check-fullness.py $<

# other prerequisites:
%-undef.json: $(project_dir)/tex-specific.lua

# Unifying several steps in one for earlier built tables
%.check: %.lua %-duplicates.json %-undef.json %.descr %.cleaned
	touch $@

check-all: $(addsuffix .check, $(basename $(wildcard *.lua)))

## Prepare comparison of glyphs and unicodes.
# Export glyph images using fontforge and save the glyph list in
# <font>-glyphs.json for later import.
%-glyphs.json: config.py
	@if [ -f $@ ]; then \
	   echo "File " $@ " exists."; \
    else \
		fontforge -script $(script_dir)/font-glyph-to-images.py $*.pfb ; \
    fi

# Save the glyph list, which is build in xdvipsk, as a dictionary
%/builtin-glyph-map.json:
	cd $(dir $@) && $(MAKE) $(notdir $@)

# Write html file for alignment of glyphs and respectives unicodes
%.html: %.lua %-glyphs.json $(project_dir)/builtin-glyph-map.json \
 $(script_dir)/pfb-unicode-html.py
	$(PYTHON)/pfb-unicode-html.py $*

# Deploy the lua tables from the current directory. Also copy a table
# <font>.lua to files listed in the variable <font>_list.  Checks for changes
# and doesn't overwrite targets if no changes are found.
# NOTE. All hyphens in name <font>_list should be changed to _.
deploy: config.py
	$(PYTHON)/deploy_lua_tables.py

# Deploy only one lua table with her copies
deploy-%: config.py
	$(PYTHON)/deploy_lua_tables.py $*.lua

# Deploy only one lua table and no copies
deploy-%-only: config.py
	$(PYTHON)/deploy_lua_tables.py $*.lua 0

## Investigation of glyph sets of fonts in 'font_dir'.
# For the beginning, save glyphs of all fonts from there in
fonts-glyphs-dict.json: config.py
	@if [ -f "fonts-glyphs-dict.json" ]; then \
       echo "File fonts-glyphs-dict.json exists."; \
   else \
       fontforge -script $(script_dir)/font-glyphs-json.py ; \
   fi

# Find and print relations between glyph sets in 'font_dir' fonts
Glyph-sets.txt: $(script_dir)/compare_glyph_sets.py
Glyph-sets.txt: fonts-glyphs-dict.json
	$(PYTHON)/compare_glyph_sets.py

# Differences between glyph sets can be assimilated by builtin glyph map
Glyph-sets-nobuilt.txt: $(project_dir)/adobe-private-lua.json
Glyph-sets-nobuilt.txt: $(script_dir)/compare-gs-nobuilt.py
Glyph-sets-nobuilt.txt: $(project_dir)/builtin-glyph-map.json
Glyph-sets-nobuilt.txt: fonts-glyphs-dict.json
	$(PYTHON)/compare-gs-nobuilt.py

# Find missing tables in config.py comparing to fonts in font_dir
config-missing-fonts.json: config.py fonts-glyphs-dict.json \
 $(script_dir)/find-missing-in-config.py
	$(PYTHON)/find-missing-in-config.py

# Recognize necessity to dublicate encodings
common-encodings.json: $(script_dir)/find-common-encodings.py
common-encodings.json: config.py $(project_dir)/pfb-tfm-map.json
	$(PYTHON)/find-common-encodings.py

# Not all common encodings deal with letters, that change code depending on
# weight.
dupl-encodings.json: $(script_dir)/check-encodings.py
dupl-encodings.json: common-encodings.json fonts-glyphs-dict.json
	$(PYTHON)/check-encodings.py

## TTF and OpenType fonts
# Export glyph images using fontforge and save the glyph list in
# <font>-unicodes.json for later import.  As the font extension is not fixed, 
%-unicodes.json: config.py
%-unicodes.json: $(script_dir)/gid-glyphs-save.py
	fontforge -script $(script_dir)/gid-glyphs-save.py $*

# Write html file for alignment of glyphs and respectives unicodes for type0
# fonts
%.html: %.lua %-unicodes.json $(project_dir)/builtin-glyph-map.json \
 $(script_dir)/nonpfb-unicode-html.py
	$(PYTHON)/nonpfb-unicode-html.py $*


## Unsupervised (k-NN) classification: emit a draft Lua table with
## Interactive Tkinter editor: open <font>, click a candidate to write the
## chosen codepoint sequence into <font>.lua and advance to the next glyph.
## By default only the unknown (0xFFFD) entries in <font>.lua are shown;
## add ALL=1 to review every entry already in the table.  New glyphs are
## added by hand after checking <font>.html, never scanned from the font.
## Usage: make edit-<font-name>.lua [TEXT_SIZE=<n>] [ALL=1]
## e.g. make edit-mt2syaf.lua   /   make edit-mt2exa.lua TEXT_SIZE=14 ALL=1
edit-%.lua: %.lua config.py $(project_dir)/glyphs-dataset/knn-index.joblib \
 $(script_dir)/edit_knn.py
	@test -n $* || { echo "Usage: make edit-FONT.lua [TEXT_SIZE=<n>]" >&2; exit 1; }
	$(PYTHON)/edit_knn.py $(if $(TEXT_SIZE),--text-size $(TEXT_SIZE)) $(if $(ALL),--all-glyphs) $*

.PRECIOUS: %-glyphs.json %.tex %.dvi %.pdf
.PRECIOUS: %-unneeded.json %-duplicates.json
.PRECIOUS: %.lua %-undef.json fonts-glyphs-dict.json

# It's good practice to declare targets that don't represent files as .PHONY
.PHONY: deploy deploy-% test-tex %-clean g2u-%-lua copy-from reindex edit-%.lua sentinels-%

.FORCE:
