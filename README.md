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

### adobe-private/

"Private" here means the Unicode Private Use Areas, not restricted material.
The directory holds the values to use instead of the PUA ones, for the AGL
names described above, and the vendor tables those PUA assignments come from:

- `adobe-private-lua.json` (in the project root) — the replacement map the
  scripts load (see `pyscripts/glyph_maps.py`).  This is the authoritative
  form.
- `adobe-private.lua` — the same data with the Unicode names spelled out, so
  that a change can be reviewed in terms of the characters it affects.  It is
  generated from the JSON by `make adobe-private/adobe-private.lua`, which
  keeps the two from drifting apart.
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
