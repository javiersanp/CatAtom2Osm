# -*- coding: utf-8 -*-
import mock
import unittest
import sys, os
import logging
logging.disable(logging.WARNING)
from cStringIO import StringIO
import codecs
from contextlib import contextmanager
os.environ['LANGUAGE'] = 'C'
import setup
import main

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

def raiseIOError(*args, **kwargs):
    raise IOError('bartaz')

def raiseImportError(*args, **kwargs):
    raise ImportError('qgis')


class TestMain(unittest.TestCase):

    @mock.patch('main.sys.argv', ['catatom2osm.py'])
    def test_no_args(self):
        with capture(main.run) as output:
            self.assertIn("Usage: catatom2osm", output)

    @mock.patch('main.sys.argv', ['catatom2osm.py', 'foo', 'bar'])
    @mock.patch('main.log.error')
    def test_too_many_args(self, mocklog):
        main.run()
        output = mocklog.call_args_list[0][0][0]
        self.assertIn("Too many arguments", output)

    @mock.patch('main.sys.argv', ['catatom2osm.py', 'foobar'])
    @mock.patch('catatom2osm.CatAtom2Osm')
    def test_default(self, mockcat):
        main.run()
        self.assertTrue(mockcat.called)
        self.assertEquals(mockcat.call_args_list[0][0][0], 'foobar')
        options = mockcat.call_args_list[0][0][1]
        d = {'building': False, 'all': False, 'tasks': True, 'log_level': 'INFO', 
            'parcel': False, 'list': False, 'zoning': True, 'version': False, 
            'address': True}
        for (k, v) in d.items():
            self.assertEquals(getattr(options, k), v)

    @mock.patch('main.sys.argv', ['catatom2osm.py', 'foobar', '-a'])
    @mock.patch('catatom2osm.CatAtom2Osm')
    def test_all(self, mockcat):
        main.run()
        self.assertTrue(mockcat.called)
        options = mockcat.call_args_list[0][0][1]
        d = {'building': True, 'all': True, 'tasks': True, 'log_level': 'INFO', 
            'parcel': True, 'list': False, 'zoning': True, 'version': False, 
            'address': True}
        for (k, v) in d.items():
            self.assertEquals(getattr(options, k), v)

    @mock.patch('main.sys.argv', ['catatom2osm.py', 'foobar', '-b'])
    @mock.patch('catatom2osm.CatAtom2Osm')
    def test_building(self, mockcat):
        main.run()
        self.assertTrue(mockcat.called)
        options = mockcat.call_args_list[0][0][1]
        d = {'building': True, 'all': False, 'tasks': False, 'log_level': 'INFO', 
            'parcel': False, 'list': False, 'zoning': False, 'version': False, 
            'address': False}
        for (k, v) in d.items():
            self.assertEquals(getattr(options, k), v)

    @mock.patch('main.sys.argv', ['catatom2osm.py', 'foobar', '--log=foobar'])
    @mock.patch('main.log.error')
    @mock.patch('catatom2osm.CatAtom2Osm')
    def test_bad_level(self, mockcat, mocklog):
        main.run()
        output = mocklog.call_args_list[0][0][0]
        self.assertIn("Invalid log level", output)

    @mock.patch('main.sys.argv', ['catatom2osm.py', '-v'])
    def test_version(self):
        with capture(main.run) as output:
            self.assertIn(setup.app_version, output)

    @mock.patch('main.sys.argv', ['catatom2osm.py', '-l', '33'])
    @mock.patch('catatom2osm.catatom.list_municipalities')
    def test_list(self, mocklist):
        main.run()
        mocklist.assert_called_once_with('33')

    @mock.patch('main.sys.argv', ['catatom2osm.py', '-l', '33'])
    @mock.patch('catatom2osm.catatom.list_municipalities', raiseIOError)
    @mock.patch('main.log.error')
    def test_list_error(self, mocklog):
        main.run()
        output = mocklog.call_args_list[0][0][0]
        self.assertTrue(mocklog.called)

    @mock.patch('main.sys.argv', ['catatom2osm.py', 'foobar'])
    @mock.patch('catatom2osm.CatAtom2Osm', raiseIOError)
    @mock.patch('main.log.error')
    def test_IOError(self, mocklog):
        main.run()
        output = mocklog.call_args_list[0][0][0]
        self.assertEquals(output, 'bartaz')

    @mock.patch('main.sys.argv', ['catatom2osm.py', 'foobar'])
    @mock.patch('catatom2osm.CatAtom2Osm', raiseImportError)
    @mock.patch('main.log.error')
    def test_ImportError(self, mocklog):
        main.run()
        output1 = mocklog.call_args_list[0][0][0]
        output2 = mocklog.call_args_list[1][0][0]
        self.assertEquals(output1, 'qgis')
        self.assertIn('install QGIS', output2)

    @mock.patch('main.sys.argv', ['catatom2osm.py', 'foobar', '--log=DEBUG'])
    @mock.patch('catatom2osm.CatAtom2Osm', raiseImportError)
    @mock.patch('main.log')
    def test_debug(self, mocklog):
        mocklog.getEffectiveLevel.return_value = logging.DEBUG
        with self.assertRaises(ImportError):
            main.run()
        mocklog.setLevel.assert_called_once_with(logging.DEBUG)
        mocklog.error.assert_not_called()
