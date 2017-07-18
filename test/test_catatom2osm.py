# -*- coding: utf-8 -*-
import os
import mock
from qgis.core import *

import main
import unittest
import setup
import hgwnames
from catatom2osm import *
from layer import AddressLayer


class TestCatAtom2Osm(unittest.TestCase):

    def setUp(self):
        self.options = dict(tasks=False, zoning=False, building=False, 
            address=False, parcel=False, log_level="DEBUG")

    def test_get_translations(self):
        app = CatAtom2Osm('09999', self.options)
        address_gml = QgsVectorLayer('test/address.gml|layername=address', 'tn', 'ogr')
        layer = AddressLayer()
        self.assertTrue(layer.isValid(), "Init QGIS"    )
        layer.append(address_gml)
        thoroughfarename = QgsVectorLayer('test/address.gml|layername=thoroughfarename', 'tn', 'ogr')
        layer.join_field(thoroughfarename, 'TN_id', 'gml_id', ['text'], 'TN_')
        translations = {}
        for feat in layer.getFeatures():
            if feat['designator'] == 'S-N':
                translations[feat['TN_text']] = ''
            else:
                translations[feat['TN_text']] = hgwnames.parse(feat['TN_text'])
        highway_types_path = os.path.join(setup.app_path, 'highway_types.csv')
        highway_names_path = os.path.join('09999', 'highway_names.csv')
        if os.path.exists(highway_types_path):
            os.remove(highway_types_path)
        if os.path.exists(highway_names_path):
            os.remove(highway_names_path)
        (names, is_new) = app.get_translations(layer, None)
        self.assertTrue(os.path.exists(highway_names_path))
        self.assertTrue(os.path.exists(highway_types_path))
        for n in translations:
             self.assertEquals(names[n], translations[n])
        self.assertTrue(is_new)
        (names, is_new) = app.get_translations(layer, None)
        self.assertEquals(translations, names)
        self.assertFalse(is_new)
        os.remove(highway_types_path)
        os.remove(highway_names_path)
        os.rmdir('09999')

