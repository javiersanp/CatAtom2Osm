import codecs
import json
import os
import zipfile

import main
import hgwnames
import download
import overpass
import setup
import catatom2osm
import layer
from qgis.core import *
from osgeo import gdal
from osmxml import etree

qgs = catatom2osm.QgsSingleton()

baseurl = "http://www.catastro.minhap.es/INSPIRE/CadastralParcels/"
fh = codecs.open('check_mun_names.csv', 'w', 'utf-8')
ns = {
    'atom': 'http://www.w3.org/2005/Atom', 
    'georss': 'http://www.georss.org/georss',
    'gco': 'http://www.isotc211.org/2005/gco', 
    'gmd': 'http://www.isotc211.org/2005/gmd'
}
i = 0
for prov_code in setup.valid_provinces:
    url = setup.prov_url['BU'] % (prov_code, prov_code)
    response = download.get_response(url)
    root = etree.fromstring(response.content)
    for entry in root.findall("atom:entry[atom:title]", namespaces=ns):
        title = entry.find('atom:title', ns).text
        zip_code = title[1:6]
        mun = title.replace('buildings', '').strip()[6:]
        matching = False
        url = u"{0}{1}/{2}-{3}/A.ES.SDGC.CP.{2}.zip".format(baseurl, prov_code, zip_code, mun)
        fn = 'temp{}.zip'.format(i)
        download.wget(url, fn)
        zf = zipfile.ZipFile(fn)
        root = etree.parse(zf.open('A.ES.SDGC.CP.MD..{}.xml'.format(zip_code))).getroot()
        gml_code = root.find('.//gmd:code/gco:CharacterString', ns)
        source_crs_ref = int(gml_code.text.split('/')[-1])
        vsizip_path = "/vsizip/{}/A.ES.SDGC.CP.{}.cadastralzoning.gml".format(fn, zip_code)
        gml = layer.BaseLayer(vsizip_path, 'cz', 'ogr')
        gml.setCrs(QgsCoordinateReferenceSystem(source_crs_ref))
        bbox = gml.bounding_box()
        del gml
        os.remove(fn)
        query = overpass.Query(bbox, 'json', False, False)
        query.add('rel["admin_level"="8"]')
        response = download.get_response(query.get_url())
        data = response.json()
        matching = hgwnames.dsmatch(mun, data['elements'], lambda e: e['tags']['name'])
        match =  matching['tags']['name'] if matching else ''
        color = {False: '\033[0;31m', True: '\033[0m'}[len(match) == len(mun)]
        print u'{}{}\t{}\t{}\t{}'.format(color, zip_code, mun, match, len(match) == len(mun))
        fh.write(u'{}\t{}\t{}\t{}\n'.format(zip_code, mun, match, len(match) == len(mun)))
        i += 1
print '\033[0m'
if os.path.exists('temp'):
    os.remove('temp')
qgs.exitQgis()
