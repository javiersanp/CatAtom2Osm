# -*- coding: utf-8 -*-
"""Application preferences"""
import sys, os, locale
import csv

app_name = 'CatAtom2Osm'
app_version = '2017-07-05'
app_author = u'Javier Sánchez Portero'
app_copyright = u'2017, Javier Sánchez Portero'
app_desc = 'Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services to OSM files'
app_tags = ''

log_level = 'INFO' # Default console log level
log_file = 'catatom2osm.log'
log_format = '%(asctime)s - %(levelname)s - %(message)s'

fn_prefix = 'A.ES.SDGC' # Inspire Atom file name prefix

silence_gdal = False

dup_thr = 0.012 # Distance in meters to merge nearest vertexs.
                # 0.011 is about 1E-7 degrees in latitude
dist_thr = 0.02 # Threshold in meters for vertex simplification and topological points.
straight_thr = 2 # Threshold in degrees from straight angle to delete a vertex
acute_thr = 5 # Remove vertices with an angle smaller than this value
min_area = 0.05 # Delete geometries with an area smaller than this value
addr_thr = 10 # Distance in meters to merge address node with building footprint

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
    "BU": base_url['BU'] + "%s/ES.SDGC.bu.atom_%s.xml",
    "AD": base_url['AD'] + "%s/ES.SDGC.ad.atom_%s.xml",
    "CP": base_url['CP'] + "%s/ES.SDGC.CP.atom_%s.xml"
}

valid_provinces = ["%02d" % i for i in range(2,57)]

language, encoding = locale.getdefaultlocale()
app_path = os.path.dirname(__file__)
localedir = os.path.join(app_path, 'locale', 'po')
platform = sys.platform
eol = '\r\n' if platform.startswith('win') else '\n'

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

place_types = [
	'Agregado', 'Aldea', u'Área', 'Barrio', 'Barranco', u'Cañada', 'Colegio', 
	'Cigarral', 'Chalet', 'Concejo', 'Campa', 'Campo', u'Caserío', 'Conjunto', 
	u'Diputación', 'Diseminados', 'Edificios', 'Extramuros', 'Entrada', 
	'Ensanche', 'Extrarradio', 'Finca', 'Grupo', 'Huerta', 'Huerto', 
	'Jardines', 'Lugar', 'Mercado', 'Muelle', 'Municipio', u'Masías', 'Monte', 
	'Manzana', 'Poblado', 'Partida', u'Polígono', u'Páramo', 'Parroquia', 'Solar', 
	'Terrenos', u'Urbanización', 'Bulevar', 'Sector'
]

