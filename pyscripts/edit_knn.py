#!/usr/bin/env python3
"""Tkinter editor: assign Unicode codepoints to glyphs by clicking k-NN candidates.

For each glyph in the named font (PFB/OTF/TTF), run k-NN over glyphs-dataset/
and present the top-K candidates as clickable cells.  Clicking a candidate
writes the chosen codepoint sequence into the corresponding line of
<font>.lua (in the current working dir) and advances to the next glyph.

Lua-file convention follows the rest of the project: PFB keys are glyph
names, OTF/TTF keys are GIDs (quoted decimal strings).  Multi-codepoint
sequences (e.g. notequal = (0x003D, 0x0338)) are written as
`{ 0x003D, 0x0338 }` so they round-trip cleanly through read_lua_table_in_dict.

Usage:
    cd <working-dir>
    python3 .../pyscripts/edit_knn.py <font>

The editor expects `make index` to have built glyphs-dataset/knn-index.joblib.
"""
import argparse
import os
import re
import sys
import tkinter as tk
from collections import defaultdict
from pathlib import Path
from tkinter import ttk

import fontforge
import joblib
import numpy as np
from PIL import Image, ImageTk
from skimage.feature import hog

PROJECT_DIR = Path(os.environ.get("project_dir"))
sys.path.insert(0, os.environ.get("script_dir"))
from font_helpers import (rasterize, resolve_font, is_pfb,
                          iter_labelled_glyphs, query_feature)
from config import font_dir
font_dir = Path(font_dir)

from io_glyph_data import read_lua_table_in_dict, is_unknown_codes, UNKNOWN_UNICODE
from unicode_descriptions import unicode_descr_for_code

def primary_name(cp_seq):
    """Best-effort human-readable name for a codepoint sequence.

    unicode_descr_for_code expects a hex *string* ('0x0041'), so each codepoint
    (possibly a numpy int from the k-NN bundle) is formatted before lookup.
    """
    if not cp_seq:
        return ""
    head = unicode_descr_for_code(f"0x{int(cp_seq[0]):04X}")
    if len(cp_seq) == 1:
        return head
    rest = " + ".join(unicode_descr_for_code(f"0x{int(cp):04X}")
                      for cp in cp_seq[1:])
    return f"{head} + {rest}"

def cp_seq_hex(seq):
    """Format a codepoint tuple/list as 'AAAA+BBBB' hex (no 0x prefix needed)."""
    return "+".join(f"{cp:04X}" for cp in seq)

def cp_seq_chars(seq):
    """Concatenated chr() string for a codepoint sequence (combining marks ok)."""
    out = []
    for cp in seq:
        try:
            out.append(chr(cp))
        except (ValueError, OverflowError):
            pass
    return "".join(out)

def vote_with_refs(distances, indices, seqs_all, names_all, top_k):
    grouped = defaultdict(lambda: {"vote": 0.0, "refs": []})
    for d, idx in zip(distances, indices):
        seq = tuple(seqs_all[int(idx)])
        grouped[seq]["vote"] += 1.0 / (float(d) + 1e-6)
        grouped[seq]["refs"].append((float(d), names_all[int(idx)]))
    out = []
    for seq, info in grouped.items():
        info["refs"].sort(key=lambda r: r[0])
        out.append((seq, info["vote"],
                    [name for _, name in info["refs"]]))
    out.sort(key=lambda x: -x[1])
    return out[:top_k]


# Math-friendly font fallbacks (Tk doesn't do CSS-style fallback, but the
# first that exists on the system will be picked at widget creation time).
SYMBOL_FONT_CANDIDATES = ("Latin Modern Math", "STIX Two Math",
                          "Noto Sans Math", "DejaVu Sans", "TkDefaultFont")


def first_available_font(root, candidates):
    from tkinter import font as tkfont
    families = set(tkfont.families(root))
    for c in candidates:
        if c in families or c == "TkDefaultFont":
            return c
    return "TkDefaultFont"


def parse_hex_codes(s):
    """Parse '0x003D, 0x0338' / '003D 0338' -> ['0x003D', '0x0338'].

    Returns None on any invalid token or empty input.
    """
    tokens = [t for t in re.split(r"[\s,]+", s.strip()) if t]
    if not tokens:
        return None
    out = []
    for t in tokens:
        t2 = t[2:] if t.lower().startswith("0x") else t
        try:
            out.append(f"0x{int(t2, 16):04X}")
        except ValueError:
            return None
    return out


class EditorApp:
    def __init__(self, root, args, bundle):
        self.root = root
        self.args = args
        self.bundle = bundle
        self.entries = []          # ordered list of dicts
        self.lua_dict = {}         # key -> [hex_str, ...]
        self.by_gid = False
        self.font_path = None
        self.lua_path = None
        self.photo_refs = []       # PhotoImage lifetime anchors
        self.current_key = None
        self.dataset_root = Path(args.dataset)

        self._setup_paths()
        self._build_ui()
        self._load_lua()
        self._predict()
        self._populate_tree()
        self.root.bind("<Escape>", lambda _e: self.root.destroy())

    # ----- paths and IO ----------------------------------------------------

    def _setup_paths(self):
        wd = Path(self.args.working_dir).resolve()
        if not font_dir or not font_dir.is_dir():
            sys.exit(f"Could not resolve font_dir from {wd}/config.py")
        fp = resolve_font(self.args.font, font_dir)
        if fp is None:
            sys.exit(f"Font not found: {self.args.font} (looked in {font_dir})")
        self.font_path = fp
        self.by_gid = not is_pfb(fp)
        self.lua_path = wd / f"{fp.stem}.lua"

    def _load_lua(self):
        if self.lua_path.is_file():
            self.lua_dict = read_lua_table_in_dict(str(self.lua_path)) or {}

    def _save_lua(self):
        """Atomic write of self.lua_dict to self.lua_path."""
        keys = list(self.lua_dict.keys())
        if self.by_gid:
            keys.sort(key=lambda k: int(k))
        else:
            keys.sort()
        tmp = self.lua_path.with_suffix(self.lua_path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("return {\n")
            for k in keys:
                codes = self.lua_dict[k]
                if not codes:
                    continue
                f.write(f"  ['{k}'] = {{ {', '.join(codes)} }},\n")
            f.write("  }\n")
        os.replace(tmp, self.lua_path)

    # ----- inference -------------------------------------------------------

    def _predict(self):
        self._set_status(f"Rendering {self.font_path.name} ...")
        self.root.update_idletasks()
        nn = self.bundle["index"]
        seqs_all = self.bundle["codepoint_seqs"]
        names_all = self.bundle["names"]
        hog_params = self.bundle["hog_params"]
        size_weight = self.bundle.get("size_weight", 0.0)

        # The work-list is always <font>.lua, never the whole font: initial-
        # lua.py decides which glyphs the table holds, and new glyphs are added
        # by hand after checking the .html.  By default we recognise only the
        # entries still marked "unknown" (the 0xFFFD sentinel); --all-glyphs
        # widens this to every entry in the table, so already-resolved values
        # can be revised too.  Glyphs absent from the table are never scanned.
        if self.args.all_glyphs:
            target_keys = set(self.lua_dict.keys())
        else:
            target_keys = {k for k, codes in self.lua_dict.items()
                           if is_unknown_codes(codes)}

        font = fontforge.open(str(self.font_path))
        try:
            for key, g in iter_labelled_glyphs(font, self.by_gid):
                if key not in target_keys:
                    continue
                if not g.isWorthOutputting():
                    continue
                arr = rasterize(g, self.args.pixelsize,
                                self.args.size, self.args.margin)
                if arr is None:
                    continue
                feat = query_feature(arr, font, g, hog_params, size_weight)
                distances, indices = nn.kneighbors(
                    feat, n_neighbors=self.args.k_neighbors,
                    return_distance=True)
                ranked = vote_with_refs(distances[0], indices[0],
                                        seqs_all, names_all, self.args.top_k)
                self.entries.append({
                    "key": key,
                    "image": arr,
                    "candidates": ranked,
                })
        finally:
            font.close()

        if self.by_gid:
            self.entries.sort(key=lambda e: int(e["key"]))
        else:
            self.entries.sort(key=lambda e: e["key"])

        missing = target_keys - {e["key"] for e in self.entries}
        if not target_keys:
            if self.args.all_glyphs:
                msg = f"{self.lua_path} has no entries to review."
            else:
                msg = (f"No 'unknown' ({UNKNOWN_UNICODE}) entries in "
                       f"{self.lua_path} — nothing to recognise. "
                       f"Add ALL=1 to review every entry in the table.")
        else:
            if self.args.all_glyphs:
                msg = (f"{len(self.entries)} of {len(target_keys)} entries in "
                       f"{self.lua_path} to review")
            else:
                msg = (f"{len(self.entries)} unknown glyph(s) to recognise in "
                       f"{self.font_path.name}; editing {self.lua_path}")
            if missing:
                msg += (f"  [{len(missing)} entry/entries not renderable, "
                        f"e.g. {sorted(missing)[:3]}]")
        self._set_status(msg)

    # ----- UI construction ------------------------------------------------

    def _build_ui(self):
        self.root.title(f"Edit Lua: {self.args.font}")
        self.root.geometry("1280x780")

        # Larger fonts for the glyph list (Treeview) and the Custom entry.
        ts = max(7, int(self.args.text_size))
        style = ttk.Style()
        style.configure("Treeview",
                        font=("TkDefaultFont", ts),
                        rowheight=int(ts * 2.2))
        style.configure("Treeview.Heading",
                        font=("TkDefaultFont", ts, "bold"))
        self._custom_font = ("TkFixedFont", ts)

        # --- Top header: persistent save-target + Quit ---
        header = tk.Frame(self.root, bg="#eef6ff", bd=1, relief=tk.SUNKEN)
        header.pack(side=tk.TOP, fill=tk.X)
        tk.Label(header, text="Auto-saving to:",
                 bg="#eef6ff", font=("TkDefaultFont", 10, "bold")
                 ).pack(side=tk.LEFT, padx=(8, 4), pady=4)
        tk.Label(header, text=str(self.lua_path),
                 bg="#eef6ff", font=("TkFixedFont", 10), fg="#1a3a5c"
                 ).pack(side=tk.LEFT, pady=4)
        tk.Button(header, text="Quit", command=self.root.destroy
                  ).pack(side=tk.RIGHT, padx=6, pady=2)

        # --- Bottom status bar (transient) ---
        self.status_var = tk.StringVar(value="Initializing...")
        tk.Label(self.root, textvariable=self.status_var,
                 anchor="w", relief=tk.SUNKEN, bd=1
                 ).pack(side=tk.BOTTOM, fill=tk.X)

        paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL,
                               sashrelief=tk.RAISED, sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True)

        # --- Left: glyph list ---
        left = tk.Frame(paned)
        cols = ("key", "current", "top1")
        self.tree = ttk.Treeview(left, columns=cols, show="headings",
                                 selectmode="browse")
        self.tree.heading("key", text=("GID" if self.by_gid else "Glyph"))
        self.tree.heading("current", text="Lua value")
        self.tree.heading("top1", text="Predicted top-1")
        self.tree.column("key", width=160, anchor="w")
        self.tree.column("current", width=160, anchor="w")
        self.tree.column("top1", width=160, anchor="w")
        ysb = tk.Scrollbar(left, command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        paned.add(left, minsize=460)

        # --- Right: detail ---
        right = tk.Frame(paned)
        paned.add(right, minsize=700)
        self.right = right

        self.detail_header = tk.Label(right, font=("TkDefaultFont", 16, "bold"))
        self.detail_header.pack(pady=(8, 4))
        self.glyph_img_label = tk.Label(right, bg="#fafafa", relief=tk.SUNKEN, bd=1)
        self.glyph_img_label.pack()
        self.current_value_label = tk.Label(right, font=("TkFixedFont", 11),
                                            fg="#444")
        self.current_value_label.pack(pady=4)

        self.symbol_font = first_available_font(self.root,
                                                SYMBOL_FONT_CANDIDATES)
        self.cands_frame = tk.Frame(right)
        self.cands_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    # ----- tree population and updates ------------------------------------

    def _populate_tree(self):
        for e in self.entries:
            self.tree.insert("", "end", iid=e["key"],
                             values=(e["key"], self._format_current(e["key"]),
                                     self._format_top1(e)))
        first = self.tree.get_children()
        if first:
            self.tree.selection_set(first[0])
            self.tree.focus(first[0])
            self.tree.see(first[0])

    def _format_current(self, key):
        codes = self.lua_dict.get(key)
        if not codes:
            return "—"
        return ", ".join(codes)

    def _format_top1(self, entry):
        if not entry["candidates"]:
            return ""
        seq, vote, _ = entry["candidates"][0]
        return f"0x{cp_seq_hex(seq)} ({vote:.1f})"

    def _set_status(self, text):
        self.status_var.set(text)

    # ----- selection + detail rendering -----------------------------------

    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        key = sel[0]
        entry = next((e for e in self.entries if e["key"] == key), None)
        if entry is None:
            return
        self.current_key = key
        self._render_detail(entry)

    def _render_detail(self, entry):
        for w in self.cands_frame.winfo_children():
            w.destroy()
        self.photo_refs.clear()

        self.detail_header.config(text=str(entry["key"]))
        arr_u8 = (entry["image"] * 255).astype("uint8")
        big = Image.fromarray(arr_u8).resize((128, 128), Image.NEAREST)
        photo = ImageTk.PhotoImage(big)
        self.photo_refs.append(photo)
        self.glyph_img_label.config(image=photo)
        self.current_value_label.config(
            text=f"current Lua value: {self._format_current(entry['key'])}")

        for col, (seq, vote, ref_paths) in enumerate(entry["candidates"]):
            cell = tk.Frame(self.cands_frame, relief=tk.RIDGE, bd=1,
                            padx=8, pady=8, bg="#fafafa")
            cell.grid(row=0, column=col, padx=4, pady=4, sticky="n")
            tk.Label(cell, text=f"0x{cp_seq_hex(seq)}",
                     font=("TkFixedFont", 11), fg="#c41a16",
                     bg="#fafafa").pack()
            tk.Label(cell, text=f"vote {vote:.2f}",
                     font=("TkDefaultFont", 9),
                     fg="#666", bg="#fafafa").pack()
            ch = cp_seq_chars(seq) or "?"
            tk.Label(cell, text=ch,
                     font=(self.symbol_font, 32),
                     bg="#fafafa").pack(pady=2)
            tk.Label(cell, text=primary_name(seq),
                     wraplength=170, font=("TkDefaultFont", 9),
                     fg="#333", bg="#fafafa", justify="center").pack()
            refs_row = tk.Frame(cell, bg="#fafafa")
            refs_row.pack(pady=4)
            for rp in ref_paths[:3]:
                try:
                    rimg = Image.open(self.dataset_root / rp).resize(
                        (40, 40), Image.NEAREST)
                    rphoto = ImageTk.PhotoImage(rimg)
                    self.photo_refs.append(rphoto)
                    tk.Label(refs_row, image=rphoto, bg="#fafafa"
                             ).pack(side=tk.LEFT, padx=1)
                except FileNotFoundError:
                    pass
            tk.Button(cell, text="Apply",
                      command=lambda k=entry["key"], s=seq: self._apply(k, s)
                      ).pack(pady=(6, 0))

        # --- Manual override row ---
        custom_row = tk.Frame(self.cands_frame)
        custom_row.grid(row=1, column=0, columnspan=99, pady=(12, 4),
                        sticky="ew")
        tk.Label(custom_row, text="Custom codepoints (hex):"
                 ).pack(side=tk.LEFT)
        self.custom_var = tk.StringVar(
            value=", ".join(self.lua_dict.get(entry["key"], [])))
        custom_entry = tk.Entry(custom_row, textvariable=self.custom_var,
                                width=32, font=self._custom_font)
        custom_entry.pack(side=tk.LEFT, padx=4)
        tk.Button(custom_row, text="Apply custom",
                  command=lambda k=entry["key"]: self._apply_custom(k)
                  ).pack(side=tk.LEFT)
        custom_entry.bind(
            "<Return>", lambda _e, k=entry["key"]: self._apply_custom(k))

        tk.Button(self.cands_frame,
                  text=f"Mark unknown ({UNKNOWN_UNICODE})",
                  fg="#7a1fa2",
                  command=lambda k=entry["key"]: self._mark_unknown(k)
                  ).grid(row=2, column=0, columnspan=99, pady=4)
        tk.Button(self.cands_frame, text="Clear current",
                  command=lambda k=entry["key"]: self._apply(k, None)
                  ).grid(row=3, column=0, columnspan=99, pady=4)
        tk.Button(self.cands_frame, text="Skip (next)",
                  command=self._advance
                  ).grid(row=4, column=0, columnspan=99, pady=4)

    # ----- mutation -------------------------------------------------------

    def _apply(self, key, seq):
        if seq is None:
            self.lua_dict.pop(key, None)
        else:
            self.lua_dict[key] = [f"0x{cp:04X}" for cp in seq]
        self._save_lua()
        self.tree.set(key, "current", self._format_current(key))
        self._set_status(f"Saved {self.lua_path}")
        self._advance()

    def _mark_unknown(self, key):
        """Flag a glyph with the sentinel so a future pass re-searches it.

        Useful when the current value is wrong or the font itself has an
        erroneous/mis-named glyph: writing 0xFFFD puts the glyph (back) into
        the work-list that the default edit_knn mode recognises.
        """
        self.lua_dict[key] = [UNKNOWN_UNICODE]
        self._save_lua()
        self.tree.set(key, "current", self._format_current(key))
        self._set_status(f"Marked {key} unknown ({UNKNOWN_UNICODE}); "
                         f"will be re-searched next pass")
        self._advance()

    def _apply_custom(self, key):
        s = self.custom_var.get().strip()
        if not s:
            self._apply(key, None)
            return
        codes = parse_hex_codes(s)
        if codes is None:
            self._set_status(f"Cannot parse '{s}' as hex codepoint(s)")
            return
        self._apply(key, tuple(int(c, 16) for c in codes))

    def _advance(self):
        if not self.current_key:
            return
        nxt = self.tree.next(self.current_key)
        if nxt:
            self.tree.selection_set(nxt)
            self.tree.focus(nxt)
            self.tree.see(nxt)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("font", help="Font name (PFB/OTF/TTF) e.g. mt2syaf")
    ap.add_argument("--index",
                    default=str(PROJECT_DIR / "glyphs-dataset" / "knn-index.joblib"))
    ap.add_argument("--dataset", default=str(PROJECT_DIR / "glyphs-dataset"))
    ap.add_argument("--working-dir",
                    default=os.environ.get("working_dir") or os.getcwd())
    ap.add_argument("--k-neighbors", type=int, default=20)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--size", type=int, default=64)
    ap.add_argument("--margin", type=int, default=4)
    ap.add_argument("--pixelsize", type=int, default=64)
    ap.add_argument("--text-size", type=int, default=11,
                    help="Font size for the glyph list and Custom entry "
                    "(default 11; try 14 or 16 for a bigger view)")
    ap.add_argument("--all-glyphs", action="store_true",
                    help="Review every entry already in <font>.lua, not only "
                    f"the ones marked unknown ({UNKNOWN_UNICODE}).  Never "
                    "scans glyphs absent from the table.  Default: only the "
                    "unknown entries.")
    args = ap.parse_args()

    if not Path(args.index).is_file():
        sys.exit(f"Index not found: {args.index}\n"
                 f"Run `make index` at project root first.")
    bundle = joblib.load(args.index)
    root = tk.Tk()
    EditorApp(root, args, bundle)
    root.mainloop()


if __name__ == "__main__":
    main()
