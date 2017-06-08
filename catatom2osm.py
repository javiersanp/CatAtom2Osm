# -*- coding: utf-8 -*-
"""
Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services to OSM files
"""
import os
import math
import re
import codecs
import logging
import zipfile

from qgis.core import (QGis, QgsApplication, QgsVectorLayer, 
    QgsCoordinateReferenceSystem)
from osgeo import gdal

import setup
import layer
import translate
import osmxml
import osm
import download

log = logging.getLogger(setup.app_name + "." + __name__)
if setup.silence_gdal:
    gdal.PushErrorHandler('CPLQuietErrorHandler')

try:
    from lxml import etree
    log.debug(_("Running with lxml.etree"))
except ImportError:
    try:
        import xml.etree.ElementTree as etree
        log.debug(_("Running with ElementTree on Python 2.5+"))
    except ImportError:
        try:
            import cElementTree as etree
            log.debug(_("Running with cElementTree"))
        except ImportError:
            try:
                import elementtree.ElementTree as etree
                log.debug(_("Running with ElementTree"))
            except ImportError:
                raise ImportError(_("Failed to import ElementTree from any known place"))


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
        m = re.match("\d{5}", os.path.split(a_path)[-1])
        if not m:
            raise ValueError(_("Directory name must begin with a 5 digits ZIP code"))
        self.path = a_path
        self.zip_code = m.group()
        self.prov_code = self.zip_code[0:2]
        if self.prov_code not in setup.valid_provinces:
            raise ValueError(_("Province code '%s' don't exists") % self.prov_code)
        if not os.path.exists(a_path):
            os.makedirs(a_path)
        if not os.path.isdir(a_path):
            raise IOError(_("Not a directory: '%s'") % a_path)
        # Init qGis API
        QgsApplication.setPrefixPath(setup.qgs_prefix_path, True)
        
        self.qgs = QgsApplication([], False)
        self.qgs.initQgis()
        # sets GDAL to convert xlink references to fields but not resolve
        gdal.SetConfigOption('GML_ATTRIBUTES_TO_OGR_FIELDS', 'YES')
        gdal.SetConfigOption('GML_SKIP_RESOLVE_ELEMS', 'ALL')
        log.debug(_("Initialized qGis API"))

    def run(self):
        """Launches the app"""
        building_gml = self.read_gml_layer("building")
        cat_crs = building_gml.crs()
        if self.options.zoning:        
            zoning_gml = self.read_gml_layer("cadastralzoning", cat_crs)
            (urban_zoning, rustic_zoning) = layer.ZoningLayer.clasify_zoning(zoning_gml)
            urban_zoning.explode_multi_parts()
            rustic_zoning.explode_multi_parts()
            urban_zoning.merge_adjacents()
            del zoning_gml
            urban_zoning.set_labels('%05d')
            rustic_zoning.set_labels('%03d')
        
        if self.options.building or self.options.tasks:
            building = layer.ConsLayer()
            building.append(building_gml)
            part_gml = self.read_gml_layer("buildingpart")
            building.append(part_gml)
            del part_gml
            other_gml = self.read_gml_layer("otherconstruction")
            building.append(other_gml)
            del other_gml
            building.explode_multi_parts()
            building.remove_parts_below_ground()
            if self.options.tasks:
                building.set_tasks(urban_zoning, rustic_zoning)
            if log.getEffectiveLevel() == logging.DEBUG:
                self.export_layer(building, 'building.shp')
            building.clean()
            building.reproject()
            if log.getEffectiveLevel() == logging.DEBUG:
                self.export_layer(building, 'building.geojson', 'GeoJSON')
        del building_gml

        if self.options.building: 
            building_osm = self.osm_from_layer(building, translate.building_tags)
            self.write_osm(building_osm, "building.osm")
            del building_osm
        elif self.options.tasks:
            self.split_building_in_tasks(building, urban_zoning, rustic_zoning)

        if self.options.zoning:
            urban_zoning.clean()
            rustic_zoning.clean()
            urban_zoning.reproject()
            rustic_zoning.reproject()
            self.export_layer(urban_zoning, 'urban_zoning.geojson', 'GeoJSON')
            self.export_layer(rustic_zoning, 'rustic_zoning.geojson', 'GeoJSON')
            if log.getEffectiveLevel() == logging.DEBUG:
                self.export_layer(urban_zoning, 'urban_zoning.shp')
                self.export_layer(urban_zoning, 'rustic_zoning.shp')

        if self.options.parcel:
            parcel = layer.ParcelLayer()
            parcel_gml = self.read_gml_layer("cadastralparcel", cat_crs)
            parcel.append(parcel_gml)
            del parcel_gml
            parcel.reproject()
            parcel_osm = self.osm_from_layer(parcel)
            self.write_osm(parcel_osm, "parcel.osm")
            if log.getEffectiveLevel() == logging.DEBUG:
                self.export_layer(parcel, 'parcel.geojson', 'GeoJSON')
                self.export_layer(parcel, 'parcel.shp')

        if self.options.address:
            address_gml = self.read_gml_layer("address")
            address = layer.AddressLayer()
            address.append(address_gml)
            thoroughfarename = self.read_gml_layer("thoroughfarename")
            adminunitname = self.read_gml_layer("adminunitname")
            postaldescriptor = self.read_gml_layer("postaldescriptor")
            address.join_field(thoroughfarename, 'TN_id', 'gml_id', ['text'], 'TN_')
            address.join_field(adminunitname, 'AU_id', 'gml_id', ['text'], 'AU_')
            address.join_field(postaldescriptor, 'PD_id', 'gml_id', ['postCode'])
            del thoroughfarename, adminunitname, postaldescriptor
            address.reproject()
            address_osm = self.osm_from_layer(address, translate.address_tags)
            self.write_osm(address_osm, "address.osm")
            if log.getEffectiveLevel() == logging.DEBUG:
                self.export_layer(address, 'address.geojson', 'GeoJSON')
                self.export_layer(address, 'address.shp')

    def exit(self):
        log.info(_("Finished!"))
        if hasattr(self, 'qgs'):
            self.qgs.exitQgis()
        
    def get_atom_file(self, url):
        """Given the url of a Cadastre ATOM service, tries to download the ZIP
        file for self.zip_code"""
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

    def get_crs_from_gml(self, zip_path, gml_path):
        print gml_path
        if os.path.exists(gml_path):
            text = open(gml_path, 'r').read()
            print "gml"
        else:
            zip = zipfile.ZipFile(zip_path)
            text = zip.read(os.path.basename(gml_path))
            print "zip"
        root = etree.fromstring(text)
        is_empty = len(root) == 0 or len(root[0]) == 0
        crs_ref = int(root.find('.//*[@srsName]').get('srsName').split(':')[-1])
        crs = QgsCoordinateReferenceSystem(crs_ref)
        return (is_empty, crs)
        
    def read_gml_layer(self, layername, crs=None):
        """
        Create a qgis vector layer for a Cadastre layername. Derives the GML 
        filename from layername. If it don't exists, try with the ZIP file, if
        it don't exists, try to download it.

        Args:
            layername (str): Short name of the Cadastre layer. Any of 
                'building', 'buildingpart', 'otherconstruction', 
                'cadastralparcel', 'cadastralzoning', 'address', 
                'thoroughfarename', 'postaldescriptor', 'adminunitname'
            crs (QgsCoordinateReferenceSystem): Source Crs. It's necessary 
                because parcel and zoning layers don't have it defined.

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
            return None
        url = setup.url[group] % (self.prov_code, self.prov_code)
        if group == 'AD':    
            gml_fn = ".".join((setup.fn_prefix, group, self.zip_code, 
                "gml|layername=%s" % layername))
        else:
            gml_fn = ".".join((setup.fn_prefix, group, self.zip_code, layername, "gml"))
        zip_fn = ".".join((setup.fn_prefix, group, self.zip_code, "zip"))
        gml_path = os.path.join(self.path, gml_fn)
        zip_path = os.path.join(self.path, zip_fn)
        if not os.path.exists(gml_path) and not os.path.exists(zip_path):
            self.get_atom_file(url)
        crs = self.get_crs_from_gml(zip_path, gml_path)
        print crs
        raise IOError()
        gml_layer = QgsVectorLayer(gml_path, layername, "ogr")
        if not gml_layer.isValid():
            gml_path = "/".join(('/vsizip', self.path, zip_fn, gml_fn))
            gml_layer = QgsVectorLayer(gml_path, layername, "ogr")
            if not gml_layer.isValid():
                if not gml_layer.isValid():
                    raise IOError(_("Failed to load layer: '%s'") % gml_path)
        if crs:
            gml_layer.setCrs(crs)
        log.info(_("Loaded %d features in the '%s' layer"), gml_layer.featureCount(), 
            gml_layer.name().encode('utf-8'))
        return gml_layer
    
    def export_layer(self, layer, filename, driver_name='ESRI Shapefile'):
        """
        Export a vector layer.
        
        Args:
            layer (QgsVectorLayer): Source layer.
            filename (str): Output filename.
            driver_name (str): Defaults to ESRI Shapefile.
        """
        out_path = os.path.join(self.path, filename)
        if not layer.export(out_path, driver_name):
            raise IOError(_("Failed to write layer: '%s'") % filename)
        
    
    def osm_from_layer(self, layer, tags_translation=translate.all_tags):
        """
        Create a Osm data set from a vector layer.

        Args:
            layer (QgsVectorLayer): Source layer.
            tags_translation (function): Function to translate fields to tags. 
                By defaults convert all fields.

        Returns:
            Osm: OSM data set
        """
        data = osm.Osm()
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
        log.info(_("Loaded %d nodes, %d ways, %d relations from '%s' layer"), 
            len(data.nodes), len(data.ways), len(data.relations), 
            layer.name().encode('utf-8'))
        return data
        
    def write_osm(self, data, filename):
        """
        Generates a OSM XML file for a Osm data set.

        Args:
            data (Osm): OSM data set
            filename (str): output filename
        """
        log.debug(_("Generating '%s'"), filename)
        osm_path = os.path.join(self.path, filename)
        data.new_indexes()
        with codecs.open(osm_path,"w", "utf-8") as file_obj:
            file_obj.write("<?xml version='1.0' encoding='UTF-8'?>\n")
            file_obj.write(osmxml.serialize(data))
            file_obj.close()

    def split_building_in_tasks(self, building, urban_zoning, rustic_zoning):
        """Generates osm files to import with the task manager"""
        base_path = os.path.join(self.path, 'tasks')
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        for zoning in (urban_zoning, rustic_zoning):
            to_clean = []
            for zone in zoning.getFeatures():
                label = zoning.name()[0].upper() + zone['label']
                task = layer.ConsLayer(baseName=label)
                query = lambda feat: feat['task'] == label
                task.append(building, rename={}, query=query)
                if task.featureCount() > 0:
                    task_path = os.path.join('tasks', label + '.osm')
                    task_osm = self.osm_from_layer(task, translate.building_tags)
                    self.write_osm(task_osm, task_path)
                else:
                    log.info(_("Zone '%s' is empty"), label.encode('utf-8'))
                    to_clean.append(zone.id())
            if to_clean:
                zoning.startEditing()
                zoning.writer.deleteFeatures(to_clean)
                zoning.commitChanges()

