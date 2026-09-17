#!/usr/bin/env python 
# Generate HTML file from pfb to check correspondence between glyphs and unicodes

import os
import base64
import sys
from io_glyph_data import read_lua_table_in_dict
from io_data import load_list_from_json
from glyph_maps import find_unicodes

pfb_font = sys.argv[1]
# 1. Get glyph data from the source PFB
glyph_list = load_list_from_json(pfb_font + '-glyphs.json')

# 2. Import the custom map for pfb font from the lua table
pfb_map = read_lua_table_in_dict(pfb_font + '.lua')

def generate_glyph_table_rows(font_name, glist):
    """
    Generates a body of HTML table.
    """
    # Start the table
    glyph_table = f"""
            <table>
            <thead>
                <tr>
                    <th>Glyph Name</th>
                    <th>Glyph image</th>
                    <th>Unicode(s) rendered</th>
                    <th>Unicode(s)</th>
                </tr>
            </thead>
            <tbody>
    """
    # Fill table body
    for glyph_name in glist:
        # set path to the glyph image
        glyph_image_path = os.path.join('.',font_name, glyph_name + '.png')
        # find unicode values for the glyph
        unicode_vals = find_unicodes(glyph_name, pfb_map)
        # define strings for html from unicode values
        if unicode_vals == []:
            unicode_str = "<em>(not mapped)</em>"
            otf_chars_to_render = ""
        else:
            unicode_str = ", ".join(v for v in unicode_vals)
            otf_chars_to_render = "".join(chr(int(v,16)) for v in unicode_vals)
        # Fill in the table row form
        glyph_table += f"""
        <tr>
            <td class="gid">{glyph_name}</td>
            <td class="glyph">
                 <img src="{glyph_image_path}"
                      alt="{glyph_name + ' image'}" /></td>
            <td class="otf-reference-render">{otf_chars_to_render}</td>
            <td><span class="code">{unicode_str}</span></td>
        </tr>
        """
    # Finish the table
    glyph_table += f"""
            </tbody>
        </table>
    """
    return glyph_table

# Generating html file
def generate_html_specimen(font, glyph_table_string, html_file):
    """
    Generates a HTML file.
    """
    # Define CSS
    html_css = f"""
    <style>
        table {{ border-collapse: collapse; margin-top: 1.5em; font-size: 24px; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: middle; word-wrap: break-word; }}
        th {{ background-color: #f8f8f8; }}
        .gid {{ text-align: right; font-family: monospace; }}
        .code {{ font-family: 'SF Mono', 'Menlo', 'Consolas', monospace; color: #c41a16; }}
        .otf-reference-render {{
            font-family: 'STIX Two Math', 'Latin Modern Math', 'Noto Sans Math', 'Latin Modern', 'Gentium Plius', Junicode, serif;
            font-size: 100px;
        }}
    </style>
"""
    # Fill in the html file form
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Glyph Specimen: {font}</title>
        {html_css}
    </head>
    <body>
        <h1>Glyph Specimen</h1>
        <h2>{font}</h2>
                {glyph_table_string}
    </body>
    </html>
    """
    # Write html to the given file
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    print(f"Successfully generated self-contained HTML specimen: '{html_file}'")

# Script execution
# 3. Generate the HTML file
if __name__ == '__main__':
    if glyph_list:
        print("--- Generating self-contained HTML specimen ---")
        table_rows = generate_glyph_table_rows(
            pfb_font,
            glyph_list)
        generate_html_specimen(
            pfb_font,
            table_rows,
            pfb_font + '.html')
