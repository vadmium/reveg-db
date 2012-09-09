#! /usr/bin/env python3

import sys
from unittest import (TestCase, TestSuite)
from misc import deco_factory
import reveg
from tempfile import TemporaryDirectory
from os import path
import csv

@deco_factory
def suite_add(suite, Test):
    suite.addTest(Test())
    return Test

@deco_factory
def testfunc(func, base=TestCase):
    return type(func.__name__, (base,), dict(runTest=func))

def load_tests(loader, default, pattern):
    return suite
suite = TestSuite()

@suite_add(suite)
@testfunc()
def punct(self):
    """Merge data with varying punctuation and abbreviations"""
    
    join = run_join(
        cpl=(("Acacia lanigera var. whanii", "A"),),
        freqs=(("Acacia lanigera v whanii", 100),),
    )
    self.assertEqual(join, (
        ["Acacia lanigera var. whanii", "Dummy common", "", "A", None,
            "1.00"],
    ))

@suite_add(suite)
@testfunc()
def species(self):
    """Include all entries for matching species"""
    
    join = run_join(
        cpl=(
            ("Danthonia", "A"),
            ("Crassula decumbens var incumbents", ""),
        ),
        freqs=(
            ("Danthonia s.l. spp.", 20),
            ("Crassula decumbens var. decumbens", 100),
        ),
    )
    self.assertEqual(join, (
        ["Crassula decumbens var. decumbens", "", "", "", "", "1.00"],
        ["Crassula decumbens var incumbents", "Dummy common", "", "", None, ""],
        ["Danthonia", "Dummy common", "", "A", None, ""],
        ["Danthonia s.l. spp.", "", "", "", "", "0.20"],
    ))

def run_join(cpl=(), freqs=()):
    with TemporaryDirectory(prefix="reveg") as dir:
        cplfile = path.join(dir, "cpl.csv")
        with open(cplfile, "w") as file:
            file = csv.writer(file)
            for (name, areas) in cpl:
                file.writerow((
                    name, "", "Dummy common", "Family", None, "D",
                    areas, None, "000",
                ))
        
        freqfile = path.join(dir, "freqs.csv")
        with open(freqfile, "w") as file:
            file = csv.writer(file)
            file.writerow((
                "EVC", "BioregionNo", "Frequency", "NAME", "ORIGIN",
                    "FAMILYNO", "DIVISION", "SPECNUM",
            ))
            for row in freqs:
                (name, freq, *row) = row
                if row:
                    (origin,) = row
                else:
                    origin = ""
                file.writerow((10, 0, freq, name, origin, 0, 4, 0))
        
        join = reveg.join(TestGui(),
            ca_file=cplfile, grid=None, area="A",
            freq_file=freqfile, evcs=(10,), evc_names=("EVC",), freq_thold=0.3,
            quads=(), quad_names=(),
        )
        return tuple(join)

class TestGui(object):
    def id(self, *pos, **kw):
        return self
    
    def __getattr__(self, name):
        return self.id

if __name__ == "__main__":
    import unittest
    unittest.main()
