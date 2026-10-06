#!/usr/bin/env python3
"""Review page for <font>.gpm.json: every glyph, what is known about it, where
that came from, and what each project will derive from it.

One row per glyph: the raster from <font>.pos/, the base, the four axes with
their provenance (colour-coded), and the two derivations side by side -- the
Unicode glyphs2u will emit and the value htf will get.  Rows where Unicode
cannot express the property combination are highlighted: those are the ones
where the two projects necessarily part company.

Usage: gpm_html.py <font> [--gpm FILE]
"""
import argparse, html, json, os, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("--data", default=G.DATA)
ap.add_argument("--gpm")
a = ap.parse_args()
gpm = a.gpm or f"{a.font}.gpm.json"
rec = G.load(gpm)
var = G.Variants(a.data)

STATUS_CLASS = {"?": "unk", "decl": "decl", "unicode": "uni", "lua": "uni",
                "cmp": "cmp", "visual": "vis", "manual": "man"}

def uni_name(codes):
    out = []
    for c in codes:
        try:
            out.append(unicodedata.name(chr(c)))
        except ValueError:
            out.append(f"U+{c:04X}")
    return "/".join(out)

decl = {ax: rec.get("props", {}).get(ax, "normal") for ax in G.AXES}

# The htf column shows what <font>.htf.lua actually holds, read from
# <font>.gpm.map.json rather than worked out again here.  Deriving it a second
# time is what made this page disagree with the block at 243 positions: the
# policy computes the remainder against the DECLARATION gpm_to_htf chose, which
# after deduplication is not the record's font-level properties -- for
# stix-mathbbit-bold it settled on style=normal and left weight=bold to the
# positions, while this page assumed bold was declared and showed no mathvariant
# at all.  One derivation, in one place.
htf_map = {}
try:
    _m = json.load(open(f"{a.font}.gpm.map.json", encoding="utf-8"))
    htf_map = {p: e for p, e in _m.get("positions", {}).items()}
    htf_policy = _m.get("policy", "?")
except (OSError, ValueError):
    htf_policy = None
rows, n_drop, n_part, n_dtls, n_open = "", 0, 0, 0, 0
for gname, g in sorted(rec["glyphs"].items(), key=lambda kv: kv[1].get("pos", 1 << 30)):
    eff = G.effective(rec, g)
    st = g.get("status", {})
    tok = G.mv_token(eff)
    codes, kind, lost = G.uni_codes(rec, g, var, gname)
    base = g.get("base", G.UNKNOWN)
    open_row = not G.has_base(g)
    # 'drop' lost the whole combination and shows the base; 'part' kept the
    # character and lost only the axes in 'lost', so it is a much milder thing
    # and marked apart -- reading them as one number hid which was which.
    drop = kind == "base" and tok
    part = kind == "partial"
    n_drop += bool(drop)
    n_part += bool(part)
    n_dtls += kind == "dtls"
    n_open += bool(open_row)

    axes = ""
    for ax in G.AXES:
        own = ax in g.get("props", {})
        src = st.get(ax) if own else rec.get("status", {}).get(ax, G.UNKNOWN)
        cls = STATUS_CLASS.get(src, "unk")
        mark = "" if own else "&middot;"      # inherited from the font level
        axes += (f'<td class="ax {cls}" title="{html.escape(str(src))}'
                 f'{" (font level)" if not own else ""}">{eff[ax]}{mark}</td>')

    src = G.glyph_image(a.font, gname, g.get("slot"))
    img = f'<img src="{src}">' if src else ""
    # The htf value the CHARACTER-FIRST policy emits, which is what
    # gpm_to_htf --policy char writes and what a .htf.lua block now holds: the
    # composed character (the same codes the glyphs2u column shows), wrapped in a
    # mathvariant stating ONLY the axes the character could not carry.  The two
    # columns therefore differ in exactly one way -- htf keeps the remainder,
    # glyphs2u drops it -- which is the whole point of reading them side by side.
    #
    # It used to show base + the FULL variant token, the older attribute-first
    # answer.  Left as it was, this page would have been checked against a policy
    # the .htf.lua no longer follows.
    # Straight from the map: the value the block holds, in the notation it holds
    # it in (an entity below U+10000, a raw character above -- see
    # gpm_io.htf_value and why luarealstring needs it that way).
    ent = htf_map.get(str(g.get("pos")))
    if ent is None:                            # a slot the map does not cover
        for _x in g.get("alt", []):
            ent = htf_map.get(str(_x.get("pos")))
            if ent is not None:
                break
    if ent is not None and ent.get("new_value") is not None:
        hcell = html.escape(ent["new_value"]).replace("&lt;mfont", "&lt;mfont")
    elif ent is not None:                      # action 'keep': nothing changes
        hcell = '<span class=lost title="no base: the value is left as it is">'\
                '&mdash;</span>'
    else:
        hcell = ('<span class=lost title="no gpm.map.json here -- run '
                 'gpm_to_htf.py to see the htf value">?</span>')
    ucell = ("&mdash;" if not codes else
             " ".join(f"U+{c:04X}" for c in codes))
    if kind == "dtls":
        ucell += (f' <span class="lost" title="dotless i/j cut, resolved by '
                  f'dtls-policy.json">'
                  f'{"&minus;dot" if lost else "&minus;font view"}</span>')
    if part:
        ucell += (f' <span class="lost" title="no Unicode for the whole '
                  f'combination; these axes are only in the htf side">'
                  f'&minus;{"+".join(lost)}</span>')
    cls = "open" if open_row else ("drop" if drop else ("part" if part else ""))
    # a glyph the encoding repeats is shown once, with all its positions
    pos_cell = ", ".join(str(p) for p in
                         [g.get("pos", "")] + [x["pos"] for x in g.get("alt", [])])
    rows += (f'<tr class="{cls}"><td class=n>{pos_cell}</td>'
             f'<td class=g>{img}</td>'
             f'<td class=gn>{html.escape(gname)}</td>'
             f'<td class=b>{html.escape(base)}</td>{axes}'
             f'<td class=mv>{tok or "&mdash;"}</td>'
             f'<td class=cp>{ucell}<div class=nm>{html.escape(uni_name(codes))}</div></td>'
             f'<td class=hv>{hcell}</td></tr>\n')

open_axes = G.font_open_axes(rec)
doc = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>{a.font} glyph properties</title><style>
 body{{font-family:sans-serif;margin:2em}} h1{{font-size:1.2em}}
 table{{border-collapse:collapse}} td,th{{border:1px solid #ccc;padding:2px 6px;vertical-align:middle}}
 th{{background:#f0f0f0;font-size:.85em}} .n,.cp{{font-family:monospace;text-align:right}}
 .cp{{color:#c41a16;font-size:.85em}} .nm{{color:#666;font-size:.75em;font-family:sans-serif;text-align:left}}
 .g img{{max-width:64px;max-height:36px}} .gn{{font-family:monospace;font-size:.85em}}
 .b{{font-size:1.3em;text-align:center}} .mv,.hv{{font-family:monospace;font-size:.8em}}
 .ax{{font-size:.78em;text-align:center}}
 .unk{{background:#eee;color:#999}} .decl{{background:#eef4ff}} .uni{{background:#eaf7ea}}
 .cmp{{background:#fff6c0}} .vis{{background:#ffe8cc}} .man{{background:#ffd9d9}}
 tr.drop td.cp{{background:#ffecec}} tr.open td.b{{background:#ffd9d9}}
 tr.part td.cp{{background:#fff8e1}}
 .lost{{color:#8a6d3b;font-size:85%}}
 .legend span{{padding:2px 6px;margin-right:6px;border:1px solid #ccc;font-size:.8em}}
</style></head><body>
<h1>{a.font} &mdash; glyph property map ({len(rec['glyphs'])} glyphs)</h1>
<p>font level: <code>{html.escape(str(rec.get('props', {}) or '(none)'))}</code>
 {'&middot; <b>unanswered axes: ' + ', '.join(open_axes) + '</b>' if open_axes else ''}
 &middot; {n_open} glyph(s) unrecognised
 &middot; <span style="background:#fff8e1">{n_part} keeping the character but not
 every property</span>
 &middot; <span style="background:#ffecec">{n_drop} with no Unicode for their
 property combination</span> (glyphs2u gets the base alone; htf keeps the variant).</p>
<p>The <b>htf</b> column is read from <code>{a.font}.gpm.map.json</code>
(policy: <b>{htf_policy or 'no map'}</b>) &mdash; it is the value
<code>{a.font}.htf.lua</code> holds, not a second derivation of it. Under
<code>char</code> that is the composed character with a <code>mathvariant</code>
only for the axes no character could carry; where it shows a bare character the
whole property set is in the codepoint and nothing is stated twice.</p>
<p class=legend>provenance:
 <span class=unk>not set</span><span class=decl>htf declaration</span>
 <span class=uni>unicode</span><span class=cmp>font-pair comparison</span>
 <span class=vis>confirmed by eye</span><span class=man>hand-edited</span>
 &middot; &middot;&nbsp;marks a value inherited from the font level</p>
<table><tr><th>pos</th><th>glyph</th><th>name</th><th>base</th>
{''.join(f'<th>{ax}</th>' for ax in G.AXES)}
<th>mathvariant</th><th>glyphs2u</th><th>htf (character first)</th></tr>
{rows}</table></body></html>"""
out = f"{a.font}.gpm.html"
open(out, "w", encoding="utf-8").write(doc)
print(f"gpm_html: {out}  ({len(rec['glyphs'])} rows, {n_open} unrecognised, "
      f"{n_drop} without a unicode for their properties, "
      f"{n_part} keeping the character but not every property"
      f"{f', {n_dtls} dotless cut(s) by policy' if n_dtls else ''})")
