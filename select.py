#! /usr/bin/env python3

from tkinter import Tk
from lib.tk import ScrolledTree
from sys import argv
from readers import (CaPlantReader, FreqReader, QuadratReader)
from contextlib import closing
import tkinter

def main(*, ca=(), freqs=(), quad=()):
    root = Tk()
    root.title("Plant list")
    
    list = ScrolledTree(root, tree=False, columns=(
        Record(heading="Name", width=16),
        Record(heading="Authority", width=6),
        Record(heading="Common name", width=12),
        Record(heading="Origin", width=1),
        Record(heading="Family", width=(3, ScrolledTree.FIGURE)),
        Record(heading="Family", width=6),
        Record(heading="Family", width=6),
        Record(heading="Division", width=(1, ScrolledTree.FIGURE)),
        Record(heading="Division", width=6),
        Record(heading="Note", width=3),
        Record(heading="SPECNUM", width=(4, ScrolledTree.FIGURE)),
    )
    list.pack(fill=tkinter.BOTH, expand=True)
    list.focus_set()
    
    for file in ca:
        with closing(CaPlantReader(file)) as file:
            for plant in file:
                list.add(values=(
                    plant.name, "", plant.common, plant.ex,
                    "", plant.family, plant.fam_com, "", plant.group,
                    plant.note, ""))
    for file in freqs:
        with closing(FreqReader(file)) as file:
            for plant in file:
                list.add(values=(
                    plant["NAME"], plant["AUTHORITY"], plant["COMMONNAME"],
                    plant["ORIGIN"],
                    plant["FAMILYNO"], plant["FAMILYNAME"], "",
                    plant["DIVISION"], plant["DivisionText"],
                    "", plant["SPECNUM"]))
    for file in quad:
        with closing(QuadratReader(file)) as file:
            for plant in file:
                list.add(values=(
                    plant.name, "", plant.common, plant.origin,
                    "", getattr(plant, "family", ""), "",
                    "", getattr(plant, "group", ""), "", ""))
    
    root.mainloop()

from lib import run_main
run_main(__name__)
