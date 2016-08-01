from shorthand import SimpleNamespace
from xlrd import open_workbook
from xlrd import (XL_CELL_EMPTY, XL_CELL_BLANK)
from numbers import Number
from contextlib import closing
from db import FREQS_EMPTIES, freq_ints
from sys import stderr
from collections import Sequence

def CplExcelReader(file):
    HEADING_FIELDS = {
        "r": "vrots",
        "w": "weed",
        "Grd": "grid",
        "E": "ex",
        "Ex": "ex",
        "Name": "name",
        "Common Name": "common",
        "Area": "area",
        "Notes": "note",
    }
    
    with closing(excel_sheets(file)) as file:
        for sheet in file:
            extra = dict()
            expect_headings = False
            for row in range(sheet.nrows):
                types = sheet.row_types(row)
                group_col = None
                for (col, type) in enumerate(types):
                    if type in EXCEL_BLANKS:
                        continue
                    if group_col is None:
                        group_col = col
                    else:
                        break
                else:
                    if group_col is not None:
                        group = sheet.cell_value(row, group_col)
                        extra.update(group=group.strip())
                        expect_headings = True
                    continue
                if expect_headings:
                    fields = dict()
                    for (col, heading) in enumerate(sheet.row_values(row)):
                        try:
                            field = HEADING_FIELDS[heading]
                        except LookupError:
                            continue
                        fields[field] = col
                    expect_headings = False
                    continue
                
                fam_fields = ("name", "common")
                for (col, type) in enumerate(types):
                    if col in (fields[field] for field in fam_fields):
                        continue
                    if type not in EXCEL_BLANKS:
                        break
                else:
                    extra.update(
                        family=sheet.cell_value(row, fields["name"]),
                        fam_com=sheet.cell_value(row, fields["common"]),
                    )
                    continue
                
                plant = SimpleNamespace(**extra)
                for (name, col) in fields.items():
                    value = excel_value(sheet, row, col)
                    if isinstance(value, Number):
                        # Seen area=0 recorded as a number
                        value = format(value, "g")
                    elif value is not None:
                        value = value.strip()
                    setattr(plant, name, value)
                convert_empty(plant.__dict__,
                    ("vrots", "weed", "ex", "area", "note"))
                yield plant

class FreqExcelReader(Sequence):
    def __init__(self, file):
        self._book = open_workbook(file,
            on_demand=True, ragged_rows=True, logfile=stderr)
        with self._book:
            self._sheet = self._book.sheet_by_index(0)
        try:
            self._fields = self._sheet.row_values(0)
        except:
            self.close()
            raise
    
    def close(self):
        self._book.unload_sheet(0)
    
    def __len__(self):
        return self._sheet.nrows - 1
    
    def __getitem__(self, i):
        row = range(1, self._sheet.nrows)[i]
        plant = dict()
        for [col, field] in enumerate(self._fields):
            plant[field] = excel_value(self._sheet, row, col)
        convert_empty(plant, FREQS_EMPTIES)
        freq_ints(plant)
        return plant

def excel_sheets(*args, **kw):
    book = open_workbook(*args,
        on_demand=True, ragged_rows=True, logfile=stderr, **kw)
    with book:
        for i in range(book.nsheets):
            try:
                yield book.sheet_by_index(i)
            finally:
                book.unload_sheet(i)

def excel_value(sheet, row, col):
    try:
        cell = sheet.cell(row, col)
    except LookupError:
        return None
    if cell.ctype in EXCEL_BLANKS:
        return None
    return cell.value

EXCEL_BLANKS = (XL_CELL_EMPTY, XL_CELL_BLANK)

def convert_empty(record, fields):
    for name in fields:
        if record[name] is None:
            record[name] = ""
