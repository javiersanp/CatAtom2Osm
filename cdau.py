# -*- coding: utf-8 -*-
"""Reader of CDAU CSV files"""

import logging
import os
os.environ['LANGUAGE'] = 'C'

import download
import setup

log = logging.getLogger(setup.app_name + "." + __name__)


andalucia = {'04': 'Almeria', '11': 'Cadiz', '14': 'Cordova', '18': 'Granada',
    '21': 'Huelva', '23': 'Jaen', '29': 'Malaga', '41': 'Sevilla'}

cdau_url = 'http://www.juntadeandalucia.es/institutodeestadisticaycartografia/cdau/portales/{}'
csv_name = 'portal_{}.csv'
meta_url = 'http://www.callejerodeandalucia.es/portal/web/cdau/inf_alfa'

class Reader(object):
    """Class to download and read CDAU CSV files"""

    def __init__(self, a_path):
        """
        Args:
            a_path (str): Directory where the source files are located.
        """
        self.path = a_path
        if not os.path.exists(a_path):
            os.makedirs(a_path)
        if not os.path.isdir(a_path):
            raise IOError(_("Not a directory: '%s'") % a_path)

    def read(self, prov_code):
        if prov_code not in andalucia.keys():
            raise ValueError(_("Province code '%s' not valid") % prov_code)
        csv_fn = csv_name.format(andalucia[prov_code])
        csv_path = os.path.join(self.path, csv_fn)
        url = cdau_url.format(csv_fn)
        if not os.path.exists(csv_path):
            log.info(_("Downloading '%s'"), csv_path)
            download.wget(url, csv_path)

