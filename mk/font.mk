# Per-tfm font-investigation rules: glyph exports, encodings, dvipng rasters,
# and font-variant comparison.  Include this from a local Makefile in a tfm
# work directory (under tfm/).  Written with the help of Claude Opus model.
include $(dir $(lastword $(MAKEFILE_LIST)))shared.mk

# --- which font this work directory is for -----------------------------------
# Every pattern rule below matches ANY <font>.* stem, and nothing ties the stem
# to the directory it is run in.  So `make <other-font>.cmp.html` in the wrong
# work dir does not fail: it renders that font's rasters here, finds no plain
# sibling to compare against, and writes a 253-byte map and an empty review page
# -- an answer that looks like an answer.  The same slip leaves a bare
# <other-font>.gpm.json skeleton behind, newer than the real record and with
# nothing in it.
#
# A work dir is for exactly one font -- its own directory name -- plus, for the
# comparison, that font's plain sibling, whose .pos rasters are rendered here.
# The guard is a SECOND-EXPANDED PREREQUISITE rather than a recipe line, so it
# fires while the rule is being considered -- before any raster is on disk.
this_font := $(notdir $(CURDIR))
# The plain sibling's name lives in the fixed file 'plain' in this dir (written
# by `make <font>.tfmdir`); read it once, both for the guard and so its rasters
# can be a prerequisite of the comparison.  A tfm dir has exactly one plain
# counterpart, so a fixed file suffices -- no per-target computed prerequisite.
#
# When the file is absent, ASK rather than give up.  It is only a cache of what
# cmp_sibling.py works out, and a dir can easily end up without one -- .tfmdir
# writes it only if the sibling resolved at the moment the dir was made, so a
# font seeded before its pairing was derivable has none.  An empty $(plain) then
# quietly dropped the plain font's rasters from the comparison's prerequisites,
# and cmp_classify wrote a map with every count zero: an answer that looks like
# an answer, which is exactly what the directory guard above exists to prevent.
plain     := $(shell cat plain 2>/dev/null || \
                     $(PYTHON) $(script_dir)/cmp_sibling.py $(this_font) 2>/dev/null)

# --- plain-named helpers for this dir's own font ------------------------------
# So a work dir needs no font name on the command line: `make sibling` rather
# than `make <font>.gpm.sibling`.  All of them read $(this_font) above.

# `make reviewed` writes down that this record has been read and found right --
# ONE entry at font level, because reading <font>.gpm.html is one act about one
# font, not a separate observation per glyph.  It changes no value; it says the
# record was looked over, so it need not be looked over again, and `make show`
# says which fonts still lack the note.  EXCEPT=<positions> records the rows the
# reading found wrong, so the note carries what is still open; WHAT=<name> if
# something other than the review page was read.
#   make reviewed        make reviewed EXCEPT=24,82        make show
.PHONY: reviewed show
reviewed: ; @$(PYTHON) $(script_dir)/gpm_set.py $(this_font) --reviewed $(WHAT) \
              $(if $(EXCEPT),--except $(EXCEPT))
show:     ; @$(PYTHON) $(script_dir)/gpm_set.py $(this_font) --show

# `make sibling` carries the paired font's properties across, minus the axis the
# pair differs by; sibling-dry reports without writing.
.PHONY: sibling sibling-dry
sibling:     ; @$(MAKE) --no-print-directory $(this_font).gpm.sibling
sibling-dry: ; @$(PYTHON) $(script_dir)/gpm_sibling.py $(this_font) --dry-run

# `make rename` writes the published name for every dotted glyph that needs one;
# rename-dry proposes without writing.  Read the dry run first: the names reach
# the lua table, and a rename is also what keeps a row from being pruned, so one
# on the wrong glyph puts a row back that should not be there.
.PHONY: rename rename-dry
rename:     ; @$(MAKE) --no-print-directory $(this_font).gpm.rename
rename-dry: ; @$(PYTHON) $(script_dir)/gpm_rename.py $(this_font) --list \
                  --data $(data_dir) \
                  $(if $(wildcard $(builtin_glyph_map)),--builtin $(builtin_glyph_map))

# `make plain` rewrites this dir's 'plain' file from the current pairing, so an
# edit to the family's ../pairs map reaches a work dir that already exists.
# Not resolved on every make invocation: that would put a Python start-up in
# front of every command in the tree, for a value that changes about never.
# `make htf-entry` writes the entry as it should stand in the table: an
# ['alias'] where the characters are identical to the entry it would alias, a
# full ['chars'] table where they are not.  Named <ENTRY>.htf.lua, after the htf
# TARGET from 2024/tfm-htf-map.json rather than after this directory's tfm --
# bbm10's block is ["bbm"], and the file should say so.
#
# An alias is a CONCLUSION.  The comparison is against the owner's NEW values,
# from its own map in the sibling work dir, not against the characters the table
# holds today: those are still the old uncomposed letters, so comparing with them
# would call every cut different and give each its own table -- the opposite of
# the truth, bbmbx's 58 composed values being identical to bbm's.
#
# For the full table of one font whatever an alias could do -- which is what you
# read when checking -- ask for <font>.htf.lua by name.
.PHONY: htf-entry
htf-entry: $(this_font).gpm.map.json
	@$(PYTHON) $(script_dir)/htf_entry.py $(this_font) --data $(data_dir)

# `make exclude` lists the slots this font names and fills with something that
# is not a glyph -- drawn, so no emptiness test rejects them, but drawn in the
# wrong place: bbmssbx10's nine circumflex composites are the base letter's
# outline left of the origin, two thirds of it outside the advance width.
# `make exclude-seed` writes them into <font>.exclude COMMENTED OUT; uncommenting
# one is the decision, and gpm_init then skips it as it skips '.notdef'.  A
# re-seed keeps every line already there, as the family 'pairs' file does.
.PHONY: exclude exclude-seed
exclude:      $(this_font).metrics.json
	@$(PYTHON) $(script_dir)/gpm_exclude.py $(this_font) $(if $(MARGIN),--margin $(MARGIN))
exclude-seed: $(this_font).metrics.json
	@$(PYTHON) $(script_dir)/gpm_exclude.py $(this_font) --seed \
	  $(if $(MARGIN),--margin $(MARGIN))

.PHONY: plain
plain:
	@if s=`$(PYTHON) $(script_dir)/cmp_sibling.py $(this_font) 2>/dev/null`; then \
		echo "$$s" > plain; echo "plain sibling: $$s"; \
	else rm -f plain; echo "no comparison pair for $(this_font) -- 'plain' removed"; fi

wrong_dir = $(error '$(1)' is not this directory's font -- here is '$(this_font)'$(if $(plain), (plain sibling '$(plain)')). Run it in that font's own work dir: make -C $(tfm_dir)/<supplier>/<family>/$(1) <target>, or `make $(1).tfmdir` in $(project_dir) to create one)
# stem must be this directory's font ...
own  = $(if $(filter $(1),$(this_font)),,$(call wrong_dir,$(1)))
# ... or its plain sibling, whose rasters the comparison renders here too
pair = $(if $(filter $(1),$(this_font) $(plain)),,$(call wrong_dir,$(1)))

# Enabled here rather than further down: the guard above is a prerequisite, so
# every guarded rule must be defined after this directive.  Rules with no '$$'
# in their prerequisites are unaffected by it.
.SECONDEXPANSION:

# --- the generated maps these rules depend on --------------------------------
# They live in data_dir and their rules live in the top Makefile, so from a work
# dir make cannot build one -- and when a missing map blocks a pattern rule,
# make blames the target that was asked for:
#     make: *** No rule to make target 'stix-mathcal-bold.cmp.html'.  Stop.
# which says nothing about htf_mfont_targets.json being the actual cause.  So
# hand any data_dir map back to the top Makefile, and the chain builds itself.
# Tree-derived maps: under the branch, so the sub-make is asked for the
# branch-qualified name it actually has a rule for.
$(data_dir)/%.json:
	$(MAKE) -C $(project_dir) $(data_rel)/$(@F)
# Standards-derived data (Unicode, MathML): shared by every branch, so it stays
# in the project root and is asked for by bare name.  Splitting these two was
# forced by the move: naming char_to_properties under $(data_dir) sent make
# looking in 2024/ for a file that is not branch-dependent and never moved.
# Two rules, not one with two target patterns: a pattern rule listing several
# targets tells make that ONE run produces them all, so building
# base_to_variants.json made it expect a base_to_variants.csv beside it and warn
# 'pattern recipe did not update peer target' when no such file appeared.  The
# .csv data here (mathml-ops, stretchy-accents) is hand-kept input, not something
# the .json recipes emit.
$(std_dir)/%.json:
	$(MAKE) -C $(project_dir) $(@F)
$(std_dir)/%.csv:
	$(MAKE) -C $(project_dir) $(@F)

# --- fontforge glyph exports / encodings ------------------------------------
%.pfb.enc.json: $$(call own,$$*) %.pfb.path
	@if [ -f $@ ]; then echo "File $@ exists."; \
	else fontforge -script $(script_dir)/pfb-enc-json.py $*.pfb; fi
%.enc.json: %.enc.path
	@if [ -f $@ ]; then echo "File $@ exists."; \
	else $(PYTHON) $(script_dir)/enc-save.py $*.enc; fi
%.enc.lua: %.enc.json $(script_dir)/enc_to_lua.py
	$(PYTHON) $(script_dir)/enc_to_lua.py $*
%-glyphs.json: $$(call own,$$*) %.pfb.path
	@if [ -f $@ ]; then echo "File $@ exists."; \
	else fontforge -script $(script_dir)/ff_glyph_images.py $*.pfb $*.pfb.path; fi
# Real bounding boxes.  The exported PNGs cannot serve: fontforge's export()
# without a pixel size does not render at a fixed em scale, so image heights
# keep the ORDER of the glyphs but not their proportions.
%.metrics.json: $$(call own,$$*) %.pfb.path
	fontforge -script $(script_dir)/glyph_metrics.py $*.pfb
%.htf.path: $(script_dir)/htf-path.py $(data_dir)/htf_db.json
	$(PYTHON) $(script_dir)/htf-path.py $*
%.path: $(script_dir)/kpsea-path.py
	$(PYTHON) $(script_dir)/kpsea-path.py $*

# --- per-font glyph rasters (dvipng), rendered once per font and reused ------
%.pos.tex: $$(call pair,$$*) $(script_dir)/render_font_tex.py
	$(PYTHON) $(script_dir)/render_font_tex.py $* > $@
%.pos.dvi: $$(call pair,$$*) %.pos.tex
	$(texdvi) $*.pos.tex
	@mkdir -p $*.pos
	$(dvipng) -T tight -D 150 -bg White -o $*.pos/%03d.png $*.pos.dvi
	@rm -f $*.pos.aux $*.pos.log

# --- variant comparison: map (auto verdicts to confirm) + review html --------
# ('plain' is read at the top of this file, next to the directory guard.)
# Guarded with 'own', not 'pair': the comparison belongs to the VARIANT font's
# work dir, where both fonts' rasters are rendered.  Asking for it in the plain
# sibling's dir is the mistake this catches -- there is no sibling of the
# sibling there, so it used to produce an empty map rather than an error.
# ../pairs is a prerequisite: it decides WHICH font this is compared against and
# on WHICH axis, so re-pairing a font invalidates its comparison as surely as a
# new raster does.  Without it, changing the pairing left `make <font>.cmp.map.json`
# saying 'up to date' about a map built for a different pair -- and the stale map
# still names the old plain font and the old axis inside, so nothing looks wrong.
%.cmp.map.json: $$(call own,$$*) %.pos.dvi $(if $(plain),$(plain).pos.dvi) \
                $(wildcard ../pairs) \
                $(script_dir)/cmp_classify.py $(data_dir)/htf_mfont_targets.json
	$(PYTHON) $(script_dir)/cmp_classify.py $*
%.cmp.html: $$(call own,$$*) %.cmp.map.json $(script_dir)/cmp_html.py
	$(PYTHON) $(script_dir)/cmp_html.py $*

# --- glyph property map: the record both projects derive from ---------------
# Filled in a step at a time, each step writing back into the same file: what
# the encoding and the htf table already say (init), what the assigned unicode
# implies (uni), what a font-pair raster comparison settles (cmp), and what
# only looking at the glyph can answer (edit).  From the filled record come the
# two outputs: <font>.gpm.map.json for htf_data.lua, <font>.gpm.lua for
# glyphs2u.  The .uni/.cmp steps are stamps because they modify the record in
# place rather than producing a file of their own.
# The skeleton needs the font's OWN encoding: the .enc vector psfonts.map names
# for it, or the pfb's built-in one when it names none.  gpm_encfile.py says
# which, resolved per target (second expansion), as cmp_sibling.py does for the
# comparison sibling.
# --merge, because make re-triggers this whenever htf_data.lua changes: a merge
# refreshes the htf values and the declaration while keeping every property
# already settled.  Use `gpm_init.py <font> --force` by hand to start over.
%.gpm.json: $$(call own,$$*) $$(shell $(PYTHON) $(script_dir)/gpm_encfile.py $$*) \
            $(data_dir)/htf_data.json $(script_dir)/gpm_init.py
	$(PYTHON) $(script_dir)/gpm_init.py $* --merge
# LUA_DIR defaults to the directory 2024/glyphs2u-dirs.json names for THIS font,
# so it no longer has to be remembered and spelled on the command line.  That
# was worth removing: the two examples in the top Makefile are both under
# public/, Computer Modern is filed in amsfonts/cm, and a wrong or forgotten
# LUA_DIR does not fail -- it seeds the whole family with nothing from glyphs2u
# and says so nowhere.  Setting LUA_DIR explicitly still wins.
LUA_DIR ?= $(shell $(PYTHON) $(script_dir)/glyphs2u_dirs.py --font $(this_font) \
                     --glyphs2u $(glyphs2u_dir) --map $(data_dir)/glyphs2u-dirs.json)

# LUA_DIR=<glyphs2u working dir> also seeds from that family's finished tables
# (base only, for glyphs the htf table is silent about); the builtin AGL list
# is the last fallback.  Neither settles any property the htf value does not.
%.gpm.uni: $$(call own,$$*) %.gpm.json $(std_dir)/char_to_properties.json $(script_dir)/gpm_unicode.py
	$(PYTHON) $(script_dir)/gpm_unicode.py $* $(if $(LUA),--lua $(LUA)) \
	  $(if $(LUA_DIR),--lua-dir $(LUA_DIR)) \
	  $(if $(wildcard $(builtin_glyph_map)),--builtin $(builtin_glyph_map))
	@touch $@
# The sibling carry runs FIRST where there is a pairing.  It is the prior -- what
# the paired font already settled, known before anything is looked at -- and the
# comparison is the measurement that answers the one axis they differ by.  Doing
# the inference afterwards reads as though it could revise the measurement, and it
# can: both write with a status outside CONFIRMED, so either may overwrite the
# other.  They stay apart only while both agree which axis differs, and a
# re-pairing broke that agreement in stix-mathsfit-bold -- the carry had run under
# 'differs=style', so it wrote weight, the very axis the new pairing gives to the
# comparison.  Ordering it here means the sequence no longer has to be remembered.
%.gpm.cmp: $$(call own,$$*) %.gpm.json %.cmp.map.json $(script_dir)/gpm_cmp.py \
           $(if $(plain),%.gpm.sibling)
	$(PYTHON) $(script_dir)/gpm_cmp.py $*
	@touch $@
# Everything the pair does NOT differ by, taken from the sibling's record: a
# bold cut does not become upright or sans-serif, so the axes settled by eye in
# the plain font are settled for this one too.  Matched by position, because the
# glyph NAMES diverge exactly where the characters do (u1D44D vs u1D468).  Run
# it after the sibling is settled and before/after .gpm.cmp indifferently -- cmp
# owns the axis this one skips, so they never touch the same value.
# The sibling's record is NOT a prerequisite: naming ../<plain>/<plain>.gpm.json
# here makes this dir try to BUILD another font's record, which is exactly what
# the directory guard exists to stop (it fires, with a stem of '../x/x').  A work
# dir builds its own font only; gpm_sibling.py checks the file and says which
# directory to settle first.
%.gpm.sibling: $$(call own,$$*) %.gpm.json $(script_dir)/gpm_sibling.py
	$(PYTHON) $(script_dir)/gpm_sibling.py $*
	@touch $@
# What the font says in its glyph names -- the upright cut of a slanted glyph
# (uni222B vs uni222B.up) that no codepoint distinguishes and no comparison
# against another font can settle.  Conventions are per family, so the rules
# live in $(std_dir)/gpm_name_rules.json; survey a new family with
# `gpm_names.py <font> --list` before adding it there.
%.gpm.names: $$(call own,$$*) %.gpm.json $(script_dir)/gpm_names.py $(std_dir)/gpm_name_rules.json
	$(PYTHON) $(script_dir)/gpm_names.py $* --data $(data_dir)
# The name a dotted glyph is PUBLISHED under, Distiller truncating at the first
# dot.  Built from the stem map plus the font's own suffix, so the map is a
# prerequisite -- naming a character there settles it for every family at once.
# The metrics come in because a cut's selector is measured, and the name has to
# be built on the same sequence the table will carry.
# NOT a prerequisite of %.gpm.lua, though the names show up there: what a glyph
# is published as is a decision, and `make rename-dry` is for reading the
# proposals before any of them is written.
%.gpm.rename: $$(call own,$$*) %.gpm.json %.metrics.json \
              $(std_dir)/rename-stems.json \
              $(script_dir)/gpm_rename.py $(script_dir)/gpm_ladder.py
	$(PYTHON) $(script_dir)/gpm_rename.py $* --data $(data_dir) \
	  $(if $(wildcard $(builtin_glyph_map)),--builtin $(builtin_glyph_map))
	@touch $@
	@touch $@
# The review page shows a picture of every glyph, so it pulls in the fontforge
# export (<font>/<glyphname>.png, keyed by name as the record is, and no TeX
# run needed).  Where a font also has .pos rasters from a comparison, those
# serve as the fallback.
# %.gpm.map.json is a prerequisite because the page's htf column is READ from it
# rather than derived again (see gpm_html.py).  Leaving it out let the page show
# a value from a map written before the record changed: bbmbx10's parenleft
# appeared with mathvariant="double-struck" long after its own variant=normal had
# settled the matter, because U+2985 IS the white parenthesis and the property is
# in the character.  A page that reports another file's contents has to depend on
# that file.
%.gpm.html: $$(call own,$$*) %.gpm.json %.gpm.map.json %-glyphs.json \
            $(std_dir)/base_to_variants.json \
            $(script_dir)/gpm_html.py
	$(PYTHON) $(script_dir)/gpm_html.py $*
# The size ladder of the stretchable glyphs, measured from the font metrics.
%.gpm.sizes: $$(call own,$$*) %.metrics.json $(std_dir)/stretchy-chars.json $(std_dir)/stretchy-extra.json $(script_dir)/gpm_sizes.py
	$(PYTHON) $(script_dir)/gpm_sizes.py $*
# Interactive: `make edit-<font>.gpm [AXIS=style] [REVIEW=1]`.  AXIS lists the
# glyphs with no value of their own for that axis (the sweep for confirming one
# property); SIZES=1 lists the glyphs with a pending size-cut proposal;
# TEXT_SIZE=<n> enlarges the list font and with it the glyph pictures;
# REVIEW lists every glyph.  Needs the k-NN index in glyphs2u_dir
# for the base-character proposals; works without it, minus the proposals.
# The metrics and the glyph images are prerequisites because the editor needs
# both: the size-cut panel reads the metrics, and the list draws a picture of
# every glyph.  Without them it opens with an empty list or with no pictures.
edit_opts = $(if $(AXIS),--axis $(AXIS)) $(if $(REVIEW),--review) \
            $(if $(POS),--pos $(POS)) \
            $(if $(SIZES),--sizes) $(if $(TEXT_SIZE),--text-size $(TEXT_SIZE)) \
            --glyphs2u $(glyphs2u_dir)
# The editor is a window, so there is nothing for make to wait for: it is started
# DETACHED and the shell prompt comes straight back.  setsid rather than a bare
# '&' so it survives closing the terminal, and its output goes to a log instead
# of interleaving with whatever you type next (fontforge is chatty at start-up).
# BG=0 keeps it in the foreground, which is what you want when it will not start
# and you need the traceback inline.
BG ?= 1
edit-%.gpm: $$(call own,$$*) %.gpm.json %.metrics.json %-glyphs.json $(script_dir)/gpm_edit.py
	@if [ "$(BG)" = "1" ]; then \
		setsid $(PYTHON) $(script_dir)/gpm_edit.py $* $(edit_opts) \
			>$*.gpm.edit.log 2>&1 & \
		echo "gpm_edit: $* started detached (log: $*.gpm.edit.log)"; \
		echo "  it holds the whole record in memory and rewrites it on every click,"; \
		echo "  so do not run another $*.gpm.* step while the window is open."; \
	else \
		$(PYTHON) $(script_dir)/gpm_edit.py $* $(edit_opts); \
	fi

# --- the two derivations -----------------------------------------------------
# htf: apply with `htf_mfont_apply.py --cmp <font>.gpm.map.json` (the map itself
# records whether dropping the ['font'] declaration came out more economic).
# CHARS=1 spells every value as the character itself rather than a hex entity
# below U+10000 -- for a table that composes wholly, where the mix reads worse
# and behaves identically (bbm).
#
# NODECL=1 declares NOTHING at font level and states every remainder per
# position.  Right for stix, wrong for bbm, and the difference is structural
# rather than a preference:
#
#   bbm is ONE char table and seven declarations.  The declarations are the only
#       thing distinguishing its cuts -- bbmbx IS bbm plus weight=bold -- so
#       dropping them gives every cut its own full table and destroys four
#       working aliases.
#   each stix font OWNS its chars, so a declaration distinguishes nothing.  And
#       on the axes that matter it cannot be escaped: MathML's only negative
#       token is 'normal', which means "no variant at all" rather than "not
#       this axis".  So a weight=bold declaration over stix-mathbb-bold cannot
#       be taken back on the 112 of its 222 glyphs the raster comparison found
#       NOT bold -- there is no token for "double-struck but not bold".
#
# 'style' looks like the exception, having italic and normal both stateable, and
# is not: for stix-mathrm the style=normal declaration is not an escape at all
# but the upright GUARD, and declaring it sets the driver's has_font, which
# SUPPRESSES the element-aware guard at vtxml-mathml.lua:1127.  158 of
# stix-mathrm's 256 positions are symbols, marks and digits that MathML never
# slants, so the blunt declaration replaces a correct guard on 98 letters with a
# pointless one on all 256.
%.gpm.map.json: $$(call own,$$*) %.gpm.json $(script_dir)/gpm_to_htf.py
	$(PYTHON) $(script_dir)/gpm_to_htf.py $* $(if $(CHARS),--chars) \
	  $(if $(NODECL),--drop-decl)
# <font>.htf.lua -- this font's entry as it would stand in htf_data.lua once the
# map is applied: the piece to copy in, exactly as <font>.gpm.lua is the piece
# copied into glyphs2u.  Cut from the rewritten whole rather than composed here,
# so what you paste is what the in-place rewrite would have written.
# The system htf_data.lua is READ, never touched: this target cannot alter it,
# and the copying stays a deliberate act.
# FULL=1 BUILDS the entry from the record plus what it inherits, rather than
# cutting the rewritten entry out of the lua.  It happens by itself where the cut
# would be incomplete -- an entry that is an ['alias'] has no ['chars'] to
# replace, so bbmss came out as eight lines saying nothing -- and FULL=1 asks for
# it anyway, which is how to see whether a font really differs from the entry it
# aliases.  An alias is a CONCLUSION: write the whole table, compare, and only if
# every value matches is the alias the right way to spell it.
# glyphs2u: deploy by copying into the font's glyphs2u working dir as <font>.lua.
# base_to_variants decides which base+properties have a codepoint of their own
# and which fall back to the base, so regenerating it changes this output.
# The metrics are a prerequisite, not an option: the size cuts are ranked from
# them, and without them every stretchable glyph would lose the variation
# selector that says WHICH cut it is -- a table that looks complete and is not.
%.gpm.lua: $$(call own,$$*) %.gpm.json %.metrics.json \
           $(std_dir)/base_to_variants.json $(std_dir)/stretchy-chars.json \
           $(std_dir)/stretchy-extra.json $(std_dir)/dtls-policy.json \
           $(script_dir)/gpm_to_lua.py $(script_dir)/gpm_ladder.py
	$(PYTHON) $(script_dir)/gpm_to_lua.py $* --out $@ --report $*.gpm.dropped \
	  $(if $(wildcard $(builtin_glyph_map)),--builtin $(builtin_glyph_map))

# Final cleanup of the glyph-investigation workflow (glyph dirs + all .json).
# <font>.gpm.json is the one file here that holds hand-made decisions, so it
# survives; remove it by hand to start the investigation over.
clean-fonts:
	@for j in *-glyphs.json; do [ -e "$$j" ] || continue; \
		dir=$${j%-glyphs.json}; \
		if [ -d "$$dir" ]; then echo "rm -rf $$dir"; rm -rf "$$dir"; fi; \
	done
	@for j in *.json; do [ -e "$$j" ] || continue; \
		case "$$j" in *.gpm.json) echo "keeping $$j";; *) rm -f "$$j";; esac; \
	done
	@# The write-lock sidecars gpm_edit leaves behind (see G.hold in gpm_io.py).
	@# A HELD one must survive: flock is on the inode, so deleting it while an
	@# editor has it open would let the next process create a fresh file and take
	@# a second lock on the same record -- turning the guard off precisely when it
	@# is doing its job.  `flock -n` answers whether anyone holds it.
	@for l in *.gpm.json.lock; do [ -e "$$l" ] || continue; \
		if flock -n "$$l" true 2>/dev/null; then rm -f "$$l"; echo "rm $$l"; \
		else echo "keeping $$l -- an editor is holding it right now"; fi; \
	done

.PRECIOUS: %.path %-glyphs.json %.enc.json %.pfb.enc.json %.pos.dvi %.cmp.map.json
# without this make deletes the metrics as an intermediate of %.gpm.sizes
.PRECIOUS: %.metrics.json
.PRECIOUS: %.gpm.json %.gpm.map.json
