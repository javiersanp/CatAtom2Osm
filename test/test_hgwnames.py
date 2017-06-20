# -*- coding: utf-8 -*-
import unittest
import logging
import gettext
import os
from tempfile import gettempdir

from qgis.core import *

import setup
import hgwnames
from unittest_main import QgsSingleton

logging.disable(logging.WARNING)
if setup.platform.startswith('win'):
    if os.getenv('LANG') is None:
        os.environ['LANG'] = setup.language
gettext.install(setup.app_name.lower(), localedir=setup.localedir)

#QgsApplication.setPrefixPath(setup.qgs_prefix_path, True)
qgs = QgsSingleton() #QgsApplication([], False)


"""def setUpModule():
    qgs.initQgis()

def tearDownModule():
    qgs.exitQgis()
"""

class TestHgwnames(unittest.TestCase):

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
            "XX FooBar": "XX Foobar"
        }
        for (inp, out) in names.items():
            self.assertEquals(hgwnames.parse(inp), out)

    def test_get_names(self):
        layer = QgsVectorLayer('test/address.gml|layername=thoroughfarename', 'tn', 'ogr')
        self.assertTrue(layer.isValid(), "Init QGIS")
        translations = {}
        for feat in layer.getFeatures():
            translations[feat['text']] = hgwnames.parse(feat['text'])
        a_path = gettempdir()
        highway_types_path = os.path.join(setup.app_path, 'highway_types.csv')
        highway_names_path = os.path.join(a_path, 'highway_names.csv')
        if os.path.exists(highway_types_path):
            os.rename(highway_types_path, highway_types_path + '.bak')
        self.assertFalse(os.path.exists(highway_names_path))
        (names, is_new) = hgwnames.get_translations(layer, a_path)
        self.assertTrue(os.path.exists(highway_names_path))
        self.assertTrue(os.path.exists(highway_types_path))
        self.assertEquals(translations, names)
        self.assertTrue(is_new)
        (names, is_new) = hgwnames.get_translations(layer, a_path)
        self.assertEquals(translations, names)
        self.assertFalse(is_new)
        os.remove(highway_types_path)
        os.remove(highway_names_path)
        if os.path.exists(highway_types_path + '.bak'):
            os.rename(highway_types_path + '.bak', highway_types_path)
