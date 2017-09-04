# -*- coding: utf-8 -*-
import unittest
import mock
import os
os.environ['LANGUAGE'] = 'C'

import hgwnames
import hgwnames as nonfuzzy_hgwnames

class TestHgwnames(unittest.TestCase):

    def setUp(self):
        self.temp_fuzz = hgwnames.fuzz
        self.ds = [
            {'id':1, 'n':'Foobar'}, 
            {'id':2, 'n':'Foo bar'}, 
            {'id':3, 'n':'Footaz'}
        ]
        self.fn = lambda x:x['n']
        self.choices = ['Foobar', 'Foo bar', 'Footaz']
        self.ds2 = [
            {'id':1, 'n':'Móstoles'}, 
            {'id':2, 'n':'Las Rozas de Madrid'},
            {'id':3, 'n':'Rivas-Vaciamadrid'},
            {'id':4, 'n':'Madrid'}]
        
    def test_normalize(self):
        self.assertEquals(hgwnames.normalize('  ABCD  '), 'abcd')

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

    def test_fuzzy_match(self):
        self.assertEquals(hgwnames.match('FOOB', self.choices), 'Foobar')
        self.assertEquals(hgwnames.match('CL FRANCIA', self.choices), 'Calle Francia')

    @mock.patch('hgwnames.fuzz', None)
    def test_nonfyzzy_match(self):
        self.assertEquals(hgwnames.match('CL FOOBAR', self.choices), 'Calle Foobar')

    def test_fuzzy_dsmatch(self):
        self.assertEquals(hgwnames.dsmatch('FOOB', self.ds, self.fn)['id'], 1)
        self.assertEquals(hgwnames.dsmatch('MADRID', self.ds2, self.fn)['id'], 4)
        self.assertEquals(hgwnames.dsmatch('MADRID', self.ds2, self.fn)['n'], 'Madrid')

    @mock.patch('hgwnames.fuzz', None)
    def test_nonfuzzy_match(self):
        self.assertEquals(hgwnames.dsmatch('FOOBAR', self.ds, self.fn)['id'], 1)
        self.assertEquals(hgwnames.dsmatch('FOO', self.ds, self.fn), None)

    def tearDown(self):
        hgwnames.fuzz = self.temp_fuzz
