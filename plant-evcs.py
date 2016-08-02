#! /usr/bin/env python3

from excel import FreqExcelReader
from contextlib import closing
import db
from sys import stderr
from time import monotonic

def lookup_tree(root, key):
    for [i, subkey] in enumerate(key):
        try:
            root = root[subkey]
        except LookupError:
            return (root, key[i:])
    return (root, ())

def add_tree(root, key):
    for subkey in key:
        children = dict()
        root[subkey] = children
        root = children

def walk_tree(root, *, _path=list()):
    for [key, children] in sorted(root.items()):
        _path.append(key)
        try:
            if children:
                yield from walk_tree(children, _path=_path)
            else:
                yield _path
        finally:
            _path.pop()

def parse_synonyms(filename, tree):
    if not filename:
        return
    
    prev = dict()
    with open(filename, "rt") as reader:
        for line in reader:
            line = line.rstrip(" \r\n")
            line = line.split(" = ")
            for [i, plant] in enumerate(line):
                key = list()
                for word in plant.split(" "):
                    abbr = word
                    if abbr.endswith("."):
                        abbr = abbr[:-1]
                    if abbr in db.abbr:
                        continue
                    
                    if word.endswith("."):
                        genus = None
                        if not key and len(word) == 2:
                            genus = prev.get(word[0], None)
                        if genus is None:
                            msg = "No match for abbreviated {!r}"
                            print(msg.format(plant), file=stderr)
                        else:
                            word = genus
                    elif not key:
                        prev[word[0]] = word
                    key.append(word)
                
                genus = key[0]
                if genus.istitle():
                    key[0] = genus.lower()
                else:
                    msg = "Genus {!r} is not in title case"
                    print(msg.format(genus), file=stderr)
                
                [children, remainder] = lookup_tree(tree, key)
                if remainder:
                    if children or children is tree:
                        if not i:
                            msg = "First synonym {} not already listed"
                            print(msg.format(plant), file=stderr)
                        add_tree(children, remainder)
                    else:
                        msg = "Supertaxon of {} already listed".format(plant)
                        print(msg, file=stderr)
                else:
                    if children:
                        while children:
                            [subname, _] = children.popitem()
                            msg = "{} subtaxon {} already listed"
                            print(msg.format(plant, subname), file=stderr)
                    elif i:
                        msg = "{} equivalent already listed".format(plant)
                        print(msg, file=stderr)

def main(freqs, selection=None, *, synonyms=None):
    deadline = monotonic() + 1
    midline = False
    
    tree = dict()  # {subname: ..., ...}
    if selection:
        prev = None
        with open(selection, "rt") as reader:
            for plant in reader:
                plant = plant.rstrip(" \r\n")
                key = list()
                for word in plant.split(" "):
                    abbr = word
                    if abbr.endswith("."):
                        abbr = abbr[:-1]
                    if abbr in db.abbr:
                        continue
                    
                    if not key:
                        if word.istitle():
                            word = word.lower()
                        else:
                            msg = "Genus {!r} is not in title case"
                            print(msg.format(word), file=stderr)
                    if word.endswith("."):
                        if prev is None:
                            msg = "No previous entry to expand {!r} from"
                            print(msg.format(plant), file=stderr)
                        elif len(prev) > len(key) \
                                and prev[:len(key)] == key \
                                and prev[len(key)].startswith(word[:-1]):
                            word = prev[len(key)]
                        else:
                            print("Abbreviated {!r} does not match " \
                                "previous entry".format(plant), file=stderr)
                    key.append(word)
                prev = key
                
                [children, remainder] = lookup_tree(tree, key)
                if remainder:
                    if children or children is tree:
                        add_tree(children, remainder)
                    else:
                        msg = "Supertaxon of {} already listed".format(plant)
                        print(msg, file=stderr)
                else:
                    if children:
                        while children:
                            [subname, _] = children.popitem()
                            msg = "{} subtaxon {} already listed"
                            print(msg.format(plant, subname), file=stderr)
                    else:
                        msg = "{} equivalent already listed".format(plant)
                        print(msg, file=stderr)
    
    parse_synonyms(synonyms, tree)
    selected = set()
    evcs = list()  # [(evc, desc, {name: freq for each plant}) for each EVC]
    max_freqs = list()  # [max(freq) for each EVC]
    with closing(FreqExcelReader(freqs)) as freqs:
        total = format(len(freqs))
        last_evc = None
        for [i, plant] in enumerate(freqs):
            if stderr:
                now = monotonic()
                if now >= deadline:
                    if midline:
                        stderr.write("\r")
                    msg = "Record {:{}}/{}".format(i + 1, len(total), total)
                    stderr.write(msg)
                    stderr.flush()
                    midline = True
                    deadline = now + 0.1
            
            if plant["EVC"] != last_evc:
                last_evc = plant["EVC"]
                last_desc = plant["EVC_DESC"]
                plant_freqs = dict()
                evcs.append((last_evc, last_desc, plant_freqs))
                max_freqs.append(plant["Frequency"])
            else:
                max_freqs[-1] = max(max_freqs[-1], plant["Frequency"])
                if plant["EVC_DESC"] != last_desc:
                    msg = "EVC {} EVC_DESC inconsistent between {!r} and " \
                        "{!r}".format(last_evc, last_desc, plant["EVC_DESC"])
                    print(msg, file=stderr)
                    last_desc = plant["EVC_DESC"]
            name = plant["NAME"]
            if selection:
                key = list(n[0] for n in db.plant_key(name))
                if not key[-1]:
                    key.pop()
                [children, remainder] = lookup_tree(tree, key)
                if remainder and children:
                    continue
            selected.add(name)
            if name in plant_freqs:
                msg = "Duplicate record for {NAME} in {EVC}"
                print(msg.format_map(plant), file=stderr)
            plant_freqs[name] = plant_freqs.get(name, 0) + plant["Frequency"]
    
    if stderr and midline:
        stderr.write("\x1B[1K\r")
        stderr.flush()
    
    heading = "{:>4.4} {:67.67}{:>5.5}"
    print(heading.format("EVC", "EVC_DESC", "max(Frequency)"))
    for [[evc, desc, _], max_freq] in zip(evcs, max_freqs):
        print("{:4} {:67.67}{:5}".format(evc, desc, max_freq))
    print(end="NAME"[:32].ljust(32))
    for [evc, _, _] in evcs:
        print(end=format(evc, "6"))
    print()
    for plant in sorted(selected, key=db.plant_key):
        print(end=plant[:32].ljust(32))
        for [[_, _, freqs], max_freq] in zip(evcs, max_freqs):
            freq = freqs.get(plant)
            if freq is None:
                print(end=" " * 6)
                continue
            found = True
            print(end=format(freq / max_freq, "6.3f"))
        print()
        
        if selection:
            # Prune any non-branching paths leading to this entry
            key = list(n[0] for n in db.plant_key(plant))
            if not key[-1]:
                key.pop()
            node = tree
            for subkey in key:
                if len(node) > 1:
                    branch_node = node
                    branch_name = subkey
                try:
                    node = node[subkey]
                except LookupError:
                    break
            if not node:
                del branch_node[branch_name]
    
    if selection:
        for path in walk_tree(tree):
            msg = "No records matching {}"
            print(msg.format(" ".join(path).capitalize()), file=stderr)

if __name__ == "__main__":
    from clifunc import run
    run(main)
