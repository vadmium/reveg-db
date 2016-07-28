import csv
from shorthand import SimpleNamespace

abbr = dict(
    aff="aff", affin="aff",
    agg="agg",
    f="f", forma="f",
    sect="sect",
    sensu="sensu",
    sl="sl",
    spp="spp", sp="spp",
    ss="ss",
    ssp="ssp", subsp="ssp",
    var="var", v="var", vars="var",
    x="x",
)

def CaCsvReader(file):
    with open(file, newline="") as file:
        for plant in csv.reader(file):
            if plant[0].startswith("\x1A"):
                break
            yield tuple_record(plant, (
                "name", "ex", "common", "family", "fam_com", "group", "area", "grid", "note",
            ), empty=("ex", "area", "note"))

def FreqCsvReader(file):
    with open(file, newline="") as file:
        for plant in csv.DictReader(file):
            convert_none_skip(plant, FREQS_EMPTIES)
            freq_ints(plant)
            yield plant

FREQS_EMPTIES = ("ORIGIN", "AROTS", "VROTS")

def freq_ints(record):
    for field in ("EVC", "Frequency", "SPECNUM"):
        record[field] = int(record[field])
    record["BioregionNo"] = float(record["BioregionNo"])

def QuadratReader(file):
    with open(file, newline="") as file:
        file = csv.reader(file)
        next(file)
        extra = SimpleNamespace()
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
            
            empty = ("arots", "vrots", "origin")
            record = tuple_record(row,
                ("arots", "vrots", "origin", "name", "common"), empty=empty)
            record.__dict__.update(vars(extra))
            if not vars(extra):
                convert_none(record.__dict__, empty)
                
                # Convert a single space to empty string
                for name in empty:
                    if getattr(record, name) == " ":
                        setattr(record, name, "")
            
            yield record

def tuple_record(values, fields, empty):
    record = SimpleNamespace()
    record.__dict__.update(zip(fields, values))
    convert_none_skip(record.__dict__, empty)
    return record

def convert_none_skip(record, skip):
    # Python 3.2.3 seems to have trouble with dict_keys() - tuple(). Bug?
    # Looks like it treats each tuple member as a separate set to subtract.
    fields = record.keys() - iter(skip)
    convert_none(record, fields)

def convert_none(record, fields):
    for field in fields:
        if not record[field]:
            record[field] = None

def plant_key(name):
    words = name.translate(NameSimplifier()).split()
    key = list()
    
    i = 0
    while i < len(words):
        desc = i
        while i < len(words):
            word = words[i]
            try:
                words[i] = abbr[word]
            except LookupError:
                break
            i += 1
        desc = tuple(words[desc:i])
        
        # If the element is of the form (desc desc name), put the name
        # part first in the key so that it has higher sorting priority
        try:
            element = (words[i],) + desc
            i += 1
        except IndexError:
            element = ("",) + desc
        
        key.append(element)
    return tuple(key)

class NameSimplifier(object):
    def __getitem__(self, cp):
        cp = chr(cp)
        if cp.isalnum():
            return cp.lower()
        if cp.isspace():
            return 0x20
        return None
