# -*- coding: utf-8 -*-
"""Reader of CDAU CSV files"""

import logging
import locale
locale.setlocale(locale.LC_TIME, ('es', 'UTF-8'))
import os
import re
from collections import defaultdict
from datetime import datetime

from qgis.core import QgsCoordinateReferenceSystem

import download
import layer
import setup

log = logging.getLogger(setup.app_name + "." + __name__)


andalucia = {'04': 'Almeria', '11': 'Cadiz', '14': 'Cordova', '18': 'Granada',
    '21': 'Huelva', '23': 'Jaen', '29': 'Malaga', '41': 'Sevilla'}

cdau_url = 'http://www.juntadeandalucia.es/institutodeestadisticaycartografia/cdau/portales/{}'
csv_name = 'portal_{}.csv'
meta_url = 'http://www.callejerodeandalucia.es/portal/web/cdau/inf_alfa'
cdau_crs = 25830
cod_mun_trans = {
    '04': {40: 901, 104: 902, 105: 903, 900: 13},
    '11': {43: 901, 44: 902, 900: 12},
    '14': {900: 21},
    '18': {20: 911, 53: 908, 59: 907, 63: 119, 83: 905, 92: 906, 105: 910, 106: 103, 120: 903, 130: 904, 132: 902, 141: 909, 163: 901, 199: 912, 200: 913, 900: 87},
    '21': {79: 60, 900: 41},
    '23': {13: 902, 23: 901, 78: 904, 100: 903, 102: 905, 900: 50},
    '29': {102: 902, 103: 901, 900: 67},
    '41': {103: 901, 104: 902, 105: 903, 900: 91}
}

def cod_mun_cat2ine(cod_mun_cat):
    """Return the INE municipality code from the Cadastre code"""
    cod_prov = cod_mun_cat[0:2]
    cod_mun = int(cod_mun_cat[2:])
    if cod_prov == '18':
        if cod_mun in cod_mun_trans[cod_prov].keys():
            cod_mun = cod_mun_trans[cod_prov][cod_mun]
        else:
            if cod_mun in range(64, 120) or cod_mun in range(137, 143):
                cod_mun -= 2
            elif cod_mun in range(144, 184):
                cod_mun -= 3
            elif cod_mun in range(185, 199):
                cod_mun -= 4
            else:
                cod_mun -= 1
    elif cod_prov == '21':
        cod_mun = cod_mun_trans[cod_prov].get(cod_mun, cod_mun + 1 if cod_mun > 59 else cod_mun)
    else: 
        cod_mun = cod_mun_trans[cod_prov].get(cod_mun, cod_mun)
    cod_mun_ine = '{}{:03d}'.format(cod_prov, cod_mun)
    return cod_mun_ine

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
        self.crs_ref = cdau_crs
        self.src_date = None

    def get_metadata(self, md_path):
        if os.path.exists(md_path):
            self.src_date = open(md_path, 'r').read()
        else:
            response = download.get_response(meta_url)
            s = re.search('fecha de referencia.*([0-9]{1,2} de .+ de [0-9]{4})', response.text)
            try:
                self.src_date = datetime.strptime(s.group(1), '%d de %B de %Y').strftime('%Y-%m-%d')
            except:
                raise IOError(_("Could not read metadata from '%s'") % 'CDAU')
            with open(md_path, 'w') as fo:
                fo.write(self.src_date)

    def read(self, prov_code):
        if prov_code not in andalucia.keys():
            raise ValueError(_("Province code '%s' not valid") % prov_code)
        csv_fn = csv_name.format(andalucia[prov_code])
        csv_path = os.path.join(self.path, csv_fn)
        url = cdau_url.format(csv_fn)
        if not os.path.exists(csv_path):
            log.info(_("Downloading '%s'"), csv_path)
            download.wget(url, csv_path)
        csv = layer.BaseLayer(csv_path, csv_fn, 'ogr')
        if not csv.isValid():
            raise IOError(_("Failed to load layer '%s'") % csv_path)
        csv.setCrs(QgsCoordinateReferenceSystem(cdau_crs))
        log.info(_("Read %d features in '%s'"), csv.featureCount(), csv_path)
        self.get_metadata(csv_path.replace('.csv', '.txt'))
        csv.source_date = self.src_date
        return csv


def conflate(cdau_address, cat_address, cod_mun_cat):
    """Conflate CDAU over Cadastre addresses datasets"""
    cod_mun = cod_mun_cat2ine(cod_mun_cat)
    q = "ine_mun='{}' and (tipo_portal_pk='{}' or tipo_portal_pk='{}')"
    exp = q.format(cod_mun, 'PORTAL', 'ACCESORIO')
    c = 0
    addresses = defaultdict(list)
    for feat in cat_address.getFeatures():
        g = feat['localId'].split('.')
        ref = '.'.join(g[:3] + g[4:])
        addresses[ref].append(feat)
    for ad in cdau_address.search(exp):
        dgc_via = ad['dgc_via']
        refcatparc = ad['refcatparc']
        ref = '{}.{}.{}.{}'.format(cod_mun_cat[:2], cod_mun_cat[2:], dgc_via, refcatparc)
        print ad['id_por_pk'], ref, len(addresses[ref])
        #for p in cat_address.search(exp):
        # Se busca el grupo de direcciones de Catastro que coincidan con los valores 'dgc_via' y 'refcatparc'.
        # Si este grupo está vacío, y no hay ninguna dirección de catastro cerca, se añade la dirección CDAU.
        # Si el grupo tiene un elemento, se sustituye la dirección de Catastro por la de CDAU.
        # Si el grupo tiene varios elementos, se sustituye la dirección de Catastro más cercana por la de CDAU.
        c += 1
    print c
        
