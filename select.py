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

def main(*, ca_csv=(), cpl_excel=(), freqs=(), freqs_csv=(), quad=()):
    root = Tk()
    ui = Ui(root)
    
    ui.add_files(CaCsvReader, ca_csv, convert_cpl)
    ui.add_files(CplExcelReader, cpl_excel, convert_cpl)
    ui.add_files(FreqExcelReader, freqs, convert_freqs)
    ui.add_files(FreqCsvReader, freqs_csv, convert_freqs)
    ui.add_files(QuadratReader, quad)
    
    
    
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
    
    def add_files(self, Reader, files, convert=attrgetter("__dict__")):
        for file in files:
            with closing(Reader(file)) as file:
                for plant in file:
                    self.add_plant(convert(plant))
    
    def add_plant(self, plant):
        fields = """
            origin, name, auth, common, famnum, family, fam_com,
            divnum, group, note, specnum
        """
        name = plant["name"]
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
                value = plant.get(field)
                if value is None:
                    if field == "origin":
                        value = "?"
                    else:
                        value = ""
                setattr(current, field, value)
        self.list.tree.item(item,
            values=tuple(getattr(current, field) for field in fields))

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

if __name__ == "__main__":
    from funcparams import command
    command()
