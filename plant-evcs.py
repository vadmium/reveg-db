#! /usr/bin/env python3

from excel import FreqExcelReader
from contextlib import closing
from sys import stderr
from time import monotonic

def main(freqs, selection=None):
    deadline = monotonic() + 1
    midline = False
    
    selset = set()
    if selection:
        with open(selection, "rt") as reader:
            for plant in reader:
                selset.add(plant.strip())
    
    evcs = list()  # [(evc, desc, {name: freq for each plant}) for each EVC]
    max_freqs = list()  # [max(freq) for each EVC]
    with closing(FreqExcelReader(freqs)) as freqs:
        total = format(len(freqs))
        last_evc = None
        for [i, plant] in enumerate(freqs):
            now = monotonic()
            if now >= deadline:
                if midline:
                    print(end="\r", file=stderr)
                msg = "Record {:{}}/{}".format(i + 1, len(total), total)
                print(end=msg, file=stderr)
                midline = True
                deadline = now + 0.1
            
            if plant["EVC"] != last_evc:
                last_evc = plant["EVC"]
                last_desc = plant["EVC_DESC"]
                plant_freqs = dict()
                evcs.append((last_evc, last_desc, plant_freqs))
                max_freqs.append(plant["Frequency"])
            else:
                max_freqs[-1] = max(max_freqs[-1], plant["Frequency"])
                if plant["EVC_DESC"] != last_desc:
                    msg = "EVC {} EVC_DESC inconsistent between {!r} and " \
                        "{!r}".format(last_evc, last_desc, plant["EVC_DESC"])
                    print(msg, file=stderr)
                    last_desc = plant["EVC_DESC"]
            name = plant["NAME"]
            if selection:
                if name not in selset:
                    continue
            else:
                selset.add(name)
            if name in plant_freqs:
                msg = "Duplicate record for {NAME} in {EVC}"
                print(msg.format_map(plant), file=stderr)
            plant_freqs[name] = plant_freqs.get(name, 0) + plant["Frequency"]
    
    if midline:
        print(end="\x1B[1K\r", file=stderr)
    
    heading = "{:>4.4} {:67.67}{:>5.5}"
    print(heading.format("EVC", "EVC_DESC", "max(Frequency)"))
    for [[evc, desc, _], max_freq] in zip(evcs, max_freqs):
        print("{:4} {:67.67}{:5}".format(evc, desc, max_freq))
    print(end="NAME"[:32].ljust(32))
    for [evc, _, _] in evcs:
        print(end=format(evc, "6"))
    print()
    for plant in sorted(selset):
        print(end=plant[:32].ljust(32))
        found = False
        for [[_, _, freqs], max_freq] in zip(evcs, max_freqs):
            freq = freqs.get(plant)
            if freq is None:
                print(end=" " * 6)
                continue
            found = True
            print(end=format(freq / max_freq, "6.3f"))
        print()
        if not found:
            print("No record of {}".format(plant), file=stderr)

if __name__ == "__main__":
    from clifunc import run
    run(main)
