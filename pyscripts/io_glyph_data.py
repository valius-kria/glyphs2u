# Functions to read and parse glyph-names-related data
# Should be used in scripts for makefiles

import sys # To exit gracefully on error
import re
import os # For file-path management
import csv # For UnicodeData parsing

# Parsing the file with missing glyphs
def parse_misglyphs_list(font, misglyphs_fname):
    """
    Parses the given txt file about missing glyphs.
    Args:
        font (str): The font name mentioned in lines about missing glyphs.
        It is used to filter only necessary glyphs, in case the file of
        missing glyphs is generated authomatically from the log file and
        may contain info about nore than one font.
        
        misglyphs_fname (str): The path to the <font>-glyphs.txt file.

    Returns:
        glist: A list of glyphs.

    """
    rexp = re.compile("Warning: Unicode .+, font (.+), glyph (.+)$")
    glist = []
    try:
        with open(misglyphs_fname, mode='r') as file:
            print(f"Reading missing glyphs file: {misglyphs_fname}")
            for line in file:
                match_data = rexp.search(line)
                if match_data:
                    if font == match_data.group(1):
                        glist.append(match_data.group(2))
        return glist

    except FileNotFoundError:
        print(f"Error: Input txt file not found at '{mis_fname}'")
        sys.exit(1) # Exit script with error status
    except Exception as e:
        print(f"An unexpected error while reading the file: {e}")
        sys.exit(1)

# Building the initial lua table with missing glyphs
def save_glist_to_lua(glyph_list, lua_filepath):
    """
    Saves a glyphs list to lua table with empty values.

    Args:
        glyph_list (list): The list if glyph names.
        lua_filepath (str): The path for the file of the lua table.
    """
    try:
        # Open the file for writing
        with open(lua_filepath, mode='w') as file:
            file.write("return {\n")
            for gl in glyph_list:
                file.write("  ['" + gl + "'] = { 0x },\n")
            file.write("  }\n")
            print(f"Preliminary lua table saved to the file: {lua_filepath}")

    except IOError as e:
        print(f"Error: Could not write to file '{lua_filepath}': {e}")
        sys.exit(1)
    except TypeError as e:
        print(f"Error: Data in list '{glyph_list}' are malformed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while writing lua table: {e}")
        sys.exit(1)

# Parsing UnicodeData.txt into dictionary
def parse_csv_to_dict(csv_filepath, delimiter=';'):
    """
    Parses a CSV file with a specified delimiter.

    Args:
        csv_filepath (str): The path to the input CSV file.
        delimiter (str): The delimiter character used in the CSV file.

    Returns:
        dict: A dictionary where keys are the first field of each row
              and values are tuples of the remaining fields.
              Returns an empty dictionary if the file cannot be read or is empty.
    """
    result_dict = {}
    try:
        # Open with newline='' as recommended for csv module
        # Use utf-8 encoding for broader compatibility
        with open(csv_filepath, mode='r', newline='', encoding='utf-8') as infile:
            # Create a CSV reader object specifying the delimiter
            reader = csv.reader(infile, delimiter=delimiter)

            print(f"Reading CSV file: {csv_filepath} with delimiter '{delimiter}'")

            row_num = 0
            for row in reader:
                row_num += 1
                # Basic check: Ensure the row is not empty and has at least one element
                if row and len(row) > 0:
                    key = row[0]
                    # Create a tuple from the second element onwards
                    values = (row[1], row[10])

                    # Check for duplicate keys (optional, depends on desired behavior)
                    if key in result_dict:
                        print(f"Warning: Duplicate key '{key}' found at row {row_num}. Overwriting previous value: {result_dict[key]} with {values}")

                    result_dict[key] = values
                elif row:
                     print(f"Warning: Skipping row {row_num} with insufficient data: {row}")
                # else: row is completely empty, csv.reader usually handles this

        print(f"Successfully parsed {len(result_dict)} records.")
        return result_dict

    except FileNotFoundError:
        print(f"Error: Input CSV file not found at '{csv_filepath}'")
        sys.exit(1) # Exit script with error status
    except csv.Error as e:
        print(f"Error parsing CSV file '{csv_filepath}' at line {reader.line_num}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while reading the CSV: {e}")
        sys.exit(1)

# Reading lua table into list of strings or tuples
def read_lua_table_in_list(lua_filepath):
    """
    Reads and parses lua table and saves into list

    Args:
        lua_filepath (str): The path to the input lua table file.
    Returns:
        result_list: A list of lines (str) or tuples (tuple) of matching groups.
        Returns an empty list if the file cannot be read or is empty.
    """
    result_list = []
    try:
        # Anchored to the line start (after indent) so a commented-out entry,
        # e.g. a '-->' rename proposal, is not parsed as a real table entry.
        rexp = r"^\s*\[([\'\"])([^\'\"]+)\1\] *= *\{([^{}]+)\},(.*)$"
        # Use utf-8 encoding for broad compatibility
        with open(lua_filepath, 'r', encoding='utf-8') as file:
            content = file.read().splitlines()
            for ln in content:
                m = re.search(rexp, ln)
                if m:
                    result_list.append(m.groups()[1:])
                else:
                    result_list.append(ln)
        return result_list
        
    except FileNotFoundError:
        print(f"Error: File not found at {lua_filepath}")
    except re.error as e:
        print(f"Error: Invalid regular expression: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Reading g2u table into list of tuples
def read_g2u_table_in_list(g2u_filepath: str) -> list[(str,str)]:
    """
    Reads and parses g2u table and saves into list of string pairs

    Args:
        g2u_filepath (str): The path to the input g2u table file.
    Returns:
        A list of lines (str) or tuples (tuple) of matching groups.
        Returns an empty list if the file cannot be read or is empty.
    """
    try:
        rexp = r"/([^ ]+) +<([0-9A-Fa-f]+)>"
        # Use utf-8 encoding for broad compatibility
        with open(g2u_filepath, 'r', encoding='utf-8') as file:
            line_list = file.read().splitlines()
        result_list = []
        for ln in line_list:
            m = re.search(rexp, ln)
            if m:
                result_list.append(m.groups())
        return result_list
        
    except FileNotFoundError:
        print(f"Error: File not found at {g2u_filepath}")
    except re.error as e:
        print(f"Error: Invalid regular expression: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Reading encoding file list of glyph names
def read_encoding_in_list(enc_filepath: str) -> list[str]:
    """
    Reads and parses encoding file and saves into list of glyph names

    Args:
        enc_filepath (str): The path to the input (encoding) file.
    Returns:
        A list of glyph names.
        Returns an empty list if the file cannot be read or is empty.
    """
    try:
        rexp = r"/([._a-zA-Z0-9]+)"
        # Use utf-8 encoding for broad compatibility
        with open(enc_filepath, 'r', encoding='utf-8') as file:
            enc_text = file.read()
        name_list = re.findall(rexp, enc_text)
        return name_list

    except FileNotFoundError:
        print(f"Error: File not found at {enc_filepath}")
    except re.error as e:
        print(f"Error: Invalid regular expression: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Saving lua table in a list format to a file
def write_lua_table_list(lua_tlist, lua_filepath):
    """
    Saves a lua table list to a lua file.

    Args:
        lua_tlist (list): The list of lua table lines or tuples to save.
        lua_filepath (str): The path for the output LUA file.
    """
    try:
        # Open the file for writing
        # Use utf-8 encoding for broader compatibility
        with open(lua_filepath, mode='w', encoding='utf-8') as outfile:
            for elm in lua_tlist:
                if type(elm) is str:
                    outfile.write(elm + '\n')
                else:
                    outfile.write("  [\'" + elm[0] + "\'] = {" + elm[1] +
                                  "}," + elm[2] + '\n')
        print(f"Lua table successfully saved to file: {lua_filepath}")

    except IOError as e:
        print(f"Error: Could not write to file '{lua_filepath}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while writing the LUA: {e}")
        sys.exit(1)

# Saving g2u table in a list format to a file
def write_g2u_list(g2u_list, g2u_fname):
    """
    Saves a g2u list to a g2u table file.

    Args:
        g2u_list (list(tuple(str,str))): The list of g2u table to save.
        g2u_fname (str): The path for the output .g2u file.
    """
    try:
        # Open the file for writing
        # Use utf-8 encoding for broader compatibility
        with open(g2u_fname, mode='w', encoding='utf-8') as outfile:
            outfile.write('/GlyphNames2Unicode <<\n')
            for tpl in g2u_list:
                outfile.write('  /' + tpl[0] + ' <' + tpl[1] + '>\n')
            outfile.write('  >> def\n')
        print(f"G2u table successfully saved to file: {g2u_fname}")

    except IOError as e:
        print(f"Error: Could not write to file '{g2u_fname}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while writing the G2U: {e}")
        sys.exit(1)

# Read lua table to list and transform to dictionary (loosing descriptions)
def read_lua_table_in_dict(lua_filepath):
    return { elm[0]: hex_codes_from_string(elm[1])
             for elm in read_lua_table_in_list(lua_filepath)
             if not type(elm) is str }

# Read lua table to list and transform to dictionary with renamed glyphs
def lua_to_renamed_glyphs_dict(lua_filepath):
    """
    Uses renamed glyph names if there is a new name string between values
    of the lua table.

    """
    renamed_dict = {}
    for elm in read_lua_table_in_list(lua_filepath):
        if not type(elm) is str:
            codes = []
            gname = elm[0]
            substrings = re.split(r'[ ,]+', elm[1])
            for item in substrings:
                if is_hex_string(item):
                    codes.append(item)
                else:
                    new_name = re.split(r'["\']+', item)[0]
                    if not new_name is None:
                        gname = new_name
            renamed_dict[gname] = codes
    return renamed_dict

# Write lua table dictionary to file
def write_lua_dict(lua_dict, lua_filepath):
    write_lua_table_list(lua_dict_to_list(lua_dict), lua_filepath)

# Transform lua dictionary to list
def lua_dict_to_list(lua_dict):
    return ["return {",] + [
        (glyph, " " + ", ".join(c for c in codes) + " ", "")
        for glyph, codes in lua_dict.items() ] + ["}",]

# Transform lua dictionary to g2u list
def lua_dict_to_g2u_list(lua_dict):
    return [ (glyph, uni32_to_uni16(codes)) for glyph, codes in lua_dict.items() ]

# Transform g2u list to lua dictionary
def g2u_list_to_lua_dict(g2u_list):
    return { tpl[0]: uni16_to_uni32(tpl[1]) for tpl in g2u_list }

# Pattern for hexadecima number strings with 0x/0X prefix.
# Anchored to the start (^) and end ($) of the string.
HEX_PATTERN = re.compile(r"^(0x|0X)[0-9a-fA-F]+$")

# Testing if string is in the hex format
def is_hex_string(s):
    """
    Checks if the input string represents a valid hexadecimal number using regex.
    
    Args:
       s: The input string to check.
    
    Returns:
        True if the string matches the hexadecimal pattern, False otherwise.
        Returns False if the input is not a string.
    """
    if not isinstance(s, str):
        return False
    # Use fullmatch to ensure the *entire* string matches the pattern
    return bool(HEX_PATTERN.fullmatch(s))

# Split strings into codes in lua tables
def hex_codes_from_string(s):
    substrings = re.split(r'[ ,]+', s)
    if substrings is None:
        codes = []
    else:
        codes = [item for item in substrings if is_hex_string(item)]
    return codes

# Placeholder codepoint marking a glyph whose real Unicode is not yet known.
# Written by initial-lua.py as the value for "unknown" glyphs (names that do
# not resolve, or that resolve only to a Private-Use/Surrogate codepoint);
# edit_knn.py targets exactly these entries for k-NN recognition.  Deliberately
# distinct from a genuine space (0x0020): U+FFFD renders as the replacement
# character, so unresolved glyphs are visible in the .html and greppable before
# deploy, and never collide with a real space glyph.
UNKNOWN_UNICODE = '0xFFFD'

def is_unknown_codes(codes):
    """True if `codes` is exactly the single 'unknown' placeholder.

    Case-insensitive on the hex string so 0xFFFD / 0xfffd both match.
    """
    return (len(codes) == 1 and is_hex_string(codes[0])
            and int(codes[0], 16) == int(UNKNOWN_UNICODE, 16))

# Convert list of codes from lua tables to string used in g2u tables.
# Generated by gemini; updated to lists and modified.
def uni32_to_uni16(hex_str_list: list[str]) -> str:
    """
    Converts list of Unicode code hex strings, possibly containing utf-32
    values, to a concatenated string of utf-16 values without prefix '0x',
    where longer than 4 chars strings changed with surrogate pairs.
    
    Args:
       hex_str_list: The input string list to convert.
    
    Returns:
        String of hex digits, possibly containing high and low surrogate pairs.
    """
    result_str = ""
    for hex_string in hex_str_list:
        try:
            codepoint = int(hex_string, 16)
        except ValueError:
            raise ValueError(f"'{hex_string}' is not a valid hex string.")

        if len(hex_string) == 6:
            result_str += hex_string[2:]
        elif len(hex_string) == 7:
            # Formula implementation
            temp_val = codepoint - 0x10000
            high_surrogate = 0xD800 + (temp_val >> 10)
            low_surrogate = 0xDC00 + (temp_val & 0x03FF)
            result_str += f"{high_surrogate:X}" + f"{low_surrogate:X}"
        else:
            raise ValueError(f"'{hex_string}' has bad length.")
    return result_str

# Convert a hex string from g2u tables into a list of hex strings usable in
# lua tables.  Generated initally by gemini for a single surrogate pair;
# updated to concatenated utf-16 strings without prefix '0x'.
def uni16_to_uni32(hex_string: str) -> list[str]:
    """
    Converts a concatenated utf-16 strings, possibly containing high and
    low UTF-16 surrogate pairs to list with utf-32 Unicode code point hex
    strings.
    """
    n = len(hex_string)
    if not n % 4 == 0:
        raise ValueError(f"'{hex_string}' has length {n} not divisible by 4.")

    hex_str_list = [ '0x' + hex_string[i:i+4] for i in range(0, n, 4) ]
    n = (n // 4) - 1
    if n < 1:
        result_list = hex_str_list
    else:
        result_list = []
        for i in range(n):
            try:
                codepoint = int(hex_str_list[i], 16)
                codepoint2 = int(hex_str_list[i + 1], 16)
            except ValueError:
                raise ValueError(f"'{hex_str_list[i]}' or '{hex_str_list[i+1]}'  is not a valid hex string.")

            if not (0xD800 <= codepoint <= 0xDBFF):
                result_list.append(hex_str_list[i])
                if i + 1 == n: # the index of the last element
                    result_list.append(hex_str_list[n])
            elif not (0xDC00 <= codepoint2 <= 0xDFFF):
                raise ValueError(f"Low surrogate '{hex_str_list[i+1]}' is out of range.")
            else:
                # Formula implementation
                high_temp = codepoint - 0xD800
                low_temp = codepoint2 - 0xDC00
                codepoint = 0x10000 + ((high_temp << 10) | low_temp)
                result_list.append(f"0x{codepoint:X}")
    return result_list
