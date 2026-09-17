# Glyphs2u — Unicode tables for Type 1 fonts used with xdvipsk

The goal of this project is to build so called Unicode tables for Type 1
(PostScript) fonts.  A table maps glyph names of a font to the Unicode value
(or list of values) that those glyphs represent, so that text set in such a
font can be extracted and searched in the resulting PDF.

The tables are consumed by [xdvipsk](https://github.com/vtex-soft/xdvipsk), an
extension of `dvips` developed at VTeX, which ships with TeX Live 2026 and
later.  `xdvipsk` adds a `GlyphNames2Unicode` dictionary to the fonts it
embeds; Ghostscript and Adobe Distiller use that dictionary to generate
`ToUnicode` CMaps.

## Why a glyph may need no entry

Not every glyph has to appear in a font table:

1. Many glyph names are already covered by the table built into `xdvipsk`
   itself.  That built-in table subsumes the
   [Adobe Glyph List](https://github.com/adobe-type-tools/agl-aglfn) and the
   glyph lists that existed in TeX Live up to 2025.  Where it maps a glyph
   correctly, the font table may omit the name.

2. A glyph name may itself denote its Unicode values, as described in the
   [Adobe Glyph List Specification](https://github.com/adobe-type-tools/agl-specification)
   — for example `uni20AC0308` (mapped to the list U+20AC, U+0308) or
   `u1040C` (mapped to U+1040C).

## Glyph names mapped into a Private Use Area

The Adobe Glyph List maps some names into a Unicode Private Use Area, and
those values are useless for extracting or searching text.  They cannot
simply be corrected in a table, because Adobe Acrobat Distiller *ignores* the
Unicode values given in the PostScript file whenever the glyph name is an AGL
name — it uses its own copy of the list instead.

The way out is renaming: if the glyph no longer carries an AGL name,
Distiller has nothing to override with, and the value supplied by `xdvipsk`
survives.  So such a glyph is renamed internally by `xdvipsk`, which is why
the intended non-PUA values are kept in a table of their own — see
[adobe-private/](#adobe-private) below.

## The three kinds of table

| Table | Where it lives | Read by xdvipsk |
| --- | --- | --- |
| built-in glyph list | compiled into the binary | always |
| `font_glyph_maps.lua` | this repository, deployed | always |
| per-font `<font>.lua` | any tree kpathsea can search | when present |

`font_glyph_maps.lua` is the **convoluted table**: the per-font tables of this
repository joined into one optimised, structured Lua table, with identical
tables collapsed to a single representative and the other font names recorded
as aliases.  It is committed here because it is the deliverable, and it is
rebuilt with `make font_glyph_maps.lua`.

Per-font tables are additional and optional.  They only have to be somewhere
`kpathsea` will find them — a system-wide tree, your personal tree, or even
the directory holding the manuscript being typeset.  That is why the
deployment directory is chosen by each working directory rather than fixed
here; see [config.py](#configpy) below.

## Requirements

- TeX Live (2026 or later for `xdvipsk`; the tables themselves are built
  against any tree that has the fonts)
- Python 3.10 or later
- [FontForge](https://fontforge.org/) with Python scripting, for extracting
  glyph names and images
- GNU Make

The k-NN glyph classifier (`make index`, `make edit-<font>.lua`) additionally
needs `scikit-learn`, `joblib`, `Pillow` and `tkinter`.

## Choosing a TeX Live installation

Everything is located through `kpathsea`: the tree used is whichever TeX Live
the `kpsewhich` on your `PATH` belongs to.  If you have several
installations, select one explicitly:

```sh
make <target> KPSEWHICH=/usr/local/texlive/2026/bin/x86_64-linux/kpsewhich
```

or export `KPSEWHICH` in the environment.  No absolute paths or release years
are recorded in the repository.

## Layout

Each directory containing Unicode tables — a *working directory* —
corresponds to one directory of Type 1 fonts.  The tree mirrors the vendor
directories of TeX Live, so `public/lm` holds the tables for the fonts in
`texmf-dist/fonts/type1/public/lm`, and `hoekwater/manfnt` those for
`type1/hoekwater/manfnt-font`.  The names are not always identical, which is
one reason each working directory carries a `config.py`.

Shared material in the project root:

| Path | Contents |
| --- | --- |
| `pyscripts/` | the Python scripts the Makefiles call |
| `common.Makefile` | all rules used inside working directories |
| `Makefile` | project-wide targets |
| `glyphlists/` | sources of the table built into xdvipsk |
| `unicode-data/` | Unicode Character Database files |
| `unicode-tables/` | Unicode values collected by class of letter or symbol |
| `adobe-private/` | non-PUA values for AGL names mapped into a PUA |
| `builtin-glyph-map.json` | the built-in table as a dictionary |
| `tex-specific.lua` | TeX conventions that override the built-in table |
| `fonttable/` | TeX sources for proofing a table as a PDF |

### glyphlists/

This is where the project started, and it is what the built-in table is made
from.  The nine glyph-to-Unicode maps that TeX Live distributes are copied in,
parsed, and combined by a documented unification algorithm into
`glyphlist_table-generated.lua`, which is then compared against the
authoritative `glyphlist_table.lua` tracked here.

Those source lists change between TeX Live releases, so the whole path from
the distribution's files to the built-in table is scripted and repeatable:

```sh
cd glyphlists
make load-sources    # copy the nine lists out of the TeX Live tree
make parse           # parse them into individual Lua tables
make build           # apply the unification algorithm
make check-changes   # compare with the authoritative glyphlist_table.lua
```

`make check-changes` is the one to watch after a TeX Live upgrade: it reports
names that appeared or disappeared, and values that changed.  A small set of
deliberate manual corrections is expected to differ.  See
[glyphlists/README.txt](glyphlists/README.txt) for the algorithm, the
per-source entry counts, and the reasoning behind each correction.

### unicode-tables/

Values collected from the Unicode Standard by class of letter or symbol —
Greek, Fraktur, blackboard bold, script, monospace, small capitals, superior
and inferior figures, big operators, number forms, small forms.  Within a
class the members mostly share their font properties, which is what makes
them worth having together: when a math font needs values for a whole
alphabet or a run of operators, the class is already worked out.

These files are **not complete Lua tables**.  They hold the entry lines only,
without the surrounding `return { ... }`, so they cannot be loaded as they
stand.  They are worked by hand: lines are copied out of them into a font's
table, with the glyph name — or whatever else needs it — changed to suit that
font.  Nothing in the build reads them.

```lua
  ['Alpha'] = { 0x0391 }, --Α Greek Capital Letter Alpha
  ['zero.inferior'] = { 0x2080, 'zerosubscript' },-- SUBSCRIPT ZERO
```

The second entry shows the two-element form used throughout the tables: the
value, then the name the glyph should be renamed to.  Renaming is what makes
a value stick when the original name would otherwise be resolved through the
Adobe Glyph List — see above.

Two `.txt` files remain, holding character, codepoint and name as they were
read out of the standard, before being reshaped into entry lines:

- `number-forms.txt` — vulgar fractions and other number forms, which have no
  `.lua` counterpart yet.
- `sup-sub-unicodes.txt` — superscripts and subscripts, arranged by digits,
  latin, symbols, greek, cyrillic, with notes.  `superior.lua` and
  `inferior.lua` cover most of it, but not the modifier letters and ordinal
  indicators, so it is kept as the fuller reference.

Where a `.txt` was fully absorbed into its `.lua` form it has been dropped.

#### A caveat on the superscript and subscript tables

These were collected before the point below was understood, and should be
read with it in mind.

Not everything that looks like a superscript or a subscript is one by
semantics.  Work on the `htf-fonts` project brought a closer reading of the
MathML documentation, which is explicit that such characters are not to be
used for mathematics: a superscript in a formula is a structural relation
between a base and an exponent, not a character that happens to sit high on
the line.  The precomposed characters are compatibility characters, present
so that older encodings round-trip.

`sup-sub-unicodes.txt` shows the clearest cases, and they are exactly the
codepoints `superior.lua` and `inferior.lua` leave out — the ordinal
indicators U+00AA and U+00BA, which are Spanish and Portuguese orthography
(`1ª`), and a set of modifier letters such as U+1DA2 modifier letter small
script g, which belong to phonetic notation.  Neither group means
exponentiation.

For this project's purpose the precomposed values are still the useful ones:
a glyph named `two.superior` is drawn as a raised two, and mapping it to
U+00B2 makes the extracted text read as a reader expects.  What they are not
is a guide to mathematical structure — that belongs to the markup, and is
worked out in `htf-fonts` rather than here.  `adobe-private.lua`'s
`asuperior` = U+00AA is the same trade-off in the same direction.

These are also where the exact-value convention is most visible: small
capitals are given as the small-capital letters (U+1D00 and neighbours), not
as the ordinary lowercase ones.

### adobe-private/

"Private" here means the Unicode Private Use Areas, not restricted material.
The directory holds the values to use instead of the PUA ones, for the AGL
names described above, and the vendor tables those PUA assignments come from:

- `adobe-private.lua` — the source: the curated table, carrying the Unicode
  names as comments and the exact values described under
  [How exact should a value be](#how-exact-should-a-value-be).
- `adobe-private-lua.json` (in the project root) — the same map as a
  dictionary, which is what the scripts load (see `pyscripts/glyph_maps.py`).
  It is generated by `make adobe-private-lua.json`, so it cannot fall behind
  the Lua table.
- `adobe-private.txt`, `apple-private.txt` — the vendors' own PUA assignment
  tables, for reference.
- `adobe-glyphlist.txt` — a copy of the Adobe Glyph List.

### config.py

`config.py` describes a working directory.  The variables are:

- `font_dir` — the directory holding the font files;
- `dest_dir` — where the Lua tables are deployed;
- `lua_tables` — the tables in this directory that should be deployed;
- `lua_tables_copy` — for a table usable by more than one font, the other font
  names it should be copied to at deployment time;
- `lua_tables_not_needed` — fonts that need no table, so that completeness
  checks can tell them from omissions;
- `lua_tables_tocheck` — fonts still to be investigated.

Paths come from the helpers in
[pyscripts/texmf_paths.py](pyscripts/texmf_paths.py) rather than being written
out, so a working directory is valid on any installation:

```python
from texmf_paths import texmf_font_dir, xdvipsk_cmap_dir
font_dir = texmf_font_dir("type1/public/lm")
dest_dir = xdvipsk_cmap_dir("type1/public/lm")
```

`xdvipsk_cmap_dir` defaults to your personal tree (`TEXMFHOME`), which is
writable without root.  Set `GLYPHS2U_DEPLOY_TREE` to deploy elsewhere, or
pass `tree=` explicitly.

Not every freely available font family is part of TeX Live.  Those are given
an explicit directory taken from the environment, so that the working
directory stays portable — `public/bbm` is the example here:

```python
from texmf_paths import font_dir_from_env, xdvipsk_cmap_dir
font_dir = font_dir_from_env("BBM_FONT_DIR")
```

## How exact should a value be

The tables were not all written with the same idea of what a glyph's Unicode
value is.  Early on, glyphs were given the obvious simple value; as the
Unicode Standard was read more closely, more exact values were used.  Small
capitals are the clearest case:

| Glyph | Simple | Exact |
| --- | --- | --- |
| `Asmall` | U+0061 `a` | U+1D00 `ᴀ` latin letter small capital a |
| `Aacutesmall` | U+00E1 `á` | U+1D00 U+0301 small capital a + combining acute |
| `asuperior` | U+0061 `a` | U+00AA `ª` feminine ordinal indicator |

The exact reading is preferred: it says what the glyph actually is, and a
combining sequence can express a character that has no precomposed form.
`adobe-private/adobe-private.lua` follows it throughout.

Older tables may still carry the simpler values, so the two conventions
coexist in the repository.  That is worth knowing before concluding that two
tables disagree by mistake.

## Adding a font

Find out whether a working directory already exists for the font's directory.
Each `config.py` records its `font_dir`, and

```sh
make print-<font>-dir
```

searches them for the directory holding `<font>.pfb`.

If there is none, create one, passing the directory where the fonts live:

```sh
make <dirname>/config.py font_path=/path/to/the/font/directory
```

This writes an initial `config.py` — with the font names found there listed in
`lua_tables_tocheck` — and a `Makefile` that includes `common.Makefile`.
Then, inside the new directory:

```sh
make fonts-glyphs-dict.json   # glyph names of every font, via FontForge
make <font>.lua               # initial table: glyphs the built-in table misses
make <font>.html              # glyph images beside the proposed values
make <font>.check             # descriptions, duplicates, completeness
make deploy                   # copy the tables to dest_dir
```

The initial table is built by simulating what `xdvipsk` would resolve on its
own: the font's glyph names minus everything the built-in table already maps
correctly, minus the names that denote their own values.  What is left is what
needs deciding.

`make <font>.check` combines the individual checks: it adds Unicode
descriptions as comments, reports glyph names that clash with the built-in
table, removes entries that are unneeded, and lists glyphs still without a
value.

For fonts whose glyph names are meaningless, the tables can be built by
recognising the glyph images instead.  `make sentinels-<font>` maps every
glyph to U+FFFD, and `make edit-<font>.lua` opens an editor offering the
nearest matches from a k-NN index built over the whole dataset.

After the per-font tables are settled, rebuild the convoluted table from the
project root:

```sh
make font_glyph_maps.lua
```

## The glyph image dataset

`make edit-<font>.lua` recognises a glyph by its shape, and what it compares
against is a dataset of labelled glyph images under `glyphs-dataset/`.  That
directory is generated and is not part of the repository — it runs to over a
gigabyte — so it has to be built before the editor is of any use.

There are two sources of labels, and they work in opposite directions:

- **Type 1 fonts**, rendered through each working directory's own tables: the
  per-font Lua table merged with the built-in one gives the codepoints, and
  every glyph with a known value is rasterised.  So the dataset is only as
  good as the tables already written — it was first built once a reasonable
  set of them existed.
- **OpenType and TrueType fonts**, which carry their Unicode values in their
  own `cmap`, so they need no table and can be ingested directly.

```sh
make dataset DIR=public/lm      # one working directory
make dataset-all                # every directory in config-list.json
make inspect-math-otf           # check a curated OTF list's conventions first
make dataset-math-otf           # then ingest it
make dataset-otf DIR=<tree>     # any other OTF/TTF tree
make clean-pua                  # drop Private Use Area labels (DRY_RUN=1 to preview)
make list-fonts                 # what is currently in there
make index                       # build glyphs-dataset/knn-index.joblib
```

`make index` has to be re-run after the dataset changes, `clean-pua`
included.

Since the dataset is built locally and never distributed, fonts whose tables
cannot be published here can still be used as training material on your own
machine.  It has to stay that way round, because the dataset contains the
tables: for a Type 1 font the glyph name is the image filename and the
codepoints are in `labels.json`, so any font's table can be read straight back
out of it — together with the built-in entries that applied, which are merged
in when the images are rendered.  A dataset built from fonts whose tables are
not public is therefore not publishable either.

The same property makes the dataset a usable copy of the tables, should one
ever be wanted.  It does not hold for the OpenType samples, which are keyed by
glyph index rather than name.

### Known state, for whenever it is next touched

Nothing here is urgent; the dataset works as it is.

- **STIX is not in it.** It was the last family worked on, and its tables
  arrived after the dataset was last rebuilt.
- **Ingesting OTF made the script slow.** Worth looking at before a full
  rebuild rather than during one.
- **Every size of a font is included separately**, which is largely
  redundant: the shapes of `cmr5` and `cmr17` differ by design but not by
  much, and carrying all of them inflates the dataset for little gain in
  recognition.  Thinning that out is the obvious first cleaning.

## Provenance of included data

Some files are reproduced from other sources and keep their own terms:

- `glyphlists/glyphlist.txt`, `glyphlists/aglfn.txt`,
  `adobe-private/adobe-glyphlist.txt` — the Adobe Glyph List and Adobe Glyph
  List For New Fonts, © 2002–2019 Adobe, BSD 3-clause.
- `adobe-private/adobe-private.txt` — Adobe's "Unicode Corporate Use Subarea"
  assignments, table version 1.2 (1998).
- `adobe-private/apple-private.txt` — the corresponding Apple assignments.
- `glyphlists/texglyphlist.txt`, `glyphlists/luaotfload-glyphlist.lua` and the
  `glyphtounicode-*.tex` files — collected from TeX Live.
- `unicode-data/` — files of the Unicode Character Database, © Unicode, Inc.,
  under the [Unicode License](https://www.unicode.org/license.txt).

Everything else is covered by [LICENSE](LICENSE).

The definitive reference is the standard itself rather than these data files:

- [The Unicode Standard, latest version](https://www.unicode.org/versions/latest/)
- [Code charts](https://www.unicode.org/charts/) — the per-block PDFs, which
  show the representative glyph for every character
- [Unicode Character Database](https://www.unicode.org/Public/UCD/latest/) —
  where the files in `unicode-data/` come from

The PDFs are not kept in the repository: they are large, and nothing in the
scripts reads them.  (Extracting the representative glyph images from the code
charts, to use as labels for the image classifier, has been considered but not
done.)

## Status and history

The first list of fonts needing tables was drawn up in 2024 by scanning
production files for the fonts they used, and covered amsfonts, Adobe pi and
dingbats, euler, latxfont, manfnt, marvosym, mathtime, mnsymbol, newtx,
niceframe, old-arrows, prodint, stmaryrd, txfonts, urw, wasy, xypic and
yhmath.  Larger families — lmodern, mlmodern, the computer modern sets, and
finally STIX — followed, and prompted the move from interactive Emacs sessions
to the Makefiles and Python scripts used now.

This repository holds the part of that work covering freely licensed fonts.
Tables for proprietary font families are not included.

Contributions are welcome, particularly tables for fonts not yet covered.
