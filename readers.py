import csv
from collections import namedtuple
from lib import Record

CaPlant = namedtuple("CaPlant",
    "name, ex, common, family, fam_com, group, area, grid, note")
def CaPlantReader(file):
    with open(file, newline="") as file:
        for plant in csv.reader(file):
            if plant[0].startswith("\x1A"):
                break
            yield CaPlant._make(plant)

def FreqReader(file):
    with open(file, newline="") as file:
        for plant in csv.DictReader(file):
            plant["Frequency"] = int(plant["Frequency"])
            yield plant

def QuadratReader(file):
    with open(file, newline="") as file:
        file = csv.reader(file)
        next(file)
        extra = Record()
        for row in file:
            if row == ("Scientific Name", "Common Name"):
                continue
            if row[1] == "t1":
                (extra.group, _, *_) = row
                family = None
                continue
            elif row[1] == "t2":
                (extra.family, _, *_) = row
                continue
            
            record = "arots, vrots, origin, name, common".split(", ")
            record = Record(zip(record, row))
            record.__dict__.update(vars(extra))
            yield record
