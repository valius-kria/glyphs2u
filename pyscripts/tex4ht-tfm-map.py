#!/usr/bin/env python3
# Build tex4ht-data/tfm-htf-map.json and tex4ht-data/htf-enc-map.json.
#
# For every TFM in pfb-tfm-map.json, resolve it to a tex4ht canonical .htf using
# the same algorithm tex4ht itself uses:
#   1. exact match against index.json
#   2. longest-prefix match against canonical .htf basenames
#   3. alias chain follow-up if the matched entry is a redirect
#   4. enc-fallback: take TFM's enc, strip ".enc", try that as an index key
#      (covers cases like cs-lmr10/lm-cs.enc -> lm-ec.htf-style lookups)
#
# Also caches every parsed .enc file into tex4ht-data/enc-cache/<enc-stem>.json
# as a 256-entry slot -> glyph-name vector (index 0 dropped — that's the
# encoding-name token, not a glyph).
#
# Output:
#   tex4ht-data/tfm-htf-map.json:
#     { "<tfm>": { "htf": "<path-in-extracted>" | null,
#                  "matched_by": "exact"|"prefix"|"alias"|"enc-fallback"|null,
#                  "enc": "<enc-file>" | null,
#                  "prefix_used": "<basename>" }, ... }
#   tex4ht-data/htf-enc-map.json:
#     { "<htf-path>": { "encs": [<enc>|null, ...],
#                       "tfm_count": <total>,
#                       "by_enc": { "<enc>|\"null\"": <count> } }, ... }

import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(os.environ["project_dir"])
# The TeX Live tree is whichever this kpsewhich belongs to.
KPSEWHICH = os.environ.get("KPSEWHICH", "kpsewhich")

sys.path.insert(0, str(PROJECT_DIR / "pyscripts"))


def parse_enc_file(path):
    """Return (encoding_name, slot_vector) for a PostScript .enc file.

    The shared io_glyph_data.read_encoding_in_list scans for `/foo` tokens
    everywhere in the file, including inside URL comments at the top — that
    captures bogus tokens like /fonts and /licenses from the GUST license
    header and shifts the slot vector.  Here we strip line comments first,
    then anchor parsing to the [...] array.
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # Drop everything after `%` on each line.
    text = "\n".join(line.split("%", 1)[0] for line in text.splitlines())
    enc_name = None
    # The encoding name lives in `/EncName[` or `/EncName [` just before the array.
    m = re.search(r"/([A-Za-z_][\w.]*)\s*\[", text)
    if m:
        enc_name = m.group(1)
        body = text[m.end():]
    else:
        body = text
    # Slot names: everything up to the closing `]`.
    close = body.find("]")
    if close >= 0:
        body = body[:close]
    names = re.findall(r"/([._A-Za-z][\w.]*)", body)
    return enc_name, names


def kpsewhich(name):
    try:
        out = subprocess.check_output(
            [KPSEWHICH, name],
            text=True, stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    out = out.strip()
    return out.splitlines()[0] if out else None


def build_prefix_index(index):
    """Return basenames sorted by descending length, for longest-prefix match.
    Only canonical entries (those NOT alias-resolved) participate in prefix
    match; the alias chain is followed after a prefix hit."""
    # index already merges alias-resolved entries; for prefix purposes any
    # basename in the index that points to an extracted .json is a valid
    # match target.
    names = list(index.keys())
    names.sort(key=lambda s: (-len(s), s))
    return names


def resolve_tfm(tfm, enc, index, prefix_names, aliases):
    """Return (htf_path, matched_by, prefix_used).  Honors:
       - exact match
       - longest-prefix match (basename is prefix of tfm)
       - alias chain (when the prefix-matched basename is an alias)
       - enc-fallback (try <enc>-without-".enc" as an index key)"""
    # 1. exact
    if tfm in index:
        return index[tfm], "exact", tfm
    # 2. longest prefix (skip the trivial empty prefix)
    for cand in prefix_names:
        if cand and tfm.startswith(cand):
            # alias chain was already resolved when index.json was built —
            # index[cand] is the canonical extracted/.../.json path.
            matched_by = "alias" if cand in aliases else "prefix"
            return index[cand], matched_by, cand
    # 3. enc-fallback
    if enc:
        stem = re.sub(r"\.enc$", "", enc)
        if stem in index:
            return index[stem], "enc-fallback", stem
    return None, None, None


def ensure_enc_cached(enc, cache_dir):
    """Parse <enc>.enc once via kpsewhich+read_encoding_in_list; cache result
    as <enc-stem>.json (a list of 256 glyph names, '.notdef' where empty)."""
    if not enc:
        return
    stem = re.sub(r"\.enc$", "", enc)
    cache = cache_dir / f"{stem}.json"
    if cache.exists():
        return
    path = kpsewhich(enc)
    if not path:
        cache.write_text(json.dumps({"error": f"kpsewhich could not locate {enc}"}),
                         encoding="utf-8")
        return
    enc_name, names = parse_enc_file(path)
    # Normalize `.notdef` to empty slot for convenience downstream.
    vec = ["" if n == ".notdef" else n for n in names]
    # pad to 256 with empty-string placeholders.
    while len(vec) < 256:
        vec.append("")
    cache.write_text(
        json.dumps(
            {"source": path, "enc_name": enc_name, "slots": vec},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main():
    index = json.loads((PROJECT_DIR / "tex4ht-data" / "index.json").read_text())
    aliases = json.loads((PROJECT_DIR / "tex4ht-data" / "aliases.json").read_text())
    pfb_tfm_map = json.loads((PROJECT_DIR / "pfb-tfm-map.json").read_text())

    out_dir = PROJECT_DIR / "tex4ht-data"
    enc_cache_dir = out_dir / "enc-cache"
    enc_cache_dir.mkdir(parents=True, exist_ok=True)

    prefix_names = build_prefix_index(index)

    # Gather every (tfm, enc) pair referenced by any PFB.
    tfm_enc_pairs = []
    seen = set()
    for pfb, tfms in pfb_tfm_map.items():
        for tfm, enc in tfms.items():
            key = (tfm, enc)
            if key in seen:
                continue
            seen.add(key)
            tfm_enc_pairs.append(key)

    tfm_htf_map = {}     # tfm -> {htf, matched_by, enc, prefix_used}
    htf_enc_counts = {}  # htf_path -> {enc_str: count}
    n_resolved = 0
    n_unresolved = 0

    for tfm, enc in tfm_enc_pairs:
        htf, matched_by, prefix_used = resolve_tfm(
            tfm, enc, index, prefix_names, aliases
        )
        tfm_htf_map[tfm] = {
            "htf": htf,
            "matched_by": matched_by,
            "enc": enc,
            "prefix_used": prefix_used,
        }
        if htf:
            n_resolved += 1
            ensure_enc_cached(enc, enc_cache_dir)
            enc_key = enc if enc else "null"
            htf_enc_counts.setdefault(htf, {}).setdefault(enc_key, 0)
            htf_enc_counts[htf][enc_key] += 1
        else:
            n_unresolved += 1

    htf_enc_map = {}
    for htf, by_enc in sorted(htf_enc_counts.items()):
        total = sum(by_enc.values())
        htf_enc_map[htf] = {
            "encs": sorted(by_enc.keys()),
            "tfm_count": total,
            "by_enc": by_enc,
        }

    (out_dir / "tfm-htf-map.json").write_text(
        json.dumps(tfm_htf_map, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    (out_dir / "htf-enc-map.json").write_text(
        json.dumps(htf_enc_map, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )

    n_enc_cached = sum(1 for _ in enc_cache_dir.glob("*.json"))
    print(f"wrote tfm-htf-map.json ({len(tfm_htf_map)} entries; "
          f"{n_resolved} resolved, {n_unresolved} unresolved)")
    print(f"wrote htf-enc-map.json ({len(htf_enc_map)} canonical htfs covered)")
    print(f"enc-cache/: {n_enc_cached} files")


if __name__ == "__main__":
    main()
