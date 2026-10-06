"""Shared glyph tests for the scripts that run under fontforge.

One question, asked in three places (the encoding export, the image export and
the metrics), and it has to be asked the same way in each or a glyph enters one
and not the others.

WHY NOT isWorthOutputting() ALONE.  bbmssbx10 encodes 256 named slots of which
only 67 draw anything.  The other 189 hold ONE DEGENERATE CONTOUR each -- enough
for isWorthOutputting() to call them glyphs, not enough to put ink anywhere -- so
154 identical 1x101 white PNGs were exported, the metrics gained 189 entries of
no size, and the review page illustrated 189 rows with pictures of nothing.

WHY NOT THE BOUNDING BOX ALONE.  A space draws nothing BY DESIGN and is a real
glyph: bbmssbx10's slot 32 is 'space', and rejecting everything with an empty
bounding box threw it out with the broken composites.

So the two are asked in order: ink settles it where there is ink, and where there
is none the question becomes what the glyph STANDS FOR.  U+0020 is meant to be
invisible; U+00C1 is not, so an Aacute that draws nothing is a hole wearing a
name -- and it cannot be told from a space by its width, both having one (881 for
Aacute, which keeps A's advance).
"""
import unicodedata

# General categories whose characters are invisible by definition: space
# separators, line and paragraph separators, format and control characters.
BLANK_OK = ("Zs", "Zl", "Zp", "Cf", "Cc")


def draws(g):
    """Is this glyph a real glyph -- ink, or blank on purpose?"""
    try:
        x0, y0, x1, y1 = g.boundingBox()
    except Exception:
        return True                    # unanswerable: keep it rather than lose it
    if (x1 - x0) > 0 and (y1 - y0) > 0:
        return True
    cp = getattr(g, "unicode", -1)
    if cp is None or cp < 0:
        return False                   # blank, and standing for nothing
    try:
        return unicodedata.category(chr(cp)) in BLANK_OK
    except ValueError:
        return False


def real(g):
    """The whole test: worth outputting AND (drawing, or blank by design)."""
    try:
        if not g.isWorthOutputting():
            return False
    except Exception:
        pass
    return draws(g)
