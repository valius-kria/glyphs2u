# Copies lua tables to destination directory
import config
lua_tables_copy = getattr(config, 'lua_tables_copy', {})
import os
import sys
import shutil
import filecmp

dest_dir = config.dest_dir
lua_tables = config.lua_tables
if len(sys.argv) > 1:
    # deploy the lua table indicated in the first argument
    lua_fname = sys.argv[1]
    lua_tables = [lua_fname,]
    if len(sys.argv) > 2:
        # single lua table deployment, no copies, whatever was the second argument
        lua_tables_copy = { lua_fname: [], }
    else:
        lua_tables_copy = { lua_fname: lua_tables_copy.get(lua_fname, []), }
        print(f"Checking all copies of {lua_fname} in {dest_dir}")
else:
    # Check all copies of all lua tables
    print(f"Checking all copies of {', '.join(lua_tables)} in {dest_dir}")

if not os.path.isdir(dest_dir):
    os.makedirs(dest_dir) # makedirs creates parent dirs if necessary, like mkdir -p
    print(f"Directory {dest_dir} created.")

for fname in lua_tables:
    if not os.path.isfile(fname):
        print(f"Warning: Source file {fname} not found. Skipping.")
        continue

    # The .get(fname, []) ensures that if list_name is not in the dict,
    # we get an empty list, preventing a KeyError.
    copy_list = lua_tables_copy.get(fname, [])
        
    # The final list includes the original fname_noext plus copies
    fname_noext = os.path.splitext(os.path.basename(fname))[0]
    copy_list = [fname_noext,] + copy_list

    for fn_base in copy_list:
        # dest_file="${dest_dir}/${other_fname}.lua"
        dest_file = os.path.join(dest_dir, f"{fn_base}.lua")
        op = ""

        # We also need to handle the case where dest_file doesn't exist yet.
        files_are_identical = False
        if os.path.exists(dest_file):
            # filecmp.cmp returns True if identical, False otherwise.
            # shallow=False means content comparison, not just stat.
            files_are_identical = filecmp.cmp(fname, dest_file, shallow=False)
                
            if files_are_identical:
                op = "Skipped (no change)"
            else:
                op = "Updated"
        else:
            op = "Added"
        if not files_are_identical:
            try:
                shutil.copyfile(fname, dest_file)
            except Exception as e:
                print(f"Error copying {fname} to {dest_file}: {e}")
                op = f"Error ({e})" # Or skip printing this one

        print(f"{op}: {dest_file}")

