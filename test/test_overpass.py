import unittest
import mock

from overpass import Query, api_servers


class TestQuery(unittest.TestCase):

    @mock.patch.object(Query, 'set_search_area')
    def test_init(self, m_q):
        q = Query('foo')
        self.assertEquals(q.output, 'xml')
        self.assertEquals(q.down, '(._;>>;);')
        self.assertEquals(q.meta, 'out meta;')
        self.assertEquals(q.area_id, '')
        self.assertEquals(q.bbox, '')
        self.assertEquals(q.statements, [])
        m_q.assert_called_once_with('foo')
        self.assertEquals(q.url, '')
        q = Query('foo', 'json', False, False)
        self.assertEquals(q.output, 'json')
        self.assertEquals(q.down, '')
        self.assertEquals(q.meta, 'out;')

    def test_set_search_area(self):
        q = Query('12345678')
        self.assertEquals(q.area_id, '12345678')
        self.assertEquals(q.bbox, '')
        q.set_search_area('1,-2, 3.1,-4.99')
        self.assertEquals(q.bbox, '1,-2, 3.1,-4.99')
        self.assertEquals(q.area_id, '')
        with self.assertRaises(TypeError):
            q.set_search_area('123456789')
        with self.assertRaises(TypeError):
            q.set_search_area('123x5678')
        with self.assertRaises(TypeError):
            q.set_search_area('-1')
        with self.assertRaises(TypeError):
            q.set_search_area('1, 2a, 3, 4')
        with self.assertRaises(TypeError):
            q.set_search_area('1, 2, 3')
        with self.assertRaises(TypeError):
            q.set_search_area('1; 2; 3; 4')

    def test_add(self):
        q = Query('1').add('foo;bar;')
        q.add(['taz', 'zap;']).add('raz')
        self.assertEquals(set(q.statements), {'foo', 'bar', 'taz', 'zap', 'raz'})
        q.statements = []
        q.add('1', '2', '3')
        self.assertEquals(set(q.statements), {'1', '2', '3'})

    def test_get_url(self):
        q = Query('1234')
        self.assertEquals(q.get_url(), '')
        q.add('foo', 'bar')
        url = api_servers[0] + "data=[out:xml][timeout:250];(area(3600001234)" \
            "->.searchArea;foo(area.searchArea);bar(area.searchArea););" \
            "(._;>>;);out meta;"
        self.assertEquals(q.get_url(), url)
        q = Query('1,2,3,4', 'json', False, False)
        q.add('foo', 'bar')
        url = api_servers[1] + "data=[out:json][timeout:250];(foo(1,2,3,4);" \
            "bar(1,2,3,4););out;"
        self.assertEquals(q.get_url(1), url)

    @mock.patch('overpass.download')
    def test_download(self, m_download):
        def raises_io(*args):
            raise IOError()
        def raises_io1(url, fn):
            if url == api_servers[0]:
                raise IOError()
        q = Query('1,2,3,4').add('foo')
        q.download('bar')
        m_download.wget.assert_called_once_with(q.get_url(0), 'bar')
        m_download.wget = raises_io
        with self.assertRaises(IOError):
            q.download('bar')
        m_download.wget = raises_io1
        q.download('bar')

    @mock.patch('overpass.download')
    def test_read(self, m_download):
        m_download.get_response.return_value.text.encode.return_value = 'bar'
        q = Query('1,2,3,4').add('foo')
        out = q.read()
        m_download.get_response.assert_called_once_with(q.get_url())
        self.assertEquals(out, 'bar')

