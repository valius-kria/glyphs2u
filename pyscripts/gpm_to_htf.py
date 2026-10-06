#!/usr/bin/env python3
"""Derivation A: <font>.gpm.json -> <font>.gpm.map.json, the htf side.

TWO POLICIES, selected by --policy (default 'char'):

  char  CHARACTER FIRST.  Compose as much of the glyph's properties into the
        Unicode character as Unicode can express -- exactly what the glyphs2u
        side does, through the same G.uni_codes -- and state the REMAINDER, the
        axes no character could carry, in a mathvariant.  So a double-struck A
        is U+1D538 with nothing around it, and a double-struck BOLD A is U+1D538
        wrapped in mathvariant="bold", bold being the part the character cannot
        hold.  Nothing is stated twice and nothing is dropped.

  attr  ATTRIBUTE FIRST, the older policy: reduce every precomposed variant
        character to its BASE and state the whole variant in the markup, so the
        properties live in one place.  Kept because it is what htf_data.lua
        holds today, and the two are worth diffing per font before the change
        lands.

Under 'char' each position gets one of:
  compose   value := the composed character, alone -- it carries everything
  wrap      value := <mfont mathvariant="REMAINDER">composed character</mfont>
  keep      nothing to change (no base to compose from)

Under 'attr' the actions are the older wrap / plain / keep, 'plain' being the
reduction of a composed character back to its base.

The mathvariant under 'char' states the REMAINDER only, never the full variant:
stating the full one is what would say double-struck twice, once in U+1D538 and
once in the attribute.  This is the same split the .master side settled on --
the character carries what it can, the residue goes to mathvariant -- so the two
halves of the pipeline now agree instead of undoing each other.

Which positions get which follows from what the font-level ['font'] declaration
carries, and choosing that declaration is the real work here.  Char-specific
always wins over font-general, so every spelling states the same record; they
differ only in how much markup it takes, and the cheapest wins.

The candidates are the current declaration, plus EVERY SUBSET of the one the
record would justify:

  keep    the declaration htf_data.lua has now.  The only candidate not drawn
          from the record, so the only one that can contradict it -- and then
          it is ruled out (stix-mathscr declares variant=small-caps where its
          letters are script).
  subset  any part of what the record justifies: the font-level properties CSS
          can express (never double-struck/fraktur/script), plus an asserted
          normal, since stix-mathrm is upright IN a slanted context and has to
          say so.  All of it is the "write" case, none of it the "drop" case.

Holding a property font-wide is not the same as it being worth declaring:
stix-mathbbit-bold is bold by name, but the comparison found only 98 of its
242 glyphs actually bold, so declaring weight=bold makes the other 134 say
mathvariant="normal" to escape it -- 198 wraps, against 108 for declaring
style=normal alone.  Four axes means at most 16 subsets, so they are all tried.
Ranking is fewest wraps, then least churn against the current declaration, so a
tie never moves the htf without reason.  --keep-decl/--drop-decl override.

The map records the verdict as decl_action (keep|write|drop) and decl_wanted,
which htf_mfont_apply reads to write, replace or remove the ['font'] block --
so a font-level property gets INTO the htf here, not only out of it:
  python3 htf_mfont_apply.py --cmp <font>.gpm.map.json

Refuses a font that has no ['chars'] of its own: an alias shares another's
table, so its htf side has to go through the owner's record.

Usage: gpm_to_htf.py <font> [--keep-decl|--drop-decl] [--gpm FILE]
"""
import argparse, itertools, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("--data", default=G.DATA)
ap.add_argument("--gpm")
ap.add_argument("--out")
ap.add_argument("--keep-decl", action="store_true", help="force keeping the ['font'] declaration")
ap.add_argument("--drop-decl", action="store_true", help="force dropping it")
# MEASUREMENT ONLY.  Letting the declaration state an axis the characters carry
# would save 243 wraps over the 24 recorded fonts (1237 -> 994) and would stop
# stix-mathcal being worse than the policy it replaces -- but only if each
# carrying position then CANCELS it with a char-level ['font'] = {axis = false}.
# luarealchar reads that (luarealchar.lua:671-679, added in vtex-dist d4bcc17cd)
# and no entry has ever used it; what the resulting properties then do downstream
# depends on changes living on xmlforge's 'comp-chars' branch, one of them still
# unconfirmed.  So the flag measures the gap and nothing writes it.
ap.add_argument("--no-dedup", action="store_true",
                help="MEASUREMENT ONLY: let the declaration state axes the "
                     "characters carry, to see what dedup costs.  The output "
                     "double-applies those properties and must not be applied.")
ap.add_argument("--chars", action="store_true",
                help="spell every value as the character itself, not a hex "
                     "entity below U+10000.  For a table that composes wholly, "
                     "where a mix of characters and hex numbers reads worse and "
                     "means nothing different (bbm).")
ap.add_argument("--policy", choices=("char", "attr"),
                default=os.environ.get("HTF_POLICY", "char"),
                help="char: compose into the character, remainder to mathvariant "
                     "(default); attr: reduce to the base and state the whole "
                     "variant in the markup (the older policy)")
a = ap.parse_args()
gpm = a.gpm or f"{a.font}.gpm.json"
out = a.out or f"{a.font}.gpm.map.json"

rec = G.load(gpm)
# base_to_variants / char_to_properties -- the same tables the glyphs2u side
# composes from, so the two derivations cannot disagree about which character
# holds which properties.
var = G.Variants(a.data)


# The truth about the font, and separately what htf_data.lua declares today.
truth = {ax: rec.get("props", {}).get(ax, "normal") for ax in G.AXES}
htf_decl = rec.get("htf_decl")
if htf_decl is None:                       # record written before htf_decl existed
    htf_decl = {ax: v for ax, v in rec.get("props", {}).items()
                if rec.get("status", {}).get(ax) == "decl"}
# Keeping the declaration only carries a property that is actually true of the
# font: where the declaration contradicts the record (stix-mathscr declaring
# small-caps for script letters), keeping it is not an option at all.
wrong = {ax: v for ax, v in htf_decl.items() if truth.get(ax, "normal") != v}
decl = {ax: htf_decl.get(ax, "normal") for ax in G.AXES}

# An alias font has its own pfb but no ['chars'] of its own -- its positions come
# from the table it aliases.  That used to be a refusal here, on the grounds that
# rewriting the shared table would put this font's properties into one the others
# read too.  It is no longer, because the sharing does not survive this project's
# output: a wrapped value states the FULL effective variant, not a delta, so once
# the parent's positions carry mathvariant="double-struck" the aliasing bold font
# reads that and its ['font'] = weight:bold no longer reaches them.  For
# stix-mathbb-bold that is 68 of 222 positions silently losing their bold.
#
# So the map is derived from THIS font's record, as for any other, and the entry
# it describes has to become one of this font's own.  Two things the writing step
# must know, recorded below rather than left implicit:
#
#   htf_owner       the table the entry aliases today.
#   alias_must_go   the alias has to be REMOVED when chars are written, because
#                   luarealchar.lua reads the two exclusively --
#                   'if htf.alias then ... elseif htf.chars then ...'
#                   (luarealchar.lua:611) -- so an entry keeping both has its own
#                   chars ignored entirely.  Dropping the alias costs nothing
#                   here: the largest-prefix rule walks 'stix-mathbb-bold' down
#                   to 'stix-mathbb' in five steps, so positions this font does
#                   not define are still found in the parent.
#
# Safe for these three fonts because nothing outside the family aliases them:
# the only stix aliases are mathbb-bold, mathex-bold and mathtt-bold, each
# pointing at its own non-bold parent, and no stix entry aliases anything else.
# A font aliased by others still needs care, which is why the fact is recorded.
owner = rec.get("htf")
entry = rec.get("htf_entry") or rec["font"]
# Two distinct situations, and only one of them is an alias:
#   by PREFIX   no entry of this font's name exists; 'bbm10' is served by 'bbm'
#               through the largest-prefix rule.  Nothing to remove -- and the
#               entry to write is 'bbm', not 'bbm10', or every other size of the
#               same cut would keep reading the old table.
#   by ALIAS    the entry exists and points at another for its chars.  That one
#               must lose its alias if it is to carry chars of its own, the two
#               being read exclusively by luarealchar.lua.
by_prefix = entry != rec["font"]
aliased = bool(owner) and owner != entry

# Statuses that mean somebody or something actually asserted the value, as
# against it being inherited or filled in as a blanket assumption.
ASSERTED = ("name", "visual", "manual", "cmp")

def asserted_normal(g, axis):
    """Is this axis positively stated to be normal -- per glyph, or font-wide?

    Which value is the unmarked default depends on the context, and the record
    says which by whether anyone bothered to assert it.  In maths, letters are
    slanted by default: stix-mathit needs no mathvariant, while stix-mathrm is
    upright IN a slanted context and has to say so as mathvariant="normal", and
    so does stix's uni222B.up beside the usual slanted uni222B.  In text the
    default is upright, nobody asserts it, and nothing is marked -- italic gets
    marked instead, which happens anyway by being a non-normal value.

    A blanket fill (status "default", from gpm_set --rest) is not an assertion
    and marks nothing.
    """
    if axis in g.get("props", {}):
        return (g["props"][axis] == "normal"
                and g.get("status", {}).get(axis) in ASSERTED)
    return (rec.get("props", {}).get(axis) == "normal"
            and rec.get("status", {}).get(axis) in ASSERTED)

def drop_implied_slant(ch, axes, var):
    """Remove a style=italic that the character's own family already carries.

    \\mathcal and \\mathscr both resolve to Unicode SCRIPT letters, which are
    drawn slanted, so a style=italic left over from the font's props is already
    expressed by the character -- stating it again gave
    <mi mathvariant="italic">the-script-Z</mi>, asking a renderer to slant a
    glyph that is slanted.  stix-mathcal has props {style: italic} measured by
    eye, and 109 of its positions wrapped for it.

    Only 'style', and only for the families in gpm_io.SLANTED_FAMILIES: a
    weight=bold over a script letter is a real remainder and stays.
    """
    if not axes or not ch:
        return axes
    if not G.slanted_by_design(ch, var):
        return axes
    return tuple(ax for ax in axes if ax != "style")

def composed(gname, g):
    """(character string, axes the character could not carry).

    Straight through G.uni_codes, the call the glyphs2u side makes, so both
    derivations compose identically and the priority order that keeps
    double-struck over bold-italic (see gpm_io.KEEP_PRIORITY) applies here too.

    The variation selectors are STRIPPED.  A selector spells which size cut of a
    stretchy symbol this is, and the htf side deliberately does not emit them --
    MathJax does not honour them reliably, wide accents least of all -- while the
    record keeps them in ['uni'] for glyphs2u.  That was true under the old
    policy and nothing about composing changes it.
    """
    codes, kind, dropped = G.uni_codes(rec, g, var, gname)
    if not codes:
        return None, ()
    ch = G.split_selectors("".join(chr(c) for c in codes))[0]
    if not ch:
        return None, ()

    # An explicit ['uni'] in the record is the FINAL WORD ON THE CODEPOINTS and
    # says nothing whatever about the properties they carry -- so uni_codes
    # returns kind 'override' with lost = (), which is right for the glyphs2u
    # side (an override is what it emits, full stop) and wrong here, where 'lost'
    # is read as "what the htf must still state".
    #
    # stix-mathex-bold showed it.  Its big operators carry ['uni'] = [0x220F,
    # 0xFE01] and the like -- the character plus a variation selector for the
    # display-size cut -- so seven of its eight n-ary operators reported no
    # remainder and silently lost the weight=bold the raster comparison had
    # MEASURED for them.  The eighth, uni2140, kept its bold only because it
    # happens to have no override.  Slot 177 wrapped and 178..184 did not, for
    # no reason visible in the record.
    #
    # So for an override the remainder is derived from what the emitted
    # characters actually encode: decompose each, collect the properties they
    # carry between them, and whatever the glyph effectively has and they do not
    # is still outstanding.  U+220F encodes nothing, so all of {weight: bold}
    # remains.
    if kind == "override":
        eff = G.effective(rec, g)
        carried = {}
        for c in ch:
            _base, props = var.decompose(c)
            for ax, v in props.items():
                carried.setdefault(ax, v)
        axes = tuple(ax for ax in G.AXES
                     if eff[ax] != "normal" and carried.get(ax) != eff[ax])
        return ch, drop_implied_slant(ch, axes, var)

    # Only real axes come back as a remainder.  uni_codes also reports 'dot',
    # which is what a dotless i/j cut gives up when dtls-policy.json chooses to
    # keep the font view (gpm_io.uni_codes, kind 'dtls') -- a lost dot is not a
    # font property and no mathvariant can state it, so it is not a remainder in
    # this sense.  It is counted separately and reported.
    axes = tuple(ax for ax in dropped if ax in G.AXES)
    return ch, drop_implied_slant(ch, axes, var)

# Positions the tfm does not define are dropped before anything is written for
# them.  TeX reaches a character through the metrics, so a value at a slot
# outside [bc, ec] can never be asked for -- writing one puts an entry in the
# table that nothing will ever read.  That is how 35 unreachable values reached
# cmr's table: cmr10's .pfb encoding repeats the Greek capitals at 161.. and the
# derivation wrote every slot it was given.
#
# Inert where no range is recorded (G.addressable), so records seeded before the
# range was kept behave exactly as they did.  Counted, because a skip that says
# nothing is indistinguishable from a bug.
skipped_unaddressable = 0

def addressable_slots(rec, slots):
    global skipped_unaddressable
    keep = [t for t in slots if G.addressable(rec, t[1])]
    skipped_unaddressable += len(slots) - len(keep)
    return keep

def plan_char(carried, declared):
    """Action per position under CHARACTER FIRST.

    Each glyph composes as far as Unicode goes; what is left over is stated in a
    mathvariant -- the REMAINDER alone, never the full variant, since the
    character already holds the rest and stating it again is the doubling this
    policy exists to remove.

    'declared' is what the ['font'] declaration explicitly says, and it can only
    ever cover REMAINDER axes: an axis some character carries is excluded from
    the declaration entirely (see 'wanted' below), because the entry's ['font']
    merges onto the atom whatever the value is (luarealchar.lua:636-641) and
    there is no way to take it back per position without the char-level ['font']
    table, which this policy does not use.

    NO VALUE EVER SAYS 'normal'.  The upright guard belongs to whichever code
    knows the ELEMENT, because that is what the guard is about: MathML slants a
    single-character <mi> by default and leaves <mo> and <mn> upright, so on an
    operator the guard says nothing.  The htf sees one position at a time and
    cannot know the element -- and something that can already does it:
    vtxml-mathml.lua:1127 adds mathvariant="normal" inside `if tag2 == 'mi'`,
    when the atom carries no font information.  Measured on the bbm corpus: 52
    such attributes, every one from the driver, none from here.

    Writing it here was worse than redundant.  An <mfont mathvariant="normal"> in
    the value sets the driver's has_mfont_variant, which SUPPRESSES its guard --
    so the htf was not adding information, it was taking the decision away from
    the code that knows the element and giving it to code that does not.  Over
    the 24 recorded fonts it accounted for 349 wrappers: 344 of them on
    characters that will never be a slanted <mi> at all, and stix-mathcal alone
    carried 126, which is why that font came out worse than the policy it
    replaces.

    Do not reinstate it behind a test for 'is the base a letter' or 'does an
    italic form exist in Unicode'.  Both are the htf guessing at what it cannot
    see, and the second is simply wrong: a font may carry a slanted cut Unicode
    never encoded -- which is the reason the .gpm record exists at all.

    The ['font'] DECLARATION may still say style=normal.  That is a different
    mechanism: it becomes CSS, stix-mathrm needs it to state uprightness
    font-wide, and it does not set has_mfont_variant, so it suppresses nothing.
    """
    pos, n = {}, {"compose": 0, "wrap": 0, "keep": 0}
    for gname, g in rec["glyphs"].items():
        if "pos" not in g or not g.get("htf_value"):
            continue
        eff = G.effective(rec, g)
        slots = [(g["pos"], g["slot"], g["htf_value"])] + \
                [(x["pos"], x["slot"], x["htf_value"]) for x in g.get("alt", [])
                 if x.get("htf_value")]
        slots = addressable_slots(rec, slots)
        base = g.get("base", G.UNKNOWN)
        ch, dropped = composed(gname, g)
        # What the character could not hold, minus whatever the declaration
        # states for the whole font.
        residue = {ax: eff[ax] for ax in dropped
                   if eff[ax] != "normal" and carried[ax] != eff[ax]}
        mv = G.mathvariant(residue)

        for p, slot, value in slots:
            if not G.has_base(g) or ch is None:
                act, out, m = "keep", None, []
            elif mv:
                act, out, m = "wrap", G.htf_value(ch, a.chars), mv
            else:
                act, out, m = "compose", G.htf_value(ch, a.chars), []
            n[act] += 1
            e = {"glyph": gname, "char_code": slot, "htf_value": value,
                 "base": base, "action": act, "wrap": act == "wrap",
                 "mathvariant": m, "carried": sorted(
                     ax for ax in G.AXES
                     if eff[ax] != "normal" and ax not in dropped)}
            if out is not None:
                # The finished value.  gpm_to_htf owns the policy, so the writer
                # substitutes this verbatim instead of rebuilding it from base +
                # mathvariant and having to know which policy produced the map.
                e["new_value"] = (f'<mfont mathvariant="{"-".join(m)}">{out}</mfont>'
                                  if act == "wrap" else out)
            pos[str(p)] = e
    return pos, n

def plan_attr(carried, declared):
    """Action per position under ATTRIBUTE FIRST -- the older policy.

    'declared' is what the declaration explicitly says, which is not the same
    as 'carried': an ABSENT style is not a declaration of normal (in maths it
    means slanted), so a glyph asserted upright must mark itself -- unless the
    declaration states style=normal, in which case it is already covered.
    """
    pos, n = {}, {"wrap": 0, "plain": 0, "keep": 0}
    for gname, g in rec["glyphs"].items():
        if "pos" not in g or not g.get("htf_value"):
            continue
        eff = G.effective(rec, g)
        # a glyph the encoding puts at several slots gets the same treatment at
        # each of them; only the guard value differs
        slots = [(g["pos"], g["slot"], g["htf_value"])] + \
                [(x["pos"], x["slot"], x["htf_value"]) for x in g.get("alt", [])
                 if x.get("htf_value")]
        slots = addressable_slots(rec, slots)
        base = g.get("base", G.UNKNOWN)
        needed = {ax: eff[ax] for ax in G.AXES if eff[ax] != carried[ax]}
        upright = (asserted_normal(g, "style")
                   and declared.get("style") != "normal")

        for p, slot, value in slots:
            if not G.has_base(g):
                act, mv = "keep", []
            elif needed or upright:
                # the mfont states the full effective variant, not just the
                # delta: a mathvariant token is a whole style, not a set of
                # switches.  Any non-empty variant already overrides the
                # default styling, so uprightness needs no extra marking;
                # where there is nothing else to say, "normal" says it.
                act, mv = "wrap", (G.mathvariant(eff) or ["normal"])
            else:
                # already covered -- but a precomposed variant character sitting
                # here would say it a second time, so reduce it to the base
                cur = G.to_chars(value)
                act = "plain" if (cur is not None and cur != base) else "keep"
                mv = []
            n[act] += 1
            pos[str(p)] = {"glyph": gname, "char_code": slot,
                           "htf_value": value, "base": base,
                           "action": act, "wrap": act == "wrap",
                           "mathvariant": mv}
    return pos, n

plan = plan_char if a.policy == "char" else plan_attr

def font_asserted(ax):
    return rec.get("status", {}).get(ax) in ASSERTED

# DEDUPLICATION.  Under character first, an axis that any character carries must
# not appear in the ['font'] declaration at all: the entry's declaration merges
# onto the atom whatever the value is (luarealchar.lua:636-641), so declaring
# variant=double-struck beside a value of U+1D538 applies double-struck twice,
# and there is no way to take it back per position -- the char-level ['font']
# table could, with axis=false, but this policy states the remainder in the value
# instead and never writes that table.
#
# Excluded if ANY position carries it, not if all do.  An axis is typically
# carried by a font's letters and left over on its operators (bbm composes its
# letters to double-struck alphanumerics while some of its operators have no
# double-struck character at all).  Declaring it would then be right for the
# operators and wrong for the letters; excluding it makes the operators state it
# per position, which is correct everywhere.
carried_anywhere = set()
if a.policy == "char" and not a.no_dedup:
    for _gname, _g in rec["glyphs"].items():
        if "pos" not in _g or not _g.get("htf_value") or not G.has_base(_g):
            continue
        _ch, _dropped = composed(_gname, _g)
        if _ch is None:
            continue
        _eff = G.effective(rec, _g)
        carried_anywhere |= {ax for ax in G.AXES
                             if _eff[ax] != "normal" and ax not in _dropped}

# The declaration the record says this font should carry: its font-level
# properties, minus the ones CSS cannot express (double-struck, fraktur,
# script), minus the ones the characters now carry, plus an asserted normal --
# stix-mathrm being upright IN a slanted context has to say so, and style=normal
# is something CSS can say.  An asserted style=normal survives the exclusion:
# 'normal' is not a property a character carries, it is the absence of one, so
# nothing can state it twice.
# An asserted normal counts as wanted, and so does one the CURRENT declaration
# already states: whoever wrote that htf entry was asserting it, and dropping it
# silently is how bbm lost its uprightness.  bbm is upright double-struck; the
# composed characters carry double-struck, so variant is excluded here, but
# 'normal' is the ABSENCE of a property and no character can carry it -- MathML
# slants a single-character <mi> by default, so if neither the declaration nor a
# value says 'normal', every one of bbm's 58 characters is slanted a second time.
# It came out as 'drop the declaration entirely, 0 wraps', which looked optimal
# and was wrong.
wanted = {ax: v for ax, v in truth.items()
          if G.declarable(ax, v)
          and (v != "normal" or font_asserted(ax) or htf_decl.get(ax) == v)
          and not (ax in carried_anywhere and v != "normal")}

# How to spell the same record.  Every SUBSET of the wanted declaration is a
# candidate, not just all-of-it or none-of-it: a font-level property the record
# holds may still be the wrong thing to declare.  stix-mathbbit-bold is bold by
# name, but the comparison found only 98 of its 242 glyphs actually bold, so
# declaring weight=bold makes the other 134 say mathvariant="normal" to escape
# it -- 198 wraps, against 108 for declaring style=normal alone.  Four axes
# means at most 16 subsets, so they are simply all tried.
# Every subset is drawn from the record, so all are true; only the CURRENT
# declaration can contradict it, and then keeping it is not an option.
def subsets(d):
    axes = [ax for ax in G.AXES if ax in d]
    for k in range(len(axes) + 1):
        for combo in itertools.combinations(axes, k):
            yield {ax: d[ax] for ax in combo}

def churn(declared):                       # how far this moves the htf
    return sum(1 for ax in G.AXES if declared.get(ax) != htf_decl.get(ax))

def label(declared):
    if declared == htf_decl:
        return "keep"
    return "drop" if not declared else "write"

# Why KEEPING the current declaration can be ruled out.  Two reasons, and the
# second was missing: the deduplication above filters the candidates DRAWN FROM
# THE RECORD, but 'keep' is drawn from htf_data.lua and slipped past it.  With
# equal wrap counts the least-churn tie-break then chose it, so bbm came out with
# 47 composed double-struck characters AND a variant=double-struck declaration --
# the doubling this policy exists to remove, reported in the same breath as
# "characters carry variant".
doubled = ({ax: v for ax, v in htf_decl.items()
            if ax in carried_anywhere and v != "normal"}
           if a.policy == "char" else {})
keep_why = None
if wrong:
    keep_why = ("the declaration states "
                + ", ".join(f"{k}={v}" for k, v in wrong.items())
                + ", which the record contradicts")
elif doubled:
    keep_why = ("the declaration states "
                + ", ".join(f"{k}={v}" for k, v in doubled.items())
                + ", which the characters now carry themselves -- keeping it "
                  "would apply the property twice")
candidates = [(htf_decl, keep_why)]
candidates += [(d, None) for d in subsets(wanted) if d != htf_decl]
# 'wanted' has the carried axes filtered out, so every subset of it is safe; the
# only unsafe candidate was 'keep', ruled out above.

plans = []
for declared, invalid in candidates:
    carried = {ax: declared.get(ax, "normal") for ax in G.AXES}
    p, n_ = plan(carried, declared)
    plans.append({"declared": declared, "invalid": invalid, "pos": p, "n": n_,
                  "wraps": n_["wrap"], "how": label(declared)})

if a.keep_decl and a.drop_decl:
    sys.exit("gpm_to_htf: --keep-decl and --drop-decl are mutually exclusive")
forced = "keep" if a.keep_decl else ("drop" if a.drop_decl else None)
if forced:
    # Selected by WHAT THE DECLARATION IS, not by the label.  label() calls a
    # candidate 'keep' whenever it equals the current declaration, so for a font
    # whose declaration is already empty -- stix-mathbb-bold, and every stix
    # entry that owns its chars -- the empty candidate is labelled 'keep' and
    # nothing is labelled 'drop'.  Asking for the label raised StopIteration, and
    # a regeneration loop that swallowed stderr left exactly that font holding
    # its previous map: the weight=bold declaration over 112 glyphs the raster
    # comparison found NOT bold, which is the case --drop-decl exists to avoid.
    if forced == "drop":
        want_it = lambda p: not p["declared"]
    else:
        want_it = lambda p: p["declared"] == htf_decl
    best = next((p for p in plans if want_it(p)), None)
    if best is None:
        sys.exit(f"gpm_to_htf: no --{forced}-decl spelling available for "
                 f"'{a.font}' (declaration now: {htf_decl or '(none)'})")
    why = "forced"
else:
    usable = [p for p in plans if p["invalid"] is None]
    # fewest wraps; on a tie the spelling that disturbs the htf least
    best = min(usable, key=lambda p: (p["wraps"], churn(p["declared"])))
    shown = sorted(usable, key=lambda p: (p["wraps"], churn(p["declared"])))[:3]
    why = "  ".join(f"{p['how']}{p['declared'] or '{}'}={p['wraps']}" for p in shown)
    ruled = next((p["invalid"] for p in plans if p["invalid"]), None)
    if ruled:
        why += f"  (keep ruled out: {ruled})"

how, pos, n, decl_wanted = best["how"], best["pos"], best["n"], best["declared"]
drop = how == "drop"
mv_font = G.mathvariant(decl)
bad = sorted({"-".join(p["mathvariant"]) for p in pos.values()
              if p["mathvariant"] and not G.mv_valid("-".join(p["mathvariant"]))})
# Positions whose htf value spells a size cut of a stretchy symbol as
# character + variation selector.  The selector is deliberately NOT emitted
# here -- MathJax does not reliably honour it, wide accents least of all -- but
# it stays in the record's ['uni'], which is what glyphs2u emits.
dropped_sel = [p for p in pos.values()
               if p["action"] != "keep"
               and G.split_selectors(G.to_chars(p["htf_value"]) or "")[1]]

G.save({"font": a.font, "source": "gpm", "authoritative": True,
        "policy": a.policy,
        # The entry to REWRITE, which need not be named after this font:
        # bbm10 has none of its own and is served by 'bbm' through the
        # largest-prefix rule, so the positions belong in 'bbm'.
        "htf_entry": entry, "htf_owner": owner,
        "by_prefix": by_prefix, "alias_must_go": aliased,
        "decl_action": how,          # keep | write | drop
        "decl": htf_decl,            # what htf_data.lua says now
        "decl_wanted": decl_wanted,  # what it should say ({} = no declaration)
        "drop_decl": drop, "font_props": rec.get("props", {}),
        "mathvariant": mv_font, "counts": n, "positions": pos}, out)

verb = {"keep": "keep", "write": "write", "drop": "drop"}[how]
if by_prefix:
    print(f"  NOTE: no htf entry is named '{rec['font']}' -- it is served by "
          f"'{entry}' through the largest-prefix rule, and that is the entry "
          f"these positions belong in.  Writing one named '{rec['font']}' would "
          f"serve this tfm alone and leave the other sizes of this cut reading "
          f"the old table.")
if aliased:
    print(f"  NOTE: this font has no ['chars'] of its own -- it aliases "
          f"'{owner}'.  Writing these positions means giving it its own entry and "
          f"REMOVING the alias: luarealchar.lua reads alias and chars "
          f"exclusively, so an entry with both ignores its chars.  The "
          f"largest-prefix rule still reaches '{owner}' for whatever this font "
          f"does not define.")
print(f"gpm_to_htf: {out}  {verb} declaration: {htf_decl or '(none)'}"
      + (f" -> {decl_wanted or '(none)'}" if how != "keep" else "")
      + f"   [wraps: {why}]")

# Properties true of the whole font that the declaration does not state.  Some
# could be stated (CSS has them) and would save a wrap on every glyph; the rest
# never can, and stay per-glyph however economical one wants to be.
def font_asserted(ax):
    return rec.get("status", {}).get(ax) in ASSERTED

# An asserted normal counts here too: stating style=normal font-wide is what
# stix-mathrm needs, and CSS can say it, so one declaration would spare every
# position an <mfont mathvariant="normal">.
# An ABSENT declaration is not a declaration of normal -- in maths, saying
# nothing means slanted.  So compare against what the declaration explicitly
# says (None when it says nothing at all).
missing = {ax: v for ax, v in truth.items()
           if htf_decl.get(ax) != v and (v != "normal" or font_asserted(ax))}
can = {ax: v for ax, v in missing.items() if G.declarable(ax, v)}
cannot = {ax: v for ax, v in missing.items() if not G.declarable(ax, v)}
if can:
    print("  declaring " + ", ".join(f"{k}={v}" for k, v in can.items())
          + f" in the htf would carry it for all {len(pos)} position(s)")
if cannot:
    print("  " + ", ".join(f"{k}={v}" for k, v in cannot.items())
          + " cannot be an htf ['font'] declaration (CSS has no such family) "
            "-- it stays per-glyph")
print("  " + "  ".join(f"{k}={v}" for k, v in n.items())
      + f"   [policy: {a.policy}]")
if skipped_unaddressable:
    _r = rec.get("tfm_range", {})
    print(f"  {skipped_unaddressable} position(s) SKIPPED as unreachable: the tfm "
          f"defines {_r.get('bc')}..{_r.get('ec')} and these fall outside it, so "
          f"nothing could ever ask for a value there")
if a.policy == "char" and carried_anywhere:
    print("  characters carry " + ", ".join(sorted(carried_anywhere))
          + " -- excluded from the ['font'] declaration so it cannot state "
            "them a second time")
if dropped_sel:
    print(f"  {len(dropped_sel)} position(s) lose a variation selector (the "
          f"stretchy size cut); it stays in the record for glyphs2u, e.g. "
          + ", ".join(f"{p['glyph']}" for p in dropped_sel[:3]))
if bad:
    print(f"  WARNING no MathML token for: {', '.join(bad)} -- check the "
          f"font-level properties in {gpm}")
print(f"  apply with: htf_mfont_apply.py --cmp {out}"
      + (" --drop-decl" if drop else ""))
