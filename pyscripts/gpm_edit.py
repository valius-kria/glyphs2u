#!/usr/bin/env python3
"""Tkinter editor for the axes no automatic step can settle.

The other steps fill what can be derived: the codepoint already assigned says
which properties Unicode ascribes to it, and a font-pair raster comparison
settles one axis mechanically.  What is left needs looking at the glyph --
whether a font is really sans-serif though nothing declares it, whether these
digits are slanted -- and, for glyphs whose names mean nothing, what the base
character even is.

Two panels, because the work has two scales:

  FONT LEVEL   the four axes for the whole font, each with its provenance.
               An axis nothing has answered ("?") is the interesting one:
               stix-mathsf declares no family and is sans-serif throughout.
               Answered once here, every glyph inherits it.

  GLYPH        the k-NN index built by glyphs2u (`make index` there) proposes
               codepoints for the rendered glyph; each proposal decomposes
               into a base plus axes, so clicking one sets both.  The axis
               buttons override any of it, and 'inherit' drops the glyph's own
               value so the font level shows through again.

  SIZE CUT     which cut of a stretchable character this glyph is, ranked from
               the font metrics (gpm_ladder) -- a different question from the
               k-NN one, which says which CHARACTER.  The ladder is shown so
               the ranking can be seen, not just taken.

Everything set here is written with status "visual", which the automatic steps
will not overwrite.  The record is saved after every click.

Work list (left):
  default    glyphs whose base is still '?'
  --axis AX  glyphs that have no value of their own for axis AX -- the sweep
             for confirming one property across the font
  --sizes    glyphs that are a cut of a stretchable character and whose
             sequence is not yet recorded (or differs from the measurement)
  --review   every glyph

Usage: gpm_edit.py <font> [--axis style] [--review] [--glyphs2u DIR]
"""
import argparse, collections, os, re, sys, tkinter as tk
import unicodedata
from collections import defaultdict
from tkinter import ttk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G
from gpm_ladder import Ladder

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("--data", default=G.DATA)
ap.add_argument("--gpm")
ap.add_argument("--glyphs2u", default=os.environ.get("glyphs2u_dir"),
                help="the glyphs2u checkout (k-NN index + rasterizer)")
ap.add_argument("--axis", choices=G.AXES, help="sweep one axis")
ap.add_argument("--review", action="store_true", help="list every glyph")
ap.add_argument("--sizes", action="store_true",
                help="list the glyphs with a size-cut proposal not yet recorded")
ap.add_argument("--pos", help="work on exactly these htf positions -- '24', "
                    "'20-30', '24,61,63'.  For checking a page and then jumping "
                    "to the few rows that need a decision, instead of stepping "
                    "through every glyph")
ap.add_argument("--k-neighbors", type=int, default=25)
ap.add_argument("--top-k", type=int, default=6)
ap.add_argument("--pixelsize", type=int, default=200)
ap.add_argument("--size", type=int, default=64)
ap.add_argument("--margin", type=int, default=4)
ap.add_argument("--text-size", type=int, default=10)
a = ap.parse_args()

GPM = a.gpm or f"{a.font}.gpm.json"
rec = G.load(GPM)
# Sizes: which cut of a stretchable character this glyph is.  A different
# question from the k-NN one -- that says WHICH CHARACTER, this says WHICH CUT
# -- and answered from the font metrics rather than from the picture.
ladder = Ladder(a.font, data=a.data)
var = G.Variants(a.data)

# --- optional: the glyphs2u classifier --------------------------------------
# Without it the editor still works -- the glyph is shown from the dvipng
# rasters this project already makes, only the proposals are missing.
knn = None
def load_knn():
    """(bundle, font_helpers, fontforge) or None, with the reason printed."""
    if not a.glyphs2u:
        print("gpm_edit: no glyphs2u dir (set glyphs2u_dir or pass --glyphs2u); "
              "candidates disabled", file=sys.stderr)
        return None
    idx = os.path.join(a.glyphs2u, "glyphs-dataset", "knn-index.joblib")
    if not os.path.exists(idx):
        print(f"gpm_edit: {idx} missing -- run `make index` in glyphs2u; "
              "candidates disabled", file=sys.stderr)
        return None
    try:
        os.environ.setdefault("project_dir", a.glyphs2u)
        sys.path.insert(0, os.path.join(a.glyphs2u, "pyscripts"))
        import joblib, fontforge                       # noqa: F401
        import font_helpers
        return joblib.load(idx), font_helpers, fontforge
    except Exception as e:                             # missing joblib/skimage/...
        print(f"gpm_edit: classifier unavailable ({e}); candidates disabled",
              file=sys.stderr)
        return None

def pfb_path():
    p = f"{a.font}.pfb.path"
    if os.path.exists(p):
        return open(p, encoding="utf-8").read().strip()
    return None

def vote(distances, indices, seqs, names, top_k):
    """Same inverse-distance vote as glyphs2u's editor, so the two agree."""
    grouped = defaultdict(lambda: {"vote": 0.0, "refs": []})
    for d, i in zip(distances, indices):
        seq = tuple(seqs[int(i)])
        grouped[seq]["vote"] += 1.0 / (float(d) + 1e-6)
        grouped[seq]["refs"].append((float(d), names[int(i)]))
    out = [(s, v["vote"]) for s, v in grouped.items()]
    out.sort(key=lambda x: -x[1])
    return out[:top_k]

# --- work list --------------------------------------------------------------
WANT = G.parse_positions(a.pos) if a.pos else set()
def worklist():
    """The glyphs to walk through, and a note when there are none."""
    items, note = [], None
    for gname, g in sorted(rec["glyphs"].items(),
                           key=lambda kv: kv[1].get("pos", 1 << 30)):
        if a.pos:
            if g.get("pos") in WANT or any(x.get("pos") in WANT
                                           for x in g.get("alt") or ()):
                items.append(gname)
        elif a.review:
            items.append(gname)
        elif a.sizes:
            p = ladder.proposal(gname, g)
            if p and g.get("uni") != p["codes"]:
                items.append(gname)
        elif a.axis:
            if a.axis not in g.get("props", {}):
                items.append(gname)
        elif G.is_open(rec, g):
            items.append(gname)
    if not items:
        note = empty_reason()
    return items, note

def empty_reason():
    """Why the work list is empty -- an empty window otherwise reads as a
    failure, when usually it means the work is done."""
    n = len(rec["glyphs"])
    if a.sizes:
        prop = [(gn, ladder.proposal(gn, g)) for gn, g in rec["glyphs"].items()]
        prop = [(gn, p) for gn, p in prop if p]
        if not ladder.ok:
            return (f"no metrics for {a.font} -- run `make {a.font}.metrics.json`, "
                    f"without them no size cut can be ranked")
        if not prop:
            return (f"none of this font's {n} glyphs is a size cut of a "
                    f"stretchable character -- nothing to rank")
        done = sum(1 for gn, p in prop
                   if rec["glyphs"][gn].get("uni") == p["codes"])
        srcs = collections.Counter(
            rec["glyphs"][gn]["status"].get("uni") for gn, p in prop
            if rec["glyphs"][gn].get("uni") == p["codes"])
        how = ", ".join(f"{v} from '{k}'" for k, v in srcs.most_common())
        return (f"all {len(prop)} size cut(s) already recorded and matching the "
                f"measurement ({how}) -- nothing to confirm")
    if a.pos:
        have = sorted(g.get("pos") for g in rec["glyphs"].values()
                      if g.get("pos") is not None)
        return (f"no glyph of {a.font} sits at position(s) {sorted(WANT)} -- "
                f"this font covers {have[0]}..{have[-1]}" if have else
                f"{a.font} has no positioned glyphs")
    if a.axis:
        return (f"every glyph has a {a.axis} of its own -- nothing left to sweep")
    if a.review:
        return f"{a.font} has no glyphs in its record"
    return (f"no glyph is still unrecognised (base '?') in {a.font} -- "
            f"try REVIEW=1, SIZES=1, or AXIS=<axis>")

class App:
    def __init__(self, root):
        self.root = root
        self.keys, self.empty_note = worklist()
        self.cands = {}            # glyph name -> [(codepoint seq, vote)]
        self.images = {}           # glyph name -> PhotoImage
        self._build()
        self._predict()
        self._fill_tree()
        root.bind("<Escape>", lambda _e: root.destroy())

    # ----- data ------------------------------------------------------------
    def _predict(self):
        global knn
        if self.empty_note:
            self._status(self.empty_note)
            print(f"gpm_edit: {self.empty_note}")
            return
        knn = load_knn()
        if not knn:
            self._status(f"{len(self.keys)} glyph(s) to review; no classifier, "
                         f"showing the rasters only")
            return
        bundle, fh, fontforge = knn
        path = pfb_path()
        if not path:
            self._status("no <font>.pfb.path -- run `make <font>.pfb.path`")
            return
        self._status(f"rendering {os.path.basename(path)} ...")
        self.root.update_idletasks()
        nn, seqs = bundle["index"], bundle["codepoint_seqs"]
        names, hp = bundle["names"], bundle["hog_params"]
        sw = bundle.get("size_weight", 0.0)
        font = fontforge.open(path)
        try:
            todo = set(self.keys)
            for gname in font:
                if gname not in todo:
                    continue
                g = font[gname]
                if not g.isWorthOutputting():
                    continue
                arr = fh.rasterize(g, a.pixelsize, a.size, a.margin)
                if arr is None:
                    continue
                feat = fh.query_feature(arr, font, g, hp, sw)
                d, i = nn.kneighbors(feat, n_neighbors=a.k_neighbors,
                                     return_distance=True)
                self.cands[gname] = vote(d[0], i[0], seqs, names, a.top_k)
        finally:
            font.close()
        self._status(f"{len(self.keys)} glyph(s) to review; "
                     f"{len(self.cands)} with proposals")

    def _save(self):
        G.save(rec, GPM)

    # ----- ui --------------------------------------------------------------
    def _build(self):
        r = self.root
        r.title(f"gpm: {a.font}")
        r.geometry("1300x820")
        ts = max(7, a.text_size)
        # Row height first, then the thumbnails are scaled to fit it.  The
        # fontforge exports are 100..377 px tall (a big delimiter is three ems),
        # so a fixed subsample crops them against any sane row.
        self.thumb_h = max(24, int(ts * 3.0))
        # and a width limit too: a wide accent is 2.3 em against a delimiter's
        # 0.2, so fitting the height alone lets it spill over the next column
        self.thumb_w = max(40, int(ts * 6.0))
        ttk.Style().configure("Treeview", font=("TkDefaultFont", ts),
                              rowheight=self.thumb_h + 6)

        head = tk.Frame(r, bg="#eef6ff", bd=1, relief=tk.SUNKEN)
        head.pack(side=tk.TOP, fill=tk.X)
        tk.Label(head, text="auto-saving to:", bg="#eef6ff",
                 font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=(8, 4), pady=4)
        tk.Label(head, text=os.path.abspath(GPM), bg="#eef6ff",
                 font=("TkFixedFont", 10), fg="#1a3a5c").pack(side=tk.LEFT, pady=4)
        tk.Button(head, text="Quit", command=r.destroy).pack(side=tk.RIGHT, padx=6, pady=2)

        self.status_var = tk.StringVar(value="...")
        tk.Label(r, textvariable=self.status_var, anchor="w",
                 relief=tk.SUNKEN, bd=1).pack(side=tk.BOTTOM, fill=tk.X)

        # --- font-level panel ---
        fl = tk.LabelFrame(r, text="font level — inherited by every glyph",
                           padx=8, pady=6)
        fl.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)
        self.fvars, self.flabels = {}, {}
        for col, ax in enumerate(G.AXES):
            box = tk.Frame(fl)
            box.grid(row=0, column=col, padx=10, sticky="w")
            self.flabels[ax] = tk.Label(box)
            self.flabels[ax].pack(anchor="w")
            v = tk.StringVar(value=rec.get("props", {}).get(ax, "normal"))
            self.fvars[ax] = v
            om = ttk.OptionMenu(box, v, v.get(), *G.AXIS_VALUES[ax],
                                command=lambda _val, ax=ax: self._set_font_axis(ax))
            om.pack(anchor="w")
        self._refresh_font_labels()

        paned = tk.PanedWindow(r, orient=tk.HORIZONTAL, sashrelief=tk.RAISED,
                               sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(paned)
        cols = ("pos", "glyph", "base", "mv")
        self.tree = ttk.Treeview(left, columns=cols, show="tree headings",
                                 selectmode="browse")
        for c, w in zip(cols, (50, 150, 60, 190)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w")
        self.tree.column("#0", width=self.thumb_w + 10, stretch=False,
                         anchor="center")
        sb = tk.Scrollbar(left, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._select())
        paned.add(left, minsize=560)

        right = tk.Frame(paned)
        paned.add(right, minsize=700)
        self.header = tk.Label(right, font=("TkDefaultFont", 15, "bold"))
        self.header.pack(pady=(8, 2))
        self.big = tk.Label(right, bg="#fafafa", relief=tk.SUNKEN, bd=1)
        self.big.pack()

        # per-glyph axes
        gl = tk.LabelFrame(right, text="this glyph — overrides the font level",
                           padx=8, pady=6)
        gl.pack(fill=tk.X, padx=8, pady=8)
        self.gvars = {}
        for col, ax in enumerate(G.AXES):
            box = tk.Frame(gl)
            box.grid(row=0, column=col, padx=8, sticky="w")
            var, lab = tk.StringVar(value="inherit"), tk.Label(box, text=ax)
            lab.pack(anchor="w")
            ttk.OptionMenu(box, var, "inherit",
                           *(("inherit",) + G.AXIS_VALUES[ax]),
                           command=lambda _v, ax=ax: self._set_glyph_axis(ax)
                           ).pack(anchor="w")
            # One click for the common case.  Saying "this glyph does not
            # inherit the font-level property" through the OptionMenu costs two
            # clicks -- open it, then pick 'normal' -- and it is the edit made
            # most often.  The button's LABEL is what one click will do, so it
            # needs no explanation: 'normal' while the glyph inherits, and
            # 'inherit' once it has a value of its own, which also makes it the
            # undo for a value set by mistake.
            btn = tk.Button(box, width=7,
                            command=lambda ax=ax: self._toggle_inherit(ax))
            btn.pack(anchor="w", pady=(2, 0))
            self.gvars[ax] = (var, lab, btn)

        bl = tk.Frame(right)
        bl.pack(fill=tk.X, padx=8)
        tk.Label(bl, text="base:").pack(side=tk.LEFT)
        self.base_var = tk.StringVar()
        e = tk.Entry(bl, textvariable=self.base_var, width=18,
                     font=("TkFixedFont", 12))
        e.pack(side=tk.LEFT, padx=4)
        e.bind("<Return>", lambda _ev: self._set_base_manual())
        tk.Button(bl, text="set base", command=self._set_base_manual).pack(side=tk.LEFT)
        tk.Button(bl, text="next", command=self._next).pack(side=tk.RIGHT)
        # what the base actually is: a bare character says nothing when it is a
        # combining mark or something unprintable in this font
        self.base_info = tk.Label(right, font=("TkDefaultFont", 9), fg="#555",
                                  anchor="w", justify="left")
        self.base_info.pack(fill=tk.X, padx=8, pady=(2, 0))

        self.cands_frame = tk.Frame(right)
        self.cands_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.size_frame = tk.LabelFrame(right, text="size cut", padx=8, pady=6)
        self.size_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

    def _refresh_font_labels(self):
        """An axis nothing has answered is the one worth answering: flagged."""
        for ax, lab in self.flabels.items():
            st = rec.get("status", {}).get(ax, G.UNKNOWN)
            unset = st == G.UNKNOWN
            lab.config(text=f"{ax}  ({st})", fg="#c41a16" if unset else "#333",
                       font=("TkDefaultFont", 9, "bold" if unset else "normal"))

    def _status(self, t):
        self.status_var.set(t)

    # ----- tree ------------------------------------------------------------
    def _row(self, gname):
        g = rec["glyphs"][gname]
        return (g.get("pos", ""), gname, g.get("base", G.UNKNOWN),
                G.mv_token(G.effective(rec, g)) or "—")

    def _fill_tree(self):
        for gname in self.keys:
            img = self._thumb(gname)
            self.tree.insert("", "end", iid=gname, values=self._row(gname),
                             image=img if img else "")
        kids = self.tree.get_children()
        if kids:
            self.tree.selection_set(kids[0])
            self.tree.focus(kids[0])

    def _refresh_row(self, gname):
        self.tree.item(gname, values=self._row(gname))

    def _thumb(self, gname):
        """A picture of the glyph: the fontforge export if it is there, else
        the dvipng raster the font-pair comparison produced."""
        g = rec["glyphs"].get(gname, {})
        p = G.glyph_image(a.font, gname, g.get("slot"))
        if p is None:
            return None
        if gname not in self.images:
            try:
                img = tk.PhotoImage(file=p)
                # subsample takes integers, so round the factor up: better a
                # little small than cropped
                k = max(1, -(-img.height() // self.thumb_h),
                        -(-img.width() // self.thumb_w))
                self.images[gname] = img.subsample(k, k) if k > 1 else img
            except tk.TclError:
                return None
        return self.images[gname]

    # ----- selection -------------------------------------------------------
    def _current(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _select(self):
        gname = self._current()
        if not gname:
            return
        g = rec["glyphs"][gname]
        self.header.config(text=f"{gname}   pos {g.get('pos', '?')}   "
                                f"htf {g.get('htf_value') or '—'}")
        img = self._thumb(gname)
        self.big.config(image=img if img else "", text="" if img else "(no raster)")
        b = g.get("base", G.UNKNOWN)
        self.base_var.set("" if b == G.UNKNOWN else b)
        self.base_info.config(text=self._base_text(b))
        self._refresh_axes(gname)
        self._render_candidates(gname)
        self._render_size(gname)

    def _refresh_axes(self, gname=None):
        """The four axis widgets, and nothing else.

        Split out of _select() because an axis edit used to call _select(),
        which ends in _render_candidates() -- and that destroys and rebuilds
        every proposal widget and its thumbnail.  The proposals themselves are
        computed once, at startup, in _predict(); the rebuild was pure flicker,
        and it read as if the classifier had gone and thought again.
        """
        gname = gname or self._current()
        if not gname:
            return
        g = rec["glyphs"][gname]
        eff = G.effective(rec, g)
        for ax in G.AXES:
            v, lab, btn = self.gvars[ax]
            own = g.get("props", {}).get(ax)
            v.set(own if own else "inherit")
            src = g.get("status", {}).get(ax) if own else \
                rec.get("status", {}).get(ax, G.UNKNOWN)
            lab.config(text=f"{ax}: {eff[ax]} ({src})")
            btn.config(text="inherit" if own else "normal")

    def _render_size(self, gname):
        """The ladder this glyph sits in, and the sequence that follows."""
        for w in self.size_frame.winfo_children():
            w.destroy()
        g = rec["glyphs"][gname]
        p = ladder.proposal(gname, g)
        if p is None:
            # Show the ladder anyway where there is one: the commonest reason
            # for no proposal is that this IS the text cut, and seeing the cuts
            # above it says so better than any wording.
            stem = gname.split(".")[0]
            cuts = ladder.cuts(stem) if ladder.ok else []
            if len(cuts) > 1:
                rungs = "   ".join(
                    ("[%s %.2f]" if n == gname else "%s %.2f")
                    % (n.split(".")[-1] if "." in n else "(plain)", sz)
                    for sz, n in cuts)
                tk.Label(self.size_frame, text=rungs, font=("TkFixedFont", 10),
                         fg="#333").pack(anchor="w")
            tk.Label(self.size_frame, text=self._size_reason(gname, g),
                     fg="#888").pack(anchor="w")
            return
        rungs = "   ".join(
            ("[%s %.2f]" if n == gname else "%s %.2f")
            % (n.split(".")[-1] if "." in n else "(plain)", sz)
            for sz, n in p["ladder"])
        tk.Label(self.size_frame, text=rungs, font=("TkFixedFont", 10),
                 fg="#333").pack(anchor="w")
        seq = " ".join(p["codes"])
        row = tk.Frame(self.size_frame)
        row.pack(fill=tk.X, pady=(4, 0))
        tk.Label(row, text=f"cut {p['rank']} of {p['of']}  ->  {seq}",
                 font=("TkFixedFont", 11), fg="#c41a16").pack(side=tk.LEFT)
        cur = g.get("uni")
        if cur == p["codes"]:
            tk.Label(row, text="  already recorded", fg="#2a7").pack(side=tk.LEFT)
        else:
            if cur:
                tk.Label(row, text=f"  (now {' '.join(cur)})",
                         fg="#888").pack(side=tk.LEFT)
            tk.Button(row, text="accept",
                      command=lambda c=p["codes"]: self._accept_uni(c)
                      ).pack(side=tk.LEFT, padx=8)

    def _size_reason(self, gname, g):
        """Why this glyph has no size proposal -- the cases differ a lot."""
        if not ladder.ok:
            return f"no metrics -- run `make {a.font}.metrics.json`"
        char = G.char_at(g)
        if char is None:
            return "no base recorded yet, so nothing to build a sequence on"
        if ladder.flags(char) is None and ladder.flags(g.get("base") or "") is None:
            return f"{char!r} is not a character that takes size cuts"
        stem = gname.split(".")[0]
        if gname in ladder.assembly(stem):
            return ("an assembly piece (shares an advance with the others) -- "
                    "part of a construction, not a size")
        cuts = ladder.cuts(stem)
        if len(cuts) < 2:
            return "the only cut of this character in this font"
        plain = [n for _, n in cuts if "." not in n]
        if plain and gname == plain[0]:
            return "this is the text cut -- written plain, it takes no selector"
        if not plain and ladder.size(gname) == cuts[0][0]:
            return "the smallest cut here -- would be FE01, but it already is"
        return "smaller than the text cut -- left alone, nothing sits below FE01"

    def _accept_uni(self, codes):
        gname = self._current()
        if not gname:
            return
        G.set_uni(rec["glyphs"][gname], codes, "visual", force=True)
        self._save()
        self._render_size(gname)
        self._status(f"{gname} uni = {' '.join(codes)} (visual)")

    def _render_candidates(self, gname):
        for w in self.cands_frame.winfo_children():
            w.destroy()
        cands = self.cands.get(gname) or []
        if not cands:
            tk.Label(self.cands_frame, fg="#888",
                     text="no proposals — set the base and axes by hand"
                     ).pack(anchor="w")
            return
        tk.Label(self.cands_frame, text="k-NN proposals (click to accept base "
                 "and the properties it implies):", fg="#333").pack(anchor="w")
        row = tk.Frame(self.cands_frame)
        row.pack(fill=tk.X, pady=4)
        for col, (seq, v) in enumerate(cands):
            ch = "".join(chr(int(c)) for c in seq)
            # a k-NN label may carry a size selector (parenleftbig = 0028 FE01);
            # that belongs in ['uni'], never in the base, which stays the plain
            # character the htf side emits
            core, _had = G.split_selectors(ch)
            base, props = (var.decompose(core) if len(core) == 1 else (core, {}))
            cell = tk.Frame(row, relief=tk.RIDGE, bd=1, padx=6, pady=6, bg="#fafafa")
            cell.grid(row=0, column=col, padx=4, sticky="n")
            tk.Label(cell, text=ch, font=("TkDefaultFont", 26), bg="#fafafa").pack()
            tk.Label(cell, text="+".join(f"{int(c):04X}" for c in seq),
                     font=("TkFixedFont", 9), fg="#c41a16", bg="#fafafa").pack()
            tk.Label(cell, text=f"base {base}", bg="#fafafa",
                     font=("TkDefaultFont", 10)).pack()
            tk.Label(cell, text=", ".join(f"{k}={w}" for k, w in props.items()) or "—",
                     bg="#fafafa", fg="#555", font=("TkDefaultFont", 8),
                     wraplength=140).pack()
            tk.Button(cell, text=f"accept ({v:.1f})",
                      command=lambda b=base, p=props, s=seq:
                          self._accept(b, p, s)).pack(pady=2)

    # ----- edits -----------------------------------------------------------
    def _set_font_axis(self, ax):
        rec.setdefault("props", {})[ax] = self.fvars[ax].get()
        rec.setdefault("status", {})[ax] = "visual"
        self._save()
        self._refresh_font_labels()
        for gname in self.keys:
            self._refresh_row(gname)
        # the font level moved, so every glyph's EFFECTIVE value may have moved
        # with it -- but the k-NN proposals did not, so do not touch them
        self._refresh_axes()
        self._status(f"font level {ax} = {self.fvars[ax].get()} (visual)")

    def _set_glyph_axis(self, ax, val=None):
        """Set one axis of the current glyph.  val=None reads the OptionMenu."""
        gname = self._current()
        if not gname:
            return
        g = rec["glyphs"][gname]
        if val is None:
            val = self.gvars[ax][0].get()
        if val == "inherit":
            g.get("props", {}).pop(ax, None)
            g.get("status", {}).pop(ax, None)
        else:
            G.set_axis(g, ax, val, "visual", force=True)
        self._save()
        self._refresh_row(gname)
        self._refresh_axes(gname)
        self._status(f"{gname} {ax} = {val}"
                     + ("" if val == "inherit" else " (visual)"))

    def _toggle_inherit(self, ax):
        """The one-click button: inherit <-> an explicit 'normal'.

        Which way it goes is decided from the record at click time, so the
        button and its label can never disagree.
        """
        gname = self._current()
        if not gname:
            return
        own = rec["glyphs"][gname].get("props", {}).get(ax)
        self._set_glyph_axis(ax, "inherit" if own else "normal")

    def _base_text(self, base):
        """'U+222B INTEGRAL' -- the codepoints and names behind a base."""
        if not base or base == G.UNKNOWN:
            return "no base set -- type a character, or codepoints like 0x222B"
        out = []
        for c in base:
            try:
                nm = unicodedata.name(c)
            except ValueError:
                nm = "(unnamed)"
            out.append(f"U+{ord(c):04X} {nm}")
        return "  +  ".join(out)

    def _set_base_manual(self):
        """Accept either the character itself or its codepoints.

        Typing 'integral' is not possible and pasting one is awkward, so
        '0x222B', 'U+222B' and '222B' are read as codes -- several of them, space
        or comma separated, for a base that is a sequence.  Anything that is not
        all codes is taken literally, so a plain 'A' still works.
        """
        gname = self._current()
        if not gname:
            return
        raw = self.base_var.get().strip()
        if not raw:
            return
        base = self._parse_base(raw)
        if base is None:
            self._status(f"cannot read {raw!r} as a character or codepoints")
            return
        G.set_base(rec["glyphs"][gname], base, "manual", force=True)
        self._save()
        self._refresh_row(gname)
        self._select()
        self._status(f"{gname} base = {base!r}  {self._base_text(base)} (manual)")

    @staticmethod
    def _parse_base(raw):
        """'0x222B' / 'U+222B 0xFE01' / '222B' -> the characters; else literal."""
        toks = [t for t in re.split(r"[\s,]+", raw) if t]
        codes = []
        for t in toks:
            # An explicit 0x/U+ always means a code.  Without one, only 4-6 hex
            # digits containing a digit count -- otherwise 'ab' would be read as
            # U+00AB rather than as the two letters someone typed.
            m = re.fullmatch(r"(?:0[xX]|[uU]\+)([0-9A-Fa-f]{1,6})", t)
            if not m and re.fullmatch(r"[0-9A-Fa-f]{4,6}", t) and any(
                    c.isdigit() for c in t):
                m = re.fullmatch(r"([0-9A-Fa-f]{4,6})", t)
            if not m:
                return raw            # not codes at all: take it as typed
            try:
                codes.append(chr(int(m.group(1), 16)))
            except ValueError:
                return None
        return "".join(codes) if codes else None

    def _accept(self, base, props, seq):
        gname = self._current()
        if not gname:
            return
        g = rec["glyphs"][gname]
        G.set_base(g, base, "visual", force=True)
        for ax, v in props.items():
            G.set_axis(g, ax, v, "visual", force=True)
        if len(seq) > 1:
            # a k-NN label may carry a size selector (producttext = 220F FE01),
            # so accepting one records a sequence as well as a character -- with
            # its provenance, like everything else
            G.set_uni(g, [f"0x{int(c):04X}" for c in seq], "visual", force=True)
        self._save()
        self._refresh_row(gname)
        self._select()
        self._status(f"{gname} = {base} {props or ''} (visual)")
        self._next()

    def _next(self):
        gname = self._current()
        if not gname:
            return
        nxt = self.tree.next(gname)
        if nxt:
            self.tree.selection_set(nxt)
            self.tree.see(nxt)

if not os.path.exists(GPM):
    sys.exit(f"gpm_edit: {GPM} missing -- run gpm_init.py {a.font} first")
# Hold the write lock for the whole session.  The editor keeps the record in
# memory and rewrites all of it on every click, so any step that wrote while
# this window was open would be lost at the next click; with the lock held, the
# step refuses instead.  Released by the kernel when this process ends, however
# it ends -- there is no stale lock to clear.
if not G.hold(GPM, "gpm_edit"):
    sys.exit(f"gpm_edit: {GPM} is locked by {G._holder(GPM)} -- another editor "
             f"is open on it, or a step is writing right now")
root = tk.Tk()
app = App(root)
root.mainloop()
print(f"gpm_edit: saved {GPM}")
