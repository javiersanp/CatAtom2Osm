# -*- coding: utf-8 -*-
"""
CSV related help functions
"""

import csv
import codecs
from setup import eol, encoding, delimiter


def dict2csv(csv_path, a_dict):
    """Writes a dictionary to a csv file"""
    with codecs.open(csv_path, 'w', encoding) as csv_file:
        for (k, v) in a_dict.items():
            csv_file.write(u'%s%s%s%s' % (k, delimiter, v, eol))

def csv2dict(csv_path, a_dict, encoding=encoding):
    """Read a dictionary from a csv file"""
    with open(csv_path) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=delimiter)
        for row in csv_reader:
            a_dict[row[0].decode(encoding)] = row[1].decode(encoding)
    return a_dict

