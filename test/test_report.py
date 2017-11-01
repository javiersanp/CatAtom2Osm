# -*- coding: utf-8 -*-
import unittest
import os
from datetime import datetime

os.environ['LANGUAGE'] = 'C'
import setup
import report


class TestReport(unittest.TestCase):

    def test_setattr(self):
        r = report.Report()
        r.mun_name = 'foobar'
        self.assertEquals(r.values['mun_name'], 'foobar')

    def test_getattr(self):
        r = report.Report()
        r.values['mun_name'] = 'foobar'
        self.assertEquals(r.mun_name, 'foobar')
        
    def test_to_string0(self):
        r = report.Report()
        output = r.to_string()
        expected = "Date: " + datetime.now().strftime('%x') + setup.eol
        self.assertEquals(output, expected)

    def test_to_string1(self):
        r = report.Report()
        r.mun_name = 'Foobar'
        r.code = 99999
        r.inp_address = 1000
        r.warnings = []
        output = r.to_string()
        expected = u"Municipality: Foobar" + setup.eol \
            + "Date: " + datetime.now().strftime('%x') + setup.eol + setup.eol \
            + "=Input data=" + setup.eol \
            + "Addresses: 1000" + setup.eol + setup.eol \
            + "=Output data=" + setup.eol
        self.assertEquals(output, expected)

    def test_to_string2(self):
        r = report.Report()
        r.warnings = ['w1', 'w2']        
        output = r.to_string()
        expected = u"Date: " + datetime.now().strftime('%x') + setup.eol \
            + setup.eol + "=Output data=" + setup.eol \
            + "Warnings:" + setup.eol \
            + "w1" + setup.eol + "w2" + setup.eol
        self.assertEquals(output, expected)

    def test_to_file(self):
        r = report.Report()
        r.mun_name = u"áéíóúñ"
        output = r.to_string()
        fn = 'test_report.txt'
        r.to_file(fn, 'iso-8859-15')
        with open(fn, 'r') as fo:
            text = fo.read().decode('iso-8859-15')
        self.assertEquals(output, text)
        if os.path.exists(fn):
            os.remove(fn)
