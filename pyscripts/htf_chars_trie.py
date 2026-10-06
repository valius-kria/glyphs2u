#!/usr/bin/env python3
"""A prefix tree over the ['chars'] VECTORS of htf_data.lua (and user_htf.lua).

Whether a font needs an htf of its own is data-driven: if another font's table
already says the same thing, that one can be used -- by the largest-prefix rule
on the names, or by an explicit ['alias'] when the names do not cooperate, or by
keeping the ['chars'] and adding only font-level properties.  Deciding that means
comparing vectors of up to 256 values, which pairwise is 1382 x 1382 x 256.

A trie makes the comparison structural instead.  Each font's table is read as a
DENSE vector, position 1..256, with a hole where a position is undefined, and the
vectors are inserted into a tree keyed by the value at each position.  Then:

  * two fonts with the SAME table end at one leaf -- alias candidates outright;
  * one table being a PREFIX of another (it agrees as far as it goes and defines
    nothing beyond) is a parent/child relation in the tree -- the shorter font
    can take the longer one's table;
  * where two tables first differ is the depth at which their paths part, so the
    tree also says how nearly two fonts agree, which pairwise comparison would
    have to compute one pair at a time.

The report is what the tree shows, not the tree itself: identical groups, prefix
relations, and how deep tables agree before parting.

Usage: htf_chars_trie.py [--lua FILE ...] [--min-prefix N] [--out FILE]
"""
import argparse, collections, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpm_io as G

LUA_DIR = os.path.dirname(G.HTF_LUA)
ap = argparse.ArgumentParser()
ap.add_argument("--lua", nargs="*", default=[os.path.join(LUA_DIR, "htf_data.lua"),
                                             os.path.join(LUA_DIR, "user_htf.lua")])
ap.add_argument("--min-prefix", type=int, default=64,
                help="report pairs agreeing at least this far (default 64)")
ap.add_argument("--top", type=int, default=12, help="how many examples to print")
a = ap.parse_args()

# --- reading ----------------------------------------------------------------
# Tolerant of whitespace inside the brackets: user_htf.lua has [<TAB>"fplmbb"].
Q = r'(?:"([^"]*)"|\'([^\']*)\')'
_top = re.compile(r'^\t\[\s*' + Q + r'\s*\]\s*=\s*$')
_sect = re.compile(r'^\t\t\[\s*(?:"(\w+)"|\'(\w+)\')\s*\]')
_pos = re.compile(r'^\t\t\t\[\s*' + Q + r'\s*\]')
_val = re.compile(r'\[\s*(?:"value"|\'value\')\s*\]\s*=\s*' + Q)
_alias = re.compile(r'^\t\t\[\s*(?:"alias"|\'alias\')\s*\]\s*=\s*' + Q)

def qv(m, o=0):
    return m.group(1 + o) if m.group(1 + o) is not None else m.group(2 + o)

def parse(path):
    out, cur, section, p = {}, None, None, None
    for line in open(path, encoding="utf-8", errors="replace"):
        mt = _top.match(line)
        if mt:
            cur = qv(mt)
            out[cur] = {"chars": {}, "font": None, "alias": None, "src": path}
            section = p = None
            continue
        if cur is None:
            continue
        ma = _alias.match(line)
        if ma:
            out[cur]["alias"] = qv(ma)
            continue
        ms = _sect.match(line)
        if ms:
            section = ms.group(1) or ms.group(2)
            if section == "font":
                out[cur]["font"] = {}
            continue
        if section == "chars":
            mp = _pos.match(line)
            if mp:
                p = int(qv(mp))
                continue
            mv = _val.search(line)
            if mv and p is not None:
                out[cur]["chars"][p] = qv(mv)
    return out

fonts = {}
for path in a.lua:
    if not os.path.exists(path):
        print(f"  (no {os.path.basename(path)})", file=sys.stderr)
        continue
    for k, v in parse(path).items():
        fonts[k] = v                    # later file wins, as the loader does

MAXPOS = 256
HOLE = None

def vector(chars):
    """Positions 1..(last defined), a hole where the table skips one.

    Dense from 1, so that a prefix means 'agrees from the first position', and a
    hole INSIDE the range is a value in the tree like any other -- two tables
    that differ only in whether position 60 is defined must part there.

    But TRUNCATED at the last defined position, not padded to 256, and that is
    the whole point: padded, every vector has the same length and no vector can
    be a proper prefix of another, so the parent/child relation the tree exists
    to show would never appear.  Truncated, a table defined to 128 is a prefix of
    a fuller one it agrees with, which is exactly the case where the shorter font
    can take the longer one's table.
    """
    if not chars:
        return ()
    last = max(chars)
    return tuple(chars.get(i, HOLE) for i in range(1, last + 1))

vecs = {f: vector(d["chars"]) for f, d in fonts.items() if d["chars"]}

# --- the tree ---------------------------------------------------------------
class Node:
    __slots__ = ("kids", "ends", "depth")
    def __init__(self, depth=0):
        self.kids = {}                  # value at this depth -> Node
        self.ends = []                  # fonts whose vector stops being defined here
        self.depth = depth

root = Node()
n_nodes = 1
for font, v in sorted(vecs.items()):
    node = root
    for d, val in enumerate(v):
        nxt = node.kids.get(val)
        if nxt is None:
            nxt = node.kids[val] = Node(d + 1)
            n_nodes += 1
        node = nxt
    node.ends.append(font)

# --- what it shows ----------------------------------------------------------
same = [ns for ns in (n.ends for n in ()) if ns]        # filled below
identical, branch, depth_hist = [], 0, collections.Counter()
stack = [root]
while stack:
    n = stack.pop()
    if len(n.ends) > 1:
        identical.append(sorted(n.ends))
    if len(n.kids) > 1:
        branch += 1
        depth_hist[n.depth] += len(n.kids) - 1
    stack.extend(n.kids.values())

# a table that is a PREFIX of another: its path continues past its own end
prefix_of = []
def walk(n, ended):
    for f in n.ends:
        if n.kids:                      # something continues below this leaf
            deeper = []
            st = list(n.kids.values())
            while st:
                m = st.pop()
                deeper.extend(m.ends)
                st.extend(m.kids.values())
            if deeper:
                prefix_of.append((f, n.depth, sorted(deeper)))
    for k in n.kids.values():
        walk(k, ended)
walk(root, [])

# how far the nearest other table agrees, per font: sort and compare neighbours
keys = sorted(vecs.items(), key=lambda kv: tuple("" if x is HOLE else x for x in kv[1]))
def lcp(u, v):
    n = 0
    for x, y in zip(u, v):
        if x != y:
            break
        n += 1
    return n
near = {}
for i, (f, v) in enumerate(keys):
    best = 0
    if i:
        best = max(best, lcp(v, keys[i - 1][1]))
    if i + 1 < len(keys):
        best = max(best, lcp(v, keys[i + 1][1]))
    near[f] = best

print(f"htf_chars_trie: {len(fonts)} entries read, {len(vecs)} with a ['chars'] "
      f"table\n  aliases={sum(1 for d in fonts.values() if d['alias'])}  "
      f"font-decl only={sum(1 for d in fonts.values() if d['font'] is not None and not d['chars'])}")
print(f"  distinct vectors: {len(set(vecs.values()))}   trie nodes: {n_nodes}   "
      f"branch points: {branch}")

print(f"\n  identical tables ({len(identical)} group(s), "
      f"{sum(len(g) for g in identical)} fonts) -- one table would do for each group:")
for g in sorted(identical, key=len, reverse=True)[:a.top]:
    al = [f for f in g if fonts[f]["alias"]]
    print(f"    {len(g):>3}  {', '.join(g[:6])}{' ...' if len(g) > 6 else ''}"
          + (f"   ({len(al)} already aliased)" if al else ""))

print(f"\n  a table that is a PREFIX of another ({len(prefix_of)}): the shorter font "
      f"could take the longer one's table")
for f, d, deeper in sorted(prefix_of, key=lambda x: -x[1])[:a.top]:
    print(f"    {f:<26} defined to {d:>3}, continues in: "
          f"{', '.join(deeper[:4])}{' ...' if len(deeper) > 4 else ''}")

print(f"\n  how far the nearest other table agrees:")
buckets = collections.Counter()
for f, n in near.items():
    buckets[(n // 32) * 32] += 1
for lo in sorted(buckets):
    print(f"    {lo:>3}..{lo+31:<3} {buckets[lo]:>5} font(s)")
deep = [(n, f) for f, n in near.items() if n >= a.min_prefix and
        vecs[f] not in {vecs[g] for g in sum(identical, []) if g != f}]
print(f"\n  agreeing {a.min_prefix}+ positions yet not identical ({len(deep)}), "
      f"the near-misses worth a look:")
for n, f in sorted(deep, reverse=True)[:a.top]:
    i = [j for j, (g, _v) in enumerate(keys) if g == f][0]
    others = [keys[j][0] for j in (i - 1, i + 1) if 0 <= j < len(keys)
              and lcp(vecs[f], keys[j][1]) == n]
    print(f"    {f:<26} agrees to {n:>3} with {', '.join(others)}")
