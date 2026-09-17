#!/usr/bin/env python3
import sys
import os
import logging

# Suppress warnings from the ML model
logging.getLogger().setLevel(logging.ERROR)

try:
    from PIL import Image
    from pix2tex.cli import LatexOCR
    from pylatexenc.latex2text import LatexNodes2Text
except ImportError:
    print("Error: Run 'pip install pix2tex pylatexenc pillow'")
    sys.exit(1)

def analyze_math_glyph(image_path):
    if not os.path.isfile(image_path):
        print(f"Error: File '{image_path}' not found.")
        sys.exit(1)

    try:
        # Load the Math OCR model
        model = LatexOCR()
        
        # Open image
        img = Image.open(image_path)
        # Ensure it has a white background (Pix2Tex expects black text on white bg)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Predict the LaTeX string
        latex_prediction = model(img)
        clean_latex = latex_prediction.strip()
        
        if not clean_latex:
            print("Could not recognize a math symbol.")
            return

        print(f"--- Results for: {image_path} ---")
        print(f"LaTeX Output : {clean_latex}")

        # Convert the LaTeX string (e.g. \Omega) to a real character (e.g. Ω)
        converter = LatexNodes2Text()
        actual_char = converter.latex_to_text(clean_latex).strip()

        # Print the Unicode Hex
        for char in actual_char:
            unicode_hex = hex(ord(char))[2:].upper().zfill(4)
            return (char, unicode_hex)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_math_unicode.py <path_to_image>")
        sys.exit(1)
        
    image_file = sys.argv[1]
    print(analyze_math_glyph(image_file))
