#!/usr/bin/env python
# Builds builtin-roots.json: a "reversed map" from the built-in glyph map that,
# for every base codepoint carrying size/style variants (a 0xFE0x variation
# selector as its second code), stores the glyph-name ROOT and the variant
# family.  These names are TeX-command related, not Unicode related, so the root
# is recovered from the built-in names themselves (by stripping the family
# suffix), never synthesised from Unicode.
#
# Output structure:
#   { "families": { <family>: { <VS-code>: <suffix> } },
#     "roots":    { <base-code>: { "root": <str>, "family": <family> } } }
#
# The families and their variation-selector -> suffix tables encode the TeX
# conventions:
#   fences    (parenleft, radical, brackets, ...) -> big / Big / bigg / Bigg
#   operators (integral, summation, ...)          -> text / display
#   accents   (circumflex->hat, tilde, ...)       -> wide / wider / widest
from io_data import save_data_to_json, load_dict_from_json
import sys

# Variation-selector code (0xFE00..0xFE0F) -> suffix, per variant family.
FAMILIES = {
    "fences":    {"0xFE01": "big",  "0xFE02": "Big",     "0xFE03": "bigg", "0xFE04": "Bigg"},
    "operators": {"0xFE01": "text", "0xFE02": "display"},
    "accents":   {"0xFE01": "wide", "0xFE02": "wider",   "0xFE03": "widest"},
}


def canon(code: str) -> str:
    """Canonical hex-code string, casing/padding independent."""
    return "0x%X" % int(code, 16)


def is_vs(code: str) -> bool:
    return 0xFE00 <= int(code, 16) <= 0xFE0F


if __name__ == "__main__":
    builtin_fname = sys.argv[1]
    json_fname = sys.argv[2]
    builtin_map = load_dict_from_json(builtin_fname)

    roots = {}
    unmatched = []
    for name, codes in builtin_map.items():
        if len(codes) != 2 or not is_vs(codes[1]):
            continue
        base, vs = canon(codes[0]), canon(codes[1])
        # The name ends in exactly one family's suffix for this VS; strip it.
        matched = False
        for family, table in FAMILIES.items():
            suffix = table.get(vs)
            if suffix and name.endswith(suffix):
                root = name[: -len(suffix)]
                prev = roots.get(base)
                if prev and (prev["root"] != root or prev["family"] != family):
                    print(f"Warning: conflicting root for {base}: "
                          f"{prev} vs {{'root': {root!r}, 'family': {family!r}}}")
                roots[base] = {"root": root, "family": family}
                matched = True
                break
        if not matched:
            unmatched.append((name, codes))

    data = {"families": FAMILIES, "roots": roots}
    save_data_to_json(data, json_fname)
    print(f"builtin-roots.json: {len(roots)} base codepoints with variant roots.")
    if unmatched:
        print(f"  {len(unmatched)} variant entries matched no known family, e.g. "
              f"{unmatched[:5]}")
