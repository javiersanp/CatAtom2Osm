"""Reader of ATOM GML files"""
import json
import logging
import os
import re
import zipfile
from qgis.core import QgsCoordinateReferenceSystem

import download
import hgwnames
import layer
import overpass
import setup
from osmxml import etree

log = logging.getLogger(setup.app_name + "." + __name__)

class Reader(object):

    def __init__(self, a_path):
        """
        Args:
            a_path (str): Directory where the source files are located.
        """
        self.path = a_path
        m = re.match("^\d{5}$", os.path.split(a_path)[-1])
        if not m:
            raise ValueError(_("Last directory name must be a 5 digits ZIP code"))
        self.zip_code = m.group()
        self.prov_code = self.zip_code[0:2]
        if self.prov_code not in setup.valid_provinces:
            raise ValueError(_("Province code '%s' don't exists") % self.prov_code)
        if not os.path.exists(a_path):
            os.makedirs(a_path)
        if not os.path.isdir(a_path):
            raise IOError(_("Not a directory: '%s'") % a_path)

    def get_gml_date(self, md_path, zip_path=""):
        """Get the source file production date from the metadata."""
        if os.path.exists(md_path):
            text = open(md_path, 'r').read()
        else:
            zf = zipfile.ZipFile(zip_path)
            text = zf.read(os.path.basename(md_path))
        root = etree.fromstring(text)
        is_empty = len(root) == 0 or len(root[0]) == 0
        namespace = {
            'gco': 'http://www.isotc211.org/2005/gco', 
            'gmd': 'http://www.isotc211.org/2005/gmd'
        }
        if hasattr(root, 'nsmap'):
            namespace = root.nsmap
        gml_date = root.find('gmd:dateStamp/gco:Date', namespace)
        if is_empty or gml_date == None:
            raise IOError(_("Could not read date from '%s'") % md_path)
        return gml_date.text

    def get_atom_file(self, url):
        """
        Given the url of a Cadastre ATOM service, tries to download the ZIP
        file for self.zip_code
        """
        s = re.search('INSPIRE/(\w+)/', url)
        log.info(_("Searching the url for the '%s' layer of '%s'..."), 
            s.group(1), self.zip_code)
        response = download.get_response(url)
        s = re.search('http.+/%s.+zip' % self.zip_code, response.text)
        if not s:
            raise ValueError(_("Zip code '%s' don't exists") % self.zip_code)
        url = s.group(0)
        filename = url.split('/')[-1]
        out_path = os.path.join(self.path, filename)
        log.info(_("Downloading '%s'"), out_path)
        download.wget(url, out_path)

    def get_crs(self, gml_path, zip_path=""):
        """
        Determines the CRS of a GML file. This is necessary because QGIS don't
            detect correctly the CRS of the parcel and zoning layers.
                    
        Args:
            gml_path (str): path to the file
            zip_path (str): optionally zip file that contains the gml

        Returns:
            is_empty (bool): True if the GML file contains no feature
            crs (QgsCoordinateReferenceSystem): CRS of the file
        """
        gml_path = gml_path.split('|')[0]
        if os.path.exists(gml_path):
            text = open(gml_path, 'r').read()
        else:
            zf = zipfile.ZipFile(zip_path)
            text = zf.read(os.path.basename(gml_path))
        root = etree.fromstring(text)
        is_empty = len(root) == 0 or len(root[0]) == 0
        crs_ref = None
        if not is_empty:
            crs_ref = int(root.find('.//*[@srsName]').get('srsName').split(':')[-1])
        crs = QgsCoordinateReferenceSystem(crs_ref)
        return (is_empty, crs)
        
    def get_layer_paths(self, layername):
        if layername in ['building', 'buildingpart', 'otherconstruction']:
            group = 'BU'
        elif layername in ['cadastralparcel', 'cadastralzoning']:
            group = 'CP'
        elif layername in ['address', 'thoroughfarename', 'postaldescriptor', 
                'adminunitname']:
            group = 'AD' 
        else:
            raise ValueError(_("Unknow layer name '%s'") % layername)
        gml_fn = ".".join((setup.fn_prefix, group, self.zip_code, layername, "gml"))
        if group == 'AD':    
            gml_fn = ".".join((setup.fn_prefix, group, self.zip_code, 
                "gml|layername=%s" % layername))
        md_fn = ".".join((setup.fn_prefix, group, "MD", self.zip_code, "xml"))
        if group == 'CP':
            md_fn = ".".join((setup.fn_prefix, group, "MD.", self.zip_code, "xml"))
        zip_fn = ".".join((setup.fn_prefix, group, self.zip_code, "zip"))
        md_path = os.path.join(self.path, md_fn)
        gml_path = os.path.join(self.path, gml_fn)
        zip_path = os.path.join(self.path, zip_fn)
        vsizip_path = "/".join(('/vsizip', self.path, zip_fn, gml_fn))
        return (md_path, gml_path, zip_path, vsizip_path, group)
    
    def read(self, layername, allow_empty=False, force_zip=False):
        """
        Create a QGIS vector layer for a Cadastre layername. Derives the GML 
        filename from layername. Downloads the file if not is present. First try
        to read the ZIP file, if fails try with the GML file.

        Args:
            layername (str): Short name of the Cadastre layer. Any of 
                'building', 'buildingpart', 'otherconstruction', 
                'cadastralparcel', 'cadastralzoning', 'address', 
                'thoroughfarename', 'postaldescriptor', 'adminunitname'
            allow_empty (bool): If False (default), raise a exception for empty
                layer, else returns None
            force_zip (bool): Force to use ZIP file.
                
        Returns:
            QgsVectorLayer: Vector layer.
        """
        (md_path, gml_path, zip_path, vsizip_path, group) = self.get_layer_paths(layername)
        url = setup.prov_url[group] % (self.prov_code, self.prov_code)
        if not os.path.exists(zip_path) and (not os.path.exists(gml_path) or force_zip):
            self.get_atom_file(url)
        gml_date = self.get_gml_date(md_path, zip_path)
        (is_empty, crs) = self.get_crs(gml_path, zip_path)
        if is_empty:
            if not allow_empty:
                raise IOError(_("The layer '%s' is empty") % gml_path)
            else:
                log.info(_("The layer '%s' is empty"), gml_path.encode('utf-8'))
                return None
        if not crs.isValid():
            raise IOError(_("Could not determine the CRS of '%s'") % gml_path)
        gml = layer.BaseLayer(vsizip_path, layername+'.gml', 'ogr')
        if not gml.isValid():
            gml = layer.BaseLayer(gml_path, layername+'.gml', 'ogr')
            if not gml.isValid():
                raise IOError(_("Failed to load layer '%s'") % gml_path)
        gml.setCrs(crs)
        log.info(_("Read %d features in '%s'"), gml.featureCount(), 
            gml_path.encode('utf-8'))
        gml.source_date = gml_date
        return gml

    def get_boundary(self):
        """
        Gets the bounding box of the municipality from the ATOM service
        and the id of the OSM administrative boundary from Overpass
        """
        if not hgwnames.fuzz:
            log.warning(_("Failed to import FuzzyWuzzy. "
                "Install requeriments for address conflation."))
        url = setup.prov_url['BU'] % (self.prov_code, self.prov_code)
        response = download.get_response(url)
        root = etree.fromstring(response.content)
        ns = {
            'atom': 'http://www.w3.org/2005/Atom', 
            'georss': 'http://www.georss.org/georss'
        }
        mun = ''
        for entry in root.findall("atom:entry[atom:title]", namespaces=ns):
            title = entry.find('atom:title', ns).text
            if self.zip_code in title:
                mun = title.replace('buildings', '').strip()[6:]
                poly = entry.find('georss:polygon', ns).text
                lat = [float(lat) for lat in poly.strip().split(' ')[::2]]
                lon = [float(lon) for lon in poly.strip().split(' ')[1:][::2]]
                bbox_bltr = [min(lat)-0.1, max(lon)-0.1, min(lat)+0.1, max(lon)+0.1]
                bbox = ','.join([str(i) for i in bbox_bltr])
        if not mun:
            raise IOError(_("Couldn't find '%s' in the ATOM Service") % self.zip_code)
        query = overpass.Query(bbox, 'json', False, False)
        query.add('rel["admin_level"="8"]')
        self.boundary_name = mun
        self.boundary_search_area = bbox
        matching = False
        try:
            data = json.loads(query.read())
            matching = hgwnames.dsmatch(mun, data['elements'], 
                lambda e: e['tags']['name'])
        except Exception:
            pass
        if matching:
            self.boundary_search_area = str(matching['id'])
            self.boundary_name = matching['tags']['name']
            log.info(_("Municipality: '%s'"), self.boundary_name)
        else:
            log.warning(_("Failed to find administrative boundary, falling "
                "back to bounding box"))

def list_municipalities(prov_code):
    """Get from the ATOM services a list of municipalities for a given province"""
    if prov_code not in setup.valid_provinces:
        raise ValueError(_("Province code '%s' don't exists") % prov_code)
    url = setup.prov_url['BU'] % (prov_code, prov_code)
    response = download.get_response(url)
    root = etree.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    office = root.find('atom:title', ns).text.split('Office ')[1]
    title = _("Territorial office %s") % office
    print
    print title
    print "=" * len(title)
    for entry in root.findall('atom:entry', namespaces=ns):
        row = entry.find('atom:title', ns).text.replace('buildings', '')
        print row

