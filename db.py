import csv
from collections import namedtuple
from lib import Record
from xlrd import open_workbook
from xlrd import (XL_CELL_EMPTY, XL_CELL_BLANK)
from numbers import Number
from contextlib import closing

def CaCsvReader(file):
    with open(file, newline="") as file:
        for plant in csv.reader(file):
            if plant[0].startswith("\x1A"):
                break
            yield tuple_record(plant, """
                name, ex, common, family, fam_com, group, area, grid, note,
            """, empty="""ex, area, note""")

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
                    
                    fam_fields = parse_fields("""name, common""")
                    for (col, type) in enumerate(types):
                        if col in (fields[field] for field in fam_fields):
                            continue
                        if type not in EXCEL_BLANKS:
                            break
                    else:
                        family = Record()
                        for name in fam_fields:
                            value = sheet.cell_value(row, fields[name])
                            setattr(family, name, value.strip())
                        extra.update(family=family)
                        continue
                    
                    plant = Record(extra)
                    for (name, col) in fields.items():
                        value = excel_value(sheet, row, col)
                        if isinstance(value, Number):
                            # Seen area=0 recorded as a number
                            value = format(value, "g")
                        elif value is not None:
                            value = value.strip()
                        setattr(plant, name, value)
                    convert_empty(plant.__dict__,
                        """vrots, weed, ex, area, note""")
                    yield plant

def FreqCsvReader(file):
    with open(file, newline="") as file:
        for plant in csv.DictReader(file):
            convert_none_skip(plant, FREQS_EMPTIES)
            freq_ints(plant)
            yield plant

def FreqExcelReader(file):
    with closing(excel_sheets(file)) as file:
        for sheet in file:
            fields = sheet.row_values(0)
            for row in range(1, sheet.nrows):
                plant = dict()
                for (col, field) in enumerate(fields):
                    plant[fields[col]] = excel_value(sheet, row, col)
                convert_empty(plant, FREQS_EMPTIES)
                freq_ints(plant)
                yield plant

FREQS_EMPTIES = """ORIGIN, AROTS, VROTS"""

def freq_ints(record):
    for field in parse_fields("""EVC, Frequency, SPECNUM"""):
        record[field] = int(record[field])
    record["BioregionNo"] = float(record["BioregionNo"])

def QuadratReader(file):
    with open(file, newline="") as file:
        file = csv.reader(file)
        next(file)
        extra = Record()
        for row in file:
            if tuple(row) == ("Scientific Name", "Common Name"):
                continue
            if row[1] == "t1":
                (extra.group, _, *_) = row
                family = None
                continue
            elif row[1] == "t2":
                (extra.family, _, *_) = row
                continue
            
            empty = """arots, vrots, origin"""
            record = tuple_record(row,
                """arots, vrots, origin, name, common""", empty=empty)
            record.__dict__.update(vars(extra))
            if not vars(extra):
                empty = parse_fields(empty)
                convert_none(record.__dict__, empty)
                
                # Convert a single space to empty string
                for name in empty:
                    if getattr(record, name) == " ":
                        setattr(record, name, "")
            
            yield record

def excel_sheets(*args, **kw):
    with open_workbook(*args, on_demand=True, ragged_rows=True, **kw) as (
    book):
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
    for name in parse_fields(fields):
        if record[name] is None:
            record[name] = ""

def tuple_record(record, fields, empty):
    record = Record(zip(parse_fields(fields), record))
    convert_none_skip(record.__dict__, empty)
    return record

def convert_none_skip(record, skip):
    # Python 3.2.3 seems to have trouble with dict_keys() - tuple(). Bug?
    # Looks like it treats each tuple member as a separate set to subtract.
    fields = record.keys() - iter(parse_fields(skip))
    convert_none(record, fields)

def convert_none(record, fields):
    for field in fields:
        if not record[field]:
            record[field] = None

def parse_fields(str):
    return str.replace(",", " ").split()
