# -*- coding: utf-8 -*-
import mock
import unittest
import codecs
import os, sys
from cStringIO import StringIO
from contextlib import contextmanager
from optparse import Values

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
    sys.stdout = codecs.getwriter('utf-8')(StringIO())
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


class TestQgsSingleton(unittest.TestCase):

    @mock.patch('catatom2osm.QgsSingleton._qgs', None)
    @mock.patch('catatom2osm.gdal')
    @mock.patch('catatom2osm.QgsApplication')
    def test_new(self, m_qgsapp, m_gdal):
        q1 = cat.QgsSingleton()
        self.assertEquals(m_qgsapp.call_count, 1)
        m_gdal.SetConfigOption.assert_has_calls([
            mock.call('GML_ATTRIBUTES_TO_OGR_FIELDS', 'YES'),
            mock.call('GML_SKIP_RESOLVE_ELEMS', 'ALL')
        ])
        q2 = cat.QgsSingleton()
        self.assertEquals(m_qgsapp.call_count, 1)
        self.assertTrue(q1 is q2)


class TestCatAtom2Osm(unittest.TestCase):

    def setUp(self):
        self.options = {'building': False, 'all': False, 'tasks': True, 
            'log_level': 'INFO', 'parcel': False, 'list': False, 'zoning': True, 
            'version': False, 'address': False}
        self.m_app = mock.MagicMock()
        self.m_app.options = Values(self.options)
        self.m_app.get_translations.return_value = ([], False)
        self.m_app.path = 'foo'

    @mock.patch('catatom2osm.os')
    @mock.patch('catatom2osm.QgsSingleton')
    def test_init(self, m_qgs, m_os):
        m_os.path.split = lambda x: x.split('/')
        m_qgs.return_value = 'foo'
        self.m_app.init = cat.CatAtom2Osm.__init__.__func__
        with self.assertRaises(ValueError) as cm:
            self.m_app.init(self.m_app, '09999/xxxxx', self.options)
        self.assertIn('directory name', cm.exception.message)
        with self.assertRaises(ValueError) as cm:
            self.m_app.init(self.m_app, 'xxx/999', self.options)
        self.assertIn('directory name', cm.exception.message)
        with self.assertRaises(ValueError) as cm:
            self.m_app.init(self.m_app, 'xxx/99999', self.options)
        self.assertIn('Province code', cm.exception.message)
        m_os.path.exists.return_value = True
        m_os.path.isdir.return_value = False
        with self.assertRaises(IOError) as cm:
            self.m_app.init(self.m_app, 'xxx/12345', self.options)
        self.assertIn('Not a directory', cm.exception.message)
        m_os.makedirs.assert_not_called()
        m_os.path.exists.return_value = False
        m_os.path.isdir.return_value = True
        app = self.m_app.init(self.m_app, 'xxx/12345', self.options)
        m_os.makedirs.assert_called_with('xxx/12345')
        self.assertEquals(self.m_app.path, 'xxx/12345')
        self.assertEquals(self.m_app.zip_code, '12345')
        self.assertEquals(self.m_app.prov_code, '12')
        self.assertEquals(self.m_app.qgs, 'foo')

    @mock.patch('catatom2osm.gdal')
    def test_gdal(self, m_gdal):
        reload(cat)
        self.assertFalse(m_gdal.PushErrorHandler.called)
        setup.silence_gdal = True
        reload(cat)
        m_gdal.PushErrorHandler.called_once_with('CPLQuietErrorHandler')

    @mock.patch('catatom2osm.os')
    @mock.patch('catatom2osm.log')
    @mock.patch('catatom2osm.hgwnames')
    def test_start(self, m_hgw, m_log, m_os):
        # is new, exit
        m_hgw.fuzz = True
        self.m_app.start = cat.CatAtom2Osm.start.__func__
        self.m_app.options.address = True
        self.m_app.options.tasks = True
        self.m_app.options.building = True
        self.m_app.get_translations.return_value = ([], True)
        self.m_app.fixmes = 1
        self.m_app.start(self.m_app)
        self.m_app.read_address.assert_called_once_with()
        self.assertFalse(self.m_app.options.tasks)
        self.m_app.get_current_ad_osm.assert_not_called()
        self.assertEquals(self.m_app.fixmes, 1)
        m_log.warning.assert_not_called()
        # not new, continue, not buildings or tasks
        self.m_app.get_translations.return_value = ([], False)
        self.m_app.options.building = False
        self.m_app.start(self.m_app)
        self.assertEquals(self.m_app.fixmes, 0)
        #base path exists
        self.m_app.options.address = False
        self.m_app.options.tasks = True
        m_os.path.join = lambda *args: '/'.join(args)
        m_os.path.exists.return_value = True
        self.m_app.start(self.m_app)
        m_os.makedirs.assert_not_called()
        self.m_app.get_current_bu_osm.assert_called_once_with()
        #not exists
        m_hgw.fuzz = False
        m_os.path.exists.return_value = False
        self.m_app.start(self.m_app)
        self.assertTrue(m_log.warning.called)
        m_os.makedirs.assert_called_once_with('foo/tasks')

    def test_merge_address(self):
        address = osm.Osm()
        address.Node(0,0, {'ref': '1', 'addrtags': 'address1'})
        address.Node(2,0, {'ref': '2', 'addrtags': 'address2', 'entrance': 'yes'})
        address.Node(4,0, {'ref': '3', 'addrtags': 'address3', 'entrance': 'yes'})
        address.Node(6,0, {'ref': '4', 'addrtags': 'address4', 'entrance': 'yes'})
        building = osm.Osm()
        w0 = building.Way([], {'ref': '0'}) # building with ref not in address
        w1 = building.Way([(0,0), (1,0), (1,1), (0,0)], {'ref': '1'}) # no entrance address, tags to way
        w2 = building.Way([(2,0), (3,0), (3,1), (2,0)], {'ref': '2'}) # entrance exists, tags to node
        w3 = building.Way([(4,1), (5,0), (5,1), (4,1)], {'ref': '3'}) # entrance don't exists, no tags
        w4 = building.Way([(6,0), (7,0), (7,1), (6,0)], {'ref': '4'}) # many buildings, tags to relation
        w5 = building.Way([(6,2), (7,2), (7,3), (6,2)], {'ref': '3'})
        w6 = building.Way([(6,4), (9,4), (9,7), (6,7), (6,4)])
        w7 = building.Way([(7,5), (8,5), (8,6), (7,6), (7,5)])
        r = building.Relation(tags = {'ref': '4'})
        r.append(w6, 'outer') # outer members to address relation
        r.append(w7, 'inner')

    def test_write_task(self):
        self.m_app.write_task = cat.CatAtom2Osm.write_task.__func__
        self.m_app.urban_zoning = 0
        self.m_app.utaskn = 100
        self.m_app.rtaskn = 1
        self.m_app.osm_from_layer.return_value = 'foo'
        self.m_app.merge_address.return_value = 'bar'
        self.m_app.write_task(self.m_app, 0, None)
        self.m_app.write_osm.assert_called_once_with('foo', 'tasks/u00100.osm')
        self.m_app.write_task(self.m_app, 1, None, '')
        self.m_app.write_osm.assert_called_with('foo', 'tasks/r001.osm')
        self.m_app.merge_address.called_once_with('foo', 'bar')
        self.m_app.write_task(self.m_app, 0, None)
        self.m_app.write_osm.assert_called_with('foo', 'tasks/u00101.osm')
        self.m_app.write_task(self.m_app, 1, None)
        self.m_app.write_osm.assert_called_with('foo', 'tasks/r002.osm')

    @mock.patch('catatom2osm.os')
    @mock.patch('catatom2osm.csvtools')
    def test_get_translations(self, m_csv, m_os):
        self.m_app.get_translations = cat.CatAtom2Osm.get_translations.__func__
        setup.app_path = 'bar'
        m_os.path.join = lambda *args: '/'.join(args)
        m_csv.csv2dict.return_value = 'raz'
        address = mock.MagicMock()
        address.get_highway_names = mock.MagicMock(return_value = 'taz')
        m_os.path.exists.return_value = True
        (names, is_new) = self.m_app.get_translations(self.m_app, address, None)
        m_csv.dict2csv.assert_not_called()
        m_csv.csv2dict.assert_has_calls([
            mock.call('bar/highway_types.csv', setup.highway_types),
            mock.call('foo/highway_names.csv', {}),
        ])
        self.assertEquals(names, 'raz')
        self.assertFalse(is_new)
        m_csv.csv2dict.reset_mock()
        m_os.path.exists.return_value = False
        (names, is_new) = self.m_app.get_translations(self.m_app, address, None)
        m_csv.csv2dict.assert_not_called()
        m_csv.dict2csv.assert_has_calls([
            mock.call('bar/highway_types.csv', setup.highway_types),
            mock.call('foo/highway_names.csv', 'taz'),
        ])
        self.assertEquals(names, 'taz')
        self.assertTrue(is_new)

    @mock.patch('catatom2osm.layer')
    def test_get_highway(self, m_layer):
        self.m_app.read_osm.return_value = 1234
        self.m_app.get_highway = cat.CatAtom2Osm.get_highway.__func__
        h = self.m_app.get_highway(self.m_app)
        h.read_from_osm.assert_called_once_with(1234)

    def test_get_current_bu_osm(self):
        self.m_app.get_current_bu_osm = cat.CatAtom2Osm.get_current_bu_osm.__func__
        self.m_app.read_osm.return_value = 1234
        c = self.m_app.get_current_bu_osm(self.m_app)
        self.assertEquals(c, 1234)

    def test_get_current_ad_osm(self):
        d = osm.Osm()
        d.Node(0,0, {'addr:housenumber': '12', 'addr:street': 'foobar'})
        d.Node(1,1, {'addr:housenumber': '14', 'addr:street': 'foobar'})
        d.Node(2,2, {'addr:housenumber': '10', 'addr:place': 'bartaz'})
        d.Node(3,3)
        self.m_app.get_current_ad_osm = cat.CatAtom2Osm.get_current_ad_osm.__func__
        self.m_app.read_osm.return_value = d
        address = self.m_app.get_current_ad_osm(self.m_app)
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
        self.m_app.prov_code = '09'
        self.m_app.zip_code = '09999'
        self.m_app.get_boundary = cat.CatAtom2Osm.get_boundary.__func__
        self.m_app.get_boundary(self.m_app)
        url1 = setup.prov_url['BU'] % ('09', '09')
        url2 = setup.boundary_query % bbox09999
        m_download.get_response.assert_has_calls([mock.call(url1), 
            mock.call(url2)], any_order=False)
        self.assertEquals(self.m_app.boundary_id, 2)
        self.assertEquals(self.m_app.boundary_name, 'Tazmania')
        self.assertEquals(self.m_app.boundary_bbox, bbox09999)
        m2.text = '{"elements": []}'
        m_download.get_response.side_effect = [m1, m2]
        self.m_app.get_boundary(self.m_app)
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

