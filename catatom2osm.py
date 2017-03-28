# -*- coding: utf-8 -*-
"""
Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services to OSM files
"""
import os
import math
import re
import codecs
import logging

from qgis.core import (QGis, QgsApplication, QgsVectorLayer)
from osgeo import gdal

import setup
import layer
import translate
import osmxml
import osm
import download

log = logging.getLogger(setup.app_name + ".catatom2osm")
if setup.silence_gdal:
    gdal.PushErrorHandler('CPLQuietErrorHandler')


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
            raise ValueError("Directory name must begin with a 5 digits ZIP code")
        self.path = a_path
        self.zip_code = m.group()
        self.prov_code = self.zip_code[0:2]
        if self.prov_code not in setup.valid_provinces:
            raise ValueError("Province code %s don't exists" % self.prov_code)
        if not os.path.exists(a_path):
            os.makedirs(a_path)
        if not os.path.isdir(a_path):
            raise IOError("Not a directory: '%s'" % a_path)
        # Init qGis API
        QgsApplication.setPrefixPath(setup.qgs_prefix_path, True)
        
        self.qgs = QgsApplication([], False)
        self.qgs.initQgis()
        # sets GDAL to convert xlink references to fields but not resolve
        gdal.SetConfigOption('GML_ATTRIBUTES_TO_OGR_FIELDS', 'YES')
        gdal.SetConfigOption('GML_SKIP_RESOLVE_ELEMS', 'ALL')
        log.debug("Initialized qGis API")

    def run(self):
        """Launches the app"""
        building = layer.ConsLayer()
        building_gml = self.read_gml_layer("building")
        building.append(building_gml)
        del building_gml

        part_gml = self.read_gml_layer("buildingpart")
        building.append(part_gml)
        del part_gml
        
        other_gml = self.read_gml_layer("otherconstruction")
        building.append(other_gml)
        del other_gml

        (mp, np) = building.explode_multi_parts()
        if mp:
            log.info("%d multipart buildings splited in %d parts", mp, np)

        tc = building.remove_parts_below_ground()
        if tc:
            log.info("Deleted %d building parts with no floors above ground", tc)
        
        if log.getEffectiveLevel() == logging.DEBUG:
            self.export_layer(building, 'building.shp')

        dupes = building.merge_duplicates()
        if dupes:
            log.info("Merged %d duplicated vertexs in building", dupes)

        consecutives = building.clean_duplicated_nodes_in_polygons()
        if consecutives:
            log.info("Merged %d duplicated vertexs in polygons", dupes)

        tp = building.add_topological_points()
        if tp:
            log.info ("Created %d topological points in building", tp)
        
        killed = building.simplify()
        if killed:
            log.info("Simplified %d vertexs in building", killed)

        pm = building.merge_building_parts()
        if pm:
            log.info("Merged %d building parts to footprint", pm)

        building.reproject()
        building_osm = self.osm_from_layer(building, translate.building_tags)
        self.write_osm(building_osm, "building.osm")
        
        if self.options.parcel:
            parcel = layer.ParcelLayer()
            parcel_gml = self.read_gml_layer("cadastralparcel", building.crs())
            parcel.append(parcel_gml)
            del parcel_gml
            parcel.reproject()
            self.export_layer(parcel, 'parcel.geojson', 'GeoJSON')
            parcel_osm = self.osm_from_layer(parcel)
            self.write_osm(parcel_osm, "parcel.osm")
            if log.getEffectiveLevel() == logging.DEBUG:
                self.export_layer(parcel, 'parcel.shp')

        if self.options.zoning:
            zoning = layer.ZoningLayer()
            zoning_gml = self.read_gml_layer("cadastralzoning", building.crs())
            zoning.append(zoning_gml)
            del zoning_gml
            zoning.reproject()
            self.export_layer(zoning, 'zoning.geojson', 'GeoJSON')
            zoning_osm = self.osm_from_layer(zoning)
            self.write_osm(zoning_osm, "zoning.osm")
            if log.getEffectiveLevel() == logging.DEBUG:
                self.export_layer(zoning, 'zoning.shp')
        
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
                self.export_layer(address, 'address.shp')

    def __del__(self):
        log.info("Finished!")
        if hasattr(self, 'qgs'):
            self.qgs.exitQgis()
        
    def get_atom_file(self, url):
        """Given the url of a Cadastre ATOM service, tries to download the ZIP
        file for self.zip_code"""
        s = re.search('INSPIRE/(\w+)/', url)
        log.info("Searching for %s %s url...", self.zip_code, s.group(1))
        response = download.get_response(url)
        s = re.search('http.+/%s.+zip' % self.zip_code, response.text)
        if not s:
            raise ValueError("Zip code %s don't exists" % self.zip_code)
        url = s.group(0)
        filename = url.split('/')[-1]
        out_path = os.path.join(self.path, filename)
        log.info("Downloading %s", out_path)
        download.wget(url, out_path)

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
            url = setup.url_bu % (self.prov_code, self.prov_code)
        elif layername in ['cadastralparcel', 'cadastralzoning']:
            group = 'CP'
            url = setup.url_cp % (self.prov_code, self.prov_code)
        elif layername in ['address', 'thoroughfarename', 'postaldescriptor', 
                'adminunitname']:
            group = 'AD' 
            url = setup.url_ad % (self.prov_code, self.prov_code)
        else:
            return None
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
        gml_layer = QgsVectorLayer(gml_path, layername, "ogr")
        if not gml_layer.isValid():
            gml_path = "/".join(('/vsizip', self.path, zip_fn, gml_fn))
            gml_layer = QgsVectorLayer(gml_path, layername, "ogr")
            if not gml_layer.isValid():
                if not gml_layer.isValid():
                    raise IOError("Failed to load layer: '%s'" % gml_path)
        if crs:
            gml_layer.setCrs(crs)
        log.info("Loaded %d features in %s layer", gml_layer.featureCount(), 
            gml_layer.name())
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
            raise IOError("Failed to write layer: '%s'" % filename)
        
    
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
                log.warning("Detected a %s geometry in %s", geom.wkbType(), layer.name())
            if e: e.tags.update(tags_translation(feature))
        log.info("Loaded %d nodes, %d ways, %d relations from %s layer", 
            len(data.nodes), len(data.ways), len(data.relations), layer.name())
        return data
        
    def write_osm(self, data, filename):
        """
        Generates a OSM XML file for a Osm data set.

        Args:
            data (Osm): OSM data set
            filename (str): output filename
        """
        log.debug("Generating %s", filename)
        osm_path = os.path.join(self.path, filename)
        data.new_indexes()
        with codecs.open(osm_path,"w", "utf-8") as file_obj:
            file_obj.write("<?xml version='1.0' encoding='UTF-8'?>\n")
            file_obj.write(osmxml.serialize(data))
            file_obj.close()

