#!/usr/bin/env python
# coding=utf-8

"""
Script created by L. Stonys, translated by V.Kriaučiukas.
The script collects information from .htf files and saves it in htf_data.json.
Parameters:
    <dir> and/or <file> -- several directories or files can be provided.
    The search of .htf files in directories is done recursively.

Format of htf_data.json:
    { "<file>" :  { 
                "font": {"variant": "small-caps", ...},
                "chars": {"1": "<mfont mathvariant=\"fraktur\">d</mfont>", ...},
                "alias": {"<font>"}
                }}
                
    <file>  -- tfm name. The name can be a prefix of the real name, such is
                a htf-specific way to create one .htf file for several tfm files
                with a common prefix.
    "font"  -- dictionary with htfcss information
    "chars" -- dictionary with really existing tfm chars
    "alias" -- other htf file name for searching the chars. Alias can be recursive.
    
Calling:
    python htf_to_json.py foo.htf
"""
__version__ = '0.02'
__author__ = "Linas Stonys <lstonys@vtex.lt>"

import os
import sys
import re
import json
# import pickle

## htf example
# ptmru8t 13 255
# ' ' '' 32 space        %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# '&#x2200;' '' 34 universal    % Copyright (C) `CopyYear.2004. Eitan M. Gurari %
# @<mfont mathvariant="fraktur">d</mfont>@ @@  letter d  0 `<version 0`>
# ptmru8t 13 255
# htfcss: ptmru8t font-style: italic;

htf_data = {}
output = "htf_data.json"

# The new data is added to existing in the json file
if os.path.isfile(output):
    with open(output, encoding='utf-8') as json_file:  
        htf_data = json.load(json_file)

def parse_htf_file(htf_path):
    """ 
        :htf_path: path to a htf file
        The procedure parses htf file and adds info to dictionary htf_data.
    """

    if not os.path.isfile(htf_path):
        print ('File not found: %s' % htf_path)
        exit(1)
    # print (htf_path)

    filenames_set = set()
    cur_directory = ''
    basename = os.path.basename(htf_path)[:-4]
    with open(htf_path, 'r',  encoding='utf-8', errors='ignore') as f:
        htf_lines = f.readlines()
        idx = 0
        if htf_lines[0].startswith("."):
            # this is alias
            mainfile = htf_lines[0].strip().lstrip(".")
            htf_data[basename] = {"alias": mainfile}
        else:
            mainfile, start, end = "", "", ""
            m = re.match(r'(\S+)\s+(\d+)\s+(\d+)', htf_lines[0])
            if m:
                mainfile, start, end = m.group(1), m.group(2), m.group(3)
                idx = int(start)
                htf_data[mainfile] = {"chars": {}}
            else:
                print ("ERROR: unable parse the first line: %s; %s", (htf_path, htf_lines[0]))
                return

        for line in htf_lines:
            if line.startswith("'") or line.startswith("@"):
                m = re.match(r"^('|@)(.*?)\1", line)
                # print line, m.groups()
                if m and m.group(2) not in ["", "\\nounicode"]:
                    # print line, m, m.groups()
                    results = {"value": m.group(2)}
 
                    ## get text after first match
                    i = len(m.group(2)) + 2
                    line_left = line[i:].strip()
                    ## find number (second '') representing type of symbol: "'&#x229E;' '4' squareplus         1" 
                    m2 = re.match(r"^('|@)(\d)\1", line_left)
                    if m2: 
                        results.update({"type": m2.group(2)})
                    # was
                    #try:
                    #    htf_data[mainfile]["chars"][idx] = results
                    #except KeyError as e:
                    #    print ("ERROR: cannot find file %s" % mainfile)
                    #    break
                    if mainfile in htf_data.keys():
                        if "chars" in htf_data[mainfile].keys():
                            htf_data[mainfile]["chars"][idx] = results
                        else:
                            htf_data[mainfile]["chars"] = {idx: results, }
                    else:
                        htf_data[mainfile] = {"chars": {idx: results, }, }
            idx = idx + 1

            if line.startswith("htfcss:"):
                line = line[8:].strip()
                s = re.match(r"^(\S+)", line)
                if s:
                    file  = s.group(1)
                    p = re.findall(r"font-(\w+):(\s+)?(\S+);", line )
                    if file not in htf_data:
                        htf_data[file] = {}
                    if "font" not in htf_data[file]:
                        htf_data[file].update({"font": {}})
                    if file != basename:
                        htf_data[file]["alias"] = mainfile

                    for f in p:
                        feature = f[2]
                        if feature == 'monospace,monospace':
                            feature = 'monospace'
                        htf_data[file]["font"][f[0]] = feature

                else:
                    print ("ERROR: unable parse htfcss info: %s, %s" % (htf_path, line))
                
                

"""     
    Parameters in the command line are treated as directories or htf files.
"""                
args = sys.argv[1:]
if not args:
    print ("Provide .htf file(s) or path(s) to them.")
    sys.exit(0)

filelist = []
for p in args:
    p = os.path.abspath(p)
    if (os.path.isfile(p) or os.path.islink(p)) and p.lower().endswith(".htf"):
        # parse_htf_file(os.path.relpath(p))
        parse_htf_file(p)
    elif os.path.isdir(p):
        for root, subdirs, files in os.walk(p):
            for file in files:
                if not file.lower().endswith(".htf"):
                    continue
                # parse_htf_file(os.path.relpath(os.path.join(root, file)))
                parse_htf_file(os.path.join(root, file))
    else:
        print ("Parameter '%s' is not a .htf failas and not a directory" % p)
        continue

# print (htf_data)

with open(output, 'w') as fd:
    json.dump(htf_data, fd, indent=4)
    # json.dump(htf_data, fd)

# json_data = json.dumps(htf_data)    
# py_dict = json.loads(json_data, object_hook=lambda d: {int(k) if k.lstrip('-').isdigit() else k: v for k, v in d.items()})
# # print py_dict
# with open(output, 'w') as fd:
    # # pickle.dump(py_dict, fd, 2)
