# -*- coding: utf-8 -*-
import unittest
import mock
import os
os.environ['LANGUAGE'] = 'C'

import setup
import cdau
from catatom2osm import QgsSingleton
qgs = QgsSingleton()


class TestCdau(unittest.TestCase):

    def setUp(self):
        self.m_cdau = mock.MagicMock()

    def test_cod_mun_cat2ine(self):
        self.assertEqual(cdau.cod_mun_cat2ine('04030'), '04030')
        self.assertEqual(cdau.cod_mun_cat2ine('04040'), '04901')
        self.assertEqual(cdau.cod_mun_cat2ine('04103'), '04103')
        self.assertEqual(cdau.cod_mun_cat2ine('04104'), '04902')
        self.assertEqual(cdau.cod_mun_cat2ine('14900'), '14021')
        self.assertEqual(cdau.cod_mun_cat2ine('18059'), '18907')
        self.assertEqual(cdau.cod_mun_cat2ine('18002'), '18001')
        self.assertEqual(cdau.cod_mun_cat2ine('18062'), '18061')
        self.assertEqual(cdau.cod_mun_cat2ine('18063'), '18119')
        self.assertEqual(cdau.cod_mun_cat2ine('18064'), '18062')
        self.assertEqual(cdau.cod_mun_cat2ine('18119'), '18117')
        self.assertEqual(cdau.cod_mun_cat2ine('18120'), '18903')
        self.assertEqual(cdau.cod_mun_cat2ine('18121'), '18120')
        self.assertEqual(cdau.cod_mun_cat2ine('18135'), '18134')
        self.assertEqual(cdau.cod_mun_cat2ine('18137'), '18135')
        self.assertEqual(cdau.cod_mun_cat2ine('18142'), '18140')
        self.assertEqual(cdau.cod_mun_cat2ine('18144'), '18141')
        self.assertEqual(cdau.cod_mun_cat2ine('18183'), '18180')
        self.assertEqual(cdau.cod_mun_cat2ine('18185'), '18181')
        self.assertEqual(cdau.cod_mun_cat2ine('18198'), '18194')
        self.assertEqual(cdau.cod_mun_cat2ine('18199'), '18912')
        self.assertEqual(cdau.cod_mun_cat2ine('21001'), '21001')
        self.assertEqual(cdau.cod_mun_cat2ine('21059'), '21059')
        self.assertEqual(cdau.cod_mun_cat2ine('21060'), '21061')
        self.assertEqual(cdau.cod_mun_cat2ine('21079'), '21060')
        self.assertEqual(cdau.cod_mun_cat2ine('21900'), '21041')
        self.assertEqual(cdau.cod_mun_cat2ine('29900'), '29067')

    @mock.patch('cdau.os')
    @mock.patch('cdau.layer')
    @mock.patch('cdau.download')
    def test_read(self, m_download, m_layer, m_os):
        self.m_cdau.read = cdau.Reader.read.__func__
        m_os.path.join = lambda *args: '/'.join(args)
        m_os.path.exists.return_value = True
        self.m_cdau.path = 'foobar'
        self.m_cdau.src_date = 'taz'
        csv = mock.MagicMock()
        csv.isValid.return_value = True
        m_layer.BaseLayer.return_value = csv
        self.assertEquals(self.m_cdau.read(self.m_cdau, '29'), csv)
        #self.m_cdau.get_metadata.assert_called_once_with()
        self.assertEqual(csv.source_date, 'taz')
        csv.isValid.return_value = False
        with self.assertRaises(IOError) as cm:
            self.m_cdau.read(self.m_cdau, '29')
        self.assertIn('Failed to load layer', cm.exception.message)

    @mock.patch('cdau.os')
    @mock.patch('cdau.open')
    @mock.patch('cdau.download')
    def test_get_metadata(self, m_download, m_open, m_os):
        resp = mock.MagicMock()
        resp.text = '<p> La fecha de referencia de los datos de cada uno de los ficheros es el 5 de marzo de 2018.</p> </div> <h3 class="tituloCaja">Enlaces relacionados</h3>'
        m_download.get_response.return_value = resp
        fo = mock.MagicMock()
        m_open.return_value.__enter__.return_value = fo
        m_os.path.exists.return_value = False
        self.m_cdau.get_metadata = cdau.Reader.get_metadata.__func__
        self.m_cdau.get_metadata(self.m_cdau, 'xxx')
        self.assertEqual(self.m_cdau.src_date, '2018-03-05')
        m_open.assert_called_once_with('xxx', 'w')
        fo.write.assert_called_once_with('2018-03-05')
        resp.text = ''
        with self.assertRaises(IOError):
            self.m_cdau.get_metadata(self.m_cdau, 'xxx')
        m_open.reset_mock()
        m_open.return_value.read.return_value = 'foobar'
        m_os.path.exists.return_value = True
        self.m_cdau.get_metadata(self.m_cdau, 'xxx')
        self.assertEqual(self.m_cdau.src_date, 'foobar')
        m_open.assert_called_once_with('xxx', 'r')

    def _test_conflate(self):
        cdau_address = mock.MagicMock()
        cat_address = mock.MagicMock()
        cdau_address.search.return_value = [1,2,3]
        cdau.conflate(cdau_address, cat_address, '29900')

    def test_true_read(self):
        import catatom
        reader = cdau.Reader('/home/jsanchez/temp/catastro/aux')
        cdau_address = reader.read('29')
        print cdau_address.featureCount()
        cat = catatom.Reader('/home/jsanchez/temp/catastro/29094')
        cat_address = cat.read('address')
        print cat_address.featureCount()
        cdau.conflate(cdau_address, cat_address, '29094')

