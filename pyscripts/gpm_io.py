#!/usr/bin/env python3
"""Shared reading/writing and derivation logic for the glyph property map
(<font>.gpm.json) -- the amalgamated per-font record both projects derive from.

THE RECORD
  A .gpm.json is keyed by GLYPH NAME (the key glyphs2u uses); the encoding
  position is carried along because the htf side needs it.  Font properties are
  kept SPLIT APART, one axis per key, so each axis can be filled -- and
  confirmed -- by its own method: 'weight' by comparing a font pair's rasters,
  'family'/'style' by looking at the glyph, others by the unicode already
  assigned.

    { "font": "stix-mathcal-bold", "pfb": ..., "enc": ..., "htf": ...,
      "props":  {"weight": "bold"},          <- font-level (the htf ['font'] decl)
      "status": {"weight": "decl"},
      "glyphs": {
        "uniE22D": { "slot": 0, "pos": 1, "htf_value": "&#x1D4D0;",
                     "base": "A",
                     "props":  {"family": "script", "weight": "normal"},
                     "status": {"base": "unicode", "family": "unicode",
                                "weight": "cmp"} } } }

  An axis missing from a glyph's "props" is simply not determined yet; the
  glyph then inherits the font-level value.  CHAR-SPECIFIC WINS over
  font-general -- both are kept, so the htf output step can pick whichever
  encoding is more economic.  base == "?" marks a glyph still to be recognised
  (the analogue of glyphs2u's 0xFFFD sentinel).

DERIVATIONS (never stored, always computed)
  mathvariant  = canonical MathML token list for the effective non-normal axes
  glyphs2u     = explicit ['uni'] if set, else the precomposed variant char from
                 base_to_variants, else the base's own codepoints
  htf          = <mfont mathvariant="...">base</mfont>, minus whatever the
                 font-level declaration already carries

STATUS (provenance of a value, and what may overwrite it)
  "?"        not determined            "decl"     the htf ['font'] declaration
  "unicode"  from the codepoint        "lua"      from a glyphs2u table
  "cmp"      font-pair raster compare  "visual"   confirmed in gpm_edit
  "name"     the font's own glyph name "sibling"  carried from the paired font
  "manual"   hand-edited
  Automatic steps refuse to overwrite "visual"/"manual"/"name"; they report
  instead.  "sibling" is deliberately NOT among those: it is an inference from
  the paired font, not an observation of this one, so anything that looks at
  this font may overrule it.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)          # the project: standards-derived data
# Tree-derived maps live under the BRANCH, $(project_dir)/$(TL_BRANCH), which the
# makefiles export as data_dir.  Falls back to the project root so a script run
# by hand still works, and load_map searches both -- Unicode data (which no
# branch varies) stays at the root while psfonts/htf maps sit under the branch,
# and a single --data has to serve callers that want either.
DATA = os.environ.get("data_dir") or ROOT
sys.path.insert(0, HERE)
# The canonical property-set -> MathML token-list mapping already used to build
# char_to_properties.json; reused so both directions stay in step.
from unicode_name_mathvariant import get_mathvariant

# --- axes -------------------------------------------------------------------
# The four axes of the htf ['font'] declaration.  "normal" is the neutral value
# of every axis and contributes no mathvariant token.
AXES = ("family", "weight", "variant", "style")

# --- the weight axis is a SCALE, not two states ------------------------------
# CSS numbers it 100..900 and names three of the steps -- 300 light, 400 normal,
# 700 bold -- and the htf tree already writes numbers for the rest: Palatino
# Black 900, Palatino Light 200, Bookman Demi and AvantGarde Demi 500,
# AvantGarde Book 300.  Family names for the steps ('demibold', 'semibold',
# 'black', 'heavy') are deliberately absent: they are family-local, and two
# foundries' "Demi" are not the same weight -- Bookman's and AvantGarde's are
# declared 500 where the CSS table puts Demi Bold at 600.  Not one such name
# appears in htf_data; the weights there are only bold, light and numbers.
#
# Every spelling that can reach a record, for lookup and for ordering.
WEIGHT_NUMBER = {"100": 100, "200": 200, "300": 300, "light": 300,
                 "400": 400, "normal": 400, "500": 500, "600": 600,
                 "700": 700, "bold": 700, "800": 800, "900": 900}
# What the editor and gpm_set offer: ONE spelling per step, so a record never
# has two ways to say the same thing -- the CSS name where CSS gives one, the
# number otherwise.  Ascending, so this doubles as the ordering a comparison
# ladder needs: a pair relates NEIGHBOURING steps, which only means something on
# a scale.  ('300'/'400'/'700' are reachable by lookup but not offered here;
# they are spelled light/normal/bold.)
WEIGHT_STEPS = ("100", "200", "light", "normal", "500", "600", "bold",
                "800", "900")
# MathML has exactly one heaviness, so this is where the scale collapses.  600
# rather than CSS's own 700 for the `bold` keyword: a 600 face is visibly
# heavier, so a raster comparison against the step below calls it 'differ' -- and
# a threshold of 700 would then record 'normal' for a glyph the comparison had
# just said was not, which is the kind of contradiction that costs an afternoon.
BOLD_FROM = 600

AXIS_VALUES = {
    "family":  ("normal", "sans-serif", "monospace", "script", "fraktur",
                "double-struck", "cursive"),
    "weight":  WEIGHT_STEPS,
    "variant": ("normal", "small-caps"),
    "style":   ("normal", "italic", "oblique"),
}
# Which axis a mathvariant token belongs to (inverse of the axis vocabulary).
TOKEN_AXIS = {v: ax for ax, vals in AXIS_VALUES.items() for v in vals if v != "normal"}
# What CSS spells one way and MathML another.  Both entries are LOSSY in the same
# direction and deliberately so, and they only ever apply to the per-symbol
# mathvariant -- the ['font'] declaration keeps the richer value, because it
# becomes CSS and CSS has the distinction.
#
#   cursive -> script    the script family's two names.
#   oblique -> italic    MathML has one slanted token.  CSS distinguishes an
#       oblique (an upright face slanted by the renderer) from an italic (a face
#       drawn separately), and the htf declaration keeps that -- 'oblique' is in
#       DECLARABLE below for exactly that reason.  A mathvariant cannot: its
#       vocabulary has 'italic' and nothing else, so an unaliased 'oblique' came
#       out as the non-token 'oblique' and, for a sans-serif oblique cut, as
#       'oblique-sans-serif'.  116 positions over bbmsl and bbmssi, the only
#       oblique cuts recorded, and the whole of what MathML could not name.
#       Aliased, they read 'italic' and 'sans-serif-italic', both conforming.
#
# This is the same collapse mv_weight already makes for the weight scale, and for
# the same reason: the declaration carries what CSS can use, the mathvariant what
# MathML can say.
TOKEN_ALIAS = {"cursive": "script", "oblique": "italic"}
# What an htf ['font'] declaration can actually say: it becomes CSS, so it
# reaches only the properties CSS has.  'double-struck', 'fraktur' and 'script'
# are not among them (the htf tree uses family=monospace/sans-serif/cursive/
# serif/fantasy and nothing else), so a font whose glyphs are double-struck
# cannot state that font-wide -- it has to go into each glyph's mathvariant.
DECLARABLE = {
    "family":  {"sans-serif", "monospace", "cursive", "serif", "fantasy"},
    # CSS takes the whole scale, by name or by number, so a declaration may use
    # any spelling -- this validates what htf_data holds, not what we write.
    "weight":  set(WEIGHT_NUMBER),
    "variant": {"small-caps"},
    "style":   {"italic", "oblique", "normal"},
}

def declarable(axis, value):
    return value == "normal" or value in DECLARABLE.get(axis, ())
# The MathML 3 mathvariant vocabulary, for flagging combinations that have no
# valid token (e.g. a font declaring variant=small-caps whose letters are
# really family=script -- the record shows it instead of hiding it).
MATHML_VARIANTS = {
    "normal", "bold", "italic", "bold-italic", "double-struck", "bold-fraktur",
    "script", "bold-script", "fraktur", "sans-serif", "bold-sans-serif",
    "sans-serif-italic", "sans-serif-bold-italic", "monospace",
    # not MathML, but established in this pipeline for the small-caps fonts
    "small-caps", "bold-small-caps",
}

# Families Unicode draws SLANTED, so choosing one of their characters already
# satisfies a style=italic property and stating it again in a mathvariant is
# redundant -- it asks a renderer to slant a glyph that is drawn slanted.
#
# 'script' is the case that matters, and it covers both \mathcal and \mathscr:
# they land in U+1D49C..U+1D4CF plus the letterlike holes reserved out of that
# block (U+212C SCRIPT CAPITAL B, U+2130 E, U+2131 F, U+210B H, U+2110 I,
# U+2112 L, U+2133 M, U+211B R, U+212F small e, U+210A small g, U+2134 small o),
# and every one of them is decomposed as family=script by the variants table, so
# the holes need no special case here.
#
# Not universal: euler's script cut is close to upright.  But MathML has no
# token for "upright script" to state that difference with -- 'script' is the
# whole vocabulary -- so the slant is taken as given rather than asserted per
# font.  fraktur, double-struck and monospace are deliberately NOT here: those
# are upright designs, and dropping a style=italic against them would lose a
# real property.
SLANTED_FAMILIES = ("script",)

def slanted_by_design(char, var):
    """True if any character of 'char' is drawn slanted by its own family."""
    for c in char:
        _base, props = var.decompose(c)
        if props.get("family") in SLANTED_FAMILIES:
            return True
    return False

# --- what the font can actually be asked for ---------------------------------
# A .pfb names glyphs at whatever slots its own encoding lists, but TeX reaches a
# character through the METRICS: no entry in the tfm, no character.  So the tfm's
# bc and ec -- the first and last character code it defines -- bound what any of
# this can address, and a position outside them is unreachable however real the
# outline is.
#
# That is the whole of Computer Modern's 7-bit design, stated by the fonts
# themselves: every cm tfm here reads bc=0 ec=127, while the .pfb encodings run
# to slot 164.  The 35 duplicate Greek capitals cmr10 carries at 161.. are the
# designer's, not TeX's.
#
# Two 16-bit big-endian words at byte 4, because the tfm begins lf, lh, bc, ec.
# Checked against tftopl on cmr10: header says 0..127, tftopl lists 128
# CHARACTER entries, O 0 through O 177.
def tfm_range(font, prefix=None):
    """(bc, ec) from <font>.tfm, or None when there is no tfm to ask.

    None is a real answer and must stay quiet: a font loaded by name through
    luaotfload has no tfm at all, and warning about every slot of it would be
    noise, not a finding.
    """
    import struct, subprocess
    # The tree is whichever kpsewhich this project is pointed at; `prefix'
    # survives for a caller that must wrap the call in something.
    kpse = os.environ.get("KPSEWHICH", "kpsewhich")
    for cmd in (list(prefix) + [kpse, font + ".tfm"] if prefix else [kpse, font + ".tfm"],
                [kpse, font + ".tfm"]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True).stdout
        except OSError:
            continue
        for line in out.splitlines():
            line = line.strip()
            if line and os.path.exists(line):
                try:
                    with open(line, "rb") as f:
                        head = f.read(8)
                    if len(head) < 8:
                        return None
                    _lf, _lh, bc, ec = struct.unpack(">4H", head)
                except (OSError, struct.error):
                    return None
                return (bc, ec) if bc <= ec else None
    return None

def addressable(rec, slot):
    """Is this encoding slot one the tfm defines?

    True when the record carries no range, so a record seeded before this was
    recorded behaves exactly as it did -- the filter is inert rather than
    silently dropping positions nobody has looked at.
    """
    r = rec.get("tfm_range")
    if not r:
        return True
    return r.get("bc", 0) <= slot <= r.get("ec", 0xFFFF)

UNKNOWN = "?"                          # base sentinel
# Values another step must not overwrite.  "name" is here because the font's own
# glyph name is evidence the codepoint cannot contradict: u1D55A decomposes to
# 'i' whatever its name says, so a rerun of the unicode step would silently undo
# u1D55A.dtls -> 'ı'.  A step may always refresh a value IT set (same status);
# what it may not do is overturn another method's finding.
CONFIRMED = ("name", "visual", "manual")

# --- json io ----------------------------------------------------------------
def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

# The order a glyph's keys are written in: where it sits, what it is, what is
# known about it.  Any step may add a key (gpm_names writes 'uni' onto a glyph
# that had none), so the order is imposed here rather than at each writer, and
# a record stays diffable however it was filled.
GLYPH_KEYS = ("slot", "pos", "htf_value", "alt", "base", "uni", "rename",
              "props", "status")

# --- the write lock ----------------------------------------------------------
# gpm_edit holds the whole record in memory and rewrites all of it on every
# click, so anything else that writes while a window is open is lost the moment
# the next click lands.  That was survivable while `make edit-...` blocked the
# terminal; it is not now that the editor is started detached.
#
# flock on a SIDECAR file, not on the record: save() replaces the record through
# a temp file, so a lock held on the old inode would mean nothing afterwards.
# The sidecar's inode is stable, and the kernel drops the lock when the holder
# dies -- no stale lock to clear by hand, which is the whole reason for using
# flock rather than a pid file.
try:
    import fcntl
except ImportError:                        # Windows: no flock, so no lock
    fcntl = None

_held = {}                                 # lock path -> fd this process owns

def lock_path(path):
    return path + ".lock"

def _open_lock(path):
    fd = os.open(lock_path(path), os.O_CREAT | os.O_RDWR, 0o644)
    return fd

def _holder(path):
    """Whatever the holder wrote about itself, for the message."""
    try:
        with open(lock_path(path), encoding="utf-8") as f:
            return f.read().strip() or "another process"
    except OSError:
        return "another process"

def hold(path, who="gpm_edit"):
    """Take the lock for as long as this process lives.  True if we got it.

    For the interactive editor: it keeps the record open across many saves, so
    it holds the lock the whole time instead of taking it per write.
    """
    if fcntl is None:
        return True
    fd = _open_lock(path)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return False
    os.truncate(fd, 0)
    os.write(fd, f"{who} pid {os.getpid()}\n".encode())
    _held[lock_path(path)] = fd            # kept open on purpose: closing unlocks
    return True

def save(rec, path):
    """Atomic write, so an interrupted editor never truncates the record.

    Refuses -- loudly, rather than losing the other side's work -- while someone
    else holds the write lock.  A process that already holds it (the editor)
    writes straight through.
    """
    if fcntl is not None and lock_path(path) not in _held:
        fd = _open_lock(path)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                sys.exit(f"gpm: {path} is locked by {_holder(path)} -- close it "
                         f"(or wait) rather than have one overwrite the other")
            _write(rec, path)
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
    else:
        _write(rec, path)

def _write(rec, path):
    for name, g in rec.get("glyphs", {}).items():
        rec["glyphs"][name] = {k: g[k] for k in GLYPH_KEYS if k in g} | \
                              {k: v for k, v in g.items() if k not in GLYPH_KEYS}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)

def map_path(name, data=DATA):
    """Where a generated map is, searching the branch dir and then the project.

    Tree-derived maps moved under $(TL_BRANCH); standards-derived ones did not.
    Both are reached through a single --data, so look in the given directory and
    fall back to the project root.  A name found in neither is returned as-is,
    so the caller's error names the directory it was asked for.
    """
    cands = [os.path.join(data, name), os.path.join(ROOT, name)]
    # Run by hand, without data_dir in the environment, both candidates are the
    # project root -- and a tree-derived map is not there any more.  So also try
    # the branch directories, which are the numeric ones beside the project's
    # own data.  One of them is the ordinary case; several is a genuine question
    # (which branch?) that the caller should answer with --data, so say so.
    if not os.environ.get("data_dir"):
        try:
            branches = sorted(d for d in os.listdir(ROOT)
                              if d.isdigit() and os.path.isdir(os.path.join(ROOT, d)))
        except OSError:
            branches = []
        hits = [os.path.join(ROOT, b, name) for b in branches
                if os.path.exists(os.path.join(ROOT, b, name))]
        if len(hits) > 1:
            print(f"gpm: {name} exists for branches {branches} -- taking "
                  f"{os.path.basename(os.path.dirname(hits[0]))}; pass --data to "
                  f"choose", file=sys.stderr)
        cands[1:1] = hits
    for c in cands:
        if os.path.exists(c):
            return c
    return cands[0]                    # keep the asked-for path for the error

def load_map(name, data=DATA):
    return load(map_path(name, data))

def enc_json_for(font, data=DATA):
    """Which json holds this font's slot -> glyph name mapping.

    psfonts.map names an .enc for most fonts (-> <enc>.enc.json, from the
    encoding vector); the rest are used with the encoding built into the pfb,
    which fontforge exports to <font>.pfb.enc.json.  Getting this wrong would
    silently put every glyph at the wrong position, so it follows the map
    rather than whichever file happens to be lying about.
    """
    try:
        enc = load_map("psfonts-map-tfm-data.json", data).get(font, {}).get("enc")
    except FileNotFoundError:
        enc = None
    return os.path.basename(enc) + ".json" if enc else f"{font}.pfb.enc.json"

# --- values -----------------------------------------------------------------
def to_cp(v):
    """'&#x2B32;' / '&#123;' / '&gt;' / a single char -> codepoint; else None."""
    if not v:
        return None
    m = re.fullmatch(r'&#x([0-9A-Fa-f]+);', v)
    if m: return int(m.group(1), 16)
    m = re.fullmatch(r'&#(\d+);', v)
    if m: return int(m.group(1))
    m = re.fullmatch(r'&([A-Za-z][A-Za-z0-9]*);', v)
    if m:
        ch = named_entity(m.group(1))
        return ord(ch) if ch and len(ch) == 1 else None
    return ord(v) if len(v) == 1 else None

def to_char(v):
    cp = to_cp(v)
    return chr(cp) if cp is not None else None

def is_selector(cp):
    """A variation selector (U+FE00..U+FE0F, U+E0100..U+E01EF).

    Unicode spells the larger cuts of a stretchy symbol -- parentheses, braces,
    brackets, radicals, wide accents, big operators -- as the plain character
    plus one of these, which is how tex4ht's htf tables carry them.  It is a
    presentation size, not a different character: the BASE stays the plain
    character, and the full sequence is kept in the record's ['uni'], which is
    what the glyphs2u side emits.
    """
    return 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF

def split_selectors(s):
    """(character(s) without variation selectors, had any selector)."""
    core = "".join(c for c in s if not is_selector(ord(c)))
    return core, core != s

def is_pua(cp):
    """Private-use codepoints name nothing -- they are a font's internal slot
    number, not a character.  A value made of them carries no information about
    the glyph, whether it comes from an htf table or the builtin glyph list."""
    return 0xE000 <= cp <= 0xF8FF or 0xF0000 <= cp <= 0x10FFFD

# NAMED entities, not just numeric ones.  htf values spell '<' and '>' as
# '&lt;'/'&gt;' -- they have to, the value is markup -- and '&' as '&amp;';
# htf_data holds 753 such values.  Read as literal characters they decompose
# into '&','g','t',';', which is how stix-mathit-bold ended up with
# uni=[0x0026,0x0067,0x0074,0x003B] for the greater-than sign and a base of
# '&gt;'.  The five XML predefined names are built in; the rest come from
# mathml-entities.json (2237 of them, by_entity), loaded on first use so this
# module still works with no data dir.
XML_ENTITIES = {"lt": "<", "gt": ">", "amp": "&", "quot": '"', "apos": "'"}
_named = None

def named_entity(name, data=DATA):
    """'&<name>;' -> the character(s) it stands for, or None if unknown."""
    if name in XML_ENTITIES:
        return XML_ENTITIES[name]
    global _named
    if _named is None:
        try:
            _named = load_map("mathml-entities.json", data).get("by_entity", {})
        except (OSError, ValueError):
            _named = {}
    cps = _named.get(name)
    return "".join(chr(int(c, 16)) for c in cps.split()) if cps else None

ENTITY = re.compile(r'&#x([0-9A-Fa-f]+);|&#(\d+);|&([A-Za-z][A-Za-z0-9]*);|(.)',
                    re.S)

def to_chars(v):
    """Decode a whole htf value into a string: entities, bare characters, or a
    mix -- '&#x222B;&#xFE01;' is INTEGRAL + VARIATION SELECTOR-2, one glyph
    spelled with two codepoints (as glyphs2u tables also spell them).
    Returns None if the value is markup rather than characters, or if it uses a
    named entity nothing here knows -- inventing codepoints from the letters of
    the name is worse than saying nothing, which is the bug this once had."""
    if not v or "<" in v:
        return None
    out = []
    for hx, dec, name, lit in ENTITY.findall(v):
        if hx:
            out.append(chr(int(hx, 16)))
        elif dec:
            out.append(chr(int(dec)))
        elif name:
            ch = named_entity(name)
            if ch is None:
                return None               # unknown name: say nothing, not nonsense
            out.append(ch)
        elif lit:
            out.append(lit)
    return "".join(out) or None

def entity(s):
    """ASCII kept as-is, everything else as a hex character reference."""
    return "".join(c if ord(c) < 128 else f"&#x{ord(c):04X};" for c in s)

_MFONT = re.compile(r'<mfont mathvariant="([^"]*)">(.*)</mfont>\Z', re.S)

def value_key(v):
    """An htf ['value'] reduced to what it MEANS: (mathvariant token, characters).

    Two values that say the same thing can be spelled differently -- '&#x2124;'
    and 'Z-double-struck' are one character, and htf_value writes either
    depending on --chars -- so comparing the strings answers a question about
    notation instead of about content.  It cost the alias decision: bbm written
    with --chars against bbmbx written without reported 11 of 58 values as
    differing, all of them the BMP characters, and concluded that bbmbx needed
    its own 243-line table where a 9-line ['alias'] says everything.

    Returns (None, None) for a value that is neither characters nor a single
    mfont around characters, so an unrecognised spelling never compares EQUAL to
    something else by accident.
    """
    if v is None:
        return (None, None)
    mv = ""
    m = _MFONT.match(v.strip())
    if m:
        mv, v = m.group(1), m.group(2)
    ch = to_chars(v)
    return (mv, ch) if ch is not None else (None, None)

def same_value(a, b):
    """Do two htf values say the same thing, whatever the spelling?"""
    ka, kb = value_key(a), value_key(b)
    return ka == kb if ka != (None, None) else a == b

def htf_value(s, raw=False):
    """A character sequence as an htf ['value'], spelled so luarealchar reads it
    as CHARACTERS rather than as a string.

    ASCII as-is, U+0100..U+FFFF as a 4-hex entity, and anything above U+FFFF
    RAW UTF-8.  The last part is not a style choice.  luarealstring.lua:679 turns
    a value into a character with

        string.gsub(hchar, "^&#x(....);$", ...)

    where (....) is exactly FOUR characters, so '&#x2124;' becomes U+2124 and
    takes the codepoint path, while '&#x1D538;' matches nothing, stays a
    nine-character string, and falls to 'char_dt.char = hchar' -- the path meant
    for a value spelling a SEQUENCE.  Every Mathematical Alphanumeric is five hex
    digits, so composing properties into characters would put almost every value
    on that path.  Checked with texlua: '&#x2124;' -> len 1, cp 0x2124;
    '&#x1D538;' -> len 9, string; raw 'Z-double-struck' -> len 1, cp 0x1D538.

    Below U+10000 the entity is kept by default, because it is the existing
    convention in htf_data.lua and it already reads correctly -- there is nothing
    to gain from rewriting 56 working values into raw characters in a file a
    colleague owns.

    raw=True spells EVERY non-ASCII character as itself, entities included, for a
    table that is wholly composed and reads better as characters than as a mix of
    the two: bbm's 58 values came out as 47 characters and 11 hex numbers for no
    reason a reader could see.  Both forms take the same codepoint path in
    luarealstring, so this is legibility, not behaviour.
    """
    if raw:
        return s
    return "".join(c if ord(c) < 128
                   else (f"&#x{ord(c):04X};" if ord(c) <= 0xFFFF else c)
                   for c in s)

# --- effective properties ---------------------------------------------------
def effective(rec, g):
    """Font-level props overlaid by the glyph's own -- char-specific wins."""
    props = dict(rec.get("props", {}))
    props.update(g.get("props", {}))
    return {ax: props.get(ax, "normal") for ax in AXES}

def determined(rec, g, axis):
    """Is this axis settled for this glyph (by itself or by the font level)?"""
    return axis in g.get("props", {}) or axis in rec.get("props", {})

def unset_axes(rec, g):
    return [ax for ax in AXES if not determined(rec, g, ax)]

def parse_positions(spec):
    """'24', '20-30', '24,61,63', '20-30,82' -> a set of htf positions.

    Positions, not glyph names: the review pages and the comparison page are
    both indexed by them, so a reader working from a page names what they saw.
    """
    out = set()
    for part in str(spec).replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part[1:]:
            lo, _, hi = part.partition("-")
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return out

def glyphs_at(rec, positions):
    """Glyph names sitting at those positions, including 'alt' extra slots."""
    hit = []
    for gname, g in rec.get("glyphs", {}).items():
        if g.get("pos") in positions:
            hit.append(gname)
        elif any(a.get("pos") in positions for a in g.get("alt") or ()):
            hit.append(gname)
    return sorted(hit, key=lambda n: rec["glyphs"][n].get("pos", 1 << 30))

def has_base(g):
    """Is this glyph's base settled?

    NOT `base != UNKNOWN`.  UNKNOWN is the string "?", and QUESTION MARK is a
    real character a font can hold: stix-mathrm-bold's 'question' glyph has an
    htf value of exactly '?', so its base and the not-determined sentinel are the
    same three bytes.  What tells them apart is the PROVENANCE -- an undetermined
    base carries status "?" as well, a determined one names the step that set it.

    The fallback on the value is for records written before the status was kept
    for every base: there, a non-empty base that is not "?" still counts.
    """
    st = g.get("status", {})
    if st.get("base", UNKNOWN) != UNKNOWN:
        return True
    b = g.get("base")
    return bool(b) and b != UNKNOWN

def is_open(rec, g):
    """Still needs work: the glyph has not been recognised.

    An axis nobody has spoken about is NOT open work -- it defaults to the
    font-level value, and to 'normal' below that.  Asking about every axis of
    every glyph would mean confirming that an integral sign is not small-caps.
    What IS an open question is a font-level axis nothing has settled: stix-mathsf
    declares no family, yet the whole font is sans-serif.  See font_open_axes.
    """
    return not has_base(g)

def font_open_axes(rec):
    """Font-level axes still unanswered -- the editor's first screen."""
    st = rec.get("status", {})
    return [ax for ax in AXES if st.get(ax, UNKNOWN) == UNKNOWN]

def weight_number(value):
    """A weight axis value as its CSS number, or None if it names no step."""
    return WEIGHT_NUMBER.get(value)

def mv_weight(value):
    """The weight as MathML can state it: 'bold' from BOLD_FROM up, else nothing.

    The lossy step of the whole derivation, and deliberately the only one: the
    htf ['font'] declaration keeps the number, because it becomes CSS and CSS has
    the whole scale.  Only the per-symbol mathvariant has to choose.
    """
    n = WEIGHT_NUMBER.get(value)
    return "bold" if n is not None and n >= BOLD_FROM else None

def mathvariant(props):
    """Effective axis values -> canonical MathML token list (may be empty)."""
    toks = []
    for ax in AXES:
        v = props.get(ax)
        if not v or v == "normal":
            continue
        if ax == "weight":
            v = mv_weight(v)          # a scale, collapsed to the one MathML step
            if not v:
                continue              # lighter than bold: MathML says nothing
        toks.append(TOKEN_ALIAS.get(v, v))
    return get_mathvariant(toks) if toks else []

def mv_token(props):
    return "-".join(mathvariant(props))

def mv_valid(token):
    """False for a property combination MathML has no token for."""
    return (not token) or token in MATHML_VARIANTS

# --- setting values ---------------------------------------------------------
def set_axis(g, axis, value, status, force=False):
    """Set one axis of one glyph.  Returns 'set' | 'same' | 'kept'.

    'kept' means the axis was already confirmed by eye or by hand and this
    (automatic) step is not allowed to overwrite it -- the caller reports it.
    """
    st = g.setdefault("status", {})
    old = g.get("props", {}).get(axis)
    if old == value:
        return "same"
    if st.get(axis) in CONFIRMED and st.get(axis) != status and not force:
        return "kept"
    g.setdefault("props", {})[axis] = value
    st[axis] = status
    return "set"

def char_at(g):
    """The character this position holds -- not its base.

    A variation selector applies to the character itself: uni27E6.s1 is U+27E6
    + FE01, though its base decomposes to '[' + double-struck, and recomposing
    from that lands on U+301A instead (two white square brackets share the
    base+variant key).  So take the htf value, minus any selector already
    there, and fall back to the base only when it says nothing.
    """
    cur, _ = split_selectors(to_chars(g.get("htf_value") or "") or "")
    if cur and not any(is_pua(ord(c)) for c in cur):
        return cur
    b = g.get("base")
    return b if has_base(g) and b else None

def set_uni(g, codes, status, force=False):
    """Set ['uni'], the explicit codepoint sequence the glyphs2u side emits.

    Not an axis: it is what to write when base+properties cannot say it -- a
    size cut spelled with a variation selector, or a composed sequence.  It
    gets a status entry of its own, so a value that arrived with the htf value
    can be told from one a later step worked out.
    """
    st = g.setdefault("status", {})
    if g.get("uni") == codes:
        st.setdefault("uni", status)       # same value, now with a provenance
        return "same"
    if st.get("uni") in CONFIRMED and st.get("uni") != status and not force:
        return "kept"
    g["uni"] = codes
    st["uni"] = status
    return "set"

def set_base(g, base, status, force=False):
    st = g.setdefault("status", {})
    if g.get("base") == base:
        # Record the provenance even when the value needs no change: a base that
        # happens to EQUAL the sentinel ('?', the question mark) would otherwise
        # keep status "?" for ever and read as undetermined -- which is exactly
        # what happened to stix-mathrm-bold's 'question' glyph.
        if st.get("base", UNKNOWN) == UNKNOWN:
            st["base"] = status
            return "set"
        return "same"
    if st.get("base") in CONFIRMED and st.get("base") != status and not force:
        return "kept"
    g["base"] = base
    st["base"] = status
    return "set"

# Which properties to KEEP when the whole combination has no character.  family
# and variant carry the character's identity -- Unicode gives double-struck,
# fraktur and script their own codepoints, and a bracket that loses
# 'double-struck' is a different bracket -- while weight and style are the axes
# the htf side still states in mathvariant and a renderer can synthesize.  So
# weight goes first, then style, and the identity axes are surrendered last.
#
# VARIANT outranks FAMILY, and that order is the answer to a real case rather
# than an accident of how the tuple was typed.  bbm is a blackboard-bold family
# whose sans and mono cuts are SHAPES WITHIN it: 'double-struck sans-serif' has
# no character, so one axis must go, and surrendering double-struck yielded
# U+1D5A0 MATHEMATICAL SANS-SERIF CAPITAL A wearing mathvariant="double-struck"
# -- a sans-serif character claiming to be double-struck, which is backwards.
# Double-struck is what bbm IS; the shape is what a cut of it looks like.  Keep
# the variant and the character stays 𝔸, the shape going to the attribute or
# being given up, which is what the family means.
#
# Only four fonts can tell the difference -- bbmss, bbmssi, bbmtt, bbmssb, the
# cuts holding a non-normal family AND a non-normal variant.  No stix font holds
# both, so this changes nothing there; checked over all 24 records.
KEEP_PRIORITY = ("variant", "family", "style", "weight")

def _keep_orders(axes):
    """Every subset of 'axes', best first.  The empty subset -- the base alone --
    comes last.

    Ordered by PRIORITY, not by how many properties a subset keeps: family is the
    most significant bit, so a subset holding a higher-priority axis beats every
    subset without it, however many lesser axes those hold.  Ranking by count
    first gets stix-mathbbit-bold wrong -- it is double-struck italic bold, no
    such character exists, and {style, weight} would win on size 2 and yield
    U+1D468 MATHEMATICAL BOLD ITALIC CAPITAL A, losing the double-struck identity
    that is the whole point of the font.  Priority first gives U+1D538
    MATHEMATICAL DOUBLE-STRUCK CAPITAL A, which is what glyphs2u publishes.
    Every subset is still tried, so bold-italic remains available as a fallback
    if no double-struck character existed at all.
    """
    rank = {ax: i for i, ax in enumerate(KEEP_PRIORITY)}
    top = len(KEEP_PRIORITY) - 1
    def significance(keep):
        return sum(1 << (top - rank.get(a, top)) for a in keep)
    subs = [[ax for i, ax in enumerate(axes) if mask >> i & 1]
            for mask in range(1 << len(axes))]
    subs.sort(key=significance, reverse=True)
    return subs

# --- derivations ------------------------------------------------------------
class Variants:
    """base_to_variants / char_to_properties, loaded once."""
    def __init__(self, data=DATA):
        self.b2v = load_map("base_to_variants.json", data)
        self.c2p = load_map("char_to_properties.json", data)
        try:
            self.dtls = load_map("dtls-policy.json", data)
        except (OSError, ValueError):
            self.dtls = None                # no policy file: derive as before

    def dtls_target(self, base, props):
        """(char, use, rename) for a dotless i/j cut; (None, None, None) if no
        policy applies.

        'rename' is the dot-free name the glyph must be published under, and it
        is set exactly when the policy chose a dotless target -- see
        '_about_rename' in the policy file.  It is part of the same decision as
        the codepoint, not an independent one, which is why it comes from here
        rather than from each record.

        Unicode has no double-struck, fraktur, monospace or sans-serif dotless i,
        so each of these glyphs must give up either the dot or the font view.
        Which one is a decision rather than a derivation, and it lives in
        dtls-policy.json -- see the '_about' in that file.  Nothing is written to
        the record: this runs during derivation, so the record keeps its own base
        and properties and the htf side still states them in full.
        """
        if not self.dtls or base not in ("ı", "ȷ"):
            return None, None, None
        # Match against the collapsed weight, not the literal one: weight is a
        # CSS scale here, so a rule saying 'bold' has to catch 700, 'black' and
        # 'heavy' too -- mv_weight is what decides which side of BOLD_FROM a
        # value falls on, and it is the same test the mathvariant token uses.
        cmpable = dict(props)
        cmpable["weight"] = mv_weight(props.get("weight")) or "normal"
        rule = next((r for r in self.dtls.get("rules", [])
                     if all(cmpable.get(ax, "normal") == v
                            for ax, v in r.get("when", {}).items())), None)
        use = rule["use"] if rule else self.dtls.get("default", "dotless")
        spec = self.dtls.get("targets", {}).get(use)
        if not spec:
            return None, None, None
        ren = spec.get("rename", {}).get(base)
        if spec.get("how") == "literal":
            return spec.get("char", {}).get(base), use, ren
        # 'compose': swap in the base the target wants -- 'i' for the letter with
        # its dot, 'ı' to stay dotless -- and go through the ordinary derivation,
        # so property degradation applies to it exactly as it would anywhere else.
        ch, _kept, _lost = self.best_variant(spec.get("base", {}).get(base, base),
                                             props)
        return ch, use, ren

    def variant_char(self, base, props):
        """The precomposed character for base+props, or None if Unicode has
        no such combination (the case that motivates the split-apart record)."""
        tok = mv_token(props)
        if not tok:
            return base
        return self.b2v.get(base, {}).get(tok)

    def best_variant(self, base, props):
        """As much of base+props as Unicode can express.

        Returns (char, kept, dropped).  When the whole combination has a
        character this is (that char, props, ()).  When it has not, the axes
        Unicode cannot express are dropped ONE AT A TIME rather than all at once,
        and 'dropped' names the ones given up.

        Dropping them all together is what produced a wrong character rather than
        an incomplete one: stix-mathfrak-bold's 'uni27EC' is a double-struck
        bracket in a bold font, so it asked for 'bold-double-struck'; Unicode has
        only 'double-struck' for U+3014, the lookup missed, and BOTH properties
        went -- leaving U+3014 itself, the black tortoise-shell bracket, in place
        of U+27EC, the white one.  A different character, not a plainer one.
        Keeping 'double-struck' and giving up only 'bold' yields U+27EC.
        """
        tok = mv_token(props)
        if not tok:
            return base, dict(props), ()
        table = self.b2v.get(base, {})
        ch = table.get(tok)
        if ch is not None:
            return ch, dict(props), ()
        live = [ax for ax in AXES if props.get(ax, "normal") != "normal"]
        for keep in _keep_orders(live):
            if len(keep) == len(live):
                continue                        # the full combination just missed
            trial = {ax: (props[ax] if ax in keep else "normal") for ax in AXES}
            t = mv_token(trial)
            if not t:                           # nothing recognisable left to ask
                break
            ch = table.get(t)
            if ch is not None:
                return ch, trial, tuple(ax for ax in live if ax not in keep)
        return base, {}, tuple(live)

    def decompose(self, char):
        """A precomposed char -> (base, {axis: value}); ({}, char) if plain."""
        info = self.c2p.get(char)
        if not info:
            return char, {}
        props = {}
        for t in info["mathvariant"]:
            ax = TOKEN_AXIS.get(t)
            if ax:
                props[ax] = t
        return info.get("base") or char, props

DTLS_CUT = ".dtls"          # the suffix a font puts on a dotless i/j cut

def uni_codes(rec, g, var, gname=None):
    """Codepoint list for the glyphs2u side, how it was obtained, what it cost.

    Returns (codes, kind, dropped):

      'override'  an explicit ['uni'] in the record, used verbatim
      'variant'   the whole property combination has a character
      'partial'   only part of it has: 'dropped' names the axes given up
      'dtls'      a dotless i/j cut, resolved by dtls-policy.json; 'dropped' is
                  ('dot',) when the policy kept the font view instead
      'base'      none of it has, so the base alone -- 'dropped' names them all
      'unknown'   no base yet; codes is empty

    'partial' is the case worth seeing: it means the character is right as far as
    it goes, and the axes in 'dropped' are the ones only the htf side can carry.

    'gname' is optional only so the two existing call sites keep working; the
    '.dtls' policy needs it, because the suffix is the font's own marker that a
    glyph is the dotless cut of a dotted letter.  It cannot be inferred from the
    base: stix-mathit's 'u1D6A4' and stix-mathrm's 'dotlessi' also have base 'ı'
    but ARE the dotless characters rather than cuts of a dotted one, and the
    policy must leave them alone.
    """
    if g.get("uni"):
        return [int(str(c), 16) if isinstance(c, str) else int(c)
                for c in g["uni"]], "override", ()
    base = g.get("base", UNKNOWN)
    if not has_base(g):
        return [], "unknown", ()
    props = effective(rec, g)
    if gname and DTLS_CUT in gname:
        ch, use, _ren = var.dtls_target(base, props)
        if ch:
            # 'dotted' surrendered the dot to keep the font view; the dotless
            # targets surrendered whatever the font view needed instead.
            lost = ("dot",) if use == "dotted" else ()
            return [ord(c) for c in ch], "dtls", lost
    ch, kept, lost = var.best_variant(base, props)
    codes = [ord(c) for c in ch]
    if not lost:
        return codes, ("variant" if mv_token(props) else "base"), ()
    return codes, ("partial" if mv_token(kept) else "base"), lost

def glyph_image(font, gname, slot=None):
    """Path to a picture of this glyph, or None.

    Two exports can supply one, and they are keyed differently:
      <font>/<glyphname>.png   fontforge (make <font>-glyphs.json) -- keyed by
                               name, exactly as the record is, and needing no
                               TeX run, so it is preferred;
      <font>.pos/NNN.png       dvipng of the .pos specimen (make <font>.pos.dvi)
                               -- keyed by position, which only lines up through
                               the slot+1 offset, but it is what the font-pair
                               comparison already produced.
    """
    p = os.path.join(font, gname + ".png")
    if os.path.exists(p):
        return p
    if slot is not None:
        p = f"{font}.pos/{slot + 1:03d}.png"
        if os.path.exists(p):
            return p
    return None

# --- htf_data.lua ------------------------------------------------------------
# The file the pipeline actually loads and that htf_mfont_apply rewrites, so it
# -- not htf_data.json, which is built from the .htf sources -- is what a record
# must be built from.  The two do drift: the .htf sources state their font in a
# CSS 'htfcss:' line that carries no axis, while htf_data.lua holds the ['font']
# declarations this project works with.
# The OVERLAY's copy, which is what mk/config.mk exports htf_path as.  The
# fallback matters as much as the variable: it is what a hand run outside make
# gets, and pointing it at the distribution meant such a run silently read and
# rewrote an installed file -- the thing the overlay exists to stop.  Missing an
# overlay that has not been seeded yet is the better failure: it names a file
# that is not there, instead of quietly working on the wrong one.  `make overlay`
# creates it.
HTF_DIR = (os.environ.get("htf_path") or DATA)
HTF_LUA = os.path.join(HTF_DIR, "htf_data.lua")
# user_htf.lua holds the fonts tex4ht's .htf sources do not cover -- bbm is
# there, hand-written, and nothing about it reaches htf_data.lua.  For this
# workflow it is htf data like any other: the same shape, the same alias and
# largest-prefix rules, and the same need to be corrected.  luarealchar.lua loads
# both and lets the later win, so this reads them in that order too.
USER_HTF = os.path.join(HTF_DIR, "user_htf.lua")
HTF_LUAS = (HTF_LUA, USER_HTF)

# A lua string, ESCAPES AND ALL.  [^"]* stopped at the first quote, so any value
# containing one -- and every mfont-wrapped value written by tex4ht does, as
# ["value"] = "<mfont mathvariant=\"normal\">..." -- failed to match and was
# skipped in silence.  The cost was not one value here and there: cmsy and cmbsy
# wrap EVERY position, so both parsed as chars={}, resolve() then found an entry
# with no chars, base_htf fell back to the font's own name, and their records
# were seeded believing the htf table said nothing about any of their 129
# positions.  cmmi lost the 31 of its 128 that are wrapped.
#
# Nothing this project writes was affected, which is why bbm and stix never
# showed it: htf_mfont_apply.q() single-quotes and escapes, so its values carry
# no bare double quote.  _qv/_ESC below already undo the escaping -- only the
# match was too narrow.
_Q = r'''(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')'''
_top   = re.compile(r'^\t\[\s*' + _Q + r'\s*\]\s*=\s*$')
_alias = re.compile(r'^\t\t\[(?:"alias"|\'alias\')\]\s*=\s*' + _Q + r'\s*,?\s*$')
_sect  = re.compile(r'^\t\t\[(?:"(font|chars)"|\'(font|chars)\')\]')
_close2= re.compile(r'^\t\t\}')
_pos   = re.compile(r'^\t\t\t\[' + _Q + r'\]\s*=\s*$')
_kv    = re.compile(r'^\t\t\t\[' + _Q + r'\]\s*=\s*' + _Q + r'\s*,?\s*$')
_val   = re.compile(r'\[(?:"value"|\'value\')\]\s*=\s*' + _Q + r'\s*,')

# Lua string escapes, as htf_mfont_apply writes them: a backslash or a quote
# inside a value is escaped, so 'REVERSE SOLIDUS' is stored as '\\'.  Reading
# it raw would give two characters and make the value look like a sequence.
_ESC = re.compile(r'\\(["\'\\])')

def _qv(m, i=0):
    a, b = m.group(i + 1), m.group(i + 2)
    return _ESC.sub(r'\1', a if a is not None else b)

# --- htf data from tex4ht's own .htf files -----------------------------------
# htf_data.lua and user_htf.lua are not part of a TeX Live installation: they
# belong to the vtex tree, and are the WORKED copies -- values already wrapped
# in <mfont mathvariant="...">, declarations already written.  The .htf files
# they were first derived from ARE in the distribution, so this project reads
# those instead, through htf_data.json (built by htf_to_json.py, `make
# htf_data.json').
#
# That makes the values UPSTREAM ones: a bare &#x222B; where the worked file has
# the mfont wrapper, and no ['font'] declaration where the worked file carries
# one.  Which is the point -- the .htf files are what the analysis is meant to
# correct, so the record has to start from what they actually say.
HTF_JSON = os.path.join(DATA, "htf_data.json")


def read_htf_json(path=None):
    """font -> {'chars': {pos: value}, 'font': {...}, 'alias': name}.

    The same shape read_htf_lua returns, from the .htf-derived JSON, whose
    char values are {'value': ..., 'type': ...} records rather than bare
    strings.
    """
    path = path or HTF_JSON
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    out = {}
    for name, e in raw.items():
        chars = {}
        for pos, v in (e.get("chars") or {}).items():
            chars[pos] = v.get("value") if isinstance(v, dict) else v
        out[name] = {"chars": chars,
                     "font": e.get("font") or {},
                     "alias": e.get("alias")}
    return out


def read_htf(paths=None):
    """The htf data, from whichever source this installation has.

    The worked lua files when they are present (a vtex tree), otherwise the
    .htf-derived JSON, which is what a plain TeX Live can offer.
    """
    if paths is None and not any(os.path.exists(p) for p in HTF_LUAS):
        return read_htf_json()
    return read_htf_lua(paths)


def read_htf_lua(paths=None):
    """font -> {'chars': {pos: value}, 'font': {axis: value}, 'alias': name}.

    Reads htf_data.lua AND user_htf.lua by default, in that order, so a font
    defined only in the user overlay -- bbm and its seven aliases -- is found
    like any other and a later definition of the same name wins, as the loader
    does it.  A single path may still be given.
    """
    if paths is None:
        paths = HTF_LUAS
    elif isinstance(paths, str):
        paths = (paths,)
    out = {}
    for path in paths:
        if os.path.exists(path):
            out.update(_read_one_htf_lua(path))
    return out

def htf_decl_chain(name, htf):
    """(accumulated ['font'] declaration, the chain walked) for an htf entry.

    A declaration is not one entry's business: bbmss says family=sans-serif and
    ALIASES bbm, which says variant=double-struck, so the font is both.  Reading
    only the entry that serves the font -- which is what was done -- left
    bbmss10 sans-serif and not double-struck, losing the very property that makes
    it a blackboard font.

    Precedence follows luarealchar.lua exactly, and it is not uniform:

      along an ALIAS chain the DEEPER entry wins.  get_htf_data recurses into the
      alias before merging its own ['font'] with 'if not h.font[k]', so whatever
      the aliased entry set is already there and stands.

      along the largest-PREFIX chain the NEARER (longer) name wins, the loop
      visiting the longest name first and each shorter one only filling gaps.

    Only aliases are walked here: a prefix step means no entry of that name
    exists, so there is nothing at the intermediate names to collect.
    """
    chain, seen, cur = [], set(), name
    while cur and cur in htf and cur not in seen:
        seen.add(cur)
        chain.append(cur)
        cur = htf[cur].get("alias")
    decl = {}
    for n in reversed(chain):              # deepest first: the alias target wins
        for ax, v in (htf[n].get("font") or {}).items():
            decl.setdefault(ax, v)
    return decl, chain

def htf_entry_for(name, htf):
    """The htf entry serving this font: exact name, else the LARGEST PREFIX.

    luarealchar.lua chops a character off the name and retries until something
    matches (get_htf_data, 'htf_name:sub(1, -2)'), which is how bbm10 is served
    by the entry called 'bbm' and every size of every cut needs no entry of its
    own.  Resolving it here rather than demanding an exact match is what lets a
    record be seeded for a tfm whose htf is named by a prefix.
    """
    if name in htf:
        return name
    floor = min((len(k) for k in htf), default=1)
    cur = name
    while len(cur) > floor:
        cur = cur[:-1]
        if cur in htf:
            return cur
    return None

def _read_one_htf_lua(path):
    out, cur, sect, lastpos = {}, None, None, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = _top.match(line)
            if m:
                cur = _qv(m); sect = lastpos = None
                out[cur] = {"chars": {}, "font": {}, "alias": None}
                continue
            if cur is None:
                continue
            m = _alias.match(line)
            if m:
                out[cur]["alias"] = _qv(m); continue
            m = _sect.match(line)
            if m:
                sect = m.group(1) or m.group(2); continue
            if _close2.match(line):
                sect = None; continue
            if sect == "font":
                m = _kv.match(line)
                if m:
                    out[cur]["font"][_qv(m, 0)] = _qv(m, 2)
            elif sect == "chars":
                m = _pos.match(line)
                if m:
                    lastpos = _qv(m); continue
                m = _val.search(line)
                if m and lastpos is not None:
                    out[cur]["chars"][lastpos] = _qv(m)
    return out

# --- a minimal glyphs2u lua table reader ------------------------------------
LUA_ROW = re.compile(r"""^\s*\[\s*['"]([^'"]+)['"]\s*\]\s*=\s*\{([^}]*)\}""")

def read_lua_entries(path):
    """<glyph name> -> {'codes': [...], 'rename': str|None}.

    A glyphs2u row may carry a RENAME after its codepoints --
    ['parenleft.s1'] = { 0x0028, 0xFE01, 'parenleftbig' } -- because Acrobat
    Distiller truncates a glyph name at the first dot before looking it up in
    the AGL, so xdvipsk renames such glyphs unconditionally.  418 of the 1387
    rows in the stix tables have one, and reading the row as codepoints alone
    threw them away: a non-numeric token used to abandon the whole entry, which
    made every renamed row invisible.
    """
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = LUA_ROW.match(line)
            if not m:
                continue
            codes, rename = [], None
            for tok in m.group(2).split(","):
                tok = tok.strip()
                if not tok:
                    continue
                if tok[:1] in "'\"":
                    rename = tok.strip("'\"")
                    continue
                try:
                    codes.append(int(tok, 16) if tok.lower().startswith("0x")
                                 else int(tok))
                except ValueError:
                    pass                      # a comment or something unknown
            if codes or rename:
                out[m.group(1)] = {"codes": codes, "rename": rename}
    return out

def read_lua_table(path):
    """<glyph name> -> [codepoints], for callers that want only the values."""
    return {k: v["codes"] for k, v in read_lua_entries(path).items() if v["codes"]}
