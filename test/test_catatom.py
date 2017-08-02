import unittest
import mock
import codecs
from cStringIO import StringIO
from contextlib import contextmanager
import os, sys
os.environ['LANGUAGE'] = 'C'

import main
import catatom
import setup

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


class TestCatAtom(unittest.TestCase):

    def setUp(self):
        self.m_cat = mock.MagicMock()

    @mock.patch('catatom.os')
    def test_init(self, m_os):
        m_os.path.split = lambda x: x.split('/')
        self.m_cat.init = catatom.Reader.__init__.__func__
        with self.assertRaises(ValueError) as cm:
            self.m_cat.init(self.m_cat, '09999/xxxxx')
        self.assertIn('directory name', cm.exception.message)
        with self.assertRaises(ValueError) as cm:
            self.m_cat.init(self.m_cat, 'xxx/999')
        self.assertIn('directory name', cm.exception.message)
        with self.assertRaises(ValueError) as cm:
            self.m_cat.init(self.m_cat, 'xxx/99999')
        self.assertIn('Province code', cm.exception.message)
        m_os.path.exists.return_value = True
        m_os.path.isdir.return_value = False
        with self.assertRaises(IOError) as cm:
            self.m_cat.init(self.m_cat, 'xxx/12345')
        self.assertIn('Not a directory', cm.exception.message)
        m_os.makedirs.assert_not_called()
        m_os.path.exists.return_value = False
        m_os.path.isdir.return_value = True
        self.m_cat.init(self.m_cat, 'xxx/12345')
        m_os.makedirs.assert_called_with('xxx/12345')
        self.assertEquals(self.m_cat.path, 'xxx/12345')
        self.assertEquals(self.m_cat.zip_code, '12345')
        self.assertEquals(self.m_cat.prov_code, '12')

    @mock.patch('catatom.log.warning')
    @mock.patch('catatom.overpass')
    @mock.patch('catatom.hgwnames')
    @mock.patch('catatom.download')
    def test_get_boundary(self, m_download, m_hgw, m_overpass, m_log):
        self.m_cat.get_boundary = catatom.Reader.get_boundary.__func__
        bbox09999 = "41.9997821981,-3.83420761212,42.1997821981,-3.63420761212"
        data = {"id": 2, "tags": {"name": "Tazmania"}}
        m_hgw.fuzz = True
        m_download.get_response.return_value.content = prov_atom
        m_overpass.Query().read.return_value = '{"elements": "foobar"}'
        m_hgw.dsmatch.return_value = data
        self.m_cat.prov_code = '09'
        self.m_cat.zip_code = '09999'
        self.m_cat.get_boundary(self.m_cat)
        url = setup.prov_url['BU'] % ('09', '09')
        m_download.get_response.assert_called_once_with(url)
        m_overpass.Query.assert_called_with(bbox09999, 'json', False, False)
        self.assertEquals(m_hgw.dsmatch.call_args_list[0][0][0], 'TAZ')
        self.assertEquals(m_hgw.dsmatch.call_args_list[0][0][1], 'foobar')
        self.assertEquals(m_hgw.dsmatch.call_args_list[0][0][2](data), 'Tazmania')
        self.assertEquals(self.m_cat.boundary_search_area, '2')
        self.assertEquals(self.m_cat.boundary_name, 'Tazmania')
        
        m_hgw.dsmatch.return_value = None
        self.m_cat.get_boundary(self.m_cat)
        output = m_log.call_args_list[0][0][0]
        self.assertIn("Failed to find", output)
        self.assertEquals(self.m_cat.boundary_search_area, bbox09999)
        
        m_hgw.fuzz = False
        m_hgw.dsmatch.return_value = data
        self.m_cat.get_boundary(self.m_cat)
        output = m_log.call_args_list[-1][0][0]
        self.assertIn("Failed to import", output)

    @mock.patch('catatom.download')
    def test_list_municipalities(self, m_download):
        with self.assertRaises(ValueError):
            catatom.list_municipalities('01')
        url = setup.prov_url['BU'] % ('09', '09')
        m_download.get_response.return_value.content = prov_atom
        with capture(catatom.list_municipalities, '09') as output:
            m_download.get_response.assert_called_once_with(url)
            self.assertIn('foobar', output)
            self.assertIn('FOO', output)
            self.assertIn('BAR', output)

