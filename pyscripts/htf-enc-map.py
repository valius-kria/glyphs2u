#!/usr/bin/env python 
# Load tfm-to-enc map, tfm-to-htf map, reverts the former to find encodings for htf files.
# Needed for finding glyph names in htf files

from io_data import load_dict_from_json, save_data_to_json
import sys
import os
# --- Configuration ---
tfm_htf_fname =  'tfm-htf-map.json'
tfm_enc_fname =  'tfm-enc-map.json'
htf_enc_fname =  'htf-enc-map.json'
# --- End Configuration ---

# Load data
tfm_htf_dict = load_dict_from_json(tfm_htf_fname)
tfm_enc_dict = load_dict_from_json(tfm_enc_fname)

# Compose reverted tfm_htf map with tfm_enc
htf_enc_dict = {}

# tfm-htf-map.json values became DICTS: {htf, entry, decl, chain}, because a
# declaration is spread along the alias chain and the old tfm -> htf string threw
# that away.  Only the chars owner is wanted here -- this map is for finding
# encodings -- so take ["htf"] and stay tolerant of the old string form, since a
# stale map on disk would otherwise be used as a dict and silently key everything
# by garbage rather than fail.
def _owner(v):
    return v["htf"] if isinstance(v, dict) else v

for tfm, _v in tfm_htf_dict.items():
    htf = _owner(_v)
    if htf in  htf_enc_dict.keys():
        htf_enc_dict[htf].add(tfm_enc_dict[tfm])
    else:
        htf_enc_dict[htf] = set([tfm_enc_dict[tfm],])

# change sets  to lists 
for htf, encs in htf_enc_dict.items():
    htf_enc_dict[htf] = sorted(encs)

# Save dictionary to JSON file
save_data_to_json(htf_enc_dict, htf_enc_fname)
