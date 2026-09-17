Glyph-to-Unicode mapping investigation for the xdvipsk built-in table.

Goal: build and maintain glyphlist_table.lua -- the built-in glyph→Unicode
table in xdvipsk -- covering glyph names that appear across fonts without
needing per-font entries.

glyphlist_table.lua is tracked here from the xdvipsk source project.
Investigation in 2026 revealed it was incomplete (NTX glyph list absent).
363 entries were added; both sources of truth are now in sync.


SOURCES
-------

Nine glyph-to-Unicode maps exist in the TeX Live tree (counts from TL2026):

  Name    Entries  File in texmf-dist
  ------  -------  ------------------------------------------------------
  agl      4281    fonts/map/glyphlist/glyphlist.txt
  pdftex   5505    tex/generic/pdftex/glyphtounicode.tex
  luaotf   4291    tex/luatex/luaotfload/luaotfload-glyphlist.lua
  ntx       374    tex/latex/pdfx/glyphtounicode-ntx.tex
  pdf       373    fonts/map/glyphlist/pdfglyphlist.txt
  tex       324    fonts/map/glyphlist/texglyphlist.txt  (multi-map)
  cmr       277    tex/latex/pdfx/glyphtounicode-cmr.tex
  cmex      132    tex/latex/latex-lab/glyphtounicode-cmex.tex
  cs          4    tex/csplain/fonts/glyphtounicode-cs.tex

Note: before TL2026 the glyphtounicode-* files were named glyphstounicode-*
(with an extra 's').  The Makefile handles both naming conventions.


WORKFLOW
--------

All steps are driven from this directory by the Makefile.  The TeX Live tree
is located through kpathsea; select another installation with
KPSEWHICH=/path/to/kpsewhich, or set TLROOT directly.  Sources are kept per
release, in sources/<release>/:

  make load-sources                -- copy source files into sources/<release>/
  make parse                       -- parse sources → individual .lua tables
  make build                       -- apply unification algorithm →
                                        glyphlist_table-generated.lua
  make diff-all                    -- for each source compute
                                        <source>-not-main.lua (set difference
                                        source minus glyphlist_table-generated)
  make check-changes               -- compare generated table with authoritative
                                        glyphlist_table.lua; report discrepancies

The sources/ directory and the generated .lua tables are excluded from git
(they can be regenerated from any TeX Live installation).
glyphlist_table.lua is tracked and is the authoritative table.

Scripts are in ../pyscripts/:
  parse-glyphlists.py    -- parse the 9 source files into Lua tables
  build-glyphlist-table.py -- implement the unification algorithm
  compare-glyphlists.py  -- set-difference analysis and check-changes


UNIFICATION ALGORITHM
---------------------

The algorithm produces glyphlist_table-generated.lua from the parsed source
tables.  A name is added at most once (first occurrence wins).  Private Use
Area codepoints (U+E000--U+F8FF and supplementary PUA) are included only from
AGL; all other sources skip PUA values.

  Step 1 -- AGL (agl.lua): all 4281 entries, including PUA.
            Basis of the table; Acrobat Distiller always follows AGL for
            glyph names it recognises, so these values cannot be "corrected"
            at this level.  Xdvipsk renames glyphs when a different Unicode
            value is required.

  Step 2 -- pdftex (pdftex.lua): skip PUA; skip names prefixed with 'tfm:'.
            953 entries excluded (PUA, tfm:, or already covered by AGL).
            tfm:-prefixed names belong in individual font maps.
            Steps 2 and 3 could be interchanged; pdftex and luaotf disagree
            on some Hebraic/Arabic glyphs, but their intersection is a subset
            of AGL, so no information is lost either way.

  Step 3 -- luaotf (luaotf.lua): skip PUA.
            All non-PUA entries not already in the table are added.

  Step 4 -- ntx (ntx.lua): skip PUA.
            All 374 entries are now covered (ntx-not-main.lua is empty).
            Glyph names with dots require special treatment in xdvipsk:
            Acrobat Distiller truncates at the first dot before looking up
            the AGL, so unconditional renaming must be applied.
            NTX was absent from the original built-in table; 362 entries
            were added in 2026.

  Step 5 -- cs (cs.lua): skip PUA; applied before cmr.
            Only 4 entries.  cs maps 'suppress' to an acceptable Unicode value
            while cmr maps it into the PUA, so cs must precede cmr.

  Step 6 -- cmr (cmr.lua): skip PUA; skip names matching a<digits> or d<digits>.
            144 entries excluded.  The a<digits>/d<digits> names are
            font-specific and belong in individual font maps.
            cmr subsumes cmex, so cmex contributes nothing new.

  Step 7 -- tex (tex.lua): all remaining entries not yet covered.
            tex is a multi-valued map (duplicate keys intentional; the file is
            not valid Lua).  It has 285 unique glyph names; all but 6 are
            already covered by steps 1--6, so tex contributes exactly 6 new
            entries in practice.  These happen to be xdvipsk-internal sentinel
            codepoints (surrogate range U+D801--U+D80D used as markers).

            pdf is a subset of AGL, so it is ignored.
            The full tex and pdf difference files are kept for reference.

Result: 5046 entries.


MANUAL CORRECTIONS IN glyphlist_table.lua
------------------------------------------

The authoritative table differs from the generated one in 14 entries where
manual corrections were made (presumably when the table was originally built
for xdvipsk).  These are NOT bugs; they are intentional choices.

  Name               Generated                   Authoritative
  -----------------  --------------------------  ----------------------------
  Digamma            U+2D7CB (wrong: pdftex      U+03DC  GREEK LETTER DIGAMMA
                     source has a bad surrogate
                     pair D875+DFCB encoding a
                     CJK ideograph)
  FFsmall            U+0066, U+0066              U+FB00  LATIN SMALL LIGATURE FF
  FIsmall            U+0066, U+0069              U+FB01  LATIN SMALL LIGATURE FI
  FLsmall            U+0066, U+006C              U+FB02  LATIN SMALL LIGATURE FL
  FFIsmall           U+0066, U+0066, U+0069      U+FB03  LATIN SMALL LIGATURE FFI
  FFLsmall           U+0066, U+0066, U+006C      U+FB04  LATIN SMALL LIGATURE FFL
  longst             U+017F, U+0074              U+FB05  LATIN SMALL LIGATURE LONG S T
  st                 U+0073, U+0074              U+FB06  LATIN SMALL LIGATURE ST
  Germandbls         U+0053, U+0053 (SS)         U+1E9E  LATIN CAPITAL LETTER SHARP S
  Germandblssmall    U+0073, U+0073 (ss)         U+00DF  LATIN SMALL LETTER SHARP S
  SSsmall            U+0073, U+0073 (ss)         U+00DF  LATIN SMALL LETTER SHARP S
  anticlockwise      U+27F2                      U+21BA  ANTICLOCKWISE OPEN CIRCLE ARROW
  notprecedesoreql   U+2AAF, U+0338              U+22E0  DOES NOT PRECEDE OR EQUAL
  notfollowsoreql    U+2AB0, U+0338              U+22E1  DOES NOT SUCCEED OR EQUAL

The ligature corrections (FFsmall through st) prefer precomposed ligature
codepoints over decomposed sequences.  Germandbls/SSsmall prefer the
dedicated sharp-s codepoints.  The math symbol corrections prefer
precomposed characters over combining sequences.

Valentinas


TODO -- SIZE VARIANTS (text/display) FROM THE NTX LIST
------------------------------------------------------

Big operators, parentheses, radicals and accents come in several SIZES, and
Unicode spells the size with a variation selector after the character.  The
convention these names follow, as far as one was followed:

  U+FE00  the plain/binary cut (usually omitted; MathML documents a few uses)
  U+FE01  the n-ary operator at text size (inline formulas)
  U+FE02  the same at display size

with a twist: where Unicode already has a separate n-ary codepoint, the text
cut is often written with no selector at all and the DISPLAY cut then takes
U+FE01 rather than U+FE02.  No strict rule was formulated while this table was
compiled from the nine TeX Live sources, so the endings are not consistent.

Of the 19 name-stems ending in 'text'/'display', 14 follow the main pattern:

  summation     plain U+2211   text U+2211 FE01   display U+2211 FE02
  circleplus    plain U+2295   text U+2A01 FE01   display U+2A01 FE02

The other 5 do not, and ALL of them come from the ntx list alone (checked
against the parsed sources: the well-formed ones such as summationtext and
integraldisplay come from cmr/cmex).  NTX was added in 2026 without careful
checking -- see step 4 of the unification algorithm above:

  intersectionsq    text 2A05 FE01   display 2A05 FE01   display repeats text
  cupdot            text 2A03        display 2A03        no selector at all
  intersectsqmulti  text 2A05 FE00   display 2A05 FE00   both FE00; base
                                                         collides with
                                                         intersectionsq
  unionsqmulti      text 2A04 FE00   display 2A04 FE00   both FE00; base
                                                         collides with
                                                         unionmulti
  intersectmulti    plain 2A44 FE01  text 2A44 FE00      selectors inverted:
                    display 2A44 FE00                    the PLAIN entry has
                                                         FE01, text/display FE00

So in four of them the text and display cuts are indistinguishable through
this table, and in intersectmulti they are the wrong way round.  Not crucial
-- nothing downstream depends on telling those two cuts apart today -- but
they should be checked against the ntx source and corrected here, and a note
added to the manual-corrections table above once they are.

Selector use across the whole table, for reference:
  FE01 x66   FE02 x38   FE03 x23   FE04 x23   FE00 x6   FE05 x4   FE06 x4   FE07 x2

FE03..FE07 are the further sizes, used for parentheses, radicals and accents
rather than operators -- their per-font sequences live in the individual font
tables (stix-mathex, stix-mathit) rather than here.


The same applies to the ACCENTS, with the same split by source.  Rule: 'wide'
must always carry a selector, because the unsuffixed accent is the base and is
always present -- a 'wide' without one is an omission.  cmr/cmex follow it,
ntx does not:

  stem    plain     wide              wider                   widest
  ------  --------  ----------------  ----------------------  ----------------------
  hat     —         02C6 FE01         02C6 FE02               02C6 FE03      (cmr/cmex)
  tilde   U+02DC    02DC FE01         02DC FE02               02DC FE03      (cmr/cmex)
  arc     U+2312    0361              0361 FE01               0361 FE03      (ntx)
  oarc    —         0361 0350         0361 FE01 0350          0361 FE03 0350 (ntx)

So in arc and oarc the 'wide' cut has no selector at all, and 'widest' skips
FE02 for FE03 -- the ladder is shifted by one rung throughout.  oarc also shows
where the selector goes in a multi-character sequence: after the character it
applies to, not at the end (0361 FE01 0350).

ntx also switches base partway up the tilde ladder.  tildewide/wider/widest
(cmr/cmex) sit on 02DC SMALL TILDE, while tilde4, tilde5 and tilde6 (ntx) sit
on 0303 COMBINING TILDE -- the same accent, two spellings, in one family.  That
is the only such inconsistency left in the table: see
non-stretchy-variants.txt, which lists every sequence whose base MathML does
not call stretchy (117 of 166 are fine; the 3 to reconsider are exactly these
tilde4-6, and the 46 'unlisted' are backslash* and arc*, which MathML does not
cover in any spelling).  Regenerate it with

  python3 <htf-fonts>/pyscripts/nonstretchy_variants.py --out FILE <table.lua>

WHICH BASE: COMBINING, NOT MODIFIER LETTERS
--------------------------------------------

The accents in this table are the MODIFIER LETTERS (02C6, 02DC), which is what
MathML's operator dictionary lists as stretchy accents.  The per-font tables in
this project use the COMBINING marks for the same accents (stix-mathit's
uni0302.s1 = 0302 FE01, commented 'hatwide'), and that is the policy to follow:

  Combining marks are the right base for accents that get COMBINED, which is
  what these are for.  Where a precomposed glyph exists neither in the font nor
  in Unicode, only a combining sequence can express the result.  Accents rarely
  appear in a font for standalone single-glyph use; they are there to be put on
  something.  MathML names several candidate bases and does not make the choice
  clear, and stretchable accents tested under MathJax (in the xmlforge test
  project) did not all behave as the documentation says -- the result depends on
  the MathJax font set and engine, so the documentation is not decisive here.

tex4ht's htf tables follow the same policy, and split it by function: standalone
accent characters (the T1 text positions -- diaeresis, macron, acute, breve,
tilde, caron) use the spacing forms, 4793 uses across the htf tree, while
accents in combination use combining marks, 1408 uses -- most often 0338
COMBINING LONG SOLIDUS OVERLAY (411) for negated relations, which has no
precomposed form at all.  Every stretchable cut is combining: stix-mathit maps
.s1 .. .s5 of hat, tilde and caron to 0302, 0303 and 030C.

So the modifier letters here are inherited from the cmr/cmex source lists rather
than chosen.  mtpro2 has both inside one family (combining 030C for caron, 02DC
for tilde), which is a further symptom of the same thing.

NOTE: MathML follows the other policy.  Its operator dictionary lists the
SPACING accents as the stretchy ones -- 02C6, 02C7, 02C9, 02CD, 02DC, 00AF --
and of the combining marks only 0302 appears at all; 0300, 0301, 0303, 0304,
0306, 0307, 0308, 030A, 030C, 0332, 0338, 20D6 and 20D7 are absent.  We keep
the combining spelling regardless, for the reason above, so the per-font tables
(stix-mathit's uni0303.s1, uni030C.s1 ...) will not conform to the dictionary
on this point and are not meant to.  They are consistent in themselves: each
keeps the codepoint its glyph name states.  Nor would conforming help in
practice -- neither spelling of the caron is stretched by the MathJax setting
used in the xmlforge test project.


THESE SEQUENCES ARE NOT STANDARDIZED BY UNICODE
------------------------------------------------

Checked against Unicode's StandardizedVariants.txt (UCD, latest).  It defines
only SHAPE variants for mathematics, all with FE00 -- 24 sequences in the
2200-22FF and 2A00-2AFF ranges, of the form:

  2229 FE00; with serifs;                   # INTERSECTION
  2295 FE00; with white rim;                # CIRCLED PLUS
  2A3C FE00; tall variant with narrow foot; # INTERIOR PRODUCT

None of the bases used here appear in it at all: not 02C6/02C7/02C9/02DC/0302/
030C/0361 (the accents), not 23DE/23DF (curly brackets), not 221A, 222B, 2211,
220F or 2A00.  The file's higher selectors (FE02..FE06) belong to Sibe
punctuation and rotated Egyptian hieroglyphs, nothing mathematical.

So the whole size ladder -- FE01 for text, FE02 for display, FE03.. for the
further cuts -- is a TeX-world convention, not a Unicode one.  That explains
what is observed above: no strict rule was ever formulated because there was
none to follow, the ladders drift between the nine sources, mtpro2 continues a
ladder across sibling fonts when 15 selectors are not enough for one base
(mt2exf starts its tilde and caron at FE04), and no renderer is obliged to
honour any of it -- which is why MathJax handles these unreliably, accents
worst.

MathML does not fill the gap either.  Its operator dictionary marks WHICH
operators stretch (90 entries carry 'stretchy, accent'), never how far or in
what steps; stretching is a rendering behaviour driven by the stretchy
attribute, not by codepoints.  MathML 4 does use FE00/FE01 on mathematical
alphanumerics, but for Chancery versus Roundhand script -- a style
distinction, unrelated to size.
