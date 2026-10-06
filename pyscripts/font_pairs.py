#!/usr/bin/env python3
"""Which font a variant is compared against, and on which axis.

The pairing is derived automatically in htf_mfont_targets.json ('same-family
fonts differing by one font-level declaration'), which works only as far as the
declarations do.  A font whose declaration is missing or wrong gets no pair at
all, and there is nowhere to say otherwise -- the derived file is regenerated.

So a family may carry a HAND-EDITABLE map, one level up from the work dirs:

    tfm/<supplier>/<family>/pairs

        # variant            plain            differs
        stix-mathfrak-bold   stix-mathfrak    weight=bold
        stix-mathbbit        stix-mathbb      style=italic
        stix-mathex          -                -          # no sibling, do not pair

Three whitespace-separated columns, '#' comments, blank lines ignored.  A '-' in
the plain column suppresses a pair -- needed to reject a wrong derived one, not
just to add a right one.  The plain font may live in another family's directory;
only its name matters, since both fonts' rasters are rendered in the variant's
work dir either way.

The file WINS for any variant it names; everything else falls back to the
derived pairs, so only the entries the derivation gets wrong are written by
hand.  Searched in ./, ../ and ../../ so it is found from a work dir (where the
family dir is one up) and from the family dir itself.

The 'differs' column is not decoration: cmp_classify.py uses it as the axis the
comparison settles, and it is what the review page says the comparison answers.
A pair without it cannot be classified.

Usage:
  font_pairs.py <variant>            # print the plain sibling (exit 1 if none)
  font_pairs.py --axis <variant>     # print 'plain<TAB>axis=value'
  font_pairs.py --seed [DIR]         # write DIR/pairs from the derived pairs
  font_pairs.py --show [DIR]         # list how each font in DIR resolves
"""
import json, os, sys, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("data_dir") or os.path.dirname(HERE)          # generated maps live in data_dir
PAIRS = "pairs"
SEARCH_UP = 3                          # ./, ../, ../../

def _derived(data=DATA):
    """variant -> (plain, differs), as htf_mfont_targets.json worked it out."""
    path = os.path.join(data, "htf_mfont_targets.json")
    try:
        with open(path, encoding="utf-8") as f:
            pairs = json.load(f)["comparison_pairs"]
    except (OSError, ValueError, KeyError):
        return {}
    return {p["variant"]: (p["plain"], p["differs"]) for p in pairs}

def find_pairs_file(start="."):
    d = os.path.abspath(start)
    for _ in range(SEARCH_UP):
        p = os.path.join(d, PAIRS)
        if os.path.isfile(p):
            return p
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None

def read_pairs(path):
    """variant -> (plain|None, differs|None).  None means 'do not pair'."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                print(f"{path}:{n}: need at least <variant> <plain>, ignored",
                      file=sys.stderr)
                continue
            variant, plain = parts[0], parts[1]
            differs = parts[2] if len(parts) > 2 else None
            if plain == "-":
                out[variant] = (None, None)
            else:
                out[variant] = (plain, None if differs == "-" else differs)
    return out

def pair_of(variant, start=".", data=DATA):
    """(plain, differs), or (None, None) when this font is not to be compared.

    The hand-written family map is consulted first and is final for the fonts
    it names -- including a '-' that says a derived pair is wrong.
    """
    path = find_pairs_file(start)
    if path:
        hand = read_pairs(path)
        if variant in hand:
            return hand[variant]
    return _derived(data).get(variant, (None, None))

# --- cli ---------------------------------------------------------------------
def _seed(dirname, data=DATA):
    """Write <dir>/pairs from the derived pairs, for the fonts found there.

    Fonts with no derived pair go in COMMENTED, so the file never suppresses a
    pair the derivation might work out later -- it shows what is missing without
    asserting anything about it.
    """
    dirname = os.path.abspath(dirname)
    fonts = sorted(d for d in os.listdir(dirname)
                   if os.path.isdir(os.path.join(dirname, d)))
    derived = _derived(data)
    out = [f"# Pairing map for {os.path.basename(dirname)} -- hand-editable.",
           "# Seeded from htf_mfont_targets.json; edit freely, this file wins.",
           "# A '-' in the plain column means 'do not compare this font'.",
           "#",
           "# variant                plain                  differs"]
    have, missing = 0, 0
    for f in fonts:
        if f in derived:
            plain, differs = derived[f]
            out.append(f"{f:<24} {plain:<22} {differs}")
            have += 1
        else:
            out.append(f"# {f:<22} ?                      ?")
            missing += 1
    path = os.path.join(dirname, PAIRS)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"font_pairs: {path}  {have} pair(s), {missing} font(s) with none "
          f"(commented out -- fill in by hand if they have one)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant", nargs="?")
    ap.add_argument("--axis", action="store_true",
                    help="print 'plain<TAB>axis=value' instead of just the name")
    ap.add_argument("--seed", nargs="?", const=".", metavar="DIR")
    ap.add_argument("--show", nargs="?", const=".", metavar="DIR")
    ap.add_argument("--data", default=DATA)
    a = ap.parse_args()

    if a.seed is not None:
        return _seed(a.seed, a.data)
    if a.show is not None:
        d = os.path.abspath(a.show)
        src = find_pairs_file(d)
        print(f"pairs file: {src or '(none -- derived pairs only)'}")
        for f in sorted(x for x in os.listdir(d)
                        if os.path.isdir(os.path.join(d, x))):
            plain, differs = pair_of(f, d, a.data)
            print(f"  {f:<24} {plain or '-':<22} {differs or '-'}")
        return
    if not a.variant:
        sys.exit("font_pairs: give a variant font name, --seed or --show")
    plain, differs = pair_of(a.variant, ".", a.data)
    if not plain:
        sys.exit(f"font_pairs: no comparison pair for '{a.variant}'")
    print(f"{plain}\t{differs}" if a.axis else plain)

if __name__ == "__main__":
    main()
