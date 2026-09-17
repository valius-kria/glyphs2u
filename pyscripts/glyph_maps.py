# Functions to manipulate glyph sets and maps
import os
import re
import sys
from io_glyph_data import read_lua_table_in_dict, read_lua_table_in_list, is_hex_string, lua_to_renamed_glyphs_dict, UNKNOWN_UNICODE
from io_data import load_dict_from_json, load_list_from_json

# Almost all functions work in context of loaded additonal maps.
# 1. Glyph lists of all pfb fonts actual to the current working directory.
fg_dict_fname = 'fonts-glyphs-dict.json'
fg_dict = load_dict_from_json(fg_dict_fname)
# 2. Import built-in glyph to unicode map
builtin_map_path = os.path.join(os.environ['project_dir'], 'builtin-glyph-map.json')
builtin_map = load_dict_from_json(builtin_map_path)
# 3. Import replacement map for adobe private area values from builtin
adobe_priv_path = os.path.join(os.environ['project_dir'], 'adobe-private-lua.json')
adobe_priv_map = load_dict_from_json(adobe_priv_path)
# 4. Import tex-specific changes to adobe values in builtin
tex_lua_fname = os.path.join(os.environ['project_dir'], 'tex-specific.lua')
tex_map = read_lua_table_in_dict(tex_lua_fname)
# 5. Reversed map of size/style-variant name roots (built by build-roots.py).
#    Optional: absent until 'make builtin-roots.json' has been run.
roots_path = os.path.join(os.environ['project_dir'], 'builtin-roots.json')
roots_data = load_dict_from_json(roots_path) if os.path.exists(roots_path) else {}
name_roots = roots_data.get('roots', {})
variant_families = roots_data.get('families', {})
# 6. Reverse of the builtin map: canonical code tuple -> builtin glyph names.
#    Used to reuse an established TeX name when renaming a glyph.
builtin_rev = {}
for _name, _codes in builtin_map.items():
    builtin_rev.setdefault(tuple('0x%X' % int(c, 16) for c in _codes), []).append(_name)

# For check-fullness.py, compare-gs-nobuilt.py, compare-glyphs-sets.py
def glyph_list_to_add(gname: str) -> list[str]:
    """
    Checks the structure of the glyph name and transforms, if needed,
    into a list of names to be added to the map.

    """
    res_list = []
    if gname in builtin_map.keys() and not gname in adobe_priv_map.keys():
        pass
    elif '_' in gname: # split name by _
        gnames = gname.rsplit('_')
        for gname1 in gnames:
            res_list += glyph_list_to_add(gname1)
    elif '.' in gname: # take the stem until the first dot
        gname1 = gname.rsplit('.')[0]
        if not gname1 == "": # case of .notdef
            res_list += glyph_list_to_add(gname1)
    elif gname.startswith('uni') and \
         is_hex_string('0x' + gname.removeprefix('uni')):
        pass
    elif gname.startswith('u') and \
         is_hex_string('0x' + gname.removeprefix('u')):
        pass
    else:
        res_list += [gname,]
    return res_list

def wanted_glyphs(font: str) -> list[str]:
    """
    Collect all glyphs that should be defined in custom table.
    """
    wanted_glist = []
    for gname in fg_dict[font]:
        if not glyph_list_to_add(gname) == []:
            wanted_glist.append(gname)
    return wanted_glist


# For pfb-unicode-html.py
# Finding unicode values in maps by the given glyph name.
# Recursively defined function.
def find_unicodes(gname: str, lmap: dict) -> list[str]:
    """
    We need to model here algorithms of xdvipsk and distillers to have
    similar results.  In some cases, manipulation with glyph name is needed.

    Args:
        gname (str): glyph name
        lmap (dict): custom glyph to unicode map
    Returns:
        list(hex): Code list from Unicode
    """
    unicodes = []
    # Finding simply by a glyph name in dictionaries
    if gname in lmap.keys():
        unicodes = lmap[gname]
    elif gname in builtin_map.keys():
        unicodes = builtin_map[gname]
    elif '_' in gname: # split name by _
        gnames = gname.rsplit('_')
        list_of_unicodes = [find_unicodes(gn, lmap) for gn in gnames]
        unicodes = [cd for sublist in list_of_unicodes for cd in sublist]
    elif '.' in gname: # take the stem until the first dot
        unicodes = find_unicodes(gname.rsplit('.')[0], lmap)
    # Glyph name can contain unicode
    elif gname.startswith('uni'):
        maybe_hex = gname.removeprefix('uni')
        l = len(maybe_hex)
        if is_hex_string('0x' + maybe_hex):
            unicodes = ['0x' + maybe_hex[i:i+4] for i in range(0, l, 4)]
    elif gname.startswith('u'):
        maybe_hex = '0x' + gname.removeprefix('u')
        if is_hex_string(maybe_hex):
            unicodes = unicodes = [maybe_hex,]
    return unicodes

# For initial-lua.py
def initial_lua(lua_fname: str) -> dict:
    """
    Reads the glyph list from pfb file, removes some part of glyphs common with
    the builtin table
    """
    # 1. Find the font name
    font = os.path.splitext(os.path.basename(lua_fname))[0]
    # 2. Get glyph data from the source font if it exists
    uni_fname = font + '-unicodes.json'
    # 3. define the list
    lua_dict = {}
    if os.path.exists(uni_fname):
        # non-pfb font
        uni_and_names = load_list_from_json(uni_fname)
        for gid in range(len(uni_and_names)):
            gid_dict = uni_and_names[gid]
            if gid_dict["unicodes"] == []:
                gname =  gid_dict["name"]
                value = [UNKNOWN_UNICODE]
                if gname:
                    value = initial_unicode(gname)
                lua_dict[str(gid)] = value
    else:
        if font in fg_dict.keys():
            glyph_list = fg_dict[font]
        else:
            print(f"Font '{font}' is not listed in '{fg_dict_fname}'... exiting... ")
            sys.exit(1)
        for gname in glyph_list:
            value = initial_unicode(gname)
            if value:
                lua_dict[gname] = value
    return lua_dict

# For initial-lua.py 'all' mode
def sentinel_lua(lua_fname: str) -> dict:
    """
    Build a table mapping *every* glyph in the font to the unknown sentinel
    (UNKNOWN_UNICODE), ignoring glyph names and any name-based resolution.

    For fonts whose glyph names are wrong or meaningless: every glyph must then
    be recognised visually with edit_knn.py instead of trusting its name.  The
    resulting table lists the whole font as unknown; the default edit_knn mode
    (sentinel-only) therefore walks through all of it.
    """
    font = os.path.splitext(os.path.basename(lua_fname))[0]
    uni_fname = font + '-unicodes.json'
    lua_dict = {}
    if os.path.exists(uni_fname):
        # non-pfb font: key by GID
        uni_and_names = load_list_from_json(uni_fname)
        for gid in range(len(uni_and_names)):
            lua_dict[str(gid)] = [UNKNOWN_UNICODE]
    elif font in fg_dict.keys():
        # pfb font: key by glyph name
        for gname in fg_dict[font]:
            lua_dict[gname] = [UNKNOWN_UNICODE]
    else:
        print(f"Font '{font}' is not listed in '{fg_dict_fname}'... exiting... ")
        sys.exit(1)
    return lua_dict

# Aux function used twice
def initial_unicode(gname: str)-> list[str]:
    """
    Searches for some initial Unicode value by the given glyph name.
    """
    import re
    from unicode_descriptions import unicode_descr_for_code
    # 5. Define the regexp for searching descriptions
    rexp = re.compile("(Priv|Surrog)ate")
    result = None
    if not gname in builtin_map.keys():
        uni_list = find_unicodes(gname, {})
        if uni_list == [] or rexp.search( unicode_descr_for_code(uni_list[0])):
            result = [UNKNOWN_UNICODE]
    elif rexp.search( unicode_descr_for_code( builtin_map[gname][0] )):
        if gname in adobe_priv_map.keys():
            result = adobe_priv_map[gname]
        else:
            result = builtin_map[gname]
    if gname in tex_map.keys():
        result = tex_map[gname]
    return result

# For find-unneeded-glyphs.py
def unneeded_glyphs(lua_map: dict, font: str) -> dict:
    """
    Finds glyphs that are correctly defined in buil-in lua table and
    which are not in the font (may be were copied from other table)
    """
    # Define the candidates for removal
    rm_glyphs = {}
    for gname in lua_map.keys():
        if not gname in fg_dict[font]:
            rm_glyphs[gname] = "not in font " + font
        elif gname in builtin_map.keys():
            if lua_map[gname] == builtin_map[gname]:
                rm_glyphs[gname] = "defined in builtin table"
    return rm_glyphs

# For check-encodings.py
def renaming_maps(pfb_set: set[str]) -> dict:
    """
    Constructs pfb dict with maps forcing to rename glyphs from the builtin map
    """
    pfb_map_dict = {}
    for pfb in pfb_set:
        lua_fname = os.path.splitext(pfb)[0] + '.lua'
        lua_dict = read_lua_table_in_dict(lua_fname)
        pfb_map_dict[pfb] = { glyph: codes for glyph, codes in lua_dict.items()
                              if ( glyph in builtin_map.keys()
                                   and not codes == builtin_map[glyph] ) }
    return pfb_map_dict

# For rename-info.py
# Build the glyph name xdvipsk/distiller derive from a code list.  This is the
# inverse of find_unicodes and follows the Adobe Glyph List convention: 'uni'
# followed by one or more 4-hex-digit BMP codepoints, or 'u' followed by the
# hex digits of a single non-BMP (astral) codepoint.
def name_from_codes(codes: list[str]) -> str:
    ints = [int(c, 16) for c in codes]
    if len(ints) == 1 and ints[0] > 0xFFFF:
        return 'u%04X' % ints[0]
    return 'uni' + ''.join('%04X' % v for v in ints)

# Compare two code lists regardless of hex casing or zero padding.
def same_codes(a: list[str], b: list[str]) -> bool:
    try:
        return [int(x, 16) for x in a] == [int(x, 16) for x in b]
    except ValueError:
        return a == b

# Canonical hex-code string, casing/padding independent.
def canon_code(code: str) -> str:
    return '0x%X' % int(code, 16)

# TeX name for a size/style variant [base, 0xFE0x] from the name-roots map, e.g.
# [0x221A, 0xFE03] -> 'radicalbigg'.  Returns None when the base has no known
# root or the variation selector is outside its family.
def variant_name(codes: list[str]):
    if len(codes) != 2:
        return None
    info = name_roots.get(canon_code(codes[0]))
    if not info:
        return None
    suffix = variant_families.get(info['family'], {}).get(canon_code(codes[1]))
    if not suffix:
        return None
    return info['root'] + suffix

# Combining overlay marks that build negated/struck variants, and the name
# suffix each contributes.  Solidus (slash) overlays read as 'negated'; the
# other overlay kinds get a distinct word so variants of one base never collide.
OVERLAY_SUFFIX = {
    '0x337': 'negated', '0x338': 'negated',       # short / long solidus
    '0x20D2': 'barred', '0x20D3': 'barred',        # long / short vertical line
    '0x335': 'stroked', '0x336': 'stroked',        # short / long stroke
    '0x20EB': 'dblstrokked',                       # long double solidus
    '0x20E5': 'backslashed',                        # reverse solidus
}

def is_overlay(code: str) -> bool:
    return canon_code(code) in OVERLAY_SUFFIX

# Pick an established builtin glyph name for an exact code sequence, preferring a
# readable one over 'uniXXXX'/'uXXXXX'/'afiiNNNN' aliases.  Returns None if the
# sequence has no builtin name.
def builtin_name_for(codes: list[str]):
    names = builtin_rev.get(tuple(canon_code(c) for c in codes))
    if not names:
        return None
    def cryptic(n):
        return bool(re.match(r'(uni[0-9A-Fa-f]+|u[0-9A-Fa-f]{4,6}|afii\d+)$', n))
    return min(names, key=lambda n: (cryptic(n), len(n), n))

# Unicode letter/word spellings that differ from the conventional glyph name.
GREEK_FIX = {'LAMDA': 'lambda'}
DIGIT_WORDS = {'ZERO': 'zero', 'ONE': 'one', 'TWO': 'two', 'THREE': 'three',
               'FOUR': 'four', 'FIVE': 'five', 'SIX': 'six', 'SEVEN': 'seven',
               'EIGHT': 'eight', 'NINE': 'nine'}
STYLE_TAG = {'BOLD': 'b', 'ITALIC': 'it', 'SANS-SERIF': 'sf', 'MONOSPACE': 'tt',
             'SCRIPT': 'scr', 'FRAKTUR': 'frak'}

def _letter(word: str, upper: bool) -> str:
    if len(word) == 1 and word.isalpha():          # Latin letter
        return word.upper() if upper else word.lower()
    name = GREEK_FIX.get(word, word.lower())        # Greek name
    return name.capitalize() if upper else name

# Base part of a mathematical-alphanumeric name, and whether it is a "* SYMBOL"
# variant (which takes a trailing '1').  Returns (base, is_symbol) or (None,_).
def _math_base(rest: list[str]):
    if rest and rest[-1] == 'SYMBOL':
        return _letter(rest[-2], upper=('CAPITAL' in rest)), True
    if rest[:1] == ['CAPITAL']:
        return _letter(rest[-1], upper=True), False
    if rest[:1] == ['SMALL']:
        if 'DOTLESS' in rest:
            return 'dotless' + rest[-1].lower(), False
        return _letter(rest[-1], upper=False), False
    if rest[:1] == ['DIGIT']:
        return DIGIT_WORDS.get(rest[-1]), False
    if rest == ['NABLA']:
        return 'nabla', False
    if rest == ['PARTIAL', 'DIFFERENTIAL']:
        return 'partialdiff', False
    return None, False

# Construct a readable name for a mathematical-alphanumeric codepoint from its
# Unicode name, e.g. 0x1D400 'MATHEMATICAL BOLD CAPITAL A' -> 'Ab',
# 0x1D538 'DOUBLE-STRUCK CAPITAL A' -> 'bbA'.  Base name comes first, style tags
# follow as a suffix; double-struck keeps the builtin 'bb' prefix.  None when the
# codepoint is not a constructible math-alphanumeric character.
def math_alpha_name(code: str):
    from unicode_descriptions import unicode_descr_for_code
    descr = unicode_descr_for_code(canon_code(code)) or ''
    if not descr.startswith('MATHEMATICAL '):
        return None
    words = descr[len('MATHEMATICAL '):].split()
    tags, dbl, i = [], False, 0
    while i < len(words) and (words[i] in STYLE_TAG or words[i] == 'DOUBLE-STRUCK'):
        if words[i] == 'DOUBLE-STRUCK':
            dbl = True
        else:
            tags.append(STYLE_TAG[words[i]])
        i += 1
    base, is_symbol = _math_base(words[i:])
    if base is None:
        return None
    if is_symbol:
        base += '1'
    return 'bb' + base if dbl else base + ''.join(tags)

# Name for a single astral (>U+FFFF) codepoint: an established builtin name, else
# a constructed mathematical-alphanumeric name, else the plain 'u'+hex form.
def astral_name(code: str) -> str:
    return (builtin_name_for([code]) or math_alpha_name(code)
            or name_from_codes([code]))

# Name for one codepoint used as the base of a variant (BMP or astral).
def base_name(code: str) -> str:
    if int(code, 16) > 0xFFFF:
        return astral_name(code)
    return builtin_name_for([code]) or name_from_codes([code])

# Name for a negated/struck variant [base, overlay...]: an established builtin
# name, else the base name followed by each overlay's suffix.
def overlay_name(codes: list[str]) -> str:
    established = builtin_name_for(codes)
    if established:
        return established
    suffix = ''.join(OVERLAY_SUFFIX.get(canon_code(c), '') for c in codes[1:])
    if not suffix:
        return name_from_codes(codes)
    return base_name(codes[0]) + suffix

# The name a renamed glyph receives, dispatching on the shape of its codes:
# size/style variant, negated/struck overlay variant, single astral codepoint,
# or (default) the AGL 'uni'/'u' hex form for BMP codepoints.
def codes_to_name(codes: list[str]) -> str:
    c = [canon_code(x) for x in codes]
    variant = variant_name(c)
    if variant:
        return variant
    if len(c) >= 2 and any(is_overlay(x) for x in c[1:]):
        return overlay_name(c)
    if len(c) == 1 and int(c[0], 16) > 0xFFFF:
        return astral_name(c[0])
    return name_from_codes(c)

# Read one lua table into (original name, explicit new name or None, codes)
# triples.  The new name, when present, is written among the codes inside the
# braces (see lua_to_renamed_glyphs_dict).
def lua_table_entries(lua_filepath: str) -> list:
    entries = []
    for elm in read_lua_table_in_list(lua_filepath) or []:
        if type(elm) is str:
            continue
        orig = elm[0]
        codes, new_name = [], None
        for item in re.split(r'[ ,]+', elm[1]):
            if not item:
                continue
            if is_hex_string(item):
                codes.append(item)
            else:
                stripped = item.strip('\'"')
                if stripped:
                    new_name = stripped
        entries.append((orig, new_name, codes))
    return entries

# Propose unique new names for the glyphs colliding on one final name.
#
#  * Same codepoint for all (a genuine duplicate character): the existing font
#    glyph keeps the base name; the others get 'base.altN' dot-suffixes, which
#    the distiller strips, so they still advertise the correct Unicode.
#  * Different codes forced to share a name (e.g. size variants mis-copied to one
#    hand-written name): the dot-suffix does not apply; each glyph is renamed to
#    the proper name its own codes yield (TeX root, math-alphanumeric, negated
#    variant, ...).  None keeps the shared name.
# A proposal that still collides with a taken name is reported as null, i.e. left
# for manual naming.  'used' accumulates every name already taken so no two
# proposals collide.
def propose_names(contested, origs, codes_of, used):
    csets = [codes_of[o] for o in origs]
    identical = all(same_codes(c, csets[0]) for c in csets)
    keep, rename = None, {}
    if identical:
        keepers = [o for o in origs if o == contested]
        keep = keepers[0] if keepers else sorted(origs)[0]
        for o in sorted(origs):
            if o == keep:
                continue
            n = 1
            while '%s.alt%d' % (contested, n) in used:
                n += 1
            proposed = '%s.alt%d' % (contested, n)
            used.add(proposed)
            rename[o] = proposed
    else:
        for o in sorted(origs):
            proposed = codes_to_name(codes_of[o])
            if proposed and proposed not in used:
                used.add(proposed)
            else:
                proposed = None  # name still collides: name by hand
            rename[o] = proposed
    return {'keep': keep, 'rename': rename}

# Procedure to find renamed duplicates for one table.
#
# xdvipsk renames a glyph whenever the Unicode implied by its own name (from the
# builtin map, or decoded from a 'uni'/'u' name) differs from the codes assigned
# in the lua table, regenerating a 'uni'/'u' name from those codes.  A lua table
# may instead give an explicit new name among the codes.  Either way the new
# name shares a single namespace with the glyph names already present in the
# font (e.g. STIX fonts already contain literal 'uniXXXX'/'uXXXXX' glyphs), so a
# clash occurs when two glyphs end up with the same final name.  We resolve every
# font glyph to its final name, and for each name reached by more than one glyph
# report which glyph keeps it and the proposed new name for each of the others.
def find_duplicates(lua_filepath: str):
    font = os.path.splitext(os.path.basename(lua_filepath))[0]
    # Every existing font glyph keeps its name unless the lua table renames it.
    final = { name: name for name in fg_dict.get(font, []) }
    codes_of = {}
    for orig, new_name, codes in lua_table_entries(lua_filepath):
        codes_of[orig] = codes
        if new_name:
            final[orig] = new_name
        elif codes and not same_codes(codes, [UNKNOWN_UNICODE]):
            implied = find_unicodes(orig, {})
            if implied and not same_codes(codes, implied):
                # xdvipsk generates a code-derived 'u'/'uni' name for a glyph
                # without an explicit name; the descriptive codes_to_name is only
                # for the proposal, not for what xdvipsk actually produces.
                final[orig] = name_from_codes(codes)
            else:
                final.setdefault(orig, orig)
        else:
            final.setdefault(orig, orig)
    # Reverse the mapping: collect the glyphs that reach each final name.
    by_final = {}
    for orig, fname in final.items():
        by_final.setdefault(fname, []).append(orig)
    # Codes of a retained font glyph come from its own name.
    for orig in final:
        codes_of.setdefault(orig, find_unicodes(orig, {}))
    used = set(final.values())
    return { fname: propose_names(fname, sorted(origs), codes_of, used)
             for fname, origs in by_final.items()
             if len(origs) > 1 }

