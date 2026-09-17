import os
from fontTools.ttLib import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as ReportLabTTFont
from reportlab.pdfbase.type1font import Type1Font

# --- 1. CONFIGURATION ---

# --- Your PostScript Font ---
PFB_FONT_PATH = 'myfont.pfb'
AFM_FONT_PATH = 'myfont.afm'

# --- The Modern OTF Reference Font ---
# Download STIX2Math.otf from https://github.com/stipub/stixfonts/
OTF_REFERENCE_FONT_PATH = 'STIX2Math.otf'

# --- Output PDF ---
OUTPUT_PDF_PATH = 'myfont_math_specimen.pdf'

# --- YOUR CUSTOM GLYPH-TO-UNICODE MAP ---
# This is where you define your mappings.
# The value should be a list of integers (Unicode code points).
CUSTOM_GLYPH_MAP = {
    # --- Single Mappings ---
    'integral': [0x222B],        # ∫ - Integral
    'summation': [0x2211],       # ∑ - N-ary Summation
    'radical': [0x221A],         # √ - Square Root
    
    # --- Mappings to Private Use Area (PUA) ---
    'mycustomsymbol': [0xE000],  # Example custom symbol
    
    # --- A Glyph Mapped to a SEQUENCE of Unicodes ---
    # This example maps a single glyph 'greaterorequal' to two unicode characters.
    'greaterorequal': [0x003E, 0x0331], # > and COMBINING MACRON BELOW to form ≥
    
    # --- Glyphs without a defined mapping will be shown as "N/A" ---
    '.notdef': [], # Special case, no unicode
    'space': [0x0020],
    'A': [0x0041],
    'B': [0x0042],
}


def get_glyph_data(font_path, custom_map):
    """
    Gets all glyphs from the PFB font and attaches Unicode data from the custom map.
    """
    try:
        font = TTFont(font_path)
        glyph_names = font.getGlyphOrder()
    except Exception as e:
        print(f"Error reading glyph order from {font_path}: {e}")
        return []

    glyph_data = []
    for name in glyph_names:
        unicode_vals = custom_map.get(name) # Get list of ints or None
        
        unicode_char_sequence = ""
        if unicode_vals:
            try:
                # Create a string from the sequence of unicode code points
                unicode_char_sequence = "".join(chr(u) for u in unicode_vals)
            except ValueError:
                print(f"Warning: Invalid Unicode value for glyph '{name}'")
        
        glyph_data.append({
            'name': name,
            'unicode_vals': unicode_vals,
            'char_sequence': unicode_char_sequence
        })
    return glyph_data

def create_math_specimen_pdf():
    """Generates the PDF glyph chart comparing PFB glyphs to OTF Unicode rendering."""
    # --- 2. VALIDATION AND FONT REGISTRATION ---
    if not os.path.exists(AFM_FONT_PATH) or not os.path.exists(PFB_FONT_PATH):
        print("Error: PostScript font files not found!")
        return
    if not os.path.exists(OTF_REFERENCE_FONT_PATH):
        print(f"Error: OTF Reference font '{OTF_REFERENCE_FONT_PATH}' not found!")
        return

    # Register the source PFB font
    try:
        face = Type1Font(AFM_FONT_PATH, PFB_FONT_PATH)
        pfb_font_name = face.faceName
        pdfmetrics.registerFont(face)
        print(f"Successfully registered PFB font: '{pfb_font_name}'")
    except Exception as e:
        print(f"Error registering PFB font: {e}")
        return

    # Register the reference OTF font
    try:
        otf_font_name = 'ReferenceOTF' # Internal name for ReportLab
        pdfmetrics.registerFont(ReportLabTTFont(otf_font_name, OTF_REFERENCE_FONT_PATH))
        print(f"Successfully registered OTF font: '{OTF_REFERENCE_FONT_PATH}' as '{otf_font_name}'")
    except Exception as e:
        print(f"Error registering OTF font: {e}")
        return

    # --- 3. DATA PREPARATION ---
    glyph_data = get_glyph_data(PFB_FONT_PATH, CUSTOM_GLYPH_MAP)
    if not glyph_data:
        return

    # --- 4. PDF GENERATION ---
    c = canvas.Canvas(OUTPUT_PDF_PATH, pagesize=landscape(letter))
    width, height = landscape(letter)
    
    margin, line_height, glyph_size = 50, 22, 20
    x_name, x_unicode, x_pfb_glyph, x_otf_render = margin, margin + 150, margin + 350, margin + 500

    def draw_header(page_num):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, height - margin + 20, f"Glyph Specimen for {pfb_font_name}")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x_name, height - margin, "Glyph Name")
        c.drawString(x_unicode, height - margin, "Unicode Sequence")
        c.drawString(x_pfb_glyph, height - margin, "PFB Glyph")
        c.drawString(x_otf_render, height - margin, "OTF Rendered")
        c.line(margin, height - margin - 5, width - margin, height - margin - 5)
        return height - margin - 20

    y = draw_header(1)
    page_count = 1
    
    for data in glyph_data:
        if y < margin:
            c.showPage()
            page_count += 1
            y = draw_header(page_count)

        # Column 1: Glyph Name
        c.setFont("Courier", 9)
        c.drawString(x_name, y, data['name'])

        # Column 2: Unicode Sequence
        c.setFont("Courier", 9)
        if data['unicode_vals']:
            unicode_str = ", ".join(f"U+{val:04X}" for val in data['unicode_vals'])
        else:
            unicode_str = "N/A"
        c.drawString(x_unicode, y, unicode_str)

        # Column 3: PFB Glyph Image (drawn by name)
        c.setFont(pfb_font_name, glyph_size)
        text_object = c.beginText(x_pfb_glyph, y - 6)
        # This syntax directly accesses the glyph by its PostScript name
        text_object.textLine(f'</font><font name="{pfb_font_name}">/{data["name"]}</font><font name="Helvetica">')
        c.drawText(text_object)

        # Column 4: OTF Rendered Unicode (drawn by character sequence)
        if data['char_sequence']:
            c.setFont(otf_font_name, glyph_size)
            c.drawString(x_otf_render, y - 6, data['char_sequence'])
        
        y -= line_height

    c.save()
    print(f"\nSuccessfully created PDF: {OUTPUT_PDF_PATH}")


if __name__ == '__main__':
    create_math_specimen_pdf()
