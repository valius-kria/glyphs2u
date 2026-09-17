#!/usr/bin/env python3
import os
import sys
import pathlib
import itertools

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from texmf_paths import texmf_var

# Specify the directory name
directory_path = pathlib.Path(sys.argv[1])
font_path = pathlib.Path(sys.argv[2])

def font_subpath(file_path):
    """Return the path of the font directory relative to a texmf tree's
    `fonts/` directory, e.g. "type1/public/lm", or None if the fonts do not
    live in a texmf tree at all (not every free font family is in TeX Live).
    """
    parts = pathlib.Path(file_path).parts
    try:
        return '/'.join(parts[parts.index('fonts') + 1:]) or None
    except ValueError:
        return None


def in_texmfdist(file_path):
    """True if the font directory is inside the texmf-dist of the TeX Live
    tree that kpsewhich belongs to."""
    dist = texmf_var("TEXMFDIST")
    if not dist:
        return False
    try:
        pathlib.Path(file_path).resolve().relative_to(pathlib.Path(dist).resolve())
        return True
    except ValueError:
        return False


data1 = """# Some paths and lists necessary for deployment of lua tables and not noly for that
# import os # just for the case when 'lua_tables' list is made by reading the
# directory content as in the following line:
# lua_tables = [each for each in os.listdir(r"./") if each.endswith('.lua')]
"""

data2 = """
# List all deployable tables in the current working directory
# lua_tables = []
# For each table, copyable to more than one file, list other names where to copy
# lua_tables_copy = {
#     "lmr10.lua": ["lmr17", "lmr12", "lmr9", "lmr8", "lmr7", "lmr6", "lmr5"],
#     "lmsy10.lua": ["lmsy9", "lmsy8", "lmsy7", "lmsy6", "lmsy5"],
#     "lmbsy10.lua": ["lmbsy7", "lmbsy5"],}
# lua_tables_not_needed = []
"""

data3 = f"""# Makefile
# Include the common Makefile
include {'/'.join('..' for n in directory_path.parts)}/common.Makefile
"""

if __name__ == "__main__":
    try:
        # Create the directory
        if directory_path.is_dir():
            print(f"Directory '{directory_path}' already exists.")
        else:
            directory_path.mkdir(parents=True)
            print(f"Directory '{directory_path}' created successfully.")

        # Write the initial config.py
        config_fname = directory_path / "config.py"
        subpath = font_subpath(font_path)
        if config_fname.is_file():
            print(f"File '{config_fname}' already exists. Not writing...")
        else:
            with open(config_fname, 'w') as f:
                f.write(data1)
                if subpath and in_texmfdist(font_path):
                    f.write('from texmf_paths import texmf_font_dir, '
                            'xdvipsk_cmap_dir\n')
                    f.write('font_dir = texmf_font_dir("{}")\n'.format(subpath))
                    f.write('dest_dir = xdvipsk_cmap_dir("{}")\n'.format(subpath))
                else:
                    env = directory_path.name.upper().replace('-', '_') \
                        + '_FONT_DIR'
                    f.write('from texmf_paths import font_dir_from_env, '
                            'xdvipsk_cmap_dir\n')
                    f.write('# These fonts are not in TeX Live; set {} to\n'
                            '# the directory holding them.\n'.format(env))
                    f.write('font_dir = font_dir_from_env("{}")\n'.format(env))
                    f.write('dest_dir = xdvipsk_cmap_dir("{}")\n'.format(
                        subpath or directory_path.name))
                f.write(data2)
                font_files = [ os.path.splitext(fn)[0]
                               for fn in sorted(os.listdir(font_path))
                               if fn.endswith(('.pfb', '.ttf', '.otf')) ]
                f.write( 'lua_tables_tocheck = [\n    \"' +
                         '\", \"'.join(font_files) + '\"\n]' )
            print(f"File '{config_fname}' written successfully.")

        # Write initial Makefile
        mkfname = directory_path / "Makefile"
        if mkfname.is_file():
            print(f"File '{mkfname}' already exists. Not writing...")
        else:
            with open(mkfname, 'w') as mkf:
                mkf.write(data3)
            print(f"File '{mkfname}' written successfully.")

    except PermissionError:
        print(f"Permission denied: Unable to create '{directory_path}'.")
    except Exception as e:
        print(f"An error occurred: {e}")


