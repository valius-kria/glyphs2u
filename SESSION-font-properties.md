# Session handoff — font properties in the xmlforge pipeline

Written 2026-08-31, at the end of a session rooted in
`~/gitlab/xmlforge/work/xmlforge/tests`. **Extended 2026-09-02**, from a session
rooted in `~/gitlab/htf-fonts`. Everything below was verified by running it, not
inferred. Read this before touching font-property handling again.

What the second session changed about the first:

- **§5 is done.** The overlay exists at `~/gitlab/xmlforge/vtex-overlay`, and
  `make overlay-status` is the report §5 asked for. Section rewritten.
- **§4's numbers describe `comp-chars`.** bbm's 162 surviving font tags now go
  to **0 from the htf side alone, on `main`** — see §7. §4 is still the right
  check to run; it is no longer the only way to pass it.
- **§6 was wrong about `no_font_tags`.** It is at vtex-dist `161271a0b`, not
  only in `saved/`.
- New: §7 the htf policy, §8 bbm finished, §9 what decides `<mn>` and what else
  Unicode could decide, §10 where everything is now.

---

## 1. Where the work lives — read this first

**The font-property work is on branch `comp-chars` in `~/gitlab/xmlforge/work`,
not on `main`.**

```
comp-chars (3 commits ahead of main)
  d899400  [transform] master-transform.xsl: sutvarkytas font savybių skaitymas
  4868bd7  [transform] unitomaster.py: fontų savybių komponavimas į raides
  e998590  [tests] changes of recompilled examples
```

`main` is currently checked out and carries commit
`266747d position="anchor"; images counter fix`, which is **unrelated** work. It
does not carry the font-property policy. Do not confuse the two.

To get back to the work: `git -C ~/gitlab/xmlforge/work switch comp-chars`.

There is also a `stash@{0}: WIP on uni-font` — older, unrelated to this session.

> **The "21 modified `.master`" this section used to report were not work.**
> The work repo's `.gitattributes` says `*.master text eol=crlf`, while
> `unitomaster` and `xmlpp` write LF, so a recompile marks every `.master`
> modified with **no content change** — verified on `test_tikz.master`, whose
> worktree, index, `HEAD` and cleaned-worktree hashes were all `3c9e7e4e`, 415
> bytes, no CR on either side. 20 of the 21 were exactly that. `git status`
> cannot tell them from real edits; `git diff` can, because it normalises.
>
> **The fix is local, and belongs on this side**: the colleagues are on Windows,
> check out CRLF and leave CRLF, so they have no such problem, and dropping
> `eol=crlf` would hand every Windows checkout LF files to quiet a cosmetic
> message on one machine. `make tests-refresh` in htf-fonts refreshes git's stat
> cache for exactly those paths — staging nothing, rewriting no file, the index
> being local. `make recompile` ends with it, and `tests-diff` / `tests-commit`
> run it before reporting. **The paths must be NAMED:**
> `git update-index --refresh` with no pathspec prints `needs update` for every
> entry and refreshes none of them.
>
> `make tests-diff` is the readable view of what a recompile changed —
> `.uni`/`.unipp`/`.master`/`.html` only, since every compile also rewrites 93
> binary `.dvi` in the same tree. `make tests-commit` stages those four
> extensions by naming each path explicitly, never `git add -A`, and is dry until
> `YES=1`.

---

## 2. What was wrong

Updating the stix tables in `htf_data.lua` made LuaTeX stop emitting precomposed
Unicode characters and start emitting **base letter + a compound `<mfont>`**:

```
before:  <mi><bold>&#x1D419;</bold></mi>                          (𝐙, ready-made)
after:   <mi><bold><mfont mathvariant="bold">Z</mfont></bold></mi>
```

Better markup — but it is the first time a *family* and a *weight* land on one
atom, and three places in the pipeline had never seen that. Font tags that
should have disappeared started surviving into `.master`.

Four independent defects, all fixed on `comp-chars`:

1. **`master-transform.xsl`, generic `mfont` template.** The fallback was
   `<xsl:element name="{$font}">`, so `bold-script` became a literal
   `<bold-script>` element — a name no axis table knows, so nothing downstream
   peeled it. Now decomposes the token into nested one-value-per-element markup
   via a new `mfont-nest` template.

2. **`master-transform.xsl`, `mi/italic/mfont`.** Written for the
   `mathvariant="normal"` case but matching *every* `mfont` under an `italic`,
   swallowing the variant with it. `\mathcal` came out as a bare `<mi>Z</mi>`
   with the script silently lost. Now restricted to `@mathvariant='normal'`.

3. **`master-transform.xsl`, the atom-level lifts.** They stamped
   `mathvariant="bold"` from the wrapper even though the inner `mfont` token
   *already said bold* — bold applied twice. These lifts were ultimately removed
   so the Python tiering is the single decision point.

4. **`unitomaster.py`, `_token()` — the one that kept the tags alive.** `_ORDER`
   was `family, weight, variant, style`, so bold script composed as
   `"script-bold"`. MathML's vocabulary is **not** built from one axis order: the
   bold cut of a family is weight-first (`bold-script`, `bold-fraktur`,
   `bold-sans-serif`) while the italic cut is family-first
   (`sans-serif-italic`, `sans-serif-bold-italic`). `"script-bold"` is in neither
   `base_to_variants.json` nor `_MATHML`, so those atoms fell past both tiers and
   kept their tags **by design**. `_ORDER` is now weight-first, with a one-entry
   `_SPELLING` table for the exception.

---

## 3. The policy that was settled (decided by Valentinas, not by me)

MathJax renders the `.master` math, so a `mathvariant` value is fine **provided
it conforms to MathML**. The agreed order is **character first**:

| case | output | why |
|---|---|---|
| `\mathit{Z}` | `<mi>Z</mi>` | italic **is** the single-`<mi>` default — needs nothing, stays greppable ASCII |
| `\mathit{Ziiii}` | `<mi>𝑍𝑖𝑖𝑖𝑖</mi>` | a **run** defaults to *normal*, so it genuinely needs composed characters |
| `\mathrm{Z}` | `<mi mathvariant="normal">Z</mi>` | uprightness — the only way to express it |
| `\mathbb{Z}` | `<mi mathvariant="normal">ℤ</mi>` | composed, guarded against the italic default |
| `\mathcal`, `\mathscr`, `\mathbfscr` | `<mi>𝒵</mi>`, `<mi>𝓩</mi>` | script/calligraphic glyphs are already slanted — no guard |
| `\mathbfbb{Z}` | `<mi mathvariant="bold">ℤ</mi>` | double-struck is in ℤ; the bold has nowhere else, so it goes to the attribute |

Four rules behind that table, all in `unitomaster.py`:

- **`_guard_upright`** — MathML gives a **single-character** `<mi>` a default
  `mathvariant` of *italic*; a multi-character one defaults to *normal*. A
  composed character already carries its whole font, so the default would slant
  it a second time. `mathvariant="normal"` goes on exactly the atoms exposed to
  that default: single-character `<mi>`, after merging, never `<mo>`/`<mn>`
  (whose default is normal already).
  **This is the explanation for the MathJax symptom that started the whole
  investigation** — small double-struck rendering three ways (slanted regular,
  upright regular, upright bold) while capitals rendered one way. It was never a
  font problem: it is the single-`<mi>` italic default, and capitals ℤ ℝ ℂ ℕ ℚ
  come from the Letterlike block while 𝕜-style letters come from Mathematical
  Alphanumerics.

- **`_SLANTED` / `_is_slanted`** — variants whose glyphs are slanted by design
  (`italic`, `bold-italic`, `sans-serif-italic`, `sans-serif-bold-italic`,
  `script`, `bold-script`) skip the guard. Forcing `normal` there would fight the
  face. (Some fonts do carry upright script cuts — that is a font choice, not
  something the markup should force.)

- **`_shed_default_italic`** — a lone italic letter is handed back to the `<mi>`
  default as plain ASCII. Runs are explicitly excluded: shedding there would set
  the whole word upright. This is why it runs **after** the merge.

- **Residue relocation** — what the character cannot carry (axes given up by
  `_degrade`, plus a value that lost its axis to a `_peel` clash) goes into
  `mathvariant` instead of being dropped or left as a tag. By construction it
  never duplicates what the character already encodes.

Knob: `FONT_TO_CHAR=0` inverts to attribute-first; with `_token` fixed that now
yields a conforming `mathvariant` for **every** stix case, tag-free. Verified.
`FONT_DROP_TAGS` still exists but no longer has anything to drop.

---

## 4. Verified end state (on `comp-chars`)

Whole corpus, 93 `.master`. These numbers were measured with the four
`comp-chars` fixes of §2 in place; on `main` without them, bbm still shows its
162 tags. §7 reaches the same 0 from the other end, by changing what the htf
table emits, and the two are independent — the recipe below is what tells you
which you have.

- **0** font tags inside `<math>` (was 162 in bbm + 6 in stix)
- **0** non-conforming `mathvariant` values
- **0** cases of `mathvariant` repeating what its own character encodes
- **0** properties dropped — no `.fonts.dropped` written anywhere
- `mathvariant="italic"` fell from 166 → 20 (survivors are ℓ ♯ ♭ ♮ ℘ Ϝ and
  combining marks, which have no italic codepoint — correct)

All 14 stix-using tests were recompiled from `.tex` through the real toolchain
(`make <abs-path>.recompile` from `~/gitlab/htf-fonts`). Zero failures, and
**every `.uni` reproduced byte-for-byte** — so the stix table update is fully
propagated and deterministic.

Coverage gap worth knowing: the dgbook tests reach STIX through `unicode-math`
and `STIXTwoMath-Regular.otf`, a different path that never touches the htf
tables. `links/link_els` loads the full stix math TFM family but its content only
uses italic and bold. **The exotic variants are exercised by `packages/stix` and
nothing else** — `stix.tex` is currently the only guard on them.

Re-verification recipe (run from the tests `files/` dir):

```python
import glob, collections, json
from lxml import etree
V={'bold','italic','sans-serif','monospace','small-caps','script','fraktur','double-struck','sc'}
OK={'normal','bold','italic','bold-italic','double-struck','bold-fraktur','script',
    'bold-script','fraktur','sans-serif','bold-sans-serif','sans-serif-italic',
    'sans-serif-bold-italic','monospace','small-caps','bold-small-caps'}
b2v=json.load(open('/home/valius/gitlab/htf-fonts/base_to_variants.json'))
enc={}
for base,vs in b2v.items():
    for tok,ch in vs.items(): enc.setdefault(ch,set()).add(tok)
tags=collections.Counter(); bad=set(); dup=set()
for f in sorted(glob.glob('**/*.master', recursive=True)):
    for e in etree.parse(f).iter():
        if not isinstance(e.tag,str): continue
        if e.tag in V and any(a.tag=='math' for a in e.iterancestors()): tags[(f,e.tag)]+=1
        mv=e.get('mathvariant')
        if mv:
            if mv not in OK: bad.add((f,mv))
            if mv!='normal':
                for c in (e.text or '').strip():
                    if mv in enc.get(c,()): dup.add((f,e.tag,mv,c))
print(dict(tags) or "no tags", sorted(bad) or "all conform", sorted(dup) or "no duplication")
```

---

## 5. Overriding colleagues' repos — DONE

Four colleague-owned git repos are in the workflow:
`/usr/local/texlive/2024` (outer — holds `texmf-config` and `bin`),
`2024/texmf-dist`, `2024/texmf-vtex`, and `vtex-dist`. Only `htf-fonts` and
`glyphs2u` are ours.

**The overlay is `~/gitlab/xmlforge/vtex-overlay`** — its own git repo, beside
the `work` checkout, **local only and staying that way** (no remote, decided
2026-09-01). It is the staging area and the local history; a colleague never
looks at it. What reaches them is `make deploy-<file>`, which copies into their
repo's **working tree** and stops — nothing staged, committed or pushed, and
`git checkout` there undoes it. The team is on Windows and this checkout is on
Linux with no shared filesystem, so pointing their `TEXMFAUXTREES` here was
never the route.

```
make overlay          seed what is missing, build what is generated
make overlay-status   per file: still different from upstream?  has it moved?
make overlay-env      the exports, with the comma
make deploy[-<file>]  overlay -> their working tree
make refresh[-<file>] their version -> overlay, discarding ours
```

Both directions refuse rather than warn. Deploy refuses when upstream has moved
since the copy was taken, and when they have an **uncommitted** edit to that
path — copying over that destroys work no repository holds. Refresh refuses
unless the overlay's copy is committed here first, which is why the overlay is a
git repo and not a directory of files. The report and both guards share one
definition of a file's state (`overlay_common.state`), so a guard cannot
disagree with what `overlay-status` just printed.

`htf_data.lua` and `htf_data.luc` are declared as each other's **`pair`** in
`overlay-files.json`: naming either moves both, and deploy refuses the whole set
if the `.luc` is missing or older than its `.lua`. Checking that per file was not
enough — an unrebuilt `.luc` is still byte-identical to upstream, so row by row
it reads *identical*, gets skipped, and only the `.lua` goes over.

`TEXMFAUXTREES` is the mechanism. From `texmf-vtex/web2c/texmf.cnf`:

```
TEXMFAUXTREES = {}
TEXMF = {$TEXMFAUXTREES!!$TEXMFSYSVAR,!!$TEXMFSYSCONFIG,!!$TEXMFLOCAL,!!$TEXMFROOT/texmf-var,!!$TEXMFDIST}
```

It splices in at the **front** of `TEXMF`, ahead of all four repos, and is the
only entry without `!!` — so it is **scanned live from disk** while every shared
tree is ls-R-only. That enforces "never the stale variant" through the path
setup rather than through discipline.

Proven by experiment:

- overriding `htf_data.lua` → resolves to the overlay ✔
- a brand-new file with **no `mktexlsr`** → found immediately ✔
- `.tfm` and `psfonts.map` → override cleanly ✔
- survives the `texbin`/`texrun` wrappers (they do not scrub the env) ✔

```sh
export TEXMFAUXTREES="$HOME/gitlab/xmlforge/vtex-overlay,"   # trailing comma REQUIRED
```

`mk/config.mk` exports it, and `TEXMFDOTDIR` as well, so the overlay answers even
in a shell where the first was never set.

Unsetting it gives an instant A/B against the pristine distribution.

### The trap that would silently defeat it

`luarealchar.lua:72` — `require_luc` probes `.luc` **before** `.lua`:

```lua
-- try .luc first
local luc_file = kpse.find_file(name .. ".luc", "lua")
```

Confirmed consequence: with only `htf_data.lua` in the overlay, the lookup still
returns **vtex-dist's stale `.luc`**. The edit is ignored, with no error.

> **Rule: the overlay must carry the `.luc`, not just the `.lua`.**

Done: the rule is `$(htf_path)/htf_data.luc` in `mk/overlay.mk`, named for the
overlay rather than left as a pattern, and `%.uni` depends on the `.luc` and not
on the `.lua`. **Not every overlay file has this problem** —
`xmlforge/vtxml-mathml.lua` is loaded by plain `require` from `vtxml.lua:459`, so
it has no `.luc` to keep in step. The `pair` declaration says which files do.

### Two things the overlay does *not* cover

- **`texmf.cnf`** — `texbin/posix/texdist:23` force-sets `TEXMFCNF`, overwriting
  anything exported, so no env var reaches it. But `texmf-config/web2c/texmf.cnf`
  is already searched first and already serves as the local-override slot
  (earlier definitions win, so it need only hold the changed lines).
- **`HTF_DIRS`** — an explicit absolute-path list in the top Makefile that never
  goes through kpathsea, so an overlay `.htf` is invisible to `htf_data.json`
  generation unless the overlay is prepended by hand.

### Why not branches in their repos

Beyond the merge pain: those repos **are the live installed distribution**.
Switching a branch in `/usr/local/texlive/2024/texmf-vtex` changes what every TeX
run on the machine sees. A worktree fixes that, but its path is not searched
unless added to `TEXMFAUXTREES` — which is the overlay again. So it is one
mechanism at two sizes: sparse overlay for a few files, full worktree named in
`TEXMFAUXTREES` when a change wants real history. To share, colleagues point
`TEXMFAUXTREES` at a clone — nothing to merge.

### Local changes still sitting in their repos

Deliberately left alone (asked 2026-09-01: "Do not touch the texmf.cnf and
binaries in TeX, they related to other project"):

- `2024/texmf-vtex/web2c/texmf.cnf` — `error_line=254`, `half_error_line=238`,
  `max_print_line=3000` (personal debugging preference)
- `2024/texmf-config/web2c/texmf.cnf` — modified
- untracked `2024/bin/x86_64-linux/xdvipsk-local`, `xdvipsk-test`
- a leftover Emacs ediff temp file in `texmf-config/web2c/`

### The weakness designed against — solved

Overlay files are copies, and upstream moves underneath them. `MANIFEST.json` in
the overlay records, per file, what upstream looked like when that file was last
seeded or written; `make overlay-status` compares and reports **not seeded /
identical / yours / rebase / undeclared**. Without that snapshot "this is my
change" cannot be told from "upstream moved underneath it".

Seeding has **no prerequisite** on the distribution copy, deliberately: with one,
make would re-copy whenever that copy was newer and silently discard the
overlay's changes.

---

## 6. Open threads

- **`_peel` axis clash (bbm)** — resolved from the htf side rather than in
  `unitomaster`. bbm nested `double-struck` outside `sans-serif` and the family
  axis was read twice; now the character carries double-struck and each cut's
  declaration carries only its own axis, so nothing states the family twice.
  §7–§8.
- **stix2 is the next family** — 15 entries, the same size as stix v1, and
  `2024/htf_mfont_targets.json` names all 81 fonts still holding precomposed
  characters. Lean on glyphs2u: both derivations compose through the same
  `G.uni_codes`, so `make gpm-seed FAMILY=stix2 LUA_DIR=$(glyphs2u_dir)/public/stix2`
  starts from finished tables.
- **`no_font_tags`** — the earlier note here was wrong. It is at vtex-dist
  **`161271a0b`** ("conservative extension to manage `<font>` tags") and was
  removed again by `0f948418e` ("som options removed"). `saved/luarealstring.lua`
  is that state plus the `debug_font` relocation, which `0f948418e` *did* commit.
  Nothing in `saved/` is unrecoverable from git.
- **Untracked in `packages/stix/`** — `stix1.master` / `stix1.html` were
  generated by a corpus-wide pass for the untracked `stix1.tex`. Gone from disk
  as of 2026-09-02; only `stix1.tex` remains.
- **22 `tfm/**/*.gpm.json` uncommitted** in htf-fonts — `htf_value` catching up
  with the installed table under `gpm_init --merge`. Ten predate this work, so
  earlier hand edits and regeneration churn are mixed; that split is not mine to
  make.

---

## 7. The htf policy — character first (2026-09-02)

The two halves of the pipeline were undoing each other. `gpm_to_htf` reduced
every precomposed variant character to its **base** and put the whole variant in
the markup, so double-struck A left the table as
`<mfont mathvariant="double-struck">A</mfont>`; `unitomaster` then composed it
back into U+1D538. The htf now carries the composed character and states in a
`mathvariant` only what no character can hold — the split §3 already settled, so
both halves agree.

Composing goes through `G.uni_codes`, the call the **glyphs2u** side makes, so
the two derivations cannot disagree about which character holds which properties.
The difference is only that the remainder becomes a `mathvariant` here and is
dropped there.

Over the 24 recorded fonts: **3976 composed, 1308 wrapped**, against 2443 wrapped
before. Ten fonts come out with no `<mfont>` at all. `--policy attr` keeps the
old behaviour for a per-font diff.

### Four things that had to be right, and were wrong first

- **Deduplication.** An axis any character carries is excluded from the
  `['font']` declaration, because luarealchar merges the declaration onto the
  atom whatever the value is (`luarealchar.lua:636-644`). The first version
  filtered the candidates drawn from the record but *not* the "keep what the
  table says today" candidate, which then won the least-churn tie: bbm came out
  with 47 composed double-struck characters **and** a `variant=double-struck`
  declaration, reported in the same breath as "characters carry variant".
- **An asserted `style=normal` must survive that exclusion.** `normal` is the
  *absence* of a property, no character can carry it, and MathML slants a
  single-character `<mi>` by default — so dropping it left every one of bbm's 58
  characters slanted a second time, at **zero wraps**, which looked optimal and
  was wrong.
- **`KEEP_PRIORITY` now puts `variant` before `family`.** `double-struck
  sans-serif` has no character, so one axis goes; surrendering double-struck
  yielded a sans-serif character wearing `mathvariant="double-struck"` —
  backwards for a family whose sans and mono cuts are *shapes within* it. The old
  order was an artefact of how the tuple was typed. Only four fonts hold both a
  non-normal family and a non-normal variant, all in bbm; **no stix font can tell
  the difference.**
- **Values above U+FFFF are raw UTF-8, entities below.**
  `luarealstring.lua:679` converts with
  `string.gsub(hchar, "^&#x(....);$", …)` — exactly four characters — so
  `&#x2124;` becomes U+2124 and takes the codepoint path while `&#x1D538;` stays
  a nine-character string and falls to the branch meant for a *sequence*. Every
  Mathematical Alphanumeric is five hex digits. Checked with `texlua` both ways.
  `CHARS=1` spells every value as itself, for a table that composes wholly.

### Aliases are a conclusion

`make htf-entry` writes the entry as it should stand: an `['alias']` where the
characters are identical to the entry it would alias, a full `['chars']` table
where they are not. Two things this got wrong before it was right:

- The comparison must be against the owner's **new** values, from its map in the
  sibling work dir. Comparing with the characters the table holds *today* calls
  every cut different, those being the old uncomposed letters.
- It must compare by **meaning**, not by spelling. A raw string compare called 11
  of bbm's 58 values different from bbmbx's when the only difference was
  `&#x2124;` against the character itself — and gave bbmbx a 243-line duplicate
  table where nine lines say it. `G.value_key` reduces a value to
  *(mathvariant token, characters)*.

Blocks are named after the htf **target**, from `2024/tfm-htf-map.json`, not
after the tfm: an htf name can be a prefix of the font's (`bbm10` is served by
`bbm`) or a name from elsewhere reached by an alias (`lm-ec` serves
`AccanthisADFStdNo3-Bold-lf-t1`).

---

## 8. bbm — finished, and what it cost to see it

**Eight entries over 39 tfms and ONE char table.** `bbm` owns 58 characters; the
other seven are aliases carrying one axis each. That shape is what `user_htf.lua`
already said — what changed is only that the characters now carry double-struck
and no declaration repeats it.

| entry | form | declaration |
|---|---|---|
| `bbm` | 58 composed chars | `style=normal` |
| `bbmbx` | alias | `weight=bold, style=normal` |
| `bbmsl` | alias | `style=oblique` |
| `bbmss` | alias | `family=sans-serif` |
| `bbmssb` | alias | `family=sans-serif, weight=bold` |
| `bbmssi` | alias | `family=sans-serif, style=oblique` |
| `bbmtt` | alias | `family=monospace` |
| `bbmsltt` | alias | `family=monospace, style=oblique` (hand-corrected; no
  record, `bbmsltt10.tfm` is not installed though psfonts.map names a pfb) |

Deployed to the overlay and recompiled (`packages/bbm`, the `.fls` confirming the
overlay's `user_htf.lua` was the file read):

- `.uni` 32209 → 26112 bytes; **`<double-struck>` 270 → 0**, while
  `<sans-serif>` 116, `<bold>` 116 and `<monospace>` 58 stay, being what no
  character can carry
- `.master` 60198 → 45594 bytes; **font tags inside `<math>` 162 → 0**, composed
  characters 0 → 235, `mathvariant="double-struck"` 270 → 0
- `unitomaster`: 0 into characters, 58 into mathvariant, **0 left as tags**, no
  `.fonts.dropped`
- §4's recipe passes: no font tags in `<math>`, every `mathvariant` conforming,
  none repeating what its own character encodes

The four char-level `['font'] = { ['variant'] = false }` are gone with the
declaration they cancelled — U+2985/U+2986/U+301A/U+301B **are** the white
brackets. **Sequencing matters:** those cancellations were read from whichever
entry supplies the chars, so bbm's four cancelled the declaration for all eight
cuts. They are safe to remove only together with `variant` coming off all eight.

### bbmssbx10 needs looking at, not trusting

Its pfb carries a **256-slot text encoding** where every other cut has bbm's 58.
Of those, 189 slots draw nothing and nine more — the circumflex composites — draw
the base letter's outline **displaced left of the origin**, two thirds of it
outside the advance width (`Acircumflex` x0=−539 against an advance of 881;
`Icircumflex` ends at x1=−187, wholly left of the origin). `bbmssbx10.exclude` is
seeded with those nine, **commented out** — uncommenting is the decision. Only
the 58 slots with htf values feed the htf side, so its block is sound either way.

### Two tests, because neither works alone

- `isWorthOutputting()` accepted all 256: 189 hold **one degenerate contour**,
  enough for that method and not enough to draw.
- A zero-area bounding box rejects those — and also rejected **`space`**, which
  draws nothing *by design*.

So: ink settles it where there is ink, and where there is none the question is
what the glyph **stands for** — Unicode `Zs`/`Zl`/`Zp`/`Cf`/`Cc` are invisible by
definition, which keeps `space` and `sfthyphen` and drops `Aacute`, whose width
(881, A's own) cannot tell them apart. Shared in `pyscripts/ff_glyph.py` so the
three fontforge scripts cannot diverge. `glyph_metrics` now records `x0`/`x1`; it
stored `y0`/`y1` and the width, so a glyph could be the right size in the wrong
place with no number showing it, which is why fontforge's GUI saw what the
pipeline could not.

---

## 9. What decides `<mn>`, and what else Unicode could decide

Composing a property into the character took its **numberhood** with it. bbm's
ten digits went from `<mn>` to `<mi>`.

The decision is **not in luarealchar** — its only class table is
`htf_char_types = {["4"] = {["variant"] = "small-caps"}}`, tex4ht's numbered
class, and only class 4 is handled. It is in
**`texmf-vtex/tex/luatex/xmlforge/vtxml-mathml.lua`**: `mml_noad` (line ~551)
maps the TeX noad class (`ord→mi`, `bin/rel/open/close/punct→mo`), and one branch
picked `<mn>` with

```lua
elseif #chars == 1 and tonumber(chars[1].char) ~= nil then
```

`tonumber` knows ASCII `0`–`9`. U+1D7D9 MATHEMATICAL DOUBLE-STRUCK DIGIT ONE is a
digit to **Unicode** and not to Lua. Fixed in the overlay to test general
category **`Nd`** against `luarealstring.unidata` — the table the run already
loads, 17720 entries, `category` lowercased. Every Mathematical Alphanumeric
digit block (U+1D7CE..U+1D7FF) is uniformly `Nd`; the letters are `Lu`.

> **Why the first attempt changed nothing.** `node_char_to_table` is called with
> `char_to_entity='not_ascii'`, which converts to an entity unless the codepoint
> is in **40..122** (`luarealstring.lua:749-755`). ASCII digits 48..57 fall inside
> that range and arrive as a **number** — the real reason `tonumber` ever worked
> — while U+1D7D9 = 120793 arrives as the **string `&#120793;`**. A helper
> testing only for a codepoint or a one-character string returned false for every
> composed digit.

### Class data already loaded and never read

`char-def-with-ccc.lua` carries more than `category`. Counted over its 17720
entries, and **referenced nowhere** in either xmlforge or luarealchar (only
`combclass` is used, twice, for accent combining):

| field | entries | what it would answer |
|---|---|---|
| `mathclass` | 228 | `variable` 119, `relation` 38, `binary` 28, `limop` 11, `number` 10, `close` 5, `punctuation` 5, `nothing` 4, `open` 3, `ord` 3, `accent` 2 |
| `mirror` | 348 | the paired/mirrored delimiters |
| `mathname` | 150 | the TeX control-sequence name |
| `mathstretch` | 4 | stretch data |

And categories carrying class: **`sm`** 914 (operator, not identifier), **`ps`**
66 / **`pe`** 65 (open/close — 131 delimiters against `mathclass`'s 8), `pd` 18.

`mathclass` would **not** have fixed the digits: only 10 characters carry
`number`, and they are ASCII. The two are complementary — `mathclass` is
semantically richer over 228 characters, `category` thinner but covers all 17720.
Anything meant to survive character substitution needs the category.

### The additive enlargement, and what it does not settle

`unicode_math_tag` in the overlay's copy reads `mathclass` first, `category`
second, and is consulted **only where nothing else spoke** — so the noad class
keeps its precedence. `\mathopen`, `\mathbin` and the rest are how an author
states intent, and TeX lets the class be changed, so an author's statement
outranks a property of the character (settled by Valentinas).

Two placements, because the first was dead code: a final `else` on the chain is
unreachable for a math char under a noad (`h.id == NOAD` matches before it). The
reachable gap is *inside* that branch — `math_atom_gruops` yields `inner` and the
three `op*` classes (**the big operators**) and `mml_noad` has an entry for
**none** of them, so `mml_attributes` returns false and the atom keeps `mi`.
Where `n.fam == 3` catches them earlier this never showed; where it does not, a
`\sum` comes out an identifier.

`packages/bbm`, `amsmath_delimiters`, `amsmath_integrals_sums` and
`ltx_fontmath` are **byte-identical** to a baseline recompiled without it. That
shows the change is harmless, **not that it works**: in those tests `n.fam == 3`
and the noad class answer everything. It is insurance for the substitution case
— which is what composing properties into characters does.

**Left unsettled, and not ours:** whether ConTeXt's `mathclass` or MathML's
operator dictionary should have priority — the dictionary is the only one of the
three sources carrying **`stretchy`**, and it was prepared with TeX experts —
and the ordering that puts the `n.fam == 3` test ahead of the noad class. The
project already holds the dictionary as `mathml-ops.csv` / `stretchy-chars.json`.
Whether the two ever *disagree* where both speak is measurable, not a matter of
opinion, and worth measuring before anyone edits a colleague's file.

---

## 10. Where everything is now (2026-09-02)

| repo | state |
|---|---|
| `htf-fonts` | 26 commits, pushed. 22 `.gpm.json` + this file uncommitted |
| `~/gitlab/xmlforge/vtex-overlay` | 8 commits, clean, **no remote and none wanted** |
| `vtex-dist`, `texmf-vtex`, `texmf-dist`, `2024`, `xmlforge/work` | untouched |

Two overlay files await review, and they go to **two different colleagues**:

```
yours  tex/luatex/luarealchar/user_htf.lua    -> vtex-dist    (bbm, §8)
yours  tex/luatex/xmlforge/vtxml-mathml.lua   -> texmf-vtex   (<mn>, §9)
```

`make deploy` moves both; `make deploy-<file>` one at a time. Neither has been
near those trees.

**The xmlforge half is still on `comp-chars`** (§1), unmerged, with one change
unconfirmed — "one `<font>` tag per char in `.uni`". That is why §7 took the
conservative fork and does **not** use the char-level `['font']` table for
cancellation: it would save 243 wraps (1237 → 994) and stop `stix-mathcal` being
worse than the policy it replaces, but what the resulting properties do
downstream depends on `comp-chars`. `gpm_to_htf --no-dedup` measures the gap and
nothing writes it. luarealchar reads that table (`luarealchar.lua:671-679`,
added by `d4bcc17cd`) and **bbm already used it** — four times, for the white
brackets — so it is not untried ground.
