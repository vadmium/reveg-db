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
    """Punctuation should be ignored when comparing names"""
    
    gui = TestGui()
    with TemporaryDirectory(prefix="reveg") as dir:
        cpl = path.join(dir, "cpl.csv")
        with open(cpl, "w") as file:
            file = csv.writer(file)
            file.writerow((
                "A bee var. cee", "", "Dummy common", "Family", None, "D",
                "A", None, "000",
            ))
        
        freqs = path.join(dir, "freqs.csv")
        with open(freqs, "w") as file:
            file = csv.writer(file)
            file.writerows((
                ("EVC", "BioregionNo", "Frequency", "NAME", "ORIGIN", "FAMILYNO", "DIVISION", "SPECNUM"),
                (10, 0, 100, "A bee v cee", "", 0, 4, 0),
            ))
        
        join = reveg.join(gui,
            ca_file=cpl, grid=None, area="A",
            freq_file=freqs, evcs=(10,), evc_names=("EVC",), freq_thold=0.5,
            quads=(), quad_names=(),
        )
        join = tuple(join)
    
    self.assertEqual(join, (
        ["A bee var. cee", "Dummy common", "", "A", None, "1.00"],
    ))

class TestGui(object):
    def id(self, *pos, **kw):
        return self
    
    def __getattr__(self, name):
        return self.id

if __name__ == "__main__":
    import unittest
    unittest.main()
