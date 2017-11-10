"""Reader of Cadastre ATOM GML files"""
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
from compat import etree
from report import instance as report

log = logging.getLogger(setup.app_name + "." + __name__)

class Reader(object):
    """Class to download and read Cadastre ATOM GML files"""

    def __init__(self, a_path):
        """
        Args:
            a_path (str): Directory where the source files are located.
        """
        self.path = a_path
        m = re.match("^\d{5}$", os.path.split(a_path)[-1])
        if not m:
            msg = _("Last directory name must be a 5 digits ZIP code")
            raise ValueError(msg.encode(setup.encoding))
        self.zip_code = m.group()
        self.prov_code = self.zip_code[0:2]
        if self.prov_code not in setup.valid_provinces:
            msg = _("Province code '%s' don't exists") % self.prov_code
            raise ValueError(msg.encode(setup.encoding))
        if not os.path.exists(a_path):
            os.makedirs(a_path)
        if not os.path.isdir(a_path):
            msg = _("Not a directory: '%s'") % a_path
            raise IOError(msg.encode(setup.encoding))

    def get_metadata(self, md_path, zip_path=""):
        """Get the metadata of the source file"""
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
            msg = _("Could not read metadata from '%s'") % md_path
            raise IOError(msg.encode(setup.encoding))
        self.gml_date = gml_date.text
        gml_title = root.find('.//gmd:title/gco:CharacterString', namespace)
        self.cat_mun = gml_title.text.split('-')[-1].split('(')[0].strip()
        gml_code = root.find('.//gmd:code/gco:CharacterString', namespace)
        self.crs_ref = int(gml_code.text.split('/')[-1])

    def get_atom_file(self, url):
        """
        Given the url of a Cadastre ATOM service, tries to download the ZIP
        file for self.zip_code
        """
        s = re.search('INSPIRE/(\w+)/', url)
        log.debug(_("Searching the url for the '%s' layer of '%s'..."), 
            s.group(1), self.zip_code)
        response = download.get_response(url)
        s = re.search('http.+/%s.+zip' % self.zip_code, response.text)
        if not s:
            msg = _("Zip code '%s' don't exists") % self.zip_code
            raise ValueError(msg.encode(setup.encoding))
        url = s.group(0)
        filename = url.split('/')[-1]
        out_path = os.path.join(self.path, filename)
        log.info(_("Downloading '%s'"), out_path)
        download.wget(url, out_path)

    def get_layer_paths(self, layername):
        if layername in ['building', 'buildingpart', 'otherconstruction']:
            group = 'BU'
        elif layername in ['cadastralparcel', 'cadastralzoning']:
            group = 'CP'
        elif layername in ['address', 'thoroughfarename', 'postaldescriptor', 
                'adminunitname']:
            group = 'AD' 
        else:
            msg = _("Unknow layer name '%s'") % layername
            raise ValueError(msg.encode(setup.encoding))
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

    def is_empty(self, gml_path, zip_path):
        """Detects if the file is empty. Cadastre empty files (usually 
        otherconstruction) comes with a null feature and results in a non valid
        layer in QGIS"""
        if os.path.exists(zip_path):
            zf = zipfile.ZipFile(zip_path, 'r')
            f = zf.open(os.path.basename(gml_path).split('|')[0], 'r')
        else:
            f = open(gml_path, 'r')
        context = etree.iterparse(f, events=('end',))
        try:
            event, elem = context.next() # </something>
            event, elem = context.next() # </featureMember>
            event, elem = context.next() # </featureCollection>
            return False
        except StopIteration:
            return True

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
        url = setup.prov_url[group].format(code=self.prov_code)
        if not os.path.exists(zip_path) and (not os.path.exists(gml_path) or force_zip):
            self.get_atom_file(url)
        self.get_metadata(md_path, zip_path)
        if self.is_empty(gml_path, zip_path):
            if not allow_empty:
                msg = _("The layer '%s' is empty") % gml_path
                raise IOError(msg.encode(setup.encoding))
            else:
                log.info(_("The layer '%s' is empty"), gml_path.encode('utf-8'))
                return None
        gml = layer.BaseLayer(vsizip_path, layername+'.gml', 'ogr')
        if not gml.isValid():
            gml = layer.BaseLayer(gml_path, layername+'.gml', 'ogr')
            if not gml.isValid():
                msg = _("Failed to load layer '%s'") % gml_path
                raise IOError(msg.encode(setup.encoding))
        crs = QgsCoordinateReferenceSystem(self.crs_ref)
        if not crs.isValid():
            msg = _("Could not determine the CRS of '%s'") % gml_path
            raise IOError(msg.encode(setup.encoding))
        gml.setCrs(crs)
        log.info(_("Read %d features in '%s'"), gml.featureCount(), 
            gml_path.encode('utf-8'))
        gml.source_date = self.gml_date
        return gml

    def get_boundary(self, zoning):
        """
        Gets the id of the OSM administrative boundary from Overpass.
        Precondition: called after read any gml (metadata adquired)
        """
        if self.zip_code in setup.mun_fails:
            self.boundary_name = setup.mun_fails[self.zip_code][0]
            self.boundary_search_area = setup.mun_fails[self.zip_code][1]
            log.info(_("Municipality: '%s'"), self.boundary_name)
            return
        self.boundary_bbox = zoning.bounding_box()
        query = overpass.Query(self.boundary_bbox, 'json', False, False)
        query.add('rel["admin_level"="8"]')
        matching = False
        try:
            data = json.loads(query.read())
            matching = hgwnames.dsmatch(self.cat_mun, data['elements'], 
                lambda e: e['tags']['name'])
        except Exception:
            pass
        if matching:
            self.boundary_search_area = str(matching['id'])
            self.boundary_name = matching['tags']['name']
            self.boundary_data = matching['tags']
            log.info(_("Municipality: '%s'"), self.boundary_name)
        else:
            self.boundary_search_area = self.boundary_bbox
            msg = _("Failed to find administrative boundary, falling "
                "back to bounding box")
            log.warning(msg)
            report.warnings.append(msg)

def list_municipalities(prov_code):
    """Get from the ATOM services a list of municipalities for a given province"""
    if prov_code not in setup.valid_provinces:
        msg = _("Province code '%s' don't exists") % prov_code
        raise ValueError(msg.encode(setup.encoding))
    url = setup.prov_url['BU'].format(code=prov_code)
    response = download.get_response(url)
    root = etree.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    office = root.find('atom:title', ns).text.split('Office ')[1]
    title = _("Territorial office %s") % office
    print title.encode(setup.encoding)
    print "=" * len(title)
    for entry in root.findall('atom:entry', namespaces=ns):
        row = entry.find('atom:title', ns).text.replace('buildings', '')
        print row.encode(setup.encoding)
