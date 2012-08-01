#! /usr/bin/env python3

from tkinter import Tk
from lib.tk import ScrolledTree
from sys import argv
from db import (CaPlantReader, FreqReader, QuadratReader)
from contextlib import closing
from lib import Record
import tkinter
from db import (tuple_record, parse_fields)

def main(*, ca=(), freqs=(), quad=()):
    root = Tk()
    ui = Ui(root)
    
    for file in ca:
        with closing(CaPlantReader(file)) as file:
            for plant in file:
                ui.add(Record(
                    origin=plant.ex, name=plant.name, common=plant.common,
                    family=plant.family, fam_com=plant.fam_com,
                    group=plant.group, note=plant.note
                ))
    for file in freqs:
        with closing(FreqReader(file)) as file:
            for plant in file:
                ui.add(Record(
                    origin=plant["ORIGIN"],
                    name=plant["NAME"], auth=plant["AUTHORITY"],
                    common=plant["COMMONNAME"],
                    famnum=plant["FAMILYNO"], family=plant["FAMILYNAME"],
                    divnum=plant["DIVISION"], group=plant["DivisionText"],
                    specnum=plant["SPECNUM"]
                ))
    for file in quad:
        with closing(QuadratReader(file)) as file:
            for plant in file:
                ui.add(Record(
                    origin=plant.origin,
                    name=plant.name, common=plant.common,
                    family=getattr(plant, "family", None),
                    group=getattr(plant, "group", None)
                ))
    
    root.mainloop()

class Ui(object):
    def __init__(self, window):
        window.title("Plant list")
        
        self.list = ScrolledTree(window, tree=False, columns=(
            Record(heading="Origin", width=1),
            Record(heading="Name", width=20, stretch=True),
            Record(heading="Authority", width=6),
            Record(heading="Common name", width=15),
            Record(heading="Family", width=(3, ScrolledTree.FIGURE)),
            Record(heading="Family", width=8),
            Record(heading="Family", width=6),
            Record(heading="Division", width=(1, ScrolledTree.FIGURE)),
            Record(heading="Division", width=6),
            Record(heading="Note", width=3),
            Record(heading="SPECNUM", width=(4, ScrolledTree.FIGURE)),
        ))
        self.list.pack(fill=tkinter.BOTH, expand=True)
        self.list.tree.focus_set()
        
        self.items = dict()
    
    def add(self, record):
        fields = """
            origin, name, auth, common, famnum, family, fam_com,
            divnum, group, note, specnum
        """
        
        try:
            item = self.items[record.name]
        except LookupError:
            item = self.list.add()
            self.items[record.name] = item
        
        current = self.list.tree.item(item, option="values")
        current = tuple_record(current, fields, """origin""")
        if getattr(current, "origin", "?") == "?":
            current.origin = None
        fields = parse_fields(fields)
        for field in fields:
            if getattr(current, field, None) is None:
                value = getattr(record, field, None)
                if value is None:
                    if field == "origin":
                        value = "?"
                    else:
                        value = ""
                setattr(current, field, value)
        self.list.tree.item(item,
            values=tuple(getattr(current, field) for field in fields))

from lib import run_main
run_main(__name__)
