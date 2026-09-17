# The TeX Live tree is located through kpathsea, so that the sources are
# taken from whichever installation kpsewhich belongs to.  Select another
# one with KPSEWHICH=/path/to/kpsewhich, or set TLROOT directly.
KPSEWHICH ?= kpsewhich
TLROOT    ?= $(shell $(KPSEWHICH) -var-value=TEXMFDIST)
# Sources are kept per release, so that regenerating against a newer tree can
# be compared with what an older one produced.
TEXLIVE   ?= $(notdir $(patsubst %/,%,$(dir $(TLROOT))))
SRCDIR     = sources/$(TEXLIVE)
SCRIPTS   = ../pyscripts
PYTHON    = python3

.PHONY: all load-sources parse diff-all build check-changes csv

all: parse diff-all

# Copy a file whose name may carry either the glyphtounicode- or the older
# glyphstounicode- prefix.  Arguments: subpath, stem (without prefix), dest.
define cp_g2u
	@if [ -f "$(TLROOT)/$(1)/glyphtounicode-$(2)" ]; then \
	    cp "$(TLROOT)/$(1)/glyphtounicode-$(2)" "$(3)"; \
	elif [ -f "$(TLROOT)/$(1)/glyphstounicode-$(2)" ]; then \
	    cp "$(TLROOT)/$(1)/glyphstounicode-$(2)" "$(3)"; \
	else \
	    echo "ERROR: glyphtounicode-$(2) not found in $(TLROOT)/$(1)"; exit 1; \
	fi
endef

load-sources:
	mkdir -p $(SRCDIR)
	cp "$(TLROOT)/fonts/map/glyphlist/glyphlist.txt"              "$(SRCDIR)/glyphlist.txt"
	cp "$(TLROOT)/tex/generic/pdftex/glyphtounicode.tex"          "$(SRCDIR)/glyphtounicode.tex"
	cp "$(TLROOT)/tex/luatex/luaotfload/luaotfload-glyphlist.lua" "$(SRCDIR)/luaotfload-glyphlist.lua"
	cp "$(TLROOT)/fonts/map/glyphlist/pdfglyphlist.txt"           "$(SRCDIR)/pdfglyphlist.txt"
	cp "$(TLROOT)/fonts/map/glyphlist/texglyphlist.txt"           "$(SRCDIR)/texglyphlist.txt"
	$(call cp_g2u,tex/latex/pdfx,ntx.tex,$(SRCDIR)/glyphtounicode-ntx.tex)
	$(call cp_g2u,tex/latex/pdfx,cmr.tex,$(SRCDIR)/glyphtounicode-cmr.tex)
	$(call cp_g2u,tex/latex/latex-lab,cmex.tex,$(SRCDIR)/glyphtounicode-cmex.tex)
	$(call cp_g2u,tex/csplain/fonts,cs.tex,$(SRCDIR)/glyphtounicode-cs.tex)

parse: $(SRCDIR)/glyphlist.txt
	$(PYTHON) $(SCRIPTS)/parse-glyphlists.py $(SRCDIR) .

diff-all: glyphlist_table-generated.lua
	$(PYTHON) $(SCRIPTS)/compare-glyphlists.py . glyphlist_table-generated.lua

build: agl.lua pdftex.lua luaotf.lua ntx.lua pdf.lua tex.lua cmr.lua cmex.lua cs.lua
	$(PYTHON) $(SCRIPTS)/build-glyphlist-table.py .

glyphlist_table-generated.lua: build

check-changes: glyphlist_table-generated.lua
	$(PYTHON) $(SCRIPTS)/compare-glyphlists.py --check-changes \
	    glyphlist_table-generated.lua glyphlist_table.lua

csv:
	$(PYTHON) $(SCRIPTS)/export-csv.py .
