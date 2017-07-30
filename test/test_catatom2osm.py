# -*- coding: utf-8 -*-
import mock
import unittest
from cStringIO import StringIO
import codecs
from contextlib import contextmanager
import os, sys

os.environ['LANGUAGE'] = 'C'
import main
import hgwnames
import setup
import osm
import layer
from osmxml import etree
import catatom2osm as cat

@contextmanager
def capture(command, *args, **kwargs):
    out = sys.stdout
    sys.stdout = StringIO()#codecs.getwriter('utf-8')(StringIO())
    try:
        command(*args, **kwargs)
        sys.stdout.seek(0)
        yield sys.stdout.read()
    finally:
        sys.stdout = out

prov_atom = """
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:georss="http://www.georss.org/georss"  xmlns:inspire_dls = "http://inspire.ec.europa.eu/schemas/inspire_dls/1.0" xml:lang="en"> 
<title>Download Office foobar</title>
<entry>
<title> 09001-FOO buildings</title>
</entry>
<entry>
<title> 09002-BAR buildings</title>
</entry>
<entry>
<title> 09999-TAZ buildings</title>
<georss:polygon>42.0997821981015 -3.79048777556759 42.0997821981015 -3.73420761211555 42.1181603073135 -3.73420761211555 42.1181603073135 -3.79048777556759 42.0997821981015 -3.79048777556759</georss:polygon>
</entry>
</feed>
"""


class TestCatAtom2Osm(unittest.TestCase):

    def setUp(self):
        self.options = {'building': False, 'all': False, 'tasks': True, 
            'log_level': 'INFO', 'parcel': False, 'list': False, 'zoning': True, 
            'version': False, 'address': False}

    def tearDown(self):
        if os.path.exists('09999'):
            os.rmdir('09999')

    def test_write_task(self):
        app = cat.CatAtom2Osm('09999', self.options)
        app.urban_zoning = 0
        app.utaskn = 100
        app.rtaskn = 1
        app.osm_from_layer = mock.MagicMock(return_value = 'foo')
        app.merge_address = mock.MagicMock(return_value = 'bar')
        app.write_osm = mock.MagicMock()
        app.write_task(0, None)
        app.write_osm.assert_called_once_with('foo', 'tasks/u00100.osm')
        app.write_task(1, None, '')
        app.write_osm.assert_called_with('foo', 'tasks/r001.osm')
        app.merge_address.called_once_with('foo', 'bar')
        app.write_task(0, None)
        app.write_osm.assert_called_with('foo', 'tasks/u00101.osm')
        app.write_task(1, None)
        app.write_osm.assert_called_with('foo', 'tasks/r002.osm')

    def test_get_translations(self):
        app = cat.CatAtom2Osm('09999', self.options)
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

    def test_get_current_ad_osm(self):
        d = osm.Osm()
        d.Node(0,0, {'addr:housenumber': '12', 'addr:street': 'foobar'})
        d.Node(1,1, {'addr:housenumber': '14', 'addr:street': 'foobar'})
        d.Node(2,2, {'addr:housenumber': '10', 'addr:place': 'bartaz'})
        d.Node(3,3)
        app = cat.CatAtom2Osm('09999', self.options)
        app.read_osm = mock.MagicMock(return_value = d)
        address = app.get_current_ad_osm()
        self.assertEquals(address, set(['foobar14', 'foobar12', 'bartaz10']))

    @mock.patch('catatom2osm.log.warning')
    @mock.patch('catatom2osm.download')
    def test_get_boundary(self, m_download, m_log):
        bbox09999 = "41.9997821981,-3.83420761212,42.1997821981,-3.63420761212"
        mun_json = '{"elements": [{"id": 1, "tags": {"name": "Barcelona"}}, ' \
            '{"id": 2, "tags": {"name": "Tazmania"}}, {"id": 3, "tags": {"name": "Foo"}}]}'
        m1 = mock.MagicMock()
        m1.content = prov_atom
        m2 = mock.MagicMock()
        m2.text = mun_json
        m_download.get_response.side_effect = [m1, m2]
        app = cat.CatAtom2Osm('09999', self.options)
        app.get_boundary()
        url1 = setup.prov_url['BU'] % ('09', '09')
        url2 = setup.boundary_query % bbox09999
        m_download.get_response.assert_has_calls([mock.call(url1), 
            mock.call(url2)], any_order=False)
        self.assertEquals(app.boundary_id, 2)
        self.assertEquals(app.boundary_name, 'Tazmania')
        self.assertEquals(app.boundary_bbox, bbox09999)
        m2.text = '{"elements": []}'
        m_download.get_response.side_effect = [m1, m2]
        app = cat.CatAtom2Osm('09999', self.options)
        app.get_boundary()
        output = m_log.call_args_list[0][0][0]
        self.assertIn("Failed to find", output)

    @mock.patch('catatom2osm.download')
    def test_list_municipalities(self, m_download):
        url = setup.prov_url['BU'] % ('99', '99')
        m_download.get_response.return_value.content = prov_atom
        with capture(cat.list_municipalities, '99') as output:
            m_download.get_response.assert_called_once_with(url)
            self.assertIn('foobar', output)
            self.assertIn('FOO', output)
            self.assertIn('BAR', output)

