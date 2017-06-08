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

log = logging.getLogger(setup.app_name + "." + __name__)
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
            log.info(_("Loaded %d features in the '%s' layer"), 
                urban_zoning.featureCount(), urban_zoning.name().encode('utf-8'))
            log.info(_("Loaded %d features in the '%s' layer"), 
                rustic_zoning.featureCount(), rustic_zoning.name().encode('utf-8'))
            (mp, np) = urban_zoning.explode_multi_parts()
            if mp:
                log.info(_("%d multi-polygons splited into %d polygons in "
                    "the '%s' layer"), mp, np, urban_zoning.name().encode('utf-8'))
            (ap, mp) = urban_zoning.merge_adjacents()
            if ap:
                log.info(_("%d adjacent polygons merged into %d polygons in "
                    "the '%s' layer"), ap, mp, urban_zoning.name().encode('utf-8'))
            (mp, np) = rustic_zoning.explode_multi_parts()
            if mp:
                log.info(_("%d multi-polygons splited into %d polygons in "
                    "the '%s' layer"), mp, np, rustic_zoning.name().encode('utf-8'))
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
            (mp, np) = building.explode_multi_parts()
            if mp:
                log.info(_("%d multi-polygons splited into %d polygons in "
                        "the '%s' layer"), mp, np, building.name().encode('utf-8'))
            tc = building.remove_parts_below_ground()
            if tc:
                log.info(_("Deleted %d building parts with no floors above ground"), tc)

            if self.options.tasks:
                log.info (_("Assigning task number to each construction"))
                nt = building.featureCount() - \
                    building.set_tasks(urban_zoning, rustic_zoning)
                if nt:
                    log.warning(_("%d features unassigned to a task in "
                        "the '%s' layer"), nt, building.name().decode('utf-8'))
                else:
                    log.info(_("All features assigned to tasks in "
                        "the '%s' layer"), building.name().decode('utf-8'))
            if log.getEffectiveLevel() == logging.DEBUG:
                self.export_layer(building, 'building.shp')
            self.clean_layer(building, add_topological_points=True)
            pm = building.merge_building_parts()
            if pm:
                log.info(_("Merged %d building parts to footprint"), pm)
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
            self.clean_layer(urban_zoning)
            self.clean_layer(rustic_zoning)
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
        log.info(_("Searching the url for the '%s' layer of '%s'..."), s.group(1), self.zip_code)
        response = download.get_response(url)
        s = re.search('http.+/%s.+zip' % self.zip_code, response.text)
        if not s:
            raise ValueError(_("Zip code '%s' don't exists") % self.zip_code)
        url = s.group(0)
        filename = url.split('/')[-1]
        out_path = os.path.join(self.path, filename)
        log.info(_("Downloading '%s'"), out_path)
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
                task.append(building, query=query)
                if task.featureCount() > 0:
                    task.reproject()
                    task_osm = self.osm_from_layer(task, translate.building_tags)
                    task_path = os.path.join('tasks', label + '.osm')
                    self.write_osm(task_osm, task_path)
                else:
                    log.info(_("Zone '%s' is empty"), label.encode('utf-8'))
                    to_clean.append(zone.id())
            if to_clean:
                zoning.startEditing()
                zoning.writer.deleteFeatures(to_clean)
                zoning.commitChanges()

    def clean_layer(self, layer, add_topological_points=False):
        """Merge duplicated vertices and simplify layer
        
        Args:
            layer(PolygonLayer): Layer to simplify
            add_topological_points(bool): True (default) to add topological points
        """
        dupes = layer.merge_duplicates()
        if dupes:
            log.info(_("Merged %d close vertices in the '%s' layer"), dupes, 
                layer.name().encode('utf-8'))
        (dv, bg) = layer.clean_duplicated_nodes_in_polygons()
        if dv:
            log.info(_("Merged %d duplicated vertices of polygons in "
                "the '%s' layer"), dv, layer.name().encode('utf-8'))
        if bg:
            log.info(_("Deleted %d invalid geometries in the '%s' layer"),
                bg, layer.name().encode('utf-8'))
        if add_topological_points:
            tp = layer.add_topological_points()
            if tp:
                log.info (_("Created %d topological points in the '%s' layer"), 
                    tp, layer.name().encode('utf-8'))
        killed = layer.simplify()
        if killed:
            log.info(_("Simplified %d vertices in the '%s' layer"), killed, 
                layer.name().encode('utf-8'))
    
