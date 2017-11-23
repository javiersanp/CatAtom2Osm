# -*- coding: utf-8 -*-
"""Application preferences"""
import sys, os, locale
import csv
import gettext

app_name = 'CatAtom2Osm'
app_version = '2017-11-22dev'
app_author = u'Javier Sánchez Portero'
app_copyright = u'2017, Javier Sánchez Portero'
app_desc = 'Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services to OSM files'
app_tags = ''

MIN_QGIS_VERSION_INT = 21001
MIN_QGIS_VERSION = '2.10.1'

locale.setlocale(locale.LC_ALL, '')
language, encoding = locale.getdefaultlocale()
app_path = os.path.dirname(__file__)
localedir = os.path.join(app_path, 'locale', 'po')
platform = sys.platform
eol = '\n'

def winenv():
    global eol, encoding
    if platform.startswith('win'):
        eol = '\r\n'
        if os.getenv('LANG') is None:
            os.environ['LANG'] = language
winenv()

gettext.install(app_name.lower(), localedir=localedir, unicode=1)


log_level = 'INFO' # Default log level
log_file = 'catatom2osm.log'
log_format = '%(asctime)s - %(levelname)s - %(message)s'

fn_prefix = 'A.ES.SDGC' # Inspire Atom file name prefix

silence_gdal = False

dup_thr = 0.012 # Distance in meters to merge nearest vertexs.
                # 0.011 is about 1E-7 degrees in latitude
dist_thr = 0.02 # Threshold in meters for vertex simplification and topological points.
straight_thr = 2 # Threshold in degrees from straight angle to delete a vertex
acute_thr = 10 # Remove vertices with an angle smaller than this value
min_area = 0.05 # Delete geometries with an area smaller than this value
addr_thr = 10 # Distance in meters to merge address node with building footprint
acute_inv = 5 # Remove geometries/rings that result invalid after removing any vertex with an angle smaller than this value
dist_inv = 0.1 # Threshold in meters to filter angles for zig-zag and spikes
entrance_thr = 0.4 # Minimum distance in meters from a entrance to the nearest corner
warning_min_area = 1 # Area in m2 for small area warning
warning_max_area = 30000 # Area in m2 for big area warning

changeset_tags = {
    'comment': "#Spanish_Cadastre_Buildings_Import",
    'source': u"Dirección General del Catastro",
    'type': 'import',
    'url': "https://wiki.openstreetmap.org/wiki/Spanish_Cadastre/Buildings_Import" 
}

base_url = {
    "BU": "http://www.catastro.minhap.es/INSPIRE/buildings/",
    "AD": "http://www.catastro.minhap.es/INSPIRE/addresses/",
    "CP": "http://www.catastro.minhap.es/INSPIRE/CadastralParcels/"
}

serv_url = {
    "BU": base_url['BU'] + "ES.SDGC.BU.atom.xml",
    "AD": base_url['AD'] + "ES.SDGC.AD.atom.xml",
    "CP": base_url['CP'] + "ES.SDGC.CP.atom.xml"
}

prov_url = {
    "BU": base_url['BU'] + "{code}/ES.SDGC.bu.atom_{code}.xml",
    "AD": base_url['AD'] + "{code}/ES.SDGC.ad.atom_{code}.xml",
    "CP": base_url['CP'] + "{code}/ES.SDGC.CP.atom_{code}.xml"
}

cadastre_doc_url = 'http://ovc.catastro.meh.es/OVCServWeb/OVCWcfLibres/OVCFotoFachada.svc/RecuperarFotoFachadaGet?ReferenciaCatastral={}'

valid_provinces = ["%02d" % i for i in range(2,57) if i not in (20, 31, 48)]

no_number = 'S-N' # Regular expression to match addresses without number

lowcase_words = [ # Words to exclude from the general Title Case rule for highway names
    'DE', 'DEL', 'EL', 'LA', 'LOS', 'LAS', 'Y', 'AL', 'EN',
    'A LA', 'A EL', 'A LOS', 'DE LA', 'DE EL', 'DE LOS', 'DE LAS',
    'ELS', 'LES', "L'", "D'", "N'", "S'", "NA", "DE NA", "SES", "DE SES",
    "D'EN", "D'EL", "D'ES", "DE'N", "DE'L", "DE'S"
]

highway_types = { # Dictionary for default 'highway_types.csv'
    'AG': u'Agregado',
    'AL': u'Aldea/Alameda',
    'AR': u'Área/Arrabal',
    'AU': u'Autopista',
    'AV': u'Avenida',
    'AY': u'Arroyo',
    'BJ': u'Bajada',
    'BO': u'Barrio',
    'BR': u'Barranco',
    'CA': u'Cañada',
    'CG': u'Colegio/Cigarral',
    'CH': u'Chalet',
    'CI': u'Cinturón',
    'CJ': u'Calleja/Callejón',
    'CL': u'Calle',
    'CM': u'Camino/Carmen',
    'CN': u'Colonia',
    'CO': u'Concejo/Colegio',
    'CP': u'Campa/Campo',
    'CR': u'Carretera/Carrera',
    'CS': u'Caserío',
    'CT': u'Cuesta/Costanilla',
    'CU': u'Conjunto',
    'CY': u'Caleya',
    'DE': u'Detrás',
    'DP': u'Diputación',
    'DS': u'Diseminados',
    'ED': u'Edificios',
    'EM': u'Extramuros',
    'EN': u'Entrada/Ensanche',
    'ER': u'Extrarradio',
    'ES': u'Escalinata',
    'EX': u'Explanada',
    'FC': u'Ferrocarril/Finca',
    'FN': u'Finca',
    'GL': u'Glorieta',
    'GR': u'Grupo',
    'GV': u'Gran Vía',
    'HT': u'Huerta/Huerto',
    'JR': u'Jardines',
    'LD': u'Lado/Ladera',
    'LG': u'Lugar',
    'MC': u'Mercado',
    'ML': u'Muelle',
    'MN': u'Município',
    'MS': u'Masías',
    'MT': u'Monte',
    'MZ': u'Manzana',
    'PB': u'Poblado',
    'PD': u'Partida',
    'PJ': u'Pasaje/Pasadizo',
    'PL': u'Polígono',
    'PM': u'Páramo',
    'PQ': u'Parroquia/Parque',
    'PR': u'Prolongación/Continuación',
    'PS': u'Paseo',
    'PT': u'Puente',
    'PZ': u'Plaza',
    'QT': u'Quinta',
    'RB': u'Rambla',
    'RC': u'Rincón/Rincona',
    'RD': u'Ronda',
    'RM': u'Ramal',
    'RP': u'Rampa',
    'RR': u'Riera',
    'RU': u'Rúa',
    'SA': u'Salida',
    'SD': u'Senda',
    'SL': u'Solar',
    'SN': u'Salón',
    'SU': u'Subida',
    'TN': u'Terrenos',
    'TO': u'Torrente',
    'TR': u'Travesía/Transversal',
    'UR': u'Urbanización',
    'VR': u'Vereda',
    'AC': u'Acceso',
    'AD': u'Aldea',
    'BV': u'Bulevar',
    'CZ': u'Calzada',
    'PA': u'Paralela',
    'PC': u'Placeta/Plaça',
    'PG': u'Polígono',
    'PO': u'Polígono',
    'SB': u'Subida',
    'SC': u'Sector',
}

# List of highway types to translate as place addresses
place_types = [
	'Agregado', 'Aldea', u'Área', 'Barrio', 'Barranco', u'Cañada', 'Colegio', 
	'Cigarral', 'Chalet', 'Concejo', 'Campa', 'Campo', u'Caserío', 'Conjunto', 
	u'Diputación', 'Diseminados', 'Edificios', 'Extramuros', 'Entrada', 
	'Ensanche', 'Extrarradio', 'Finca', 'Grupo', 'Huerta', 'Huerto', 
	'Jardines', 'Lugar', 'Mercado', 'Muelle', 'Municipio', u'Masías', 'Monte', 
	'Manzana', 'Poblado', 'Partida', u'Polígono', u'Páramo', 'Parroquia', 'Solar', 
	'Terrenos', u'Urbanización', 'Bulevar', 'Sector'
]

# Dictionary of name and OSM boundary relation id for know municipalities
# wich fails in get_boundary method.
mun_fails = {
    '07032': [u'Maó', '1809102'],
    '07040': [u'Palma', '341321'],
    '11042': [u'Zahara', '343140'],
    '16176': [u'Pozorrubio', '347331'],
    '19178': [u'Humanes', '341781'],
    '23043': [u'Hornos', '344389'],
    '23086': [u'Torre del Campo', '346324'],
    '26004': [u'Ajamil', '348189'],
    '26093': [u'Mansilla de la Sierra', '345202'],
    '28063': [u'Gargantilla del Lozoya y Pinilla de Buitrago', '345009'],
    '29101': [u'Montecorto', '7541639'],
    '35010': [u'Santa María de Guía de Gran Canaria', '345440'],
    '37252': [u'Pereña de la Ribera', '343095'],
    '37367': [u'Villarino de los Aires', '340062'],
    '38023': [u'San Cristóbal de La Laguna', '345393'],
    '38039': [u'Santa Úrsula', '340717'],
    '39103': [u'Mancomunidad de Campoo-Cabuérniga', '340042'],
    '44007': [u'Alba', '345065'],
    '47047': [u'Castroponce', '340763'],
    '47101': [u'Muriel', '346973'],
    '47207': [u'Villafuerte', '341197'],
    '50030': [u'Añón de Moncayo', '342653'],
    '50049': [u'Biel', '348008'],
    '51021': [u'Fuente-Álamo', '341797'],
    '52024': [u'Gijón/Xixón', '345576'],
}

