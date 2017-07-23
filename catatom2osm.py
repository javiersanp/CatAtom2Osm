# -*- coding: utf-8 -*-
"""
Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services to OSM files
"""
import os
import math
import re
import codecs
import json
import logging
import zipfile
from collections import defaultdict

from qgis.core import *
from osgeo import gdal

import csvtools
import download
import hgwnames
import layer
import osm
import osmxml
from osmxml import etree
import setup
import translate

log = logging.getLogger(setup.app_name + "." + __name__)
if setup.silence_gdal:
    gdal.PushErrorHandler('CPLQuietErrorHandler')


class QgsSingleton(QgsApplication):
    """Keeps a unique instance of QGIS for the application (and tests)"""
    _qgs = None
    
    def __new__(cls):
        if QgsSingleton._qgs is None:
            # Init qGis API
            QgsSingleton._qgs = QgsApplication([], False)
            QgsSingleton._qgs.initQgis()
            # sets GDAL to convert xlink references to fields but not resolve
            gdal.SetConfigOption('GML_ATTRIBUTES_TO_OGR_FIELDS', 'YES')
            gdal.SetConfigOption('GML_SKIP_RESOLVE_ELEMS', 'ALL')
        return QgsSingleton._qgs

    
class CatAtom2Osm:
    """
    Main application class for a tool to convert the data sets from the 
    Spanish Cadastre ATOM Services to OSM files.
    
    Attributes:
        path (str): Directory where the source files are located.
        zip_code (str): Five digits (GGMMM) Zip Code matching Province (GG) 
                       and Municipality (MMM) codes.
        qgs (QgsApplication): Instance of qGis API.
    """
    
    def __init__(self, a_path, options):
        """
        Constructor.
        
        Args:
            a_path (str): Directory where the source files are located.
            options (dict): Dictionary of options.
        """
        # Gets path of data directory and Zip Code value
        self.options = options
        m = re.match("^\d{5}$", os.path.split(a_path)[-1])
        if not m:
            raise ValueError(_("Last directory name must be a 5 digits ZIP code"))
        self.path = a_path
        self.zip_code = m.group()
        self.prov_code = self.zip_code[0:2]
        if self.prov_code not in setup.valid_provinces:
            raise ValueError(_("Province code '%s' don't exists") % self.prov_code)
        if not os.path.exists(a_path):
            os.makedirs(a_path)
        if not os.path.isdir(a_path):
            raise IOError(_("Not a directory: '%s'") % a_path)
        self.qgs = QgsSingleton()
        log.debug(_("Initialized QGIS API"))
        self.address_gml = None

    def run(self):
        """Launches the app"""
        
        self.start()
        if self.is_new: return
        for zoning in (self.urban_zoning, self.rustic_zoning):
            for zone in zoning.getFeatures():
                log.info(_("Processing %s '%s' of '%s'"), 
                    zone['levelName'].encode('utf-8').lower().translate(None, '(1:) '), 
                    zone['label'], zoning.name().encode('utf-8'))
                building = layer.ConsLayer(source_date = self.building_gml.source_date)
                building.append(self.building_gml, zone, self.processed)
                task = set()
                if building.featureCount() == 0:
                    log.info(_("Zone '%s' is empty"), zone['label'].encode('utf-8'))
                else:
                    for feat in building.getFeatures():
                        self.processed.add(feat['localId'])
                        task.add(feat['localId'])
                    temp_address = None
                    if self.options.address:
                        temp_address = layer.BaseLayer(path="Point", baseName="address",
                            providerLib="memory")
                        temp_address.source_date = False
                        temp_address.append(self.address, task)
                        temp_address.reproject()
                    building.reproject()
                    self.write_task(zoning, building, temp_address)
                    self.building_osm = self.osm_from_layer(building, 
                        translate.building_tags, data=self.building_osm)
                    del temp_address
                del building
        self.write_osm(self.building_osm, 'building.osm')
        if self.options.address:
            address_osm = self.osm_from_layer(self.address, translate.address_tags)
            self.write_osm(address_osm, 'address.osm')
        return
        
        if self.options.building or self.options.tasks:
            building_gml = self.read_gml_layer("building")
            building = layer.ConsLayer(source_date = building_gml.source_date)
            building.append(building_gml)
            del building_gml
            part_gml = self.read_gml_layer("buildingpart")
            building.append(part_gml)
            del part_gml
            other_gml = self.read_gml_layer("otherconstruction", True)
            if other_gml:
                building.append(other_gml)
                del other_gml
            else:
                log.info(_("The layer '%s' is empty"), 'otherconstruction')
            if log.getEffectiveLevel() == logging.DEBUG:
                self.export_layer(building, 'building.shp')
            building.remove_outside_parts()
            building.explode_multi_parts()
            building.remove_parts_below_ground()
            if self.options.tasks:
                building.set_tasks(self.urban_zoning, self.rustic_zoning)
            building.clean()
            if self.options.address:
                building.move_address(address)
            building.check_levels_and_area()
            building.reproject()
            if log.getEffectiveLevel() == logging.DEBUG:
                self.export_layer(building, 'building.geojson', 'GeoJSON')
            building_osm = self.osm_from_layer(building, translate.building_tags)
            current_bu_osm = self.get_building()
            building.conflate(current_bu_osm)
            self.write_osm(current_bu_osm, 'current_building.osm')

        address_osm = None
        if self.options.address: 
            address.reproject()
            address_osm = self.osm_from_layer(address, translate.address_tags)

        if self.options.building: 
            if self.options.address:
                self.merge_address(building_osm, address_osm)
            self.write_osm(building_osm, "building.osm")
        elif self.options.tasks:
            self.split_building_in_tasks(building, address_osm)

        if self.options.address: 
            self.write_osm(address_osm, "address.osm")

        if self.options.zoning:
            self.urban_zoning.clean()
            self.rustic_zoning.clean()
            self.urban_zoning.reproject()
            self.rustic_zoning.reproject()
            self.export_layer(self.urban_zoning, 'urban_zoning.geojson', 'GeoJSON')
            self.export_layer(self.rustic_zoning, 'rustic_zoning.geojson', 'GeoJSON')
            if log.getEffectiveLevel() == logging.DEBUG:
                self.export_layer(self.urban_zoning, 'urban_zoning.shp')
                self.export_layer(self.urban_zoning, 'rustic_zoning.shp')

        if self.options.parcel:
            parcel = layer.ParcelLayer(source_date = building_gml.source_date)
            parcel_gml = self.read_gml_layer("cadastralparcel")
            parcel.append(parcel_gml)
            del parcel_gml
            parcel.reproject()
            parcel_osm = self.osm_from_layer(parcel)
            self.write_osm(parcel_osm, "parcel.osm")
            if log.getEffectiveLevel() == logging.DEBUG:
                self.export_layer(parcel, 'parcel.geojson', 'GeoJSON')
                self.export_layer(parcel, 'parcel.shp')

    def start(self):
        log.info(_("Start processing '%s'"), self.zip_code)
        if not hgwnames.fuzz:
            log.warning(_("Failed to import FuzzyWuzzy. "
                "Install requeriments for address conflation."))
        self.get_boundary()
        self.get_zoning()
        self.is_new = False
        if self.options.address:
            self.read_address()
            self.get_highway()
            self.get_translations()
            self.address.translate_field('TN_text', self.highway_names)
            if self.is_new:
                self.address.reproject()
                address_osm = self.osm_from_layer(self.address, translate.address_tags)
                self.write_osm(address_osm, "address.osm")
                log.info(_("The translation file '%s' have been writen in "
                    "'%s'"), 'highway_names.csv', self.path)
                log.info(_("Please, check it and run again"))
                return
            current_address = self.get_current_ad_osm()
            self.address.conflate(current_address)
            self.address_osm = osm.Osm()
        self.building_gml = self.read_gml_layer("building")
        self.building_osm = osm.Osm()
        self.processed = set()
        self.utaskn = self.rtaskn = 1

    def exit(self):
        for propname in dir(self):
            if isinstance(getattr(self, propname), QgsVectorLayer):
                delattr(self, propname)
        log.info(_("Finished!"))
        log.warning(_("Only for testing purposses. Don't upload any result to OSM"))
        if hasattr(self, 'qgs'):
            self.qgs.exitQgis()
        
    def get_gml_date(self, md_path, zip_path=""):
        """Get the source file production date from the metadata."""
        if os.path.exists(md_path):
            text = open(md_path, 'r').read()
        else:
            zip = zipfile.ZipFile(zip_path)
            text = zip.read(os.path.basename(md_path))
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

    def get_crs_from_gml(self, gml_path, zip_path=""):
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
            zip = zipfile.ZipFile(zip_path)
            text = zip.read(os.path.basename(gml_path))
        root = etree.fromstring(text)
        is_empty = len(root) == 0 or len(root[0]) == 0
        crs_ref = None
        if not is_empty:
            crs_ref = int(root.find('.//*[@srsName]').get('srsName').split(':')[-1])
        crs = QgsCoordinateReferenceSystem(crs_ref)
        return (is_empty, crs)
        
    def read_gml_layer(self, layername, allow_empty=False):
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
        if layername in ['building', 'buildingpart', 'otherconstruction']:
            group = 'BU'
        elif layername in ['cadastralparcel', 'cadastralzoning']:
            group = 'CP'
        elif layername in ['address', 'thoroughfarename', 'postaldescriptor', 
                'adminunitname']:
            group = 'AD' 
        else:
            raise ValueError(_("Unknow layer name '%s'") % layername)
        url = setup.prov_url[group] % (self.prov_code, self.prov_code)
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
        if not os.path.exists(zip_path) and (not os.path.exists(gml_path) or force_zip):
            self.get_atom_file(url)
        gml_date = self.get_gml_date(md_path, zip_path)
        (is_empty, crs) = self.get_crs_from_gml(gml_path, zip_path)
        if is_empty:
            if not allow_empty:
                raise IOError(_("The layer '%s' is empty") % gml_path)
            else:
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
    
    def export_layer(self, layer, filename, driver_name='ESRI Shapefile'):
        """
        Export a vector layer.
        
        Args:
            layer (QgsVectorLayer): Source layer.
            filename (str): Output filename.
            driver_name (str): Defaults to ESRI Shapefile.
        """
        out_path = os.path.join(self.path, filename)
        if layer.export(out_path, driver_name):
            log.info(_("Generated '%s'"), filename)
        else:
            raise IOError(_("Failed to write layer: '%s'") % filename)
        
    
    def osm_from_layer(self, layer, tags_translation=translate.all_tags, 
            data=None, upload='never'):
        """
        Create a Osm data set from a vector layer.

        Args:
            layer (QgsVectorLayer): Source layer.
            tags_translation (function): Function to translate fields to tags. 
                By defaults convert all fields.
            upload (str): upload attribute of the osm dataset, default 'never'

        Returns:
            Osm: OSM data set
        """
        if data is None:
            data = osm.Osm(upload)
        for feature in layer.getFeatures(): 
            geom = feature.geometry()
            e = None
            if geom.wkbType() == QGis.WKBPolygon:
                pol = geom.asPolygon()
                if len(pol) == 1:
                    e = data.Way(pol[0])
                else:
                    e = data.Polygon(pol)
            elif geom.wkbType() == QGis.WKBMultiPolygon:
                e = data.MultiPolygon(geom.asMultiPolygon())
            elif geom.wkbType() == QGis.WKBPoint:
                e = data.Node(geom.asPoint())
            else:
                log.warning(_("Detected a %s geometry in the '%s' layer"), 
                    geom.wkbType(), layer.name().encode('utf-8'))
            if e: e.tags.update(tags_translation(feature))
        for (key, value) in setup.changeset_tags.items():
            data.tags[key] = value
        if layer.source_date:
            data.tags['source:date'] = layer.source_date
        log.info(_("Loaded %d nodes, %d ways, %d relations from '%s' layer"), 
            len(data.nodes), len(data.ways), len(data.relations), 
            layer.name().encode('utf-8'))
        return data
        
    def read_osm(self, ql, filename):
        """
        Reads a OSM data set from a OSM XML file. If the file not exists, 
        downloads data from url
        
        Args:
            ql (str): Query to put in the url 
            filename (str): File to read/write
        
        Returns
            Osm: OSM data set
        """
        if self.boundary_id:
            query = setup.xml_query % ('area(3600{id})->.mun;' + ql)
            url = query.format(id=self.boundary_id, bb='area.mun')
        else:
            query = setup.xml_query % ql
            url = query.format(bb=self.boundary_bbox)
        osm_path = os.path.join(self.path, filename)
        if not os.path.exists(osm_path):
            log.info(_("Downloading '%s'") % filename)
            download.wget(url, osm_path)
        tree = etree.parse(osm_path)
        data = osmxml.deserialize(tree.getroot())
        if len(data.elements) == 0:
            raise IOError(_("No OSM data were obtained for '%s'") % filename)
        log.info(_("Read '%s': %d nodes, %d ways, %d relations"), 
            filename, len(data.nodes), len(data.ways), len(data.relations))
        return data

    def write_osm(self, data, filename):
        """
        Generates a OSM XML file for a OSM data set.

        Args:
            data (Osm): OSM data set
            filename (str): output filename
        """
        for e in data.elements:
            if 'ref' in e.tags:
                del e.tags['ref']
        osm_path = os.path.join(self.path, filename)
        data.merge_duplicated()
        with codecs.open(osm_path,"w", "utf-8") as file_obj:
            file_obj.write("<?xml version='1.0' encoding='UTF-8'?>\n")
            file_obj.write(osmxml.serialize(data))
            file_obj.close()
        log.info(_("Generated '%s': %d nodes, %d ways, %d relations"), 
            filename, len(data.nodes), len(data.ways), len(data.relations))

    def get_zoning(self):
        """
        Reads cadastralzoning and splits in 'MANZANA' (urban) and 'POLIGONO' 
        (rustic)
        """
        zoning_gml = self.read_gml_layer("cadastralzoning")
        self.urban_zoning = layer.ZoningLayer(baseName='urbanzoning')
        self.rustic_zoning = layer.ZoningLayer(baseName='rusticzoning')
        urban_query = lambda feat, kwargs: feat['levelName'][3] == 'M' # "(1:MANZANA )"
        rustic_query = lambda feat, kwargs: feat['levelName'][3] == 'P' # "(1:POLIGONO )"
        self.urban_zoning.append(zoning_gml, query=urban_query)
        self.rustic_zoning.append(zoning_gml, query=rustic_query)
        del zoning_gml
        self.urban_zoning.explode_multi_parts()
        self.rustic_zoning.explode_multi_parts()
        self.urban_zoning.merge_adjacents()

    def read_address(self):
        """Reads Address GML dataset"""
        address_gml = self.read_gml_layer("address")
        if address_gml.fieldNameIndex('component_href') == -1:
            address_gml = self.read_gml_layer("address", force_zip=True)
            if address_gml.fieldNameIndex('component_href') == -1:
                raise IOError(_("Could not resolve joined tables for the "
                    "'%s' layer") % address_gml.name())
        adminunitname = self.read_gml_layer("adminunitname")
        postaldescriptor = self.read_gml_layer("postaldescriptor")
        thoroughfarename = self.read_gml_layer("thoroughfarename")
        self.address = layer.AddressLayer(source_date = address_gml.source_date)
        self.address.append(address_gml)
        self.address.join_field(adminunitname, 'AU_id', 'gml_id', ['text'], 'AU_')
        self.address.join_field(postaldescriptor, 'PD_id', 'gml_id', ['postCode'])
        self.address.join_field(thoroughfarename, 'TN_id', 'gml_id', ['text'], 'TN_')

    def merge_address(self, building_osm, address_osm):
        """
        Copy address from address_osm to building_osm

        Args:
            building_osm (Osm): OSM data set with addresses
            address_osm (Osm): OSM data set with buildings
        """
        if 'source:date' in address_osm.tags:
            building_osm.tags['source:date:addr'] = address_osm.tags['source:date']
        address_index = {}
        for ad in address_osm.nodes:
            address_index[ad.tags['ref']] = ad
        building_index = defaultdict(list)
        for bu in building_osm.elements:
            if 'ref' in bu.tags:
                building_index[bu.tags['ref']].append(bu)
        for (ref, group) in building_index.items():
            if ref in address_index:
                ad = address_index[ref]
                if len(group) > 1:
                    r = building_osm.Relation()
                    r.tags.update(ad.tags)
                    r.tags['type'] = 'multipolygon'
                    for bu in group:
                        if isinstance(bu, osm.Relation):
                            map(lambda m: r.append(m.element, 'outer'),  
                                [m for m in bu.members if m.role == 'outer'])
                        else:
                            r.append(bu, 'outer')
                elif len(group) == 1:
                    bu = group[0]
                    if 'entrance' in ad.tags:
                        footprint = bu if isinstance(bu, osm.Way) \
                            else bu.members[0].element
                        entrance = footprint.search_node(ad.x, ad.y)
                        if entrance:
                            entrance.tags.update(ad.tags)
                    else:
                        bu.tags.update(ad.tags)
                    
    def write_task(self, zoning, building, address=None):
        """Generates osm file for a task"""
        if zoning is self.urban_zoning:
            fn = 'u%05d.osm' % self.utaskn
            self.utaskn += 1
        else:
            fn = 'r%03d.osm' % self.rtaskn
            self.rtaskn += 1
        base_path = os.path.join(self.path, 'tasks')
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        task_path = os.path.join('tasks', fn)
        task_osm = self.osm_from_layer(building, translate.building_tags, upload='yes')
        if address is not None:
            address_osm = self.osm_from_layer(address, translate.address_tags)
            self.merge_address(task_osm, address_osm)
        self.write_osm(task_osm, task_path)

    def get_translations(self):
        """
        If there exists the configuration file 'highway_types.csv', read it, 
        else write one with default values. If don't exists the translations file 
        'highway_names.csv', creates one parsing names_layer, else reads and returns
        it as a dictionary.
        
        * 'highway_types.csv' is List of osm elements in json formatlocated in the application path and contains 
          translations from abreviaturs to full types of highways.

        * 'highway_names.csv' is located in the outputh folder and contains 
          corrections for original highway names.
        """
        highway_types_path = os.path.join(setup.app_path, 'highway_types.csv')
        if not os.path.exists(highway_types_path):
            csvtools.dict2csv(highway_types_path, setup.highway_types)
        else:
            csvtools.csv2dict(highway_types_path, setup.highway_types)
        highway_names_path = os.path.join(self.path, 'highway_names.csv')
        if not os.path.exists(highway_names_path):
            self.highway_names = self.address.get_highway_names(self.highway)
            csvtools.dict2csv(highway_names_path, self.highway_names)
            self.is_new = True
        else:
            self.highway_names = csvtools.csv2dict(highway_names_path, {})
            self.is_new = False

    def get_highway(self):
        """Gets OSM highways needed for street names conflation"""
        ql = 'way["highway"]["name"]({bb});' \
             'relation["highway"]["name"]({bb});' \
             'way["place"="square"]["name"]({bb});' \
             'relation["place"="square"]["name"]({bb});'
        highway_osm = self.read_osm(ql, 'current_highway.osm')
        self.highway = layer.HighwayLayer()
        self.highway.read_from_osm(highway_osm)
        del highway_osm
        self.highway.reproject(self.address.crs())

    def get_current_ad_osm(self):
        """Gets OSM address for address conflation"""
        ql = 'node["addr:street"]["addr:housenumber"]({bb});' \
             'way["addr:street"]["addr:housenumber"]({bb});' \
             'relation["addr:street"]["addr:housenumber"]({bb});' \
             'node["addr:place"]["addr:housenumber"]({bb});' \
             'way["addr:place"]["addr:housenumber"]({bb});' \
             'relation["addr:place"]["addr:housenumber"]({bb});'
        address_osm = self.read_osm(ql, 'current_address.osm')
        current_address = set()
        for d in address_osm.elements:
            if 'addr:street' in d.tags:
                current_address.add(d.tags['addr:street'] + d.tags['addr:housenumber'])
            elif 'addr:place' in d.tags:
                current_address.add(d.tags['addr:place'] + d.tags['addr:housenumber'])
        return current_address

    def get_building(self):
        """Gets OSM buildings for building conflation"""
        ql = 'way["building"]({bb});relation["building"]({bb});'
        current_bu_osm = self.read_osm(ql, 'current_building.osm')
        return current_bu_osm

    def get_boundary(self):
        """
        Gets the bounding box of the municipality from the ATOM service
        and the id of the OSM administrative boundary from Overpass
        """
        url = setup.prov_url['BU'] % (self.prov_code, self.prov_code)
        response = download.get_response(url)
        root = etree.fromstring(response.content)
        ns = {
            'atom': 'http://www.w3.org/2005/Atom', 
            'georss': 'http://www.georss.org/georss'
        }
        entry = root.xpath("atom:entry/atom:title[contains(text(), '%s')]/"
            "parent::*" % self.zip_code, namespaces=ns)[0]
        mun = entry.find('atom:title', ns).text.replace('buildings', '').strip()[6:]
        poly = entry.find('georss:polygon', ns).text
        lat = [float(lat) for lat in poly.strip().split(' ')[::2]]
        lon = [float(lon) for lon in poly.strip().split(' ')[1:][::2]]
        bbox_bltr = [min(lat)-0.1, max(lon)-0.1, min(lat)+0.1, max(lon)+0.1]
        bbox = ','.join([str(i) for i in bbox_bltr])
        response = download.get_response(setup.boundary_query % bbox)
        data = json.loads(response.text)
        self.boundary_id = None
        self.boundary_name = mun
        self.boundary_bbox = bbox
        matching = hgwnames.dsmatch(mun, data['elements'], lambda e: e['tags']['name'])
        if matching:
            self.boundary_id = matching['id']
            self.boundary_name = matching['tags']['name']
            log.info(_("Municipality: '%s'"), self.boundary_name)
        else:
            log.warning(_("Failed to find administrative boundary, falling back to bounding box"))


def list_municipalities(prov_code):
    """Get from the ATOM services a list of municipalities for a given province"""
    url = setup.prov_url['BU'] % (prov_code, prov_code)
    response = download.get_response(url)
    root = etree.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    office = root.find('atom:title', ns).text.split('Office ')[1]
    title = _("Territorial office %s") % office
    print
    print title
    print "=" * len(title)
    for entry in root.xpath('atom:entry', namespaces=ns):
        row = entry.find('atom:title', ns).text.replace('buildings', '')
        print row

