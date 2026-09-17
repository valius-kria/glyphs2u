#!/usr/bin/env python
# Compare glyph sets saved in 'fonts_glyphs-dict.json'

# Function to group sets by number of elements
def group_sets_by_cardinality(set_dict: dict) -> dict:
    """
    Groups the given sets by number of elements.
    """
    cardinality_dict = {}
    for set_name, elem_list in set_dict.items():
        set_card = len(elem_list)
        cardinality_dict[set_card] = \
            cardinality_dict.get(set_card, []) + [set_name,]
    return cardinality_dict

# Function to compare sets equality and group equal sets
def group_equal_sets(set_dict: dict) -> list[list[str]]:
    # 1. Compares glyph sets by cardinality
    card_dict = group_sets_by_cardinality(set_dict)
    print(f"The sets grouped by cardinality: {card_dict}")

    partition_of_sets = []
    for card, set_list in card_dict.items():
        if len(set_list) == 1:
            set_list.insert(0, card)
            partition_of_sets.extend([set_list,])
        else:
            partition = []
            for set_name in set_list:
                set1 = set(set_dict[set_name])
                card_and_sets = [card, ]
                for font_set in partition:
                    set2 = set(set_dict[font_set[1]])
                    if set1 == set2:
                        font_set.append(set_name)
                        card_and_sets = font_set
                        break
                if len(card_and_sets) == 1:
                    partition.append([card, set_name])
            partition_of_sets.extend(partition)
    return partition_of_sets

def font_gs_rels(fonts_glyphs: dict) -> list[str]:
    """
    Finds relations between glyph sets of fonts.
    """
    # 2. Group fonts by the same glyph set
    font_set_partition = group_equal_sets(fonts_glyphs)

    # 3. Find glyph-set differences between groups
    group_dict = { i: font_set_partition[i]
                   for i in range(len(font_set_partition)) }
    diffs_matrix = {}
    for i, group in group_dict.items():
        group_diffs_dict = {'glyphs': group[0], 'group': group[1:]}
        glyphs = set(fonts_glyphs[group[1]])
        for j, group2 in group_dict.items():
            if i == j:
                group_diffs_dict[j] = [],
            else:
                diff = glyphs - set(fonts_glyphs[group2[1]])
                if len(diff) > 10:
                    group_diffs_dict[j] = "> 10 glyphs"
                else:
                    group_diffs_dict[j] = list(diff)
        diffs_matrix[i] = group_diffs_dict

    # 4. Finding some simple relations
    relations = []
    for i, diffs in diffs_matrix.items():
        gnum_str = str(diffs['glyphs']) # number of glyphs
        group_str = ", ".join(diffs['group']) # the font-name list
        relations.insert(i, "GS_" + str(i) + " with " + gnum_str + \
                         " glyphs is used in " + group_str + ".\n")
        for j, diffs2 in diffs_matrix.items():
            if not i == j:
                diff1 = diffs[j]
                diff2 = diffs2[i]
                if not type(diff1) is str: # small one difference
                    if diff1 == []: # subset relation
                        if type(diff2) is str: # more than 10 glyphs in diff2
                            relations += ["GS_" + str(j) + " = GS_" + str(i) +
                                          " + " + diff2 + "\n",]
                        else: # small another difference
                            relations += ["GS_" + str(j) + " = GS_" + str(i) +
                                          " + {" + ", ".join(diff2) + "}\n",]
                    else: # not subset, but almost
                        if type(diff2) is str: # more than 10 glyphs in diff2
                            relations += ["GS_" + str(i) + r" \ {" +
                                          ", ".join(diff1) + "} = GS_" +
                                          str(j) + r" \ " + diff2 + "\n",]
                        elif not diff2 == [] and i < j: # small another diff
                            relations += ["GS_" + str(i) + r" \ {" +
                                          ", ".join(diff1) + "} = GS_" +
                                          str(j) + r" \  {"  +
                                          ", ".join(diff2) + "}\n", ]
    return relations

if __name__ == "__main__":
    from glyph_maps import fg_dict
    rels_fname = 'font-glyph-set-rels.txt'

    with open(rels_fname, mode='w') as f:
        f.writelines(font_gs_rels(fg_dict))
    print(f"Comparison of glyph sets saved to the file: {rels_fname}")
