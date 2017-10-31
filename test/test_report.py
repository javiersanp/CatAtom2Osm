import unittest
import os

os.environ['LANGUAGE'] = 'C'
import setup
import report


class TestReport(unittest.TestCase):

    def test_to_string0(self):
        r = report.Report()
        output = r.to_string()
        expected = ""
        self.assertEquals(output, expected)

    def test_to_string1(self):
        r = report.instance
        r.mun_name = 'Foobar'
        self.assertEquals(r.values['mun_name'], r.mun_name)
        r.code = 99999
        r.inp_address = 1000
        output = r.to_string()
        expected = u"Municipality: Foobar" + setup.eol + setup.eol \
            + "=Input data=" + setup.eol \
            + "Addresses: 1000" + setup.eol
        self.assertEquals(output, expected)
