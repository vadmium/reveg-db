#! /usr/bin/env python3

from tkinter import Tk
from tkwrap import ScrolledTree
from sys import argv
from db import (CaCsvReader, FreqCsvReader)
from excel import (CplExcelReader, FreqExcelReader)
from db import QuadratReader
from contextlib import closing
import tkinter
from db import (tuple_record, parse_fields)
from operator import attrgetter
from db import (plant_key, NameSimplifier)
from sys import stderr
from tkinter import Toplevel
from tkinter.ttk import Entry
from fnmatch import fnmatchcase
from functools import partial

def main(*, ca_csv=(), cpl_excel=(), freqs=(), freqs_csv=(), quad=()):
    root = Tk()
    ui = Ui(root)
    
    ui.add_files(CaCsvReader, ca_csv, convert_cpl)
    ui.add_files(CplExcelReader, cpl_excel, convert_cpl)
    ui.add_files(FreqExcelReader, freqs, convert_freqs)
    ui.add_files(FreqCsvReader, freqs_csv, convert_freqs)
    ui.add_files(QuadratReader, quad)
    
    ui.names = list()
    for (i, (_, item)) in enumerate(sorted(ui.items.items())):
        ui.list.tree.move(item, "", i)
        
        name = ui.list.tree.set(item, 1)
        level = ui.names
        leaf = None
        for word in name.translate(NameSimplifier()).split():
            if not level or level[-1]["word"] != word:
                level.append(dict(word=word, children=list()))
            leaf = level[-1]
            level = leaf["children"]
        leaf["name"] = name
    
    win = Toplevel(root)
    win.title("Plant entry")
    
    ui.entry = Entry(win, width=30, validate="key",
        validatecommand=ValidateCommand(root, ui.entry_changed))
    ui.entry.pack(fill=tkinter.BOTH)
    ui.entry.focus_set()
    ui.entry.bind("<Return>", ui.add_entry)
    ui.entry.bind("<Up>", partial(ui.select_match, "prev"))
    ui.entry.bind("<Down>", partial(ui.select_match, "next"))
    
    ui.matches = ScrolledTree(win, tree=False, resize=True,
        columns=(dict(heading="Matches", width=30),))
    ui.matches.pack(fill=tkinter.BOTH, expand=True)
    
    root.mainloop()

class Ui(object):
    def __init__(self, window):
        window.title("Reference list")
        
        self.list = ScrolledTree(window, tree=False, resize=True, columns=(
            dict(heading="Origin", width=1),
            dict(heading="Name", width=20, stretch=True),
            dict(heading="Authority", width=6),
            dict(heading="Common name", width=15),
            dict(heading="Family", width=(3, ScrolledTree.FIGURE)),
            dict(heading="Family", width=8),
            dict(heading="Family", width=6),
            dict(heading="Division", width=(1, ScrolledTree.FIGURE)),
            dict(heading="Division", width=6),
            dict(heading="Note", width=3),
            dict(heading="SPECNUM", width=(4, ScrolledTree.FIGURE)),
        ))
        self.list.pack(fill=tkinter.BOTH, expand=True)
        self.list.tree.focus_set()
        
        self.items = dict()
        self.records = 0
    
    def add_files(self, Reader, files, convert=attrgetter("__dict__")):
        for file in files:
            print("Reading", file, file=stderr)
            with closing(Reader(file)) as file:
                for plant in file:
                    self.add_plant(convert(plant))
            self.print_count()
            print(file=stderr)
    
    def add_plant(self, plant):
        fields = """
            origin, name, auth, common, famnum, family, fam_com,
            divnum, group, note, specnum
        """
        key = plant_key(plant["name"])
        try:
            item = self.items[key]
        except LookupError:
            item = self.list.add()
            self.items[key] = item
        
        current = self.list.tree.item(item, option="values")
        current = tuple_record(current, fields, """origin""")
        if getattr(current, "origin", "?") == "?":
            current.origin = None
        fields = parse_fields(fields)
        for field in fields:
            if getattr(current, field, None) is None:
                value = plant.get(field)
                if value is None:
                    if field == "origin":
                        value = "?"
                    else:
                        value = ""
                setattr(current, field, value)
        self.list.tree.item(item,
            values=tuple(getattr(current, field) for field in fields))
        
        self.records += 1
        if not self.records % 200:
            self.print_count()
    
    def print_count(self):
        print("Records:", self.records, "Plants:", len(self.items), end="\r",
            file=stderr)
    
    def entry_changed(self, value):
        patterns = value.translate(SearchMap()).split()
        self.matches.tree.delete(*self.matches.tree.get_children())
        if patterns:
            for match in name_matches(self.names, patterns):
                s = str()
                i = 0
                space = True
                for word in match.split():
                    if not space:
                        s += " "
                    
                    while i < len(value):
                        c = value[i]
                        i += 1
                        if c.isalnum() or c == "_":
                            break
                        s += c
                    
                    s += word
                    
                    end = i
                    space = False
                    while i < len(value):
                        c = value[i]
                        i += 1
                        if c.isalnum() or c == "_":
                            end = i
                        elif c.isspace():
                            space = True
                            break
                    s += value[end:i]
                
                s += value[i:]
                self.matches.add(values=(s,))
        return True
    
    def select_match(self, dir, event):
        focus = self.matches.tree.focus()
        if (focus,) == self.matches.tree.selection():
            new = getattr(self.matches.tree, dir)(focus)
            if new:
                focus = new
        if not focus:
            return
        
        self.matches.tree.see(focus)
        self.matches.tree.focus(focus)
        self.matches.tree.selection_set((focus,))
        
        self.entry.configure(validate="none")
        self.entry.delete(0, tkinter.END)
        self.entry.insert(0, self.matches.tree.set(focus, 0))
        self.entry.select_range(0, tkinter.END)
        self.entry.configure(validate="key")
    
    def add_entry(self, event):
        print(self.entry.get())
        self.entry.delete(0, tkinter.END)

class SearchMap(object):
    def __getitem__(self, cp):
        cp = chr(cp)
        if cp == "_":
            return "*"
        if cp.isalnum():
            return cp.lower()
        if cp.isspace():
            return 0x20
        return None

def name_matches(trie, patterns, level=0):
    for node in trie:
        if (level < len(patterns) and
        not fnmatchcase(node["word"], patterns[level] + "*")):
            continue
        if level + 1 >= len(patterns) and "name" in node:
            yield node["name"]
        else:
            for name in name_matches(node["children"], patterns, level + 1):
                yield name

def convert_cpl(plant):
    plant = plant.__dict__
    plant["origin"] = plant["ex"]
    return plant

def convert_freqs(plant):
    return dict(
        origin=plant["ORIGIN"],
        name=plant["NAME"], auth=plant["AUTHORITY"],
        common=plant["COMMONNAME"],
        famnum=plant["FAMILYNO"], family=plant["FAMILYNAME"],
        divnum=plant["DIVISION"], group=plant["DivisionText"],
        specnum=plant["SPECNUM"]
    )

def ValidateCommand(tk, func):
    """Help get the new value for input validation
    
    Hinted by Michael Lange, "Validating an entry":
    http://mail.python.org/pipermail/tkinter-discuss/2006-August/000863.html
    """
    
    return (tk.register(func), "%P")

if __name__ == "__main__":
    from funcparams import command
    command()
