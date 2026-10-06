#!/usr/bin/env python3
"""Task 4: render <variant>.cmp.html -- a side-by-side plain|variant specimen
of the remainder positions in <variant>.cmp.map.json, for human confirmation
of the automatic verdicts.

Glyph images are the per-font rasters in <plain>.pos/ and <variant>.pos/.  Both
image width AND height are capped (aspect preserved) so tall/wide glyphs are not
disproportionate.  Rows kept plain (wrap=false, economy) are highlighted.

The row also names the GLYPH, which the codepoint columns cannot.  The map
labels a position from its htf value, and an htf table gives a construction
piece the codepoint of the whole symbol -- so stix-mathit slot 153 holds
'uni20D6.x', the extension bar shared by the left, right and left-right arrow
accents, but is labelled U+20D6 COMBINING LEFT ARROW ABOVE.  A bar under that
name looks like a bug in the raster until you can see the '.x'.

The name is read from the font's encoding here rather than stored in the map,
so adding this column needs no re-run of cmp_classify.py -- verdicts already
reviewed by hand stay exactly as they are.

Usage: cmp_html.py <variant> [--map PATH]
"""
import json, sys, os, html, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G

ap = argparse.ArgumentParser()
ap.add_argument("variant")
ap.add_argument("--map")
a = ap.parse_args()

mapf = a.map or f"{a.variant}.cmp.map.json"
m = json.load(open(mapf, encoding="utf-8"))
plain, variant, mv, axis = m["plain"], m["font"], m["mathvariant"], m["axis"]
axis_name, _, axis_value = axis.partition("=")
pos = m["positions"]

def enc_names(font):
    """char code (int) -> glyph name, from whichever encoding this font uses."""
    try:
        with open(G.enc_json_for(font), encoding="utf-8") as f:
            return {int(k): v for k, v in json.load(f).items() if v}
    except (OSError, ValueError):
        return {}

names_v, names_p = enc_names(variant), enc_names(plain)
if not names_v and not names_p:
    print(f"cmp_html: no encoding json found -- glyph names left blank "
          f"(make {variant}.pfb.enc.json)", file=sys.stderr)

def glyph_cell(c):
    """The glyph name, and both names when the two fonts disagree at this slot.

    A disagreement is worth seeing rather than hiding: the whole comparison
    rests on the two fonts holding the same glyph at the same position.
    """
    gv, gp = names_v.get(c), names_p.get(c)
    if gv and gp and gv != gp:
        return (f'<span class=warn>{html.escape(gp)} &ne; {html.escape(gv)}</span>')
    return html.escape(gv or gp or "")

def imgpath(font, c): return f"{font}.pos/{c + 1:03d}.png"

rows = ""
wrap_n = keep_n = 0
for htf, p in sorted(pos.items(), key=lambda kv: int(kv[0])):
    c = p["char_code"]
    wrap = p["wrap"]
    wrap_n, keep_n = (wrap_n + 1, keep_n) if wrap else (wrap_n, keep_n + 1)
    cls = "wrap" if wrap else "keep"
    # The comparison settles ONE axis -- the one the pair differs by -- so the
    # verdict is stated as that axis, not as a whole mathvariant.  What variant
    # the glyph finally gets is decided from the record, where the other axes
    # have their own provenance.
    verdict = (f'{axis_name} = {axis_value}' if wrap
               else f'identical &rarr; {axis_name} = normal')
    rows += (f'<tr class="{cls}"><td class=n>{c}</td><td class=n>{htf}</td>'
             f'<td class=gn>{glyph_cell(c)}</td>'
             f'<td class=cp>{p["codepoint"]}</td><td class=nm>{html.escape(p["name"] or "")}</td>'
             f'<td class=g><img src="{imgpath(plain, c)}"></td>'
             f'<td class=g><img src="{imgpath(variant, c)}"></td>'
             f'<td class=v>{verdict}</td></tr>\n')

doc = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{variant} vs {plain}</title>
<style>
 body{{font-family:sans-serif;margin:2em}} h1{{font-size:1.2em}}
 table{{border-collapse:collapse}} td,th{{border:1px solid #ccc;padding:3px 7px;vertical-align:middle}}
 th{{background:#f0f0f0}} .n,.cp{{font-family:monospace;text-align:right}} .cp{{color:#c41a16}}
 .gn{{font-family:monospace;color:#0a5}} .warn{{color:#c41a16;font-weight:bold}}
 .g img{{max-width:96px;max-height:44px;height:auto;width:auto}}
 tr.keep{{background:#fff6c0}} .v{{font-size:.9em}}
</style></head><body>
<h1>{variant} vs {plain} &mdash; does this glyph have {axis_name} = {axis_value}?</h1>
<p>{len(pos)} remainder positions (not unicode-matched):
 {wrap_n} judged <b>{axis_value}</b> &middot;
 <span style="background:#fff6c0">{keep_n} judged {axis_name} = normal (rasters identical)</span>.
 Auto verdicts are initial values &mdash; edit the .cmp.map.json <code>wrap</code> flags to override.</p>
<p>This pair differs by <b>{axis}</b> and answers nothing else: the other axes
 come from the record, each with its own provenance.  A glyph that is
 {axis_value} but, say, not italic is said so there &mdash;
 <code>gpm_set.py {variant} --pos N style=normal</code> &mdash; not here.</p>
<p>The <b>glyph</b> column is the name in the font's own encoding; <b>code</b>/<b>name</b>
 are what the htf table says the position renders as.  They differ where a glyph is
 a construction piece or a size cut &mdash; <code>uni20D6.x</code> is the extension bar
 shared by the left, right and left-right arrow accents, but the htf value gives it
 the plain left arrow's codepoint.</p>
<table><tr><th>char</th><th>htf</th><th>glyph</th><th>code</th><th>name</th><th>{plain}</th><th>{variant}</th><th>verdict</th></tr>
{rows}</table></body></html>"""
open(f"{a.variant}.cmp.html", "w", encoding="utf-8").write(doc)
print(f"cmp_html: {a.variant}.cmp.html  ({len(pos)} rows: {wrap_n} wrap, {keep_n} keep)")
