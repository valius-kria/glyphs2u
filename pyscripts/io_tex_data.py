# Scripts to use in makefiles
from io_data import load_dict_from_json
import sys # To exit gracefully on error
import re
import os # For file-path management
import subprocess
# The TeX Live tree is whichever this kpsewhich belongs to; override
# with the KPSEWHICH environment variable.
KPSEWHICH = os.environ.get('KPSEWHICH', 'kpsewhich')

# finding some file with kpsewhich
def apply_kpsewhich(fname):
    """
    Finds a path to one of files with the given name.
    """
    shell_command = KPSEWHICH + ' ' + fname
    try:
        fpath = subprocess.check_output(shell_command,
                                               shell=True, text=True)
        # First line only, newline stripped: callers write this straight into a
        # <file>.path that fontforge and kpathsea then open by name.
        return fpath.splitlines()[0] if fpath.strip() else None
    except subprocess.CalledProcessError as e:
        print(f"Error executing shell command: {e}")

# parsing psfonts maps into tfm dictionary
def parse_psfonts_map(input_fname):
    """
    Extracts information from a psfonts.map file into a dictionary.

    Args:
        input_fname (str): Path to the input psfonts.map file.
    """
    tfm_dict = {}
    current_source_map = "" # Stores the name of the .map file from comments

    try:
        with open(input_fname, 'r', encoding='utf-8') as infile:
            for line_content in infile:
                line = line_content.strip()

                # Skip empty lines
                if not line:
                    continue

                # Check for map file source comment
                if line.startswith('%'):
                    # Remove the leading '%' and strip whitespace
                    comment_content = line.lstrip('%').strip()
                    # Check if the comment itself is a .map filename (possibly with path)
                    # (no internal spaces for the path/filename itself and ends with .map)
                    map_file_match = re.match(r'^([\S/\\\.-]+\.map)\s*$', comment_content)
                    if map_file_match:
                        current_source_map = os.path.basename(map_file_match.group(1))
                    # Regardless of the result, this is a comment line, so skip
                    continue

                # --- Process data line ---
                tfm_name = ""
                psfont_file = ""
                encoding_file = ""

                # 1. Ignore/remove text fragments between double quotes
                line_no_quotes = re.sub(r'".*?"', '', line)
                
                # 2. Split the line into parts based on whitespace
                #    Multiple spaces will be treated as a single delimiter.
                parts = line_no_quotes.split()

                if not parts: # Line might have only contained a quoted string
                    continue

                # 3. Name of TFM file (the first word)
                tfm_name = parts[0]
                tfm_dict[tfm_name] = {'map': current_source_map}

                # Index to start searching for enc/pfb files.
                # If a font name is found, this will be incremented.
                next_part_index = 1

                # 4. Name of font (the second word), if present before the first '<' sign
                #    This means parts[1] should exist and not start with '<'
                if len(parts) > 1 and not parts[1].startswith('<'):
                    tfm_dict[tfm_name]['name'] = parts[1]
                    next_part_index = 2 # Next significant part is parts[2]

                # 5. Names of encoding and postscript font files
                #    Iterate through the remaining parts
                for i in range(next_part_index, len(parts)):
                    part = parts[i]
                    
                    # Search for encoding file (e.g., something.enc)
                    # It might be prefixed with '<' (e.g., "<texnansi.enc")
                    if not encoding_file: # Only find the first one
                        enc_match = re.search(r'([\w\.-]+\.enc)', part)
                        if enc_match:
                            encoding_file = enc_match.group(1)
                            tfm_dict[tfm_name]['enc'] = encoding_file
                    
                    # Search for psfont file name (like something.pfb or something.pfa)
                    # It might be prefixed with '<' (e.g., "<utmr8a.pfb")
                    if not psfont_file: # Only find the first one
                        ps_match = re.search(r'([\w\.-]+\.(?:pfb|pfa))', part)
                        if ps_match:
                            psfont_file = ps_match.group(1)
                            tfm_dict[tfm_name]['psfont'] = psfont_file
            return tfm_dict

    except FileNotFoundError:
        print(f"Error: Input file '{input_fname}' not found.")
        return
    except Exception as e:
        print(f"An error occurred: {e}")
        return

# generating the tex file for font table printing
def generate_fonttable_tex_file(tfm_list, tex_fname):
    """
    Generates a .tex file with the \\fonttable commands for all tfm files
    related with the given pfb font, using a template from an external file.

    Args:
        tfm_list (list of strings): tfm names
       tex_fname (str, optional): The name of the .tex file to create.
    """
    tex_file_preamble = r'''\RequirePackage{vtx-tagpdf}
\documentclass{article}
\usepackage{fonttable}
\nodecimals
\nohexoct
\pagestyle{empty}
\begin{document}
'''
    tex_file_end = r'\end{document}' + '\n'
    fontables = ""
    for tfm in tfm_list:
        fontables += r'\fonttable{' + tfm + '}\n'
    tex_content = tex_file_preamble + fontables + tex_file_end

    try:
        with open(tex_fname, "w", encoding='utf-8') as f:
            f.write(tex_content)
    except IOError as e:
        print(f"Error: Could not write to file '{tex_fname}': {e}")
        sys.exit(1)

# finding tfm list for given pfb font
def read_tfm_list(psfonts_fname, pfb_fname):
    """
    Loads psfonts.map in the form of pfb dictionary and returns the
    corresponding list of tfm names

    Args:
        psfonts_fname (str): The name of file where pfb dictionary was saved.
        pfb_fname (str): The name of postscript font file.
    """
    pfb_dict = load_dict_from_json(psfonts_fname)
    try:
        tfm_list = pfb_dict[pfb_fname].keys()
        print('Found {} tfm name(s).'.format(len(tfm_list)))
        return tfm_list
    except KeyError as error:
        print(f"Pfb name {pfb_fname} not found in the {psfonts_fname}.")
        sys.exit(1)
