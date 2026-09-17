# Makefile for managing TeX compilation tasks in fonttable directoy of the project.
# It is supposed to be called from font directories.

export TEXINPUTS := ./;$(working_dir);
# Standard TeX Live tools.  xdvipsk ships with TeX Live 2026 and later;
# override any of these to use a different build.
texdvi ?= dvilualatex
dvips  ?= xdvipsk
ps2pdf ?= ps2pdf
export project_dir := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))/..
export PYTHONPATH = ${CURDIR}
export script_dir = $(project_dir)/pyscripts
KPSEWHICH ?= kpsewhich
# Define the Python interpreter (good practice)
PYTHON = python3 $(script_dir)

%.dvi: %.tex
	$(texdvi) $<

vpath %.lua $(working_dir)

%.ps: %.dvi %.lua
	$(dvips) $*

%.pdf: %.ps %.lua
	$(ps2pdf) $*.ps $*.pdf

%-clean:
	rm $*.pdf $*.ps $*.dvi $*.tex $*.aux $*.log $*.fls $*.runtime.yaml $*.synctex.gz

clean:
	rm *.pdf *.ps *.dvi *.tex *.aux *.log *.fls *.runtime.yaml *.synctex.gz

# Files to compare pdf outputs to discover side effects of using lua tables
%-dvips.ps: %.dvi
	dvips -o $@ $*

%-dvips.pdf: %-dvips.ps
	$(ps2pdf) $< $@

%-diff.pdf: %-dvips.pdf %.pdf
	diff-pdf --output-diff=$@ -s $^

test:
	$(KPSEWHICH) -var-value TEXINPUTS

test-%:
	$(KPSEWHICH) -a $*.lua

.PRECIOUS: %.tex %.dvi %.ps

.PHONY: test clean
