# Loads unicode data and defines one function
from io_data import load_dict_from_binary
import os

# Importable dictionary of Unicode values
UNIDATA_FILE = os.path.join(os.environ['UNICODE_DIR'], 'UnicodeData.pkl')
UNICODEDATA = load_dict_from_binary(UNIDATA_FILE)

# Obtaining of Unicode description for the given code
def unicode_descr_for_code(code):
    """
    Returns Unicode description for the given code

    Args:
        code (str): a string presenting some hexadecimal number
    Returns:
        str: The Unicode description of the symbol for the given code
    """
    num = int(code, 16)
    code = code[2:]
    uni_descr = ""
    if num < 0 or num > 0x10FFFD:
        uni_descr = "Outside of the Unicode range [0,10FFFD]"
    elif num >= 0x3400 and num <= 0x4DBF:
        uni_descr = "<CJK Ideograph Extension A>"
    elif num >= 0x4E00 and num <= 0x9FFF:
        uni_descr = "<CJK Ideograph>"
    elif num >= 0xAC00 and num <= 0xD7A3:
        uni_descr = "<Hangul Syllable>"
    elif num >= 0xD800 and num <= 0xDB7F:
        uni_descr = "<Non Private Use High Surrogate>"
    elif num >= 0xDB80 and num <= 0xDBFF:
        uni_descr = "<Private Use High Surrogate>"
    elif num >= 0xDC00 and num <= 0xDFFF:
        uni_descr = "<Low Surrogate>"
    elif num >= 0xE000 and num <= 0xF8FF:
        uni_descr = "<Private Use>"
    elif num >= 0x17000 and num <= 0x187F7:
        uni_descr = "<Tangut Ideograph>"
    elif num >= 0x18D00 and num <= 0x18D08:
        uni_descr = "<Tangut Ideograph Supplement>"
    elif num >= 0x20000 and num <= 0x2A6DF:
        uni_descr = "<CJK Ideograph Extension B>"
    elif num >= 0x2A700 and num <= 0x2B739:
        uni_descr = "<CJK Ideograph Extension C>"
    elif num >= 0x2B740 and num <= 0x2B81D:
        uni_descr = "<CJK Ideograph Extension D>"
    elif num >= 0x2B820 and num <= 0x2CEA1:
        uni_descr = "<CJK Ideograph Extension E>"
    elif num >= 0x2CEB0 and num <= 0x2EBE0:
        uni_descr = "<CJK Ideograph Extension F>"
    elif num >= 0x2EBF0 and num <= 0x2EE5D:
        uni_descr = "<CJK Ideograph Extension I>"
    elif num >= 0x30000 and num <= 0x3134A:
        uni_descr = "<CJK Ideograph Extension G>"
    elif num >= 0x31350 and num <= 0x323AF:
        uni_descr = "<CJK Ideograph Extension H>"
    elif num >= 0xF0000 and num <= 0xFFFFD:
        uni_descr = "<Plane 15 Private Use>"
    elif num >= 0x100000 and num <= 0x10FFFD:
        uni_descr = "<Plane 16 Private Use>"
    elif code in UNICODEDATA:
        uni_descr = UNICODEDATA[code][0]
    else:
        uni_descr = "Code not found in UnicodeData"
    return uni_descr
