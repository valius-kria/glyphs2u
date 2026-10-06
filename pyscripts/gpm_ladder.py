#!/usr/bin/env python3
"""Rank the size cuts of a stretchable character, from the font metrics.

Shared by the size report (gpm_sizes.py) and the editor (gpm_edit.py), so both
answer "which cut is this glyph?" the same way.

WHICH CHARACTERS -- from MathML's operator dictionary (stretchy-chars.json)
plus the hand-kept supplement (stretchy-extra.json).  Nothing else is measured:
a dotless letter beside its dotted form shares an advance and is shorter, which
looks exactly like an extension piece, but 'i' does not expand so the question
never arises.

WHICH DIMENSION -- one axis for the whole STEM: width if the stem's widest cut
is wider than its tallest is tall, else height.  A delimiter grows taller, an
accent or an over-brace grows wider (hatwide/hatwider/hatwidest), and the
overall shape says which: a circumflex reaches 2.33 em wide but only 0.24 tall,
a parenthesis 3.08 tall and 0.71 wide.  "Wider" means half again as wide, since
some cuts are nearly square.

Per GLYPH it would go wrong.  uni2A0C, the quadruple integral, is wider than it
is tall at its smaller cuts, so taking each glyph's larger dimension reads its
WIDTH -- and since an upright cut is narrower than the slanted one of the same
size (1.28 against 1.63 em in stix-mathcal-bold), the two slants interleave and
the uprights look like smaller cuts.  On the stem's axis they tie, which is
what they are: the same size, differently drawn.

WHICH SELECTOR -- the cuts run FE01, FE02, ... upwards, and where that ladder
starts depends on the KIND of character, because the sources treat the two
kinds differently and agree with each other within each:

  n-ary operators (MathML's 'largeop')  the plain cut IS the text cut and takes
      FE01, the next FE02.  glyphlist_table.lua spells it summationtext =
      2211 FE01, summationdisplay = 2211 FE02.

  delimiters and accents                the plain character takes NO selector
      and the first larger cut is FE01.  cmex10, glyphlist_table.lua and the
      per-font stix tables all agree: parenleftbig = 0028 FE01, and
      stix-mathex's uni2985 keeps its plain cut bare beside uni2985.s1 = FE01.

Where a stem has no plain glyph at all -- stix-mathex holds parenleft.s1..s4
and no plain parenleft, its text size living in another font -- the smallest
cut present is FE01 either way.

Cuts SMALLER than the text cut -- stix-mathcal's .sm, a script-size cut -- get
no proposal: nothing in the scheme sits below FE01 and what they are for is
unclear.
"""
import collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G

class Ladder:
    def __init__(self, font, data=G.DATA, metrics=None):
        self.font = font
        self.ok = False
        self.gm, self.em = {}, 1000
        mf = metrics or f"{font}.metrics.json"
        if os.path.exists(mf):
            m = G.load(mf)
            self.gm, self.em, self.ok = m["glyphs"], m["em"], True
        self.stretchy = {}
        self.added, self.composed = {}, {}
        try:
            self.stretchy = G.load_map("stretchy-chars.json", data)["chars"]
        except FileNotFoundError:
            pass
        try:
            x = G.load_map("stretchy-extra.json", data)
            self.added = {k: v for k, v in x.get("add", {}).items()
                          if not k.startswith("_")}
            self.composed = {k: v for k, v in x.get("composed", {}).items()
                             if not k.startswith("_")}
        except FileNotFoundError:
            pass
        self._axis = {}
        self.fam = collections.defaultdict(list)
        for name in self.gm:
            self.fam[name.split(".")[0]].append(name)

    # ----- what expands ----------------------------------------------------
    def flags(self, base):
        """MathML's flags for this character, '+' if hand-added, None if it
        does not expand.  A trailing 'c' marks one built from pieces."""
        # A value test, not G.has_base: this takes the base STRING, with no glyph
        # and so no provenance to consult.  Harmless here even though '?' is both
        # the sentinel and a real character -- QUESTION MARK does not expand, so
        # rejecting it early and looking it up would answer the same.
        if not base or base == G.UNKNOWN:
            return None
        key = f"U+{ord(base[0]):04X}"
        c = "c" if key in self.composed else ""
        e = self.stretchy.get(key)
        if e is None:
            return ("+" + c) if key in self.added else None
        return "".join(ch for ch, k in (("s", "stretchy"), ("L", "largeop"),
                                        ("a", "accent"), ("f", "fence"),
                                        ("y", "symmetric")) if e[k]) + c

    # ----- measuring -------------------------------------------------------
    def axis(self, stem):
        """'w' or 'h' -- which way this stem's cuts grow."""
        if stem not in self._axis:
            names = self.fam.get(stem, [])
            mh = max((self.gm[n]["h_em"] for n in names), default=0)
            mw = max((self.gm[n]["w"] / self.em for n in names), default=0)
            # A margin, not a bare comparison: uni2A0C's display cut is all but
            # square (2.27 x 2.27 em) and would tip either way, while the
            # genuinely horizontal stems are far wider than tall -- a circumflex
            # 9.7x, an over-brace 4.2x, a horizontal arrow 2.0x -- and the
            # vertical ones are never above 1.0x.  Anything in between is read
            # as vertical, the commoner case.
            self._axis[stem] = "w" if mw > 1.5 * mh else "h"
        return self._axis[stem]

    def size(self, name):
        """The glyph's extent along its stem's axis, in em."""
        g = self.gm.get(name)
        if not g:
            return None
        return (g["w"] / self.em if self.axis(name.split(".")[0]) == "w"
                else g["h_em"])

    def assembly(self, stem):
        """The stem's assembly pieces, by their shared advance width.

        A construction's parts are set on one advance so they stack in a
        column: stix-mathex's radical bottom, top and extension all advance
        1184 while its four size cuts advance 928/1057/1124/1076.  Height alone
        misses the bottom piece, which is as tall as the first cut.  Where a
        group's members are all the same size it is not a construction but two
        cuts of one size (a slanted and an upright display integral).
        """
        members = self.fam.get(stem, [])
        if len(members) < 2:
            return set()
        biggest = max(self.size(n) or 0 for n in members)
        byadv = collections.defaultdict(list)
        for n in members:
            byadv[self.gm[n]["adv"]].append(n)
        pieces = set()
        for group in byadv.values():
            if len(group) < 2:
                continue
            sizes = {n: (self.size(n) or 0) for n in group}
            top = max(sizes, key=lambda n: (sizes[n], n))
            if min(sizes.values()) == sizes[top]:
                continue
            if sizes[top] == biggest or "." not in top:
                cand = {n for n in group if sizes[n] < sizes[top]}
            else:
                cand = set(group)
            # Two advances can coincide without the glyphs being parts of one
            # construction: stix-mathcal-bold sets uni222E.sm and uni222E.updsp
            # on 626 alike, and the first is a script-size cut, not a piece.
            # What tells them apart is that a cut's size recurs elsewhere in the
            # stem -- .sm measures 0.93 like .upsm outside the group -- while a
            # piece stands at a size nothing else has.
            outside = {self.size(n) for n in members if n not in group}
            pieces |= {n for n in cand if sizes[n] not in outside}
        return pieces

    def cuts(self, stem):
        """[(size, name)] of the stem's real cuts, smallest first."""
        pieces = self.assembly(stem)
        out = [(self.size(n), n) for n in self.fam.get(stem, [])
               if n not in pieces and self.size(n) is not None]
        return sorted(out)

    # ----- the proposal ----------------------------------------------------
    def proposal(self, name, g):
        """{'codes', 'selector', 'rank', 'ladder', 'text'} or None, for one
        glyph record.

        None when the character does not expand, when the glyph is an assembly
        piece, or when it is the text cut or smaller -- the text cut is written
        plain, and nothing in the scheme sits below FE01.
        """
        char = G.char_at(g)
        if char is None or not self.ok:
            return None
        # the character at the position decides both questions -- whether it
        # expands, and what the sequence is written on
        if self.flags(char) is None and self.flags(g.get("base") or "") is None:
            return None
        stem = name.split(".")[0]
        if name in self.assembly(stem):
            return None
        cuts = self.cuts(stem)
        if len(cuts) < 2 or name not in [n for _, n in cuts]:
            return None
        plain = [n for _, n in cuts if "." not in n]
        mine = self.size(name)
        largeop = "L" in (self.flags(char) or self.flags(g.get("base") or "") or "")
        text = plain[0] if plain else None
        if plain and largeop:
            # an n-ary operator: its plain cut is the text cut and takes FE01,
            # so the ladder starts there rather than above it
            text_size = self.size(text)
            if mine < text_size:
                return None
            rungs = sorted({s for s, _ in cuts if s >= text_size})
        elif plain:
            # a delimiter or accent: the plain character is written bare and the
            # cuts above it are FE01, FE02, ...
            text_size = self.size(text)
            if mine <= text_size:
                return None
            rungs = sorted({s for s, _ in cuts if s > text_size})
        else:
            # no plain glyph: the text size lives in another font, so the
            # smallest cut here IS FE01 -- stix-mathex's parenleft.s1, like
            # cmex10's parenleftbig
            rungs = sorted({s for s, _ in cuts})
        rank = rungs.index(mine) + 1
        if rank > 15:                    # FE01..FE0F is all there is
            return None
        sel = 0xFE00 + rank
        return {
            "codes": [f"0x{ord(c):04X}" for c in char] + [f"0x{sel:04X}"],
            "selector": f"U+{sel:04X}", "rank": rank, "of": len(rungs),
            "text": text, "ladder": cuts,
        }
