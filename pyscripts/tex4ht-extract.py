#!/usr/bin/env python3
# Extract Unicode mappings from tex4ht .htf files into $project_dir/tex4ht-data/.
#
# Takes a list of root directories scanned recursively for .htf files.  Later
# roots override earlier ones for the same canonical (header) name or alias
# (basename) name, matching the semantics of pyscripts/htf_to_json.py
# (L. Stonys, V. Kriaučiukas).
#
# Default roots, in precedence order (last wins):
#   $TEXMFDIST/tex4ht/ht-fonts/alias
#   $TEXMFDIST/tex4ht/ht-fonts/unicode
# where TEXMFDIST is resolved with kpsewhich.  Add a local or personal texmf
# tree with further --root flags.
# Override with one or more --root flags.
#
# Each .htf file is classified by content:
#   * first line begins with "." -> alias file: name=basename, target=<line>.lstrip('.')
#   * else -> canonical: header `<name> <first> <last>` declares the prefix;
#     slot lines follow.
#
# Slot lines: <delim><value><delim> <delim><class><delim> [glyph_name] <slot> [% comment]
# where <delim> is either ' or @ (used when the value contains the other one).
#
# Outputs:
#   tex4ht-data/extracted/<safe-name>.json   per-canonical structured data
#   tex4ht-data/aliases.json                 alias-name -> target-name
#   tex4ht-data/index.json                   name -> extracted relpath (alias-resolved)
#   tex4ht-data/extraction.log

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

KPSEWHICH = os.environ.get("KPSEWHICH", "kpsewhich")


def _texmfdist():
    """Locate texmf-dist of the TeX Live tree kpsewhich belongs to."""
    try:
        out = subprocess.check_output(
            [KPSEWHICH, "-var-value=TEXMFDIST"], text=True,
            stderr=subprocess.DEVNULL).strip()
        return out or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


TEXMFDIST = _texmfdist()
DEFAULT_ROOTS = [
    f"{TEXMFDIST}/tex4ht/ht-fonts/alias",
    f"{TEXMFDIST}/tex4ht/ht-fonts/unicode",
] if TEXMFDIST else []

ENTITY_RE = re.compile(r"&#[xX]([0-9A-Fa-f]+);|&#(\d+);")
HEADER_RE = re.compile(r"^\s*(\S+)\s+(\d+)\s+(\d+)\s*(?:%.*)?$")
# value and close-tag between matching delimiters ('...' or @...@); then rest.
SLOT_RE = re.compile(
    r"^\s*(['@])(?P<val>.*?)\1"
    r"\s+(['@])(?P<cls>.*?)\3"
    r"\s*(?P<rest>.*?)\s*$"
)
HTFCSS_RE = re.compile(r"^htfcss:\s*(\S+)\s+(.*)$")


def parse_entity(s):
    if not s:
        return []
    out = []
    for m in ENTITY_RE.finditer(s):
        h, d = m.group(1), m.group(2)
        out.append(int(h, 16) if h else int(d))
    if out:
        return out
    # No `&#x...;` entities.  If the value contains HTML/MathML markup or
    # TeX-style escapes, it is a rendering template, not a codepoint sequence
    # — skip.  Otherwise treat as a literal character run (e.g. "FF" -> [70, 70]).
    if "<" in s or ">" in s or "\\" in s:
        return []
    return [ord(c) for c in s]


def sanitize_name(name):
    """Map a header / basename name to a filesystem-safe extracted/ filename."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def parse_htf(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not lines:
        return None
    first = lines[0].rstrip()
    if first.startswith("."):
        return {"alias_to": first.lstrip(".").strip()}
    m = HEADER_RE.match(lines[0])
    if not m:
        return {"error": f"bad header: {lines[0]!r}"}
    name = m.group(1)
    first_slot = int(m.group(2))
    last_slot = int(m.group(3))
    slots = {}
    htfcss = {}
    warnings = []
    for lineno, raw in enumerate(lines[1:], start=2):
        if not raw.strip():
            continue
        if raw.startswith("htfcss:"):
            mm = HTFCSS_RE.match(raw)
            if mm:
                fname = mm.group(1)
                feats = {}
                for fm in re.finditer(r"font-(\w+):\s*([^;]+);", mm.group(2)):
                    feats[fm.group(1)] = fm.group(2).strip()
                if feats:
                    htfcss[fname] = feats
            continue
        sm = SLOT_RE.match(raw)
        if not sm:
            warnings.append([lineno, "no match", raw])
            continue
        val = sm.group("val")
        cls = sm.group("cls")
        rest = sm.group("rest")
        if "%" in rest:
            rest_main, comment = rest.split("%", 1)
            rest_main = rest_main.rstrip()
            comment = comment.strip()
        else:
            rest_main, comment = rest, ""
        toks = rest_main.split()
        if not toks:
            warnings.append([lineno, "no slot", raw])
            continue
        try:
            slot = int(toks[-1])
        except ValueError:
            warnings.append([lineno, f"slot not int: {toks[-1]!r}", raw])
            continue
        glyph_name = " ".join(toks[:-1]) if len(toks) > 1 else None
        rec = {"codepoints": parse_entity(val)}
        # Drop \nounicode -- means tex4ht has no Unicode for this slot.
        if val == r"\nounicode":
            rec["codepoints"] = []
            rec["nounicode"] = True
        # If we have a non-empty value but no codepoints, it was markup; keep
        # the raw rendering template for diagnostics, but the slot has no Unicode.
        if val and not rec["codepoints"] and val != r"\nounicode":
            rec["raw"] = val
        if cls:
            rec["class"] = cls
        if glyph_name:
            rec["name"] = glyph_name
        if comment:
            rec["comment"] = comment
        slots[slot] = rec
    out = {
        "name": name,
        "first": first_slot,
        "last": last_slot,
        "slots": {str(k): v for k, v in sorted(slots.items())},
    }
    if htfcss:
        out["htfcss"] = htfcss
    if warnings:
        out["warnings"] = warnings
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--root", action="append", default=[],
        help="ht-fonts root (recursive); pass multiple times. Later roots override earlier.",
    )
    args = ap.parse_args()
    roots = args.root if args.root else DEFAULT_ROOTS

    project_dir = Path(os.environ["project_dir"])
    out_dir = project_dir / "tex4ht-data"
    extracted_dir = out_dir / "extracted"
    if extracted_dir.exists():
        shutil.rmtree(extracted_dir)
    extracted_dir.mkdir(parents=True, exist_ok=True)

    log = []
    # Single dict keyed by name (header-name for canonical, basename for alias).
    # Later writes override earlier ones — matches colleague's last-wins semantics.
    entries = {}    # name -> parsed dict
    file_counts = {"total": 0, "alias": 0, "canonical": 0, "error": 0, "empty": 0}

    for root in roots:
        root_path = Path(root)
        if not root_path.is_dir():
            log.append(f"skip (missing): {root}")
            continue
        log.append(f"root: {root}")
        n_root_files = 0
        for htf in sorted(root_path.rglob("*.htf")):
            file_counts["total"] += 1
            n_root_files += 1
            parsed = parse_htf(htf)
            if parsed is None:
                file_counts["empty"] += 1
                log.append(f"empty: {htf}")
                continue
            if "error" in parsed:
                file_counts["error"] += 1
                log.append(f"bad header in {htf}: {parsed['error']}")
                continue
            if "alias_to" in parsed:
                file_counts["alias"] += 1
                name = htf.stem
            else:
                file_counts["canonical"] += 1
                name = parsed["name"]
            parsed.setdefault("source", str(htf))
            parsed.setdefault("source_root", root)
            entries[name] = parsed
        log.append(f"  files in {root}: {n_root_files}")

    # Split into canonicals / aliases per final classification.
    canonicals = {n: e for n, e in entries.items() if "alias_to" not in e}
    aliases = {n: e["alias_to"] for n, e in entries.items() if "alias_to" in e}

    # Write per-canonical JSONs.
    for name, parsed in sorted(canonicals.items()):
        safe = sanitize_name(name)
        (extracted_dir / f"{safe}.json").write_text(
            json.dumps(parsed, indent=1, ensure_ascii=False),
            encoding="utf-8",
        )

    # Resolve alias chains.
    def resolve(target, depth=0):
        if depth > 10:
            return None
        if target in canonicals:
            return target
        if target in aliases:
            return resolve(aliases[target], depth + 1)
        return None

    index = {name: f"{sanitize_name(name)}.json" for name in canonicals}
    for an, target in aliases.items():
        resolved = resolve(target)
        if resolved is None:
            log.append(f"alias {an!r} -> {target!r}: no canonical found")
            continue
        if an not in index:
            index[an] = index[resolved]

    (out_dir / "aliases.json").write_text(
        json.dumps(aliases, indent=1, sort_keys=True), encoding="utf-8"
    )
    (out_dir / "index.json").write_text(
        json.dumps(index, indent=1, sort_keys=True), encoding="utf-8"
    )
    (out_dir / "extraction.log").write_text("\n".join(log) + "\n", encoding="utf-8")

    print(f"roots scanned:     {len([r for r in roots if Path(r).is_dir()])}/{len(roots)}")
    print(f".htf files total:  {file_counts['total']}")
    print(f"  canonical:       {file_counts['canonical']}")
    print(f"  alias:           {file_counts['alias']}")
    print(f"  error/empty:     {file_counts['error']}/{file_counts['empty']}")
    print(f"unique canonicals: {len(canonicals)}")
    print(f"unique aliases:    {len(aliases)}")
    print(f"index entries:     {len(index)}")
    print(f"output:            {out_dir}")


if __name__ == "__main__":
    main()
