#!/usr/bin/env python3
# Build tex4ht-data/pfb-maps/<pfb>.json for every PFB that has at least one
# TFM resolving to a tex4ht canonical .htf.
#
# Inputs:
#   pfb-tfm-map.json                       PFB -> {TFM: enc}
#   tex4ht-data/tfm-htf-map.json           TFM -> {htf, enc, matched_by, ...}
#   tex4ht-data/enc-cache/<enc>.json       parsed .enc slot vectors
#   tex4ht-data/extracted/<family>/<f>.json the per-htf slot->codepoints table
#   tex4ht-data/pfb-enc-cache/<pfb>.json   per-PFB internal /Encoding (256-vec)
#   tex4ht-data/pfb-glyphs/<pfb>.json      full CharStrings name list per PFB
#
# pfb-glyphs/ and pfb-enc-cache/ files that are missing are generated via a
# single fontforge batch invocation (pfb-info-batch.py).
#
# Output per in-scope PFB at tex4ht-data/pfb-maps/<pfb>.json:
#   { "pfb": "<filename>",
#     "sources": [ {"tfm": ..., "enc": ..., "htf": ..., "matched_by": ...}, ... ],
#     "glyphs":  { "<glyph-name>": [codepoints] },
#     "conflicts": { "<glyph-name>": [
#                       {"codepoints": [...], "source": {"tfm":..., "htf":..., "enc":...}},
#                       ...
#                   ] } }
# First (TFM, enc) source contributing a glyph wins; subsequent disagreements
# go to "conflicts" with provenance.

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_DIR = Path(os.environ["project_dir"])
# The TeX Live tree is whichever this kpsewhich belongs to.
KPSEWHICH = os.environ.get("KPSEWHICH", "kpsewhich")
DATA = PROJECT_DIR / "tex4ht-data"


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


def load_enc_vector(enc_name):
    """Return 256-entry slot->name list, or None if the enc file is missing
    or wasn't cached."""
    if not enc_name:
        return None
    stem = re.sub(r"\.enc$", "", enc_name)
    p = DATA / "enc-cache" / f"{stem}.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    if "error" in data:
        return None
    vec = data.get("slots", [])
    if len(vec) < 256:
        vec = list(vec) + [""] * (256 - len(vec))
    return vec


def load_pfb_enc_vector(pfb_stem):
    p = DATA / "pfb-enc-cache" / f"{pfb_stem}.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    return data.get("slots")


def load_htf(rel_path):
    return json.loads((DATA / "extracted" / rel_path).read_text())


def main():
    pfb_tfm = json.loads((PROJECT_DIR / "pfb-tfm-map.json").read_text())
    tfm_htf = json.loads((DATA / "tfm-htf-map.json").read_text())

    pfb_maps_dir = DATA / "pfb-maps"
    pfb_glyphs_dir = DATA / "pfb-glyphs"
    pfb_enc_dir = DATA / "pfb-enc-cache"
    for d in (pfb_maps_dir, pfb_glyphs_dir, pfb_enc_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Phase 1: figure out which PFBs are in scope and what each one needs.
    in_scope = []   # list of dicts: pfb_stem, pfb_path, resolving (list of (tfm, enc, htf, matched_by)), needs_pfb_enc
    skipped_no_match = skipped_no_pfb = 0

    for pfb_filename, tfms in pfb_tfm.items():
        pfb_stem = pfb_filename[:-4] if pfb_filename.endswith(".pfb") else pfb_filename
        resolving = []
        needs_pfb_enc = False
        for tfm, enc in tfms.items():
            r = tfm_htf.get(tfm)
            if not r or not r.get("htf"):
                continue
            resolving.append((tfm, enc, r["htf"], r["matched_by"]))
            if not enc:
                needs_pfb_enc = True
        if not resolving:
            skipped_no_match += 1
            continue
        pfb_path = kpsewhich(pfb_filename)
        if not pfb_path:
            skipped_no_pfb += 1
            continue
        in_scope.append({
            "stem": pfb_stem,
            "path": pfb_path,
            "resolving": resolving,
            "needs_pfb_enc": needs_pfb_enc,
        })

    # Phase 2: collect the fontforge jobs that still need running.
    jobs = []
    for info in in_scope:
        stem = info["stem"]
        glyphs_out = pfb_glyphs_dir / f"{stem}.json"
        enc_out = pfb_enc_dir / f"{stem}.json"
        glyphs_arg = str(glyphs_out) if not glyphs_out.exists() else "-"
        enc_arg = str(enc_out) if (info["needs_pfb_enc"] and not enc_out.exists()) else "-"
        if glyphs_arg != "-" or enc_arg != "-":
            jobs.append([info["path"], glyphs_arg, enc_arg])

    if jobs:
        print(f"fontforge batch: {len(jobs)} PFBs to extract")
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump(jobs, tf)
            jobs_path = tf.name
        try:
            subprocess.check_call(
                ["fontforge", "-script",
                 str(PROJECT_DIR / "pyscripts" / "pfb-info-batch.py"),
                 jobs_path],
                stderr=subprocess.STDOUT,
            )
        finally:
            os.unlink(jobs_path)

    # Phase 3: assemble per-PFB glyph -> codepoint maps.
    n_pfb_written = n_pfb_skipped = 0
    for info in in_scope:
        stem = info["stem"]
        glyphs_path = pfb_glyphs_dir / f"{stem}.json"
        if not glyphs_path.exists():
            n_pfb_skipped += 1
            continue
        pfb_glyph_set = set(json.loads(glyphs_path.read_text()).get("glyphs", []))

        glyphs = {}      # name -> [codepoints]
        conflicts = {}   # name -> [{codepoints, source}]
        sources = []

        for tfm, enc, htf_rel, matched_by in info["resolving"]:
            if enc:
                vec = load_enc_vector(enc)
            else:
                vec = load_pfb_enc_vector(stem)
            if vec is None:
                continue
            htf = load_htf(htf_rel)
            slots = htf.get("slots", {})
            sources.append({"tfm": tfm, "enc": enc, "htf": htf_rel, "matched_by": matched_by})
            for slot_str, rec in slots.items():
                slot = int(slot_str)
                if not (0 <= slot < len(vec)):
                    continue
                name = vec[slot]
                if not name or name == ".notdef":
                    continue
                cps = rec.get("codepoints") or []
                if not cps:
                    continue
                if name not in glyphs:
                    glyphs[name] = cps
                elif glyphs[name] != cps:
                    src = {"tfm": tfm, "enc": enc, "htf": htf_rel}
                    bucket = conflicts.setdefault(name, [])
                    if not bucket:
                        # Record the original winner first.
                        bucket.append({
                            "codepoints": glyphs[name],
                            "source": "(first writer)",
                        })
                    bucket.append({"codepoints": cps, "source": src})

        # Restrict glyph keys to names actually present in the PFB CharStrings
        # (an enc may reference glyphs the PFB doesn't have — those are skipped).
        glyphs_filtered = {n: c for n, c in glyphs.items() if n in pfb_glyph_set or not pfb_glyph_set}
        conflicts_filtered = {n: c for n, c in conflicts.items() if n in glyphs_filtered}

        out = {
            "pfb": f"{stem}.pfb",
            "sources": sources,
            "glyphs": dict(sorted(glyphs_filtered.items())),
        }
        if conflicts_filtered:
            out["conflicts"] = dict(sorted(conflicts_filtered.items()))
        (pfb_maps_dir / f"{stem}.json").write_text(
            json.dumps(out, indent=1, ensure_ascii=False, sort_keys=False),
            encoding="utf-8",
        )
        n_pfb_written += 1

    print(f"in-scope PFBs:         {len(in_scope)}")
    print(f"skipped (no tex4ht):   {skipped_no_match}")
    print(f"skipped (pfb missing): {skipped_no_pfb}")
    print(f"pfb-maps written:      {n_pfb_written}")
    print(f"pfb-maps skipped (no glyph cache): {n_pfb_skipped}")


if __name__ == "__main__":
    main()
