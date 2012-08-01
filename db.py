import csv
from collections import namedtuple
from lib import Record

def CaPlantReader(file):
    with open(file, newline="") as file:
        for plant in csv.reader(file):
            if plant[0].startswith("\x1A"):
                break
            yield tuple_record(plant, """
                name, ex, common, family, fam_com, group, area, grid, note,
            """, empty="""ex, area, note""")

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
