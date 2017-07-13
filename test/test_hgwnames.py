# -*- coding: utf-8 -*-
import unittest
import mock
import logging
import gettext
import os
from tempfile import gettempdir

from qgis.core import *

import setup
import hgwnames
from layer import AddressLayer
from unittest_main import QgsSingleton

logging.disable(logging.WARNING)

qgs = QgsSingleton() #QgsApplication([], False)


class TestHgwnames(unittest.TestCase):

    def setUp(self):
        self.temp_fuzz = hgwnames.fuzz
        
    def test_normalize(self):
        self.assertEquals(hgwnames.normalize('  ABCD  '), 'abcd')

    def test_fuzzy_match(self):
        dataset = ['Foobar', 'Foo bar', 'Footaz']
        self.assertEquals(hgwnames.match(dataset, 'FOOB', lambda x:x), 'Foobar')

    @mock.patch('hgwnames.fuzz', None)
    def test_match(self):
        dataset = ['Foobar', 'Foo bar', 'Footaz']
        self.assertEquals(hgwnames.match(dataset, 'FOOBAR', lambda x:x), 'Foobar')
        self.assertEquals(hgwnames.match(dataset, 'FOO', lambda x:x), None)

    def test_parse(self):
        names = {
            "   CL  FOO BAR  TAZ  ": "Calle Foo Bar Taz",
            u"AV DE ESPAÑA": u"Avenida de España",
            "CJ GATA (DE LA)": u"Calleja/Callejón Gata (de la)",
            "CR CUMBRE,DE LA": "Carretera/Carrera Cumbre, de la",
            "CL HILARIO (ERAS LAS)": "Calle Hilario (Eras las)",
            "CL BASTIO D'EN SANOGUERA": "Calle Bastio d'en Sanoguera",
            "CL BANC DE L'OLI": "Calle Banc de l'Oli",
            "DS ARANJASSA,S'": "Diseminados Aranjassa, s'",
            u"CL AIGUA DOLÇA (L')": u"Calle Aigua Dolça (l')",
            u"CL RUL·LAN": u"Calle Rul·lan",
            "CL FONTE'L PILO": "Calle Fonte'l Pilo",
            "CL TRENET D'ALCOI": "Calle Trenet d'Alcoi",
            "CL SANT MARCEL.LI": u"Calle Sant Marcel·li",
            "CL O'DONNELL": "Calle O'Donnell",
            "XX FooBar": "XX Foobar"
        }
        for (inp, out) in names.items():
            self.assertEquals(hgwnames.parse(inp), out)

    def test_get_names(self):
        address_gml = QgsVectorLayer('test/address.gml|layername=address', 'tn', 'ogr')
        layer = AddressLayer()
        self.assertTrue(layer.isValid(), "Init QGIS")
        layer.append(address_gml)
        thoroughfarename = QgsVectorLayer('test/address.gml|layername=thoroughfarename', 'tn', 'ogr')
        layer.join_field(thoroughfarename, 'TN_id', 'gml_id', ['text'], 'TN_')
        translations = {}
        for feat in layer.getFeatures():
            if feat['designator'] == 'S-N':
                translations[feat['TN_text']] = ''
            else:
                translations[feat['TN_text']] = hgwnames.parse(feat['TN_text'])
        a_path = gettempdir()
        highway_types_path = os.path.join(setup.app_path, 'highway_types.csv')
        highway_names_path = os.path.join(a_path, 'highway_names.csv')
        if os.path.exists(highway_types_path):
            os.rename(highway_types_path, highway_types_path + '.bak')
        (names, is_new) = hgwnames.get_translations(layer, a_path, 'TN_text', 'designator')
        self.assertTrue(os.path.exists(highway_names_path))
        self.assertTrue(os.path.exists(highway_types_path))
        self.assertEquals(translations, names)
        self.assertTrue(is_new)
        (names, is_new) = hgwnames.get_translations(layer, a_path, 'TN_text', 'designator')
        self.assertEquals(translations, names)
        self.assertFalse(is_new)
        os.remove(highway_types_path)
        os.remove(highway_names_path)
        if os.path.exists(highway_types_path + '.bak'):
            os.rename(highway_types_path + '.bak', highway_types_path)

    def tearDown(self):
        hgwnames.fuzz = self.temp_fuzz
