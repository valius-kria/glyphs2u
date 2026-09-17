#!/usr/bin/env python3
# For transforming the joined data of lua tables into dictionary

from io_data import save_data_to_json, load_dict_from_json
import re

# 1. Read data
json_input = "font_glyph_maps.json"
lua_tables_data = load_dict_from_json(json_input)

# 2. Define functions to split lines
rexp = re.compile(r"\[([\'\"])([^\'\"]+)\1\] *= *\{([^{}]+)\},(.*)$")
def split_lua_line(line: str)-> list:
    """Splits a line in a list of three conpunents: glyph name, string
    consisting of hex codes and maybe a new glyph name, and a comment, may be
    empty.

    """
    global rexp
    m = rexp.search(line)
    if m:
        return [ m.groups()[1], ] + \
            hex_codes_and_maybe_name( m.groups()[2] ) + \
            [ m.groups()[3], ]
    else:
        return [line]

# Pattern for lua string
NAME_PATTERN = re.compile(r"^([\'\"])([^\'\"]+)\1$")
# Split strings into codes in lua tables
def hex_code_or_maybe_name(s: str)-> str:
    """
    Takes off the quotes if there are some.
    """
    m = NAME_PATTERN.fullmatch(s)
    if bool(m):
        return m[2]
    else:
        return s

# Splits the value of lua table
def hex_codes_and_maybe_name(s: str)-> list:
    """
    Takes off the quotes from a name.
    """
    substrings = list(filter(None,re.split(r'[ ,]+', s)))
    if substrings is None:
        codes = []
    else:
        codes = list(map(hex_code_or_maybe_name, substrings))
    return codes

if __name__ == "__main__":
    # 3. Read lua table to list and transform to a glyph dictionary
    font_glyph_dict = {}
    for font in lua_tables_data.keys():
        glyph_dict = {}
        for line in lua_tables_data[font]:
            elms = split_lua_line(line)
            glyph_dict[elms[0]] = elms[1:]
        font_glyph_dict[font] = glyph_dict
    # 4. Save data
    json_output = "font_glyph_dict.json"
    save_data_to_json(font_glyph_dict, json_output)

