import unittest
import mock
import locale
import os, sys  
os.environ['LANGUAGE'] = 'C'

import setup

class TestSetup(unittest.TestCase):

    def test_win(self):
        lang = os.getenv('LANG')
        setup.platform = 'linux2'
        setup.winenv()
        self.assertEquals(setup.eol, '\n')
        setup.platform = 'winx'
        setup.winenv()
        self.assertEquals(setup.eol, '\r\n')
        setup.language = 'foobar'
        del os.environ['LANG']
        setup.winenv()
        self.assertEquals(os.getenv('LANG'), 'foobar')
        os.environ['LANG'] = lang

