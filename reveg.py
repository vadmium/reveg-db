#! /usr/bin/env python3

#The incantation for making a Python script executable under WinNT is to give the file an extension of .cmd and add the following as the first line:

#@setlocal enableextensions & python -x %~f0 %* & goto :EOF
#cmd shebang needs quotes for "%~f0"

from sys import (argv, stderr)
from collections import defaultdict
from xml.sax import saxutils
from tkinter.tix import Tk
from tkinter.ttk import (Button, Entry, Frame, Label, LabelFrame,
    Checkbutton)
import tkinter
from tkinter.filedialog import asksaveasfile
from functools import partial
from tkinter import (StringVar, DoubleVar, Toplevel)
from tkinter.tix import FileEntry
from lib.tk import ScrolledTree
from tkinter.font import nametofont
from lib.tk import font_size
from lib.tk import Form
from db import (CaCsvReader, FreqReader, QuadratReader)
from contextlib import closing
from lib import Record

def main():
    help = False
    grid = 0o000
    area = []
    plants = []
    freq_thold = THOLD_DEFAULT
    ca_file = None
    freq_file = None
    evcs = []
    quads = []
    
    i = iter(argv)
    next(i)
    while True:
        try:
            arg = next(i)
        except StopIteration:
            break
        
        lower = arg.lower()
        if lower in {"help", "-h", "--help", "-?", "?"}:
            help = True
        elif lower == "grid":
            grid |= int(next(i), 8)
        elif lower == "area":
            area.extend(next(i))
        elif lower == "ca":
            ca_file = next(i)
        elif lower == "freqs":
            freq_file = next(i)
        elif lower == "evc":
            evcs.append(next(i))
        elif lower == "quad":
            quads.append(next(i))
        elif lower == "thold":
            freq_thold = float(next(i))
        else:
            raise SystemExit('''\
Bad command line argument: {}
Try "{} help"'''.format(arg, argv[0]))
    
    if help:
        print("""\
join ca ... [area ...] [freqs ... evc ...] [quad ...] [options] > output.html
\tIncludes only those plants selected by the "area", "evc" and "quad"
\toptions. Ignores plants with * and + origin, and ferns, orchids and
\tmistletoes.

Options:
ca <{CA_DEFAULT}>
\tCastlemaine plant list CSV file. Produce combined list based off this.
freqs <{FREQ_DEFAULT}>
\tEVC frequency plant list CSV file
grid <octal code>
\tOctal (binary) mask code of 10-minute grid references to highlight. The
\tmatching grid code(s) are indicated in the list, but this does not
\taffect whether a plant is selected in the list. A single grid code
\thighlights plants in the corresponding grid area, independent of whether
\tthey are also in any other grid areas. Multiple grid options means to
\thighlight which of the provided grids a plants is from. 
area <alphanumeric sequence>
\tCastlemaine plant list area codes to include. More than one may be
\tspecified as a string of codes or multiple options. The order does not
\tmatter. The matching codes are indicated in the list.
evc <name or number>
\tInclude plants whose relative frequencies in EVC exceed threshold. Use
\t"freqs" option alone to list EVCs. If the EVC does not exist (or is
\tspelt wrong), the only indication is the corresponding output column is
\tnot populated.
quad <Viridans CSV file>
\tInclude plants from Viridans quadrat. The "systematic format" is
\tprobably better than the alphabetical because some types of plants are
\tthen easily identified by the program and ignored.
thold <threshold>
\tEVC frequency threshold (default: {THOLD_DEFAULT})
help\tDisplay this help""".format(**locals()))
        return
    
    root = Tk()
    
    if ca_file is None and freq_file is None and not quads:
        Ui(root, grid=grid, area=area, evcs=evcs, freq_thold=freq_thold)
    else:
        join(root,
            ca_file=ca_file, grid=grid, area=area,
            freq_file=freq_file, evcs=evcs, freq_thold=freq_thold,
            quads=quads,
        )
    
    root.mainloop()

class Ui(object):
    def __init__(self, root, grid, area, evcs, freq_thold):
        self.root = root
        self.root.title("Reveg DB")
        form = Form(self.root, column=1)
        
        frame = FormSection(form, text="Castlemaine plant list")
        (self.ca_file, ca_entry) = add_file(form, CA_DEFAULT,
            text="Source file")
        
        self.grid = StringVar(value=format(grid, "03o"))
        field = Frame(self.root)
        entry = Entry(field, textvariable=self.grid, validate="key",
            validatecommand=ValidateCommand(self.root, validate_grid))
        entry.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
        grid_button = partial(grid_menu, self.grid, field)
        grid_button = Button(field, text="Menu . . .", command=grid_button)
        grid_button.pack(side=tkinter.LEFT)
        form.add_field(field, text="Highlight grid sections")
        
        self.area = StringVar(value="".join(area))
        entry = Entry(self.root, textvariable=self.area)
        form.add_field(entry, text="Select areas")
        
        frame.close()
        
        self.freqs = Freqs(form, evcs=evcs, thold=freq_thold)
        self.quads = Quads(form)
        
        button = Button(self.root, text="Produce list . . .",
            command=self.join)
        button.grid(columnspan=4)
        
        ca_entry.focus_set()
    
    def join(self):
        (evcs, evc_names) = self.freqs.get_evcs()
        (quad_files, quad_names) = self.quads.get()
        join(Toplevel(self.root),
            ca_file=self.ca_file.get() or None,
            grid=int(self.grid.get(), 8),
            area=self.area.get(),
            freq_file=self.freqs.file.get() or None,
            evcs=evcs, evc_names=evc_names,
            freq_thold=self.freqs.thold.get(),
            quads=quad_files, quad_names=quad_names,
        )

def validate_grid(value):
    if not value:
        return True
    
    try:
        value = int(value, 8)
    except ValueError as err:
        print(err, file=stderr)
        return False
    
    return 0 <= value < 0o1000

FREQ_DEFAULT = "GoldfieldsBrgnlEVCSppFreq.xls.csv"
CA_DEFAULT = "PLANT_CA.TXT"
THOLD_DEFAULT = 0.3

class grid_menu(Toplevel):
    def __init__(self, grid, master):
        self.var = grid
        
        Toplevel.__init__(self, master)
        self.title("Grid sections")
        self.bind("<Return>", self.destroy)
        self.bind("<Escape>", self.destroy)
        
        entry = Entry(self, textvariable=self.var, validate="key",
            validatecommand=ValidateCommand(master, validate_grid))
        entry.pack(fill=tkinter.X)
        
        frame = Frame(self)
        self.buttons = list()
        for column in range(3):
            frame.columnconfigure(column, weight=1)
        
        for row in range(3):
            frame.rowconfigure(row, weight=1)
            
            buttons = list()
            for (column, name) in enumerate(self.names[row]):
                command = partial(self.update_var, row, column)
                button = Checkbutton(frame, command=command, text=name)
                button.state(("!alternate",))
                button.grid(row=row, column=column, sticky=tkinter.NSEW)
                
                if not int(self.focus_lastfor()["takefocus"]):
                    button.focus_set()
                buttons.append(button)
            self.buttons.append(buttons)
        
        frame.pack(fill=tkinter.BOTH, expand=True)
        
        self.var_cb = self.var.trace_variable("w", self.update_buttons)
        self.update_buttons()
        
        button = Button(self, text="Close", command=self.destroy, default="active")
        button.pack(side=tkinter.BOTTOM)
    
    names = (
        ("M46", "M47", "M48"),
        ("N1", "N2", "N3"),
        ("N10", "N11", "N12"),
    )
    
    def update_var(self, row, column):
        current = int(self.var.get(), 8)
        value = 0o100 << row >> (column * 3)
        button = self.buttons[row][column]
        if button.instate(("selected",)):
            current |= value
        else:
            current &= ~value
        self.var.set(format(current, "03o"))
    
    def destroy(self, *_):
        self.var.trace_vdelete("w", self.var_cb)
        return Toplevel.destroy(self)
    
    def update_buttons(self, *_):
        value = int(self.var.get(), 8)
        for (row, buttons) in enumerate(self.buttons):
            for (column, button) in enumerate(buttons):
                if value & 0o100 << row >> (column * 3):
                    button.state(("selected",))
                else:
                    button.state(("!selected",))

class Quads(object):
    def __init__(self, form):
        frame = FormSection(form, text="Viridans quadrats")
        
        self.name = StringVar()
        entry = Entry(form.master, textvariable=self.name)
        form.add_field(entry, text="Name")
        
        self.file = StringVar()
        entry = FileEntry(form.master, dialogtype="tk_getOpenFile",
            variable=self.file)
        form.add_field(entry, text="Source file")
        
        buttons = Frame(form.master)
        button = Button(buttons, text="Add", command=self.add)
        button.pack(side=tkinter.LEFT, expand=True)
        button = Button(buttons, text="Remove", command=self.remove)
        button.pack(side=tkinter.LEFT, expand=True)
        buttons.grid(column=form.column, columnspan=2, sticky=tkinter.EW)
        
        self.list = ScrolledTree(form.master, tree=False,
            columns=("Name", "File"))
        self.list.grid(column=form.column, columnspan=2, sticky=tkinter.NSEW)
        form.master.rowconfigure(self.list.grid_info()["row"], weight=1)
        self.list.bind_select(self.select)
        
        frame.close()
    
    def add(self):
        item = self.list.add(values=(self.name.get(), self.file.get(),))
        self.list.tree.focus(item)
        self.list.tree.selection_set(item)
        
        # Apparently needed when calling Treeview.see() straight after adding
        # an item
        self.list.update_idletasks()
        
        self.list.tree.see(item)
    
    def select(self, *_):
        (item,) = self.list.tree.selection()
        (name, file) = self.list.tree.item(item, option="values")
        self.name.set(name)
        self.file.set(file)
    
    def remove(self):
        # Empty selection returns empty string?!
        items = tuple(self.list.tree.selection())
        
        focus = self.list.tree.focus()
        refocus = focus in items
        if refocus:
            new = focus
            while new in items:
                new = self.list.tree.next(new)
            if not new:
                new = focus
                while new in items:
                    new = self.list.tree.prev(new)
            if not new:
                refocus = False
        
        self.list.tree.delete(*items)
        
        if refocus:
            self.list.tree.focus(new)
    
    def get(self):
        files = list()
        names = list()
        for item in self.list.tree.get_children():
            (name, file) = self.list.tree.item(item, option="values")
            files.append(file)
            names.append(name)
        return (files, names)

class join(object):
    def __init__(self, window, *,
    ca_file, grid, area,
    freq_file, evcs, evc_names=None, freq_thold,
    quads, quad_names=None):
        for name in ("window, "
        "ca_file, grid, area, "
        "freq_file, evcs, freq_thold, "
        "quads").split(", "):
            setattr(self, name, vars()[name])
        
        if evc_names is None:
            self.evc_names = evcs
            self.evc_keys = EVC_KEYS
        else:
            self.evc_names = evc_names
            self.evc_keys = ("EVC",)
        
        if quad_names is None:
            self.quad_names = quads
        else:
            self.quad_names = quad_names
        
        self.window.title("Plant list")
        self.window.bind("<Return>", self.save)
        
        headings = self.headings()
        output = ScrolledTree(self.window, tree=False, columns=headings)
        output.grid(sticky=tkinter.NSEW)
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)
        self.entries = list()
        for entry in self:
            self.entries.append(entry)
            output.add(values=entry)
        
        buttons = Frame(self.window)
        buttons.grid()
        button = Button(buttons, text="Save as HTML . . .",
            command=self.save, default="active")
        button.grid(row=0, column=0)
        button = Button(buttons, text="Close", command=self.window.destroy)
        button.grid(row=0, column=1)
        
        output.tree.focus_set()
    
    def headings(self):
        headings = ["name", "common", "ex", "area", "grid"]
        headings.extend(self.evc_names)
        headings.extend(self.quad_names)
        return headings
    
    def __iter__(self):
        class Plant(object):
            def __init__(self):
                self.ca = None
                self.evcs = dict()
                self.quads = dict()
        plants = defaultdict(Plant)
        
        if self.ca_file is not None:
            with closing(CaCsvReader(self.ca_file)) as file:
                for plant in file:
                    if (plant.ex in tuple("*+") or
                    plant.group == "f" or
                    plant.family in ("Orchidaceae", "Loranthaceae")):
                        continue
                    plants[plant.name].ca = plant
        
        if self.freq_file is not None:
            DIV_FERN = "2"
            DIV_MOSS = "5"
            FAM_MISTLETOE = "100"
            FAM_ORCHID = "124"
            
            max_freq = dict()
            
            with closing(FreqReader(self.freq_file)) as file:
                for plant in file:
                    for key in self.evc_keys:
                        evc = plant[key]
                        if evc not in self.evcs:
                            continue
                        
                        freq = plant["Frequency"]
                        try:
                            max = max_freq[evc]
                        except LookupError:
                            max_freq[evc] = freq
                        else:
                            if freq > max:
                                max_freq[evc] = freq
                        
                        if (plant["ORIGIN"] == "*" or
                        plant["DIVISION"] in (DIV_FERN, DIV_MOSS) or
                        plant["FAMILYNO"] in (FAM_ORCHID, FAM_MISTLETOE)):
                            continue
                        
                        plants[plant["NAME"]].evcs[evc] = plant
        
        for quad_file in self.quads:
            with closing(QuadratReader(quad_file)) as file:
                for plant in file:
                    if (plant.origin == "*" or
                    plant.group == "6: Ferns and Fern-like Plants" or
                    plant.family in ("Orchidaceae", "Loranthaceae")):
                        continue
                    plants[plant.name].quads[quad_file] = plant
        
        for name in sorted(plants.keys()):
            plant = plants[name]
            
            if plant.ca is None:
                common = ""
                ex = ""
                area = ""
                grid = ""
            else:
                common = plant.ca.common
                ex = plant.ca.ex
                area = "".join(a for a in plant.ca.area if a in self.area)
                if plant.ca.grid:
                    grid = format(int(plant.ca.grid, 8) & self.grid, "03o")
                else:
                    grid = plant.ca.grid
            
            rel = list()
            thold_met = False
            for evc in self.evcs:
                try:
                    evc_plant = plant.evcs[evc]
                except LookupError:
                    rel.append("")
                else:
                    freq = evc_plant["Frequency"] / max_freq[evc]
                    thold_met = thold_met or freq >= self.freq_thold
                    rel.append(format(freq, ".2f"))
            
            inquads = tuple(quad in plant.quads for quad in self.quads)
            
            if not area and not thold_met and not any(inquads):
                continue
            
            res = [name, common, ex, area, grid] + rel
            res.extend("Y" if q else "" for q in inquads)
            yield res
    
    def write_html(self, entries, file):
        print("""\
<html><body><table>
  <tr>""", file=file)
        print_tagged("th", self.headings(), file)
        print("""  </tr>""", file=file)
        
        for entry in entries:
            print("""  <tr>""", file=file)
            print_tagged("td", entry, file)
            print("""  </tr>""", file=file)
        
        print("""</table></body></html>""", file=file)
    
    def save(self, event=None):
        file = asksaveasfile(title="Save as HTML", parent=self.window,
            filetypes=(
                ("HTML", (".html", ".htm")),
                ("All", ("*",)),
            ))
        if not file:
            return
        with file:
            self.write_html(self.entries, file)

def print_tagged(tag, list, file):
    for text in list:
        text = saxutils.escape(text)
        print("<{tag}>{text}</{tag}>".format_map(locals()), file=file)

EVC_KEYS = ("EVC_DESC", "EVC")

class Freqs(object):
    def __init__(self, form, evcs, thold):
        frame = FormSection(form, text="EVC frequencies")
        
        (self.file, _) = add_file(form, FREQ_DEFAULT, text="Source file")
        
        self.saved_evcs = evcs
        self.evc_list = ScrolledTree(form.master, tree=False, columns=(
            Record(heading="EVC", width=(4, ScrolledTree.FIGURE)),
            Record(heading="EVC_DESC", width=30, stretch=True),
        ))
        form.add_field(self.evc_list, text="Select EVCs", multiline=True)
        self.select_binding = self.evc_list.bind_select(self.select)
        
        self.file.trace("w", self.update)
        
        self.thold = DoubleVar(value=thold)
        vcmd = ValidateCommand(form.master, self.validate_thold)
        entry = Entry(form.master, textvariable=self.thold, validate="key",
            validatecommand=vcmd)
        form.add_field(entry, text="Frequency threshold")
        
        frame.close()
    
    def update(self, *_):
        self.evc_list.tree.delete(*self.evc_list.tree.get_children())
        
        if not self.file.get():
            return
        
        with closing(FreqReader(self.file.get())) as file:
            evcs = set(tuple(row[key] for key in EVC_KEYS)
                for row in file)
        
        selection = list()
        for (name, number) in sorted(evcs):
            item = self.evc_list.add(values=(number, name))
            if name in self.saved_evcs or number in self.saved_evcs:
                selection.append(item)
        
        if selection:
            self.evc_list.unbind_select(self.select_binding)
            self.evc_list.tree.focus(selection[0])
            self.evc_list.tree.selection_set(tuple(selection))
            
            # Treeview.see() straight after adding items does not seem to
            # work without at least update_idletasks(), and the <<Treeview
            # Select>> event does not seem to be handled until update() is
            # called.
            self.evc_list.update()
            
            self.evc_list.tree.see(selection[-1])
            self.evc_list.tree.see(selection[0])
            
            self.select_binding = self.evc_list.bind_select(self.select)
    
    def select(self, event):
        self.saved_evcs = list()
        for item in self.evc_list.tree.selection():
            item = self.evc_list.tree.item(item, option="values")
            self.saved_evcs.extend(item)
    
    def get_evcs(self):
        numbers = list()
        names = list()
        for item in self.evc_list.tree.selection():
            (number, name) = self.evc_list.tree.item(item, option="values")
            numbers.append(number)
            names.append(name)
        return (numbers, names)
    
    def validate_thold(self, value):
        if not value:
            return True
        
        try:
            value = DoubleVar(value=value).get()
        except ValueError as err:
            print(err, file=stderr)
            return False
        
        return 0 <= value <= 1

def add_file(form, default, **kw):
    field = Frame(form.master)
    file = StringVar(value=default)
    entry = FileEntry(field, dialogtype="tk_getOpenFile", variable=file)
    entry.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
    Button(field, text="Delete", command=partial(file.set, "")).pack(
        side=tkinter.LEFT)
    form.add_field(field, **kw)
    return (file, entry)

class FormSection(LabelFrame):
    def __init__(self, form, *args, **kw):
        self.form = form
        
        font = nametofont("TkDefaultFont")
        self.top = font.metrics("linespace")
        self.side = font_size(font["size"])
        padding = font_size(font["size"] / 2)
        
        LabelFrame.__init__(self, form.master, *args, **kw)
        self.grid(column=form.column - 1, columnspan=4, sticky=tkinter.NSEW,
            padx=padding, pady=(0, padding))
    
    def close(self):
        # All fields returned from grid_info() are strings!
        row = int(self.grid_info()["row"])
        
        master = self.form.master
        (_, rows) = master.size()
        self.grid(rowspan=rows + 1 - row)
        master.rowconfigure(row, minsize=self.top)
        master.columnconfigure(self.form.column - 1, minsize=self.side)
        master.columnconfigure(self.form.column + 2, minsize=self.side)
        master.rowconfigure(rows, minsize=self.side)

def ValidateCommand(tk, func):
    """Help get the new value for input validation
    
    Hinted by Michael Lange, "Validating an entry":
    http://mail.python.org/pipermail/tkinter-discuss/2006-August/000863.html
    """
    
    return (tk.register(func), "%P")

if __name__ == "__main__":
    main()

#Grid alias incl cmd line
#Fuzzy text matching; full stops are not significant: var. = var; prefer without
#@Ern: Some plants are abbreviated, minor problems worked around; eg:
# Lomandra longifolia ssp longifol.
# Dianella aff longifolia 'Benambra
# Lomandra multiflora ssp multiflor
#How to handle origin, exotic, AROTS, VROTS merging or multiple columns
