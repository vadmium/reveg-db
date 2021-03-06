#! /usr/bin/env python3

from sys import (argv, stderr)
from xml.sax import saxutils
#~ from functools import partial
from db import QuadratReader
from contextlib import closing
import guis
from functools import total_ordering
from db import plant_key
from contextlib import closing

TITLE = "Reveg DB version 0.3.0"

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
    for arg in i:
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
{TITLE}

Usage:\treveg.py [ca ... [area ...] [freqs ... evc ...] [quad ...]] [options]

Includes only those plants selected by the "area", "evc" and "quad" options.
Ignores plants with * and + origin, and ferns, orchids and mistletoes.

Options:
ca <{CA}>
\tCastlemaine plant list file, CSV or Excel. Produce combined list
\tbased off this.
freqs <{FREQS}>
\tEVC frequency plant list file, CSV or Excel
grid <octal code>
\tOctal (binary) mask code of 10-minute grid references to highlight.
\tThe matching grid code(s) are indicated in the list, but this does
\tnot affect whether a plant is selected in the list. A single grid
\tcode highlights plants in the corresponding grid area, independent of
\twhether they are also in any other grid areas. Multiple grid options
\tmeans to highlight which of the provided grid areas a plants is from. 
area <alphanumeric sequence>
\tCastlemaine plant list area codes to include. More than one may be
\tspecified as a string of codes or multiple options. The order does
\tnot matter. The matching codes are indicated in the list.
evc <name>
\tInclude plants whose relative frequencies in EVC exceed threshold.
\tIf the EVC does not exist (or is spelt wrong), the only indication is
\tthe corresponding output column is not populated.
quad <Viridans CSV file>
\tInclude plants from Viridans quadrat. The "systematic format" is
\tprobably better than the alphabetical because some types of plants
\tare then easily identified by the program and ignored.
thold <threshold>
\tEVC frequency threshold (default: {THOLD})
help\tDisplay this help""".format(
            TITLE=TITLE, CA=CA_DEFAULT, FREQS=FREQ_DEFAULT,
            THOLD=THOLD_DEFAULT))
        return
    
    gui = guis.probe()
    with closing(gui.loop):
        if ca_file is None and freq_file is None and not quads:
            Ui(gui, grid=grid, area=area, evcs=evcs, freq_thold=freq_thold)
        else:
            join(gui,
                ca_file=ca_file, grid=grid, area=area,
                freq_file=freq_file, evcs=evcs, freq_thold=freq_thold,
                quads=quads,
            )
        
        gui.loop.run_forever()

class Ui(guis.Window):
    def __init__(self, gui, grid, area, evcs, freq_thold):
        self.gui = gui
        
        self.ca_file = FileEntry(self.gui, CA_DEFAULT,
            title='Find "{CA_DEFAULT}"'.format_map(globals()),
            types=(("Spreadsheet", ("TXT", "csv", "xls")),),
        )
        
        #self.grid = StringVar(value=format(grid, "03o"))
        self.grid = guis.Entry(format(grid, "03o"))
        #entry = Entry(field, textvariable=self.grid, validate="key",
        #    validatecommand=ValidateCommand(self.root, validate_grid))
        #entry.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
        #grid_button = partial(grid_menu, self.grid, field)
        grid_button = guis.Button("Menu . . .")
        
        #self.area = StringVar(value="".join(area))
        self.area = guis.Entry("".join(area))
        
        self.freqs = Freqs(gui, evcs=evcs, thold=freq_thold)
        self.quads = Quads(gui)
        
        #button.grid(columnspan=4)
        
        guis.Window.__init__(self, gui, title=TITLE, contents=guis.Form(
            guis.Section("&Castlemaine plant list",
                guis.Field("Source file", self.ca_file.layout),
                guis.Field("Highlight &grid sections",
                    guis.Inline(self.grid, grid_button)),
                guis.Field("Select &areas", self.area),
            ),
            self.freqs.win_section,
            self.quads.win_section,
            guis.Button("&Produce list . . .", command=self.join),
        ))
        self.ca_file.set_parent(self)
        self.freqs.file.set_parent(self)
        self.quads.file.set_parent(self)
    
    def join(self):
        (evcs, evc_names) = self.freqs.get_evcs()
        (quad_files, quad_names) = self.quads.get()
        join(self.gui, self,
            ca_file=self.ca_file.entry.get() or None,
            grid=int(self.grid.get(), 8),
            area=self.area.get(),
            freq_file=self.freqs.file.entry.get() or None,
            evcs=evcs, evc_names=evc_names,
            freq_thold=float(self.freqs.thold.get()),
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

FREQ_DEFAULT = "GoldfieldsBrgnlEVCSppFreq.xls"
CA_DEFAULT = "cpl-14-04.xls"
THOLD_DEFAULT = 0.3

#class grid_menu(Toplevel):
#    def __init__(self, grid, master):
#        self.var = grid
#        
#        Toplevel.__init__(self, master)
#        self.title("Grid sections")
#        self.bind("<Return>", self.destroy)
#        self.bind("<Escape>", self.destroy)
#        
#        entry = Entry(self, textvariable=self.var, validate="key",
#            validatecommand=ValidateCommand(master, validate_grid))
#        entry.pack(fill=tkinter.X)
#        
#        frame = Frame(self)
#        self.buttons = list()
#        for column in range(3):
#            frame.columnconfigure(column, weight=1)
#        
#        for row in range(3):
#            frame.rowconfigure(row, weight=1)
#            
#            buttons = list()
#            for (column, name) in enumerate(self.names[row]):
#                command = partial(self.update_var, row, column)
#                button = Checkbutton(frame, command=command, text=name)
#                button.state(("!alternate",))
#                button.grid(row=row, column=column, sticky=tkinter.NSEW)
#                
#                if not int(self.focus_lastfor()["takefocus"]):
#                    button.focus_set()
#                buttons.append(button)
#            self.buttons.append(buttons)
#        
#        frame.pack(fill=tkinter.BOTH, expand=True)
#        
#        self.var_cb = self.var.trace_variable("w", self.update_buttons)
#        self.update_buttons()
#        
#        button = Button(self, text="Close", command=self.destroy, default="active")
#        button.pack(side=tkinter.BOTTOM)
#    
#    names = (
#        ("M46", "M47", "M48"),
#        ("N1", "N2", "N3"),
#        ("N10", "N11", "N12"),
#    )
#    
#    def update_var(self, row, column):
#        current = int(self.var.get(), 8)
#        value = 0o100 << row >> (column * 3)
#        button = self.buttons[row][column]
#        if button.instate(("selected",)):
#            current |= value
#        else:
#            current &= ~value
#        self.var.set(format(current, "03o"))
#    
#    def destroy(self, *_):
#        self.var.trace_vdelete("w", self.var_cb)
#        return Toplevel.destroy(self)
#    
#    def update_buttons(self, *_):
#        value = int(self.var.get(), 8)
#        for (row, buttons) in enumerate(self.buttons):
#            for (column, button) in enumerate(buttons):
#                if value & 0o100 << row >> (column * 3):
#                    button.state(("selected",))
#                else:
#                    button.state(("!selected",))

class Quads(object):
    def __init__(self, gui):
        self.name = guis.Entry()
        self.file = FileEntry(gui,
            title="Find Viridans quadrat file",
            types=(("CSV spreadsheet", ("CSV",)),),
            delete=False,
        )
        self.list = guis.List(("Name", "File"), selected=self.selected)
        
        self.win_section = guis.Section("Viridans &quadrats",
            guis.Field("Name", self.name),
            guis.Field("Source file", self.file.layout, access="V"),
            guis.Inline(
                guis.Button("Add", command=self.add),
                guis.Button("Remove", command=self.remove),
            ),
            self.list,
        )
    
    def add(self):
        item = self.list.add((self.name.get(), self.file.entry.get(),))
        #~ self.list.tree.focus(item)
        #~ self.list.tree.selection_set(item)
        
        #~ # Apparently needed when calling Treeview.see() straight after adding
        #~ # an item
        #~ self.list.update_idletasks()
        
        #~ self.list.tree.see(item)
    
    def remove(self):
        for item in reversed(self.list.selection()):
            self.list.remove(item)
    
    def selected(self):
        try:
            (item,) = self.list.selection()
        except ValueError:
            # Don't do anything if not exactly one item is selected
            return
        (name, file) = self.list.get(item)
        self.name.set(name)
        self.file.entry.set(file)
    
    def get(self):
        files = list()
        names = list()
        for item in self.list:
            (name, file) = self.list.get(item)
            files.append(file)
            names.append(name)
        return (files, names)

class join(object):
    def __init__(self, gui, parent=None, *,
    ca_file, grid, area,
    freq_file, evcs, evc_names=None, freq_thold,
    quads, quad_names=None):
        for name in ("gui, "
        "ca_file, grid, area, "
        "freq_file, evcs, freq_thold, "
        "quads").split(", "):
            setattr(self, name, vars()[name])
        
        if evc_names is None:
            self.evc_names = evcs
            self.evc_key = "EVC_DESC"
        else:
            self.evc_names = evc_names
            self.evc_key = "EVC"
        
        if quad_names is None:
            self.quad_names = quads
        else:
            self.quad_names = quad_names
        
        headings = self.headings()
        output = guis.List(headings)
        
        form = guis.Form(
            output,
            guis.Inline(
                guis.Button("Save as &HTML . . .", command=self.save),
                guis.Button("&Close", command=lambda: self.window.close()),
            ),
        )
        self.window = guis.Window(self.gui, parent, title="Plant list",
            contents=form)
        #~ self.window.bind("<Return>", self.save)
        
        self.entries = list()
        for entry in self:
            self.entries.append(entry)
            output.add(field or "" for field in entry)
        
        #~ buttons = Frame(self.window)
        #~ buttons.grid()
        #~ button = Button(buttons, text="Save as HTML . . .",
            #~ command=self.save, default="active")
        #~ button.grid(row=0, column=0)
        #~ button.grid(row=0, column=1)
    
    def headings(self):
        headings = ["name", "common", "ex", "area", "grid"]
        headings.extend(self.evc_names)
        headings.extend(self.quad_names)
        return headings
    
    def __iter__(self):
        # Read all likely plants from all sources
        plants = Plants()
        
        if self.ca_file is not None:
            if self.ca_file.endswith(".xls"):
                from excel import CplExcelReader as Reader
            else:
                from db import CaCsvReader as Reader
            with closing(Reader(self.ca_file)) as file:
                for plant in file:
                    if (plant.ex in tuple("*+") or
                    plant.group in ("f", "FERNS") or
                    plant.family in ("Orchidaceae", "Loranthaceae")):
                        continue
                    plants[plant.name].ca = plant
        
        if self.freq_file is not None:
            DIV_FERN = "2"
            DIV_MOSS = "5"
            FAM_MISTLETOE = "100"
            FAM_ORCHID = "124"
            
            max_freq = dict()
            
            if self.freq_file.endswith(".xls"):
                from excel import FreqExcelReader as Reader
            else:
                from db import FreqCsvReader as Reader
            with closing(Reader(self.freq_file)) as file:
                for plant in file:
                    evc = plant[self.evc_key]
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
        
        # For each species group in order, see if any plants match the
        # criteria. If so, output all plants in the species group in order.
        for species in sorted(plants.species.keys()):
            species = plants.species[species]
            
            for plant in species:
                if plant.ca is not None and any(
                a in self.area for a in plant.ca.area):
                    break
                
                for evc in self.evcs:
                    try:
                        evc_plant = plant.evcs[evc]
                    except LookupError:
                        continue
                    freq = evc_plant["Frequency"] / max_freq[evc]
                    if freq >= self.freq_thold:
                        thold_met = True
                        break
                else:
                    thold_met = False
                if thold_met:
                    break
                
                if any(quad in plant.quads for quad in self.quads):
                    break
            
            else:
                continue
            
            species.sort()
            for plant in species:
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
                for evc in self.evcs:
                    try:
                        evc_plant = plant.evcs[evc]
                    except LookupError:
                        rel.append("")
                    else:
                        freq = evc_plant["Frequency"] / max_freq[evc]
                        rel.append(format(freq, ".2f"))
                
                inquads = (quad in plant.quads for quad in self.quads)
                
                res = [plant.name, common, ex, area, grid] + rel
                res.extend("Y" if q else "" for q in inquads)
                yield res
    
    def write_html(self, entries, file):
        print("""\
<!doctype html>
<html>
<head>
  <meta charset=UTF-8>
  <title>Automatically generated plant list</title>
</head>
<body><table>
  <tr>""", file=file)
        print_tagged("th", self.headings(), file)
        print("""  </tr>""", file=file)
        
        for entry in entries:
            print("""  <tr>""", file=file)
            print_tagged("td", entry, file)
            print("""  </tr>""", file=file)
        
        print("""</table></body></html>""", file=file)
    
    def save(self):
        file = self.gui.file_browse("save", self.window,
            title="Save as HTML",
            types=(("HTML", ("html", "htm")),),
        )
        if not file:
            return
        with open(file, "w", encoding="UTF-8") as file:
            self.write_html(self.entries, file)

class Plants(dict):
    """Indexes plants by canonical name, and groups them by species"""
    
    def __init__(self):
        # Main list has keys like (("Dianella",), ("aff", "longifolia"))
        dict.__init__(self)
        self.species = dict()
    
    def __getitem__(self, name):
        key = plant_key(name)
        try:
            return dict.__getitem__(self, key)
        except LookupError:
            plant = Plant(name, key)
            self[key] = plant
            
            # Species key: first two names, ignoring all descriptors
            key = tuple(name[0] for name in key[:2])
            
            # If the last part of the key is a descriptor without a name,
            # truncate it from the key. Eg: (name) (spp agg) => (name)
            if not key[-1]:
                key = key[:-1]
            
            self.species.setdefault(key, list()).append(plant)
            
            return plant

@total_ordering
class Plant(object):
    def __init__(self, name, key):
        self.ca = None
        self.evcs = dict()
        self.quads = dict()
        self.name = name
        self.key = key
    
    def __eq__(self, other):
        return self.key == other.key
    
    def __lt__(self, other):
        return self.key < other.key

def print_tagged(tag, list, file):
    for text in list:
        text = saxutils.escape(text or "")
        print("<{tag}>{text}</{tag}>".format_map(locals()), file=file)

EVC_KEYS = ("EVC_DESC", "EVC")

class Freqs(object):
    def __init__(self, gui, evcs, thold):
        self.file = FileEntry(gui, FREQ_DEFAULT,
            title='Find "{FREQ_DEFAULT}"'.format_map(globals()),
            types=(("Spreadsheet", ("csv", "xls")),),
            command=self.update,
        )
        
        self.saved_evcs = evcs
        self.evc_list = guis.List(("EVC", "EVC_DESC"),
            selected=self.selected)
#        self.evc_list = ScrolledTree(form.master, tree=False, columns=(
#            Record(heading="EVC", width=(4, ScrolledTree.FIGURE)),
#            Record(heading="EVC_DESC", width=30, stretch=True),
#        ))
        
#        vcmd = ValidateCommand(form.master, self.validate_thold)
#        entry = Entry(form.master, textvariable=self.thold, validate="key",
#            validatecommand=vcmd)
        self.thold = guis.Entry(str(thold))
        
        self.win_section = guis.Section("EVC &frequencies",
            guis.Field("Source file", self.file.layout),
            guis.Field("Select &EVCs", self.evc_list),
            guis.Field("Frequency &threshold", self.thold),
        )
    
    def update(self):
        self.evc_list.clear()
        
        file = self.file.entry.get()
        if not file:
            return
        
        if file.endswith(".xls"):
            from excel import FreqExcelReader as Reader
        else:
            from db import FreqCsvReader as Reader
        with closing(Reader(file)) as file:
            evcs = set(tuple(row[key] for key in EVC_KEYS)
                for row in file)
        
        saved_evcs = self.saved_evcs
        for (name, number) in sorted(evcs):
            number = str(number)
            selected = name in saved_evcs or number in saved_evcs
            item = self.evc_list.add((number, name), selected=selected)
        self.saved_evcs = saved_evcs
        
        #~ if selection:
            #~ self.evc_list.tree.focus(selection[0])
            
            #~ # Treeview.see() straight after adding items does not seem to
            #~ # work without at least update_idletasks(), and the <<Treeview
            #~ # Select>> event does not seem to be handled until update() is
            #~ # called.
            #~ self.evc_list.update()
            
            #~ self.evc_list.tree.see(selection[-1])
            #~ self.evc_list.tree.see(selection[0])
    
    def selected(self):
        self.saved_evcs = list()
        for item in self.evc_list.selection():
            item = self.evc_list.get(item)
            self.saved_evcs.extend(item)
    
    def get_evcs(self):
        numbers = list()
        names = list()
        for item in self.evc_list.selection():
            (number, name) = self.evc_list.get(item)
            numbers.append(int(number))
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

class FileEntry(object):
    def __init__(self, gui, default=None, *,
    types, title=None, command=None, delete=True):
        self.gui = gui
        self.types = types
        self.title = title
        self.command = command
        
        self.entry = guis.Entry(default)
        #~ Button(field, text="Delete", command=partial(file.set, "")).pack(
            #~ side=tkinter.LEFT)
        if delete:
            delete = (guis.Button("Delete"),)
        else:
            delete = ()
        self.layout = guis.Inline(
            self.entry,
            guis.Button("Browse", command=self.browse),
        *delete)
    
    def set_parent(self, window):
        self.parent = window
    
    def browse(self):
        file = self.gui.file_browse("open", self.parent,
            title=self.title,
            types=self.types,
            file=self.entry.get(),
        )
        if file is None:
            return
        
        self.entry.set(file)
        if self.command:
            self.command()

if __name__ == "__main__":
    main()

#Grid alias incl cmd line
#How to handle origin, exotic, AROTS, VROTS merging or multiple columns
