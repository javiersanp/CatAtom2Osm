# -*- coding: utf-8 -*-
app_name = 'CatAtom2Osm'
app_version = '2017-06-07'
app_author = u'Javier Sánchez Portero'
app_copyright = u'2017, Javier Sánchez Portero'
app_desc = 'Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services to OSM files'
app_tags = ''

"""Application preferences"""
log_level = 'INFO' # Default console log level
log_file = 'catatom2osm.log'
log_format = '%(asctime)s - %(levelname)s - %(message)s'

qgs_prefix_path = '/usr' # qGis API prefix path. TODO: detect OS
fn_prefix = 'A.ES.SDGC' # Inspire Atom file name prefix

silence_gdal = False

dup_thr = 0.01 # Distance in meters to merge nearest vertexs.
dist_thr = 0.05 # Threshold in meters for vertex simplification and topological points.
angle_thr = 2 # Threshold in degrees from straight angle to delete a vertex


url = {
    "BU": "http://www.catastro.minhap.es/INSPIRE/buildings/%s/ES.SDGC.bu.atom_%s.xml",
    "AD": "http://www.catastro.minhap.es/INSPIRE/addresses/%s/ES.SDGC.ad.atom_%s.xml",
    "CP": "http://www.catastro.minhap.es/INSPIRE/CadastralParcels/%s/ES.SDGC.CP.atom_%s.xml"
}

valid_provinces = ["%02d" % i for i in range(2,57)]

import gettext, sys, os

if sys.platform.startswith('win'):
    import locale
    if os.getenv('LANG') is None:
        lang, enc = locale.getdefaultlocale()
        os.environ['LANG'] = lang
localedir = os.path.join(os.path.dirname(__file__), 'locale', 'po')
gettext.install('catatom2osm', localedir=localedir)
