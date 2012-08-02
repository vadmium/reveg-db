import csv
from collections import namedtuple
from lib import Record
from xlrd import open_workbook
from xlrd import (XL_CELL_EMPTY, XL_CELL_BLANK)
from numbers import Number

def CaCsvReader(file):
    with open(file, newline="") as file:
        for plant in csv.reader(file):
            if plant[0].startswith("\x1A"):
                break
            yield tuple_record(plant, """
                name, ex, common, family, fam_com, group, area, grid, note,
            """, empty="""ex, area, note""")

def CplExcelReader(file):
    BLANK_TYPES = (XL_CELL_EMPTY, XL_CELL_BLANK)
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
    
    with open_workbook(file, on_demand=True, ragged_rows=True) as book:
        for i in range(book.nsheets):
            sheet = book.sheet_by_index(i)
            try:
                extra = dict()
                expect_headings = False
                for row in range(sheet.nrows):
                    types = sheet.row_types(row)
                    group_col = None
                    for (col, type) in enumerate(types):
                        if type in BLANK_TYPES:
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
                        headings = sheet.row_values(row)
                        for (col, heading) in enumerate(headings):
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
                        if type not in BLANK_TYPES:
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
                        if col >= len(types) or types[col] in BLANK_TYPES:
                            setattr(plant, name, None)
                        else:
                            value = sheet.cell_value(row, col)
                            if isinstance(value, Number):
                                # Seen area=0 recorded as a number
                                value = format(value, "g")
                            else:
                                value = value.strip()
                            setattr(plant, name, value)
                    empty = parse_fields("""vrots, weed, ex, area, note""")
                    for name in empty:
                        if getattr(plant, name) is None:
                            setattr(plant, name, "")
                    yield plant
            
            finally:
                book.unload_sheet(i)

def FreqReader(file):
    with open(file, newline="") as file:
        for plant in csv.DictReader(file):
            default_none_skip(plant, """ORIGIN, AROTS, VROTS""")
            plant["Frequency"] = int(plant["Frequency"])
            yield plant

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
                default_none(record.__dict__, empty)
                
                # Convert a single space to empty string
                for name in empty:
                    if getattr(record, name) == " ":
                        setattr(record, name, "")
            
            yield record

def tuple_record(record, fields, empty):
    record = Record(zip(parse_fields(fields), record))
    default_none_skip(record.__dict__, empty)
    return record

def default_none_skip(record, skip):
    # Python 3.2.3 seems to have trouble with dict_keys() - tuple(). Bug?
    # Looks like it treats each tuple member as a separate set to subtract.
    fields = record.keys() - iter(parse_fields(skip))
    default_none(record, fields)

def default_none(record, fields):
    for field in fields:
        if not record[field]:
            record[field] = None

def parse_fields(str):
    return str.replace(",", " ").split()
