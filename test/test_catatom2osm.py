# -*- coding: utf-8 -*-
import os
import mock
from qgis.core import *

import main
import unittest
import setup
import hgwnames
from catatom2osm import *


class TestCatAtom2Osm(unittest.TestCase):

    def setUp(self):
        self.options = dict(tasks=False, zoning=False, building=False, 
            address=False, parcel=False, log_level="DEBUG")

    def test_get_translations(self):
        app = CatAtom2Osm('09999', self.options)
        address = mock.MagicMock()
        address.get_highway_names = mock.MagicMock(return_value = {})
        highway_types_path = os.path.join(setup.app_path, 'highway_types.csv')
        highway_names_path = os.path.join('09999', 'highway_names.csv')
        if os.path.exists(highway_types_path):
            os.remove(highway_types_path)
        if os.path.exists(highway_names_path):
            os.remove(highway_names_path)
        (names, is_new) = app.get_translations(address, None)
        self.assertTrue(os.path.exists(highway_names_path))
        self.assertTrue(os.path.exists(highway_types_path))
        self.assertTrue(is_new)
        (names, is_new) = app.get_translations(address, None)
        self.assertFalse(is_new)
        os.remove(highway_types_path)
        os.remove(highway_names_path)
        os.rmdir('09999')

