# Script callable from fontforge
from config import font_dir
from texmf_paths import fonts_available, missing_fonts_note
import sys
import os
import json
import fontforge

json_fname = 'fonts-glyphs-dict.json'
if os.path.isfile(json_fname):
    print(f"File {json_fname} exists; exiting... ")
    sys.exit(0)

# Everything could be written into one dictionary comprehension, but then
# fontforge.open exceptions will be not handled properly.  So we need an
# auxiliary function:
def font_glyphs(font_fname: str) -> list[str]:
    """
    Open the font and returns the glyph-name list.  In fact, we need a set,
    but the datatype set is not JSON serializable.
    Args:
        font_fname (str): path to the font file.
    """
    try:
        font = fontforge.open(font_fname)
        return [font[glyph].glyphname for glyph in font]
        print(f"Glyphs successfully read from {font.fontname}")

    except Exception as e: # Gemini guess about fontforge.error was wrong
        # Catch any other unexpected Python errors
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if not fonts_available(font_dir):
    print(missing_fonts_note(font_dir))
    sys.exit(0)

pfb_files = [os.path.join(font_dir, fname) for fname in os.listdir(font_dir)
             if fname.endswith('.pfb')]
fonts_dict = { os.path.splitext(os.path.basename(pfb_fname))[0]:
               font_glyphs(pfb_fname)
               for pfb_fname in pfb_files }
try:
    # Open the file for writing
    # Use utf-8 encoding for broader compatibility
    with open(json_fname, 'w', encoding='utf-8') as f:
        # Use json.dump to write the data to the file
        # indent=4 makes the JSON file human-readable (pretty-printed)
        # ensure_ascii=False allows non-ASCII characters (like accents, etc.)
        # to be written directly instead of escaped sequences (\uXXXX)
        json.dump(fonts_dict, f, indent=4, ensure_ascii=False)
        print(f"Glyph names from fonts in {font_dir} are saved to JSON file: {json_fname}.")

except IOError as e:
    print(f"Error: Could not write to JSON file '{json_fname}': {e}")
    sys.exit(1)
except TypeError as e:
    # This might happen if the data contains data types that are not
    # directly serializable to JSON (e.g., sets, custom objects)
    print(f"Error: Data is not fully JSON serializable: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred while writing the JSON: {e}")
    sys.exit(1)

