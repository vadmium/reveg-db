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

def main(*, ca_csv=(), cpl_excel=(), freqs=(), freqs_csv=(), quad=()):
    root = Tk()
    ui = Ui(root)
    
    for file in ca_csv:
        with closing(CaCsvReader(file)) as file:
            for plant in file:
                ui.add(
                    origin=plant.ex, name=plant.name, common=plant.common,
                    family=plant.family, fam_com=plant.fam_com,
                    group=plant.group, note=plant.note
                )
    for file in cpl_excel:
        with closing(CplExcelReader(file)) as file:
            for plant in file:
                ui.add(
                    origin=plant.ex,
                    name=plant.name, common=plant.common,
                    family=plant.family, fam_com=plant.fam_com,
                    group=getattr(plant, "group", None),
                    note=plant.note,
                )
    
    ui.add_freqs(FreqExcelReader, freqs)
    ui.add_freqs(FreqCsvReader, freqs_csv)
    
    for file in quad:
        with closing(QuadratReader(file)) as file:
            for plant in file:
                ui.add(
                    origin=plant.origin,
                    name=plant.name, common=plant.common,
                    family=getattr(plant, "family", None),
                    group=getattr(plant, "group", None)
                )
    
    root.mainloop()

class Ui(object):
    def __init__(self, window):
        window.title("Plant list")
        
        self.list = ScrolledTree(window, tree=False, columns=(
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
    
    def add(self, **kw):
        fields = """
            origin, name, auth, common, famnum, family, fam_com,
            divnum, group, note, specnum
        """
        name = kw["name"]
        try:
            item = self.items[name]
        except LookupError:
            item = self.list.add()
            self.items[name] = item
        
        current = self.list.tree.item(item, option="values")
        current = tuple_record(current, fields, """origin""")
        if getattr(current, "origin", "?") == "?":
            current.origin = None
        fields = parse_fields(fields)
        for field in fields:
            if getattr(current, field, None) is None:
                value = kw.get(field)
                if value is None:
                    if field == "origin":
                        value = "?"
                    else:
                        value = ""
                setattr(current, field, value)
        self.list.tree.item(item,
            values=tuple(getattr(current, field) for field in fields))
    
    def add_freqs(self, Reader, files):
        for file in files:
            with closing(Reader(file)) as file:
                for plant in file:
                    self.add(
                        origin=plant["ORIGIN"],
                        name=plant["NAME"], auth=plant["AUTHORITY"],
                        common=plant["COMMONNAME"],
                        famnum=plant["FAMILYNO"], family=plant["FAMILYNAME"],
                        divnum=plant["DIVISION"], group=plant["DivisionText"],
                        specnum=plant["SPECNUM"]
                    )

if __name__ == "__main__":
    from funcparams import command
    command()
