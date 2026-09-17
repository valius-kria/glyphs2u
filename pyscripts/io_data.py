# Functions to read and parse files and save data to files.
# Should be used in scripts for makefiles

import sys # To exit gracefully on error
import re
import os # For file-path management
import json 
import pickle # Added for binary serialization

# Saving data to json for manual editing and checking
def save_data_to_json(data, json_filepath):
    """
    Saves a Python data to a JSON file.

    Args:
        data (serializable): The data to save.
        json_filepath (str): The path for the output JSON file.
    """
    try:
        # Open the file for writing
        # Use utf-8 encoding for broader compatibility
        with open(json_filepath, mode='w', encoding='utf-8') as outfile:
            # Use json.dump to write the data to the file
            # indent=4 makes the JSON file human-readable (pretty-printed)
            # ensure_ascii=False allows non-ASCII characters (like accents, etc.)
            # to be written directly instead of escaped sequences (\uXXXX)
            json.dump(data, outfile, indent=4, ensure_ascii=False)
        print(f"Data successfully saved to JSON file: {json_filepath}")

    except IOError as e:
        print(f"Error: Could not write to JSON file '{json_filepath}': {e}")
        sys.exit(1)
    except TypeError as e:
        # This might happen if the data contains data types that are not
        # directly serializable to JSON (e.g., sets, custom objects)
        print(f"Error: Data is not fully JSON serializable: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while writing the JSON: {e}")
        sys.exit(1)

# Reading data from json file back to python data
def load_data_from_json(json_filepath):
    """
    Loads a Python data from a JSON file.

    Args:
        json_filepath (str): The path to the input JSON file.

    Returns:
        data: The data loaded from the file.
              Returns None if an error occurs during loading.
              Exits script on critical errors.
    """
    try:
        # Open the file for reading with UTF-8 encoding
        with open(json_filepath, mode='r', encoding='utf-8') as infile:
            # Use json.load to read the file object and parse JSON into Python object
            data = json.load(infile)
        return data

    except FileNotFoundError:
        print(f"Error: Input JSON file not found at '{json_filepath}'")
        sys.exit(1)
    except IOError as e: # Includes permission errors etc.
        print(f"Error: Could not read from JSON file '{json_filepath}': {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        # This error occurs if the file content is not valid JSON
        print(f"Error: Failed to decode JSON from file '{json_filepath}'. Invalid JSON format: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while loading the JSON file: {e}")
        sys.exit(1)

# Reading dictionary data from json file back to dictionary data type
def load_dict_from_json(json_filepath):
    """
    Loads a Python dictionary from a JSON file.

    Args:
        json_filepath (str): The path to the input JSON file.

    Returns:
        dict: The dictionary loaded from the file.
              Returns None if an error occurs during loading.
              Exits script on critical errors.
    """
    data_dict = load_data_from_json(json_filepath)
    # Basic type check after loading
    if not isinstance(data_dict, dict):
        print(f"Error: Loaded object from '{json_filepath}' is not a dictionary (type: {type(data_dict)}).")
        sys.exit(1)
#    else:
#        print(f"Dictionary successfully loaded from JSON file: {json_filepath}")
    return data_dict

# Reading list data from json file back to list data type
def load_list_from_json(json_filepath):
    """
    Loads a Python list from a JSON file.

    Args:
        json_filepath (str): The path to the input JSON file.

    Returns:
        list_data: The list loaded from the file.
              Returns None if an error occurs during loading.
              Exits script on critical errors.
    """
    list_data = load_data_from_json(json_filepath)
    # Basic type check after loading
    if not isinstance(list_data, list):
        print(f"Error: Loaded object from '{json_filepath}' is not a list (type: {type(list_data)}).")
        sys.exit(1)
    #else:
    #    print(f"List successfully loaded from JSON file: {json_filepath}")
    return list_data

# Saving dictionary to binary format for quickier loading (hopefully)
def save_dict_to_binary(dict, dict_fname):
    """
    Saves a Python dictionary to a binary file using pickle.

    Args:
        dict (dict): The dictionary to save.
        dict_fname (str): The path for the output binary file.
    """
    try:
        with open(dict_fname, mode='wb') as outfile: # 'wb' mode for binary writing
            # Use pickle.dump to serialize the object to the file
            # pickle.HIGHEST_PROTOCOL uses the most efficient protocol available
            pickle.dump(dict, outfile, pickle.HIGHEST_PROTOCOL)
        print(f"Dictionary successfully saved to binary file: {dict_fname}")

    except IOError as e:
        print(f"Error: Could not write to binary file '{dict_fname}': {e}")
        sys.exit(1)
    except pickle.PicklingError as e:
        # This might happen if the dictionary contains something unpickleable
        # (less common for standard dicts/tuples/strings)
        print(f"Error: Could not pickle the dictionary data: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while writing the binary file: {e}")
        sys.exit(1)

# Loading dictionary from binary format
def load_dict_from_binary(dict_fname):
    """
    Loads a Python dictionary from a binary file created by pickle.

    Args:
        dict_fname (str): The path to the input binary file.

    Returns:
        dict: The dictionary loaded from the file.
              Returns None if an error occurs during loading.
              Exits script on critical errors.
    """
    try:
        with open(dict_fname, mode='rb') as infile: # 'rb' mode for binary reading
            # Use pickle.load to deserialize the object from the file
            maybe_dict = pickle.load(infile)
        # Basic type check after loading (optional but recommended)
        if not isinstance(maybe_dict, dict):
            print(f"Error: Loaded object from '{dict_fname}' is not a dictionary (type: {type(maybe_dict)}).")
            sys.exit(1)
        #        else:
        #            print(f"Dictionary successfully loaded from binary file: {dict_fname}")
        return maybe_dict

    except FileNotFoundError:
        print(f"Error: Input binary file not found at '{dict_fname}'")
        sys.exit(1)
    except IOError as e:
        print(f"Error: Could not read from binary file '{dict_fname}': {e}")
        sys.exit(1)
    except pickle.UnpicklingError as e:
        # Indicates the file might be corrupted, not a pickle file,
        # or created with an incompatible Python/pickle version.
        print(f"Error: Could not unpickle data from '{dict_fname}'. File might be corrupted or incompatible: {e}")
        sys.exit(1)
    except EOFError:
        print(f"Error: Unexpected end of file reached while reading binary file '{dict_fname}'. File might be incomplete.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while loading the binary file: {e}")
        sys.exit(1)

# From my elisp definitions: one convenient way to define a file name:
def path_file(fname, dname=None, ext=None, suffix=""):
    """
    Returns a file name with optionally given a path, an extension, and a
    suffix (inserted before the extension).  In case 'dir' or 'ext' are not
    given, then the ones from the 'fname' are used.

    """
    if dname == None:
        dname, short_fname = os.path.split(fname)
    else:
        short_fname = os.path.basename(fname)
    if ext == None:
        bname, ext = os.path.splitext(short_fname)
    else:
        bname, _ = os.path.splitext(short_fname)
    return os.path.join(dname, bname + suffix + ext)
