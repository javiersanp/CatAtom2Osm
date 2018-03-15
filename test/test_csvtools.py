# -*- coding: utf-8 -*-
import unittest
from tempfile import mkstemp

import csv
import codecs
import os
os.environ['LANGUAGE'] = 'C'

from csvtools import csv2dict, dict2csv
from setup import eol, encoding, delimiter


class TestCsvTools(unittest.TestCase):

    def test_csv2dict(self):
        _, tmp_path = mkstemp()
        with codecs.open(tmp_path, 'w', encoding) as csv_file:
            csv_file.write(u'á%sx%sé%sy%s' % (delimiter, eol, delimiter, eol))
        a_dict = csv2dict(tmp_path, {})
        self.assertEquals(a_dict, {u'á':u'x', u'é':u'y'})

    def test_dict2csv(self):
        _, tmp_path = mkstemp()
        dict2csv(tmp_path, {u'á':'x', u'é':'y'})
        with codecs.open(tmp_path, 'r', encoding) as csv_file:
            text = csv_file.read()
        self.assertEquals(text, u'á%sx%sé%sy%s' % (delimiter, eol, delimiter, eol))

    def test_dict2csv_sort(self):
        _, tmp_path = mkstemp()
        dict2csv(tmp_path, {'b':'1', 'a':'3', 'c': '2'}, sort=1)
        with codecs.open(tmp_path, 'r', encoding) as csv_file:
            text = csv_file.read()
        self.assertEquals(text, u'b%s1%sc%s2%sa%s3%s' % (delimiter, eol, 
            delimiter, eol, delimiter, eol))


