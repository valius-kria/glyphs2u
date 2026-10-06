#!/usr/bin/env python3
"""Propose the published NAME for a glyph whose own name carries a dot.

Acrobat Distiller truncates a glyph name at the first dot before consulting the
AGL, so 'uni222B.dsp' is read as 'uni222B' -- the plain integral, not its display
cut.  Every dotted glyph therefore needs a dot-free name to be published under,
and that name has to mean what the glyph is.

The names are not invented here.  The BASE comes from the built-in glyph list
(glyphs2u/builtin-glyph-map.json, what xdvipsk carries) and the rest from the
glyph's own name:

  A DOTTED NAME keeps its suffix, with the dots removed: uni222B.updsp becomes
  'integralupdsp' -- 'integral' being what the list calls U+222B, 'updsp' what
  the font itself calls that cut.  Using the font's own suffixes rather than the
  list's size words is what keeps every name unique: uni222B.dsp and
  uni222B.updsp are both 222B FE02, the slanted and upright display integrals,
  so the one name 'integraldisplay' could not serve both.  Where the list does
  name the sequence, that name is reported beside the proposal for comparison.

  A SUFFIX-LESS NAME is normally left alone, nothing being truncated away -- but
  not when its value carries a VARIATION SELECTOR, which an algorithmic name
  cannot state.  stix-mathcal's uni222B reads as plain U+222B while its row says
  222B FE01, so the text cut would be published as the plain integral.  There
  the list's own name for the sequence is used ('integraltext'), there being no
  suffix to build one from.

  Anything with no base to build on is reported, not guessed at.

Values land with status "name": read off the font's own naming, which is better
than an assumption and weaker than having looked at the glyph, so "visual" and
"manual" are never overwritten.

  gpm_rename.py <font> --list     # what would be set, and from which step
  gpm_rename.py <font>            # write them
"""
import argparse, collections, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G
from gpm_ladder import Ladder

ap = argparse.ArgumentParser()
ap.add_argument("font", nargs="?",
                help="not needed with --seed-stems, which reads only "
                     "the built-in list and stretchy-chars.json")
ap.add_argument("--data", default=G.DATA)
ap.add_argument("--gpm")
ap.add_argument("--metrics")
ap.add_argument("--builtin", default=os.environ.get("builtin_glyph_map") or
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "builtin-glyph-map.json"))
ap.add_argument("--stems", default="rename-stems.json",
                help="codepoint -> stem map, looked up beside the other data")
ap.add_argument("--seed-stems", action="store_true",
                help="write/refresh that map from the built-in list and exit; "
                     "entries already in it are kept")
ap.add_argument("--list", action="store_true", help="report, change nothing")
ap.add_argument("--overwrite", action="store_true",
                help="also replace a rename set automatically (never "
                     "visual/manual)")
a = ap.parse_args()

B = G.load(a.builtin)
codes_of = {n: tuple(int(str(c), 16) if isinstance(c, str) else int(c) for c in v)
            for n, v in B.items()}
by_codes = collections.defaultdict(list)
for n, cs in codes_of.items():
    by_codes[cs].append(n)
plain_name = {cs[0]: sorted(ns) for cs, ns in by_codes.items() if len(cs) == 1}
SEL = range(0xFE00, 0xFE10)

def shortest(names):
    """The shortest spelling, ties broken alphabetically.

    The list often holds several for one thing -- 'gradient' and 'nabla' for
    U+2207 -- and the short one is the one these fonts are named after.
    """
    return sorted(names, key=lambda n: (len(n), n))[0] if names else None

# The size words the list itself uses, per rung, learned rather than listed: a
# name for [X, FE0n] that is a plain name of X plus something tells us that
# something is the word for rung n.  'integraltext' over plain 'integral' teaches
# 'text' for FE01, 'parenleftbig' over 'parenleft' teaches 'big'.
# What the glyph name itself states, read up to the first dot -- the same test
# gpm_to_lua prunes by, so the two cannot disagree about which rows exist.
ALGORITHMIC = re.compile(r"u(?:ni(?:[0-9A-Fa-f]{4})+|[0-9A-Fa-f]{4,6})\Z")

def agl_stem_codes(gname):
    stem = gname.split(".")[0]
    if not ALGORITHMIC.match(stem):
        return None
    if stem.startswith("uni"):
        b = stem[3:]
        return [int(b[i:i + 4], 16) for i in range(0, len(b), 4)]
    return [int(stem[1:], 16)]

SUFFIX = collections.defaultdict(set)
for _n, _cs in codes_of.items():
    if len(_cs) != 2 or _cs[1] not in SEL:
        continue
    for _p in plain_name.get(_cs[0], []):
        if _n.startswith(_p) and _n != _p:
            SUFFIX[_cs[1] - 0xFE00].add(_n[len(_p):])

def base_candidates(base):
    """Every name that could serve as the stem for this character.

    Two sources: names for the bare character, and its SIZE VARIANTS with the
    size word taken off.  The second matters because the two need not agree --
    the list calls U+222E 'contourintegral' on its own but names its cuts
    'contintegraltext' and 'contintegraldisplay', so the family's own stem is
    'contintegral', and taking the shortest keeps one stem per family.

    The size word is STRIPPED, not guessed at by common prefix.  A blind prefix
    breaks wherever one character carries two naming families: U+27E8 has
    angbracketleftbig and the stray angleleftbigx, whose common prefix is 'ang'
    -- which U+27E9 shares, so left and right angle brackets came out with the
    same name.  Stripping a known word instead yields 'angbracketleft', and
    leaves a spelling like 'angleleftbigx' contributing nothing, having no word
    this list ever taught.
    """
    cands = set(plain_name.get(base, []))
    for n, cs in codes_of.items():
        if len(cs) != 2 or cs[0] != base or cs[1] not in SEL:
            continue
        for w in SUFFIX.get(cs[1] - 0xFE00, ()):
            if n.endswith(w) and len(n) > len(w):
                cands.add(n[:-len(w)])
    return cands

if not a.seed_stems and not a.font:
    sys.exit("gpm_rename: name a font, or use --seed-stems to refresh the map")

if a.seed_stems:
    # Scope: the characters that can take a size cut at all (MathML's operator
    # dictionary), which is the set that ever needs a stem -- 259 rather than the
    # 4006 the built-in list mentions.  Existing entries are kept, so a name
    # decided by hand is never overwritten by a reseed; characters the list
    # cannot name are written as null, which is the list of what to fill in.
    def _stretchy_codepoints():
        """MathML's operator dictionary PLUS the hand-kept 'add' of
        stretchy-extra.json -- the characters that take size cuts although the
        dictionary does not list them.

        The supplement was missing here, and gpm_ladder (its other reader) has
        honoured it all along, so the seeder's idea of scope was narrower than
        the project's: U+2140 DOUBLE-STRUCK N-ARY SUMMATION is declared there
        with its cuts named, and was still treated as out of scope.
        """
        out = set()
        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k.startswith("U+"):
                        out.add(int(k[2:], 16))
                    walk(v)
        walk(G.load_map("stretchy-chars.json", a.data))
        try:
            extra = G.load_map("stretchy-extra.json", a.data)
        except FileNotFoundError:
            extra = {}
        # 'add' only.  'composed' is in the dictionary already -- it says a font
        # stacks pieces rather than holding sizes, not that MathML omitted it.
        for k in (extra.get("add") or {}):
            if k.startswith("U+"):
                out.add(int(k[2:], 16))
        return out
    path = os.path.join(G.ROOT, a.stems)
    old = G.load(path).get("stems", {}) if os.path.exists(path) else {}
    stems, kept, filled, blank = {}, 0, 0, 0
    for cp in sorted(_stretchy_codepoints()):
        key = f"U+{cp:04X}"
        if old.get(key):
            stems[key] = old[key]; kept += 1
            continue
        d = shortest(base_candidates(cp))
        stems[key] = d
        if d: filled += 1
        else: blank += 1
    # A stem already here for a character OUTSIDE the current scope is CARRIED,
    # never dropped.  It used to be dropped, which made this step lose decisions
    # silently: U+2140 'bbsum' was added by hand, fell outside the scope this
    # function computed, and vanished on the next reseep -- and since the reseed
    # is triggered by stretchy-chars.json being rebuilt, nobody was asking for it
    # at the time.  A stem is a decision; the scope decides what to ASK about,
    # not what to keep.  (Nulls are not carried: they are the questions, and a
    # question about a character no longer in scope is not worth keeping.)
    carried = 0
    for key, val in old.items():
        if key.startswith("U+") and key not in stems and val:
            stems[key] = val
            carried += 1
    stems = {k: stems[k] for k in sorted(stems, key=lambda k: int(k[2:], 16))}
    out = {"_about": [
        "The name to build a published glyph name on, per character.",
        "",
        "A dotted glyph name has to be republished dot-free (Distiller truncates",
        "at the first dot), and the name is built from a STEM plus the font's own",
        "suffix: U+222B -> 'integral' gives integralup, integraldsp, integralupdsp.",
        "",
        "Seeded from the built-in glyph list with `gpm_rename.py <font>",
        "--seed-stems`, which keeps every entry already here -- so a stem decided",
        "by hand survives a reseed.  A null is a character the built-in list does",
        "not name: those are the ones to fill in, once each, for every family.",
        "",
        "Scoped to the characters that can take a size cut -- stretchy-chars.json",
        "plus the 'add' of stretchy-extra.json -- since those are the only ones",
        "whose cuts need names.  A stem for a character outside that scope is",
        "kept anyway: the scope says what to ASK about, not what to keep."],
        "stems": stems}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"gpm_rename: {path}  {len(stems)} character(s): {kept} kept, "
          f"{filled} from the built-in list, {blank} still to name"
          + (f", {carried} carried from outside the current scope" if carried else ""))
    sys.exit(0)

gpm = a.gpm or f"{a.font}.gpm.json"
rec = G.load(gpm)
var = G.Variants(a.data)
mfile = a.metrics or f"{a.font}.metrics.json"
ladder = Ladder(a.font, data=a.data, metrics=mfile) if os.path.exists(mfile) else None

# The stem map: 'U+XXXX' -> the name to build on.  Seeded from the built-in list
# (--seed-stems) and then hand-kept, so a character the list never names gets a
# stem once and every font of every family reuses it, instead of the question
# coming back per font.
STEMS = {}
stem_file = G.map_path(a.stems, a.data) if a.stems else None
if stem_file and os.path.exists(stem_file):
    for k, v in (G.load(stem_file).get("stems") or {}).items():
        if k.startswith("U+") and v:
            STEMS[int(k[2:], 16)] = v

# The size word for a rung, by the kind of character -- the built-in list's own
# families establish these: integraltext/integraldisplay for an n-ary operator,
# parenleftbig/Big/bigg/Bigg for a delimiter, hatwide/wider/widest for an accent.
# Needed where a name has NO suffix to build from and the list has no entry for
# the sequence: stix-mathcal-bold's uni222C is 222C FE01, and 'integraldbl' from
# the stem map plus 'text' for FE01 gives integraldbltext.
KIND_SUFFIX = {
    "largeop":   {1: "text", 2: "display"},
    "delimiter": {1: "big", 2: "Big", 3: "bigg", 4: "Bigg"},
    "accent":    {1: "wide", 2: "wider", 3: "widest", 4: "4", 5: "5", 6: "6"},
}

def kind_of(char):
    """'largeop' | 'delimiter' | 'accent' | None -- from the operator dictionary."""
    if ladder is None:
        return None
    fl = ladder.flags(char) or ""
    if "L" in fl:
        return "largeop"
    if "a" in fl:
        return "accent"
    if "s" in fl:
        return "delimiter"
    return None

def size_word(seq):
    """The list's word for this sequence's selector, or None."""
    sels = [c for c in seq[1:] if c in SEL]
    if len(sels) != 1:
        return None
    return KIND_SUFFIX.get(kind_of(chr(seq[0])), {}).get(sels[0] - 0xFE00)

def name_value(gname):
    """The value publishing under this glyph's OWN name would give.

    A rename is needed only where that differs from the value we want.  Two
    sources, in order: the built-in list, which may name the glyph outright or
    name its stem (Distiller truncates at the first dot, so 'braceleft.s1' is
    read as 'braceleft' = U+007B); failing that, the algorithmic decoding of the
    stem ('uni23B4.l' -> U+23B4).
    """
    if gname in codes_of:
        return list(codes_of[gname])
    stem = gname.split(".")[0]
    if stem in codes_of:
        return list(codes_of[stem])
    return agl_stem_codes(gname)

def stem_for(cp):
    return STEMS.get(cp) or shortest(base_candidates(cp))

# Two names per glyph: what the built-in list calls this exact sequence, and what
# the font's own suffix builds.  The list's name is preferred -- for a delimiter
# it is exact and unique, 'parenleftbig' rather than 'parenlefts1' -- and the
# built one is the fallback for the families where it cannot be: uni222B.dsp and
# uni222B.updsp are both 222B FE02, so 'integraldisplay' cannot name both and
# BOTH move to the suffix form, keeping one convention per family.
# gpm_to_lua leaves a stem without selectors when two of its cuts measure the
# same, the rank being a guess there.  The same suppression has to happen here or
# the two disagree about the value, and it was that disagreement -- not the rule
# -- that had uni23B4.l named: measured 23B4 FE01 here, published as plain 23B4
# there, so it looked like a row saying more than its name.
ambiguous = set()
if ladder is not None:
    for _gn in rec["glyphs"]:
        _st = _gn.split(".")[0]
        if _st in ambiguous:
            continue
        _sz = [z for z, _x in ladder.cuts(_st)]
        if len(_sz) != len(set(_sz)):
            ambiguous.add(_st)

options, unnamed = {}, []
for gname, g in sorted(rec["glyphs"].items()):
    # Every glyph is considered, including one that already has a rename: what to
    # do with an existing value is decided at the writing step below.  Skipping
    # them here left a glyph unable to be re-proposed, so a name this tool had
    # written looked stale and was retracted the next run.
    codes, kind, _lost = G.uni_codes(rec, g, var, gname)
    if not codes:
        continue
    if ladder is not None and kind != "override" \
            and gname.split(".")[0] not in ambiguous:
        pr = ladder.proposal(gname, g)
        if pr:
            body = [c for c in (int(x, 16) for x in pr["codes"]) if c not in SEL]
            if body == codes:
                codes = [int(x, 16) for x in pr["codes"]]
    seq = tuple(codes)
    stem, _, suffix = gname.partition(".")

    # Only a row that reaches the table is worth naming: where the value is what
    # the glyph name already states, gpm_to_lua prunes the row, and a rename is
    # exactly what would put it back.  uni222B.sm is plain U+222B like its stem,
    # so it needs neither; uni222B.up, 222B FE01, needs both.  Every '.var' and
    # '.ital' glyph falls on the same side as '.sm'.
    if name_value(gname) == list(seq):
        continue

    exact = shortest(by_codes.get(seq, []))
    if not suffix:
        # No dot, so nothing is truncated -- unless the value carries a SELECTOR,
        # which an algorithmic name cannot state: uni222B reads as plain 222B
        # while its row says 222B FE01.  Only the list can name that, there being
        # no suffix to build from.
        if not any(c in SEL for c in seq):
            continue
        if exact:
            options[gname] = (seq, exact, None)
            continue
        # No entry for the sequence: build it, the stem plus the word for this
        # rung.  There is no suffix on the name to use, so the word has to come
        # from the convention for this kind of character.
        base_name = stem_for(seq[0])
        word = size_word(seq)
        if base_name and word:
            options[gname] = (seq, None, base_name + word)
        else:
            unnamed.append((gname, seq, "carries a selector its own name cannot "
                            "state; " + ("no stem for this character"
                                         if not base_name else
                                         "no word known for this rung")))
        continue

    base_name = stem if stem in codes_of else stem_for(seq[0])
    built = None
    if base_name:
        cand = base_name + suffix.replace(".", "")
        if cand in codes_of and codes_of[cand] != seq:
            unnamed.append((gname, seq, f"'{cand}' is taken by the built-in list "
                            f"for U+{'+'.join('%04X' % c for c in codes_of[cand])}"))
            continue
        built = cand
    if not exact and not built:
        unnamed.append((gname, seq, "no stem for this character -- give it one in "
                        f"{os.path.basename(a.stems)}"))
        continue
    options[gname] = (seq, exact, built)

# Assign the list's name where it singles a glyph out.  Where several glyphs
# resolve to one sequence, the ones that CAN build a name from their suffix give
# way to those that cannot: stix-mathcal's uni222B and uni222B.up are both
# 222B FE01, and only the suffixed one has an alternative, so the bare glyph
# keeps 'integraltext' and the cut becomes 'integralup'.  Only when every
# claimant is nameless is it a real collision.
proposals, collide = {}, []
claim = collections.defaultdict(list)
for gname, (_seq, exact, _built) in options.items():
    if exact:
        claim[exact].append(gname)
yielded = set()
for nm, gs in claim.items():
    if len(gs) < 2:
        continue
    movable = [g for g in gs if options[g][2]]
    # everyone moves except one -- and if all can move, they all do, so the
    # family keeps one convention rather than one odd member out
    keep = [g for g in gs if g not in movable]
    if len(keep) == 1:
        yielded.update(movable)
    elif not keep:
        yielded.update(gs)
    else:
        for g in keep:
            collide.append((g, nm, [x for x in gs if x != g]))
        yielded.update(movable)
        for g in keep:
            options.pop(g, None)
for gname, (_seq, exact, built) in options.items():
    if exact and gname not in yielded:
        proposals[gname] = (exact, "built-in name for these codepoints", None)
    elif built:
        how = "base name + the font's own suffix"
        if exact:
            how += f" (the built-in '{exact}' names another glyph's cut too)"
        proposals[gname] = (built, how, exact)
    else:
        unnamed.append((gname, _seq, "no name available that singles it out"))

again = collections.defaultdict(list)
for gname, (nm, _h, _e) in proposals.items():
    again[nm].append(gname)
for nm, gs in sorted(again.items()):
    if len(gs) > 1:
        for gname in gs:
            collide.append((gname, nm, [x for x in gs if x != gname]))
            proposals.pop(gname, None)

# A rename this tool put there ("name") and would no longer propose is stale:
# the rules settle over time -- what a row must say, which value its own name
# gives -- and a leftover rename is not inert, it is exactly what keeps a row in
# the table.  So they are retracted, and reported.  Anything confirmed by eye or
# by hand is left alone: those are not this tool's to withdraw.
retracted = []
for gname, g in sorted(rec["glyphs"].items()):
    if gname in proposals:
        continue
    if not g.get("rename"):
        continue
    if g.get("status", {}).get("rename") != "name":
        continue
    retracted.append((gname, g["rename"]))
    if not a.list:
        g.pop("rename", None)
        g.get("status", {}).pop("rename", None)

n_set = n_kept = n_same = 0
kept_diff = []
for gname, (nm, _how, _ex) in sorted(proposals.items()):
    g = rec["glyphs"][gname]
    if g.get("rename") == nm:
        n_same += 1
        continue
    # Only a rename this tool wrote ("name") is this tool's to replace.  The
    # records carry names of their own -- 'hatwide', 'idotless' -- with no status
    # at all, meaning they came with the font rather than from any step here, and
    # they are the established spelling: 'hatwide' is what the built-in list
    # calls the first circumflex cut, where this would construct
    # 'circumflexcmbs1' from the stem.  Kept, and the difference reported.
    st = g.get("status", {}).get("rename")
    if g.get("rename") and st != "name" and not a.overwrite:
        n_kept += 1
        kept_diff.append((gname, g["rename"], nm, st or "came with the record"))
        continue
    if not a.list:
        g["rename"] = nm
        g.setdefault("status", {})["rename"] = "name"
    n_set += 1

if not a.list and (n_set or retracted):
    G.save(rec, gpm)

if kept_diff:
    print(f"  {len(kept_diff)} rename(s) left as they are -- not written by this "
          f"step, so not its to replace:")
    for gname, have, want, why in kept_diff[:10]:
        print(f"    {gname:<18} '{have}' kept ({why}); this would say '{want}'")
    if len(kept_diff) > 10:
        print(f"    ... {len(kept_diff) - 10} more")
if retracted:
    print(f"  {len(retracted)} rename(s) "
          f"{'would be' if a.list else ''} retracted -- no longer called for, and "
          f"a leftover one keeps a row in the table:")
    for gname, was in retracted[:12]:
        print(f"    {gname:<18} was '{was}'")
    if len(retracted) > 12:
        print(f"    ... {len(retracted) - 12} more")
print(f"gpm_rename: {gpm}{' (list only)' if a.list else ''}  "
      f"{n_set} name(s) {'proposed' if a.list else 'written'}, "
      f"{len(collide)} collision(s), "
      f"{len([u for u in unnamed if not rec['glyphs'][u[0]].get('rename')])} "
      f"not nameable"
      + (f", {n_same} already right" if n_same else "")
      + (f", {n_kept} already confirmed here" if n_kept else ""))
by_how = collections.Counter(how for gn, (_nm, how, _ex) in proposals.items()
                             if rec["glyphs"][gn].get("rename") != _nm
                             or a.list and True)
for how, k in by_how.most_common():
    print(f"  {k:>4}  {how}")
for gname, (nm, _how, ex) in sorted(proposals.items()):
    print(f"    {gname:<18} -> {nm:<24}"
          + (f"  (built-in calls these codepoints {ex})" if ex else ""))
if collide:
    print(f"  {len(collide)} glyph(s) share a proposed name -- Unicode does not "
          f"tell these cuts apart and the built-in list has no name for the "
          f"distinction, so it has to be decided:")
    seen = set()
    for gname, nm, others in collide:
        if nm in seen:
            continue
        seen.add(nm)
        print(f"    {nm}: {gname}, {', '.join(others)}")
# A glyph that already carries a name is not a gap, whatever this step could or
# could not have derived for it: uni221A.x is 'radicalex' and stays so.
unnamed = [u for u in unnamed if not rec["glyphs"][u[0]].get("rename")]
if unnamed:
    print(f"  {len(unnamed)} not nameable:")
    for gname, seq, why in unnamed[:12]:
        print(f"    {gname:<18} U+{'+'.join('%04X' % c for c in seq):<14} {why}")
    if len(unnamed) > 12:
        print(f"    ... {len(unnamed) - 12} more")
