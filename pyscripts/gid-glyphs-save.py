# Script callable from fontforge
from config import font_dir
import fontforge
import os
import json
import sys

max_uni_quadro = int("ffff", 16)
def unicode_point(code: int)-> str:
    """
    Writes number in unicode point notation.
    """
    if code > max_uni_quadro:
        return f"0x{code:X}"
    else:
        return f"0x{code:04X}"

def extract_glyphs_and_unicodes(font_path):
    """
    Reads a TTF/OTF font, saves glyphs as PNGs, and generates a JSON 
    mapping GIDs to Unicode values.
    """
    
    # 1. Open the font
    try:
        font = fontforge.open(font_path)
    except Exception as e:
        print(f"Failed to open font '{font_path}': {e}")
        sys.exit(1)

    # 2. Get font name for directory and json file
    font_name = font.fontname
    if not font_name:
        # Fallback if the font name is somehow missing
        font_name = os.path.splitext(os.path.basename(font_path))[0]

    print(f"Processing font: {font_name}")

    # 3. Create the output directory
    output_dir = font_name
    os.makedirs(output_dir, exist_ok=True)

    # 4. Force Original encoding so that the index corresponds exactly to the
    # GID
    font.encoding = "Original"
    num_glyphs = len(font)

    uni_and_name = []

    print(f"Extracting {num_glyphs} glyphs...")

    # 5. Iterate over every GID
    for gid in range(num_glyphs):
        try:
            glyph = font[gid]
            
            # --- IMAGE EXPORT --- We skip exporting PNGs for empty glyphs
            # (like Space or control characters)
            if glyph.isWorthOutputting():
                png_filepath = os.path.join(output_dir, f"{gid}.png")
                glyph.export(png_filepath)

            # --- UNICODE EXTRACTION ---
            unicodes = []
            
            # glyph.unicode returns the primary mapping (-1 if unmapped)
            if glyph.unicode != -1:
                unicodes.append(glyph.unicode)
                
            # glyph.altuni contains alternate mappings if a single glyph 
            # represents multiple Unicode characters
            if glyph.altuni is not None:
                for alt in glyph.altuni:
                    # alt is a tuple: (unicode_value, variation_selector, reserved)
                    alt_val = alt[0]
                    if alt_val != -1 and alt_val not in unicodes:
                        unicodes.append(alt_val)

            # Format the unicode integers into readable hex strings (e.g., "U+0041")
            # Unmapped glyphs (like ligatures or stylistic alternates) will be an empty list []
            hex_unicodes = [ unicode_point(u) for u in unicodes]
           
            uni_and_name.insert(gid, { "unicodes": hex_unicodes,
                                       "name": glyph.glyphname} )

        except Exception as e:
            print(f"Error processing GID {gid}: {e}")
            uni_and_name.insert(gid, [])

    # 6. Save the unicode value list to JSON
    json_filename = f"{font_name}-unicodes.json"
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(uni_and_name, f, indent=4)

    font.close()
    
    print(f"Images saved to  : ./{output_dir}/")
    print(f"JSON Unicode list saved to: ./{json_filename}")


if __name__ == "__main__":
    # Change this to the path of your TTF file
    arg = os.sys.argv[1] # will be font name without extension
    font_files = { os.path.splitext(fname)[0]: os.path.join(font_dir, fname)
                   for fname in os.listdir(font_dir)
                   if fname.endswith(('.ttf', '.otf')) }
    if arg in font_files.keys():
        extract_glyphs_and_unicodes(font_files[arg])
    else:
        print(f"Error: Could not find '{arg}' in directory {font_dir}.")
