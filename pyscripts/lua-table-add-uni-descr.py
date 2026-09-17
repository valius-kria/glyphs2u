#!/usr/bin/env python
from io_glyph_data import read_lua_table_in_list, write_lua_table_list, hex_codes_from_string
from unicode_descriptions import unicode_descr_for_code
import sys

# Converting a string of codes into unicode descriptions
def hex_codes_to_uni_descr(s):
    """
    Returns concatenated descriptions for a list of codes given as a string.
    
    Args:
       s: The input string of codes.
    
    Returns:
        Concatenated with '/' unicode descriptions of the codes.
        Returns an empty string if no codes were found.
    """
    codes = hex_codes_from_string(s)
    if not codes == []:
        return '/'.join(map(unicode_descr_for_code, codes))
    else:
        return ""

# Regenerate descriptions and update, if needed
def main():
    """
    Main function to work when file called as a script.
    """
    lua_table_file = sys.argv[1]
    lua_table_list = read_lua_table_in_list(lua_table_file)
    changed = False
    for idx, elm in enumerate(lua_table_list):
        if not type(elm) is str:
            descr = "-- " + hex_codes_to_uni_descr(elm[1])
            if not descr == elm[2]:
                changed = True
                lua_table_list[idx] = lua_table_list[idx][:2] + (descr,)
    if changed:
        write_lua_table_list(lua_table_list, lua_table_file)
    else:
        print(f"No changes made in lua table {lua_table_file}")

if __name__ == "__main__":
    main()
