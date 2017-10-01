# -*- coding: utf-8 -*-
"""
Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services to OSM files
"""
import os
import codecs
import logging
from collections import defaultdict, Counter, OrderedDict

from qgis.core import *
from osgeo import gdal

import catatom
import csvtools
import layer
import osm
import osmxml
import overpass
import setup
import translate
from compat import etree

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
    """

    def __init__(self, a_path, options):
        """
        Constructor.

        Args:
            a_path (str): Directory where the source files are located.
            options (dict): Dictionary of options.
        """
        self.options = options
        self.cat = catatom.Reader(a_path)
        self.path = self.cat.path
        self.zip_code = self.cat.zip_code
        self.qgs = QgsSingleton()
        log.debug(_("Initialized QGIS API"))
        self.debug = log.getEffectiveLevel() == logging.DEBUG
        self.fixmes = 0
        self.is_new = False

    def run(self):
        """Launches the app"""
        log.info(_("Start processing '%s'"), self.zip_code)
        self.get_zoning()
        if self.options.address:
            self.read_address()
            highway = self.get_highway()
            (highway_names, self.is_new) = self.get_translations(self.address, highway)
            self.address.translate_field('TN_text', highway_names)
            if self.is_new:
                self.options.taskslm = False
                self.options.tasks = False
                self.options.building = False
            elif not self.options.manual:
                current_address = self.get_current_ad_osm()
                self.address.conflate(current_address)
            self.address_osm = osm.Osm()
        if self.options.building or self.options.tasks or self.options.taskslm:
            self.get_building()
            #self.building_gml = self.cat.read("building")
            #self.part_gml = self.cat.read("buildingpart")
            #self.other_gml = self.cat.read("otherconstruction", True)
            self.building_osm = osm.Osm()
            if not self.options.manual:
                self.current_bu_osm = self.get_current_bu_osm()
            if self.options.taskslm:
                self.process_tasks(self.building)
            else:
                self.process_building()
        log.info(_("Finished!"))
        return
        if self.options.address:
            self.process_address()
        #if self.options.zoning:
        #    self.process_zoning()
        #del self.urban_zoning
        #del self.rustic_zoning
        if self.options.building:
            self.write_building()
        if self.options.parcel:
            self.process_parcel()
        self.end_messages()

    def get_building(self):
        """Merge building, parts and pools"""
        building_gml = self.cat.read("building")
        fn = os.path.join(self.path, 'building.shp')
        layer.ConsLayer.create_shp(fn, building_gml.crs())
        self.building = layer.ConsLayer(fn, providerLib='ogr', 
            source_date=building_gml.source_date)
        #self.building = layer.ConsLayer(source_date=self.building_gml.source_date)
        self.building.append(building_gml)
        del building_gml
        part_gml = self.cat.read("buildingpart")
        self.building.append(part_gml)
        del part_gml
        other_gml = self.cat.read("otherconstruction", True)
        if other_gml:
            self.building.append(other_gml)
        del other_gml

    def process_tasks(self, source):
        base_path = os.path.join(self.path, 'tasks')
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        rprocessed = set()
        rindex = QgsSpatialIndex(source.getFeatures())
        zone_processed = set()
        for rzone in self.rustic_zoning.getFeatures():
            poligono, refs = self.process_zone(rzone, rindex, rprocessed, source)
            if refs:
                rprocessed = rprocessed.union(refs)
                temp_address = None
                if self.options.address:
                    poligono.move_address(self.address)
                    temp_address = layer.BaseLayer(path="Point", baseName="address",
                        providerLib="memory")
                    temp_address.source_date = False
                    query = lambda f, kwargs: f['localId'].split('.')[-1] in kwargs['including']
                    temp_address.append(self.address, query=query, including=refs)
                    temp_address.reproject()
                uprocessed = set()
                uindex = QgsSpatialIndex(poligono.getFeatures())
                for uzone in self.urban_zoning.getFeatures():
                    if uzone.id() not in zone_processed:
                        if layer.is_inside(uzone, rzone):
                            manzana, refs = self.process_zone(uzone, uindex, uprocessed, poligono)
                            if refs:
                                zone_processed.add(uzone.id())
                                uprocessed = uprocessed.union(refs)
                                #manzana.reproject()
                                #self.write_task(self.urban_zoning, manzana, temp_address)
                            del manzana
                """
                poligono.reproject()
                if source.providerType() == 'ogr':
                    if not self.options.manual:
                        poligono.conflate(self.current_bu_osm, delete=False)
                    if self.options.building:
                        self.building_osm = poligono.to_osm(data=self.building_osm)
                """
                if uprocessed:
                    to_clean = [f.id() for f in poligono.getFeatures() \
                        if f['localId'].split('_')[0] in uprocessed]
                    poligono.writer.deleteFeatures(to_clean)
                #self.write_task(self.rustic_zoning, poligono, temp_address)
                del temp_address
                del uindex
            del poligono
        return
        if source.providerType() == 'ogr':
            if not self.options.manual:
                to_clean = []
                num_buildings = 0
                conflicts = 0
                for el in self.current_bu_osm.elements:
                    if 'building' in el.tags:
                        num_buildings += 1
                        if 'conflict' not in el.tags:
                            to_clean.append(el)
                        else:
                            conflicts += 1
                            del el.tags['conflict']
                for el in to_clean:
                    self.current_bu_osm.remove(el)
                if to_clean:
                    self.write_osm(self.current_bu_osm, 'current_building.osm')
                log.debug(_("Detected %d conflicts in %d buildings from OSM"), 
                    conflicts, num_buildings)
                del self.current_bu_osm
            del self.building_gml
            del self.part_gml
            del self.other_gml
        del rindex

    def process_zone(self, zone, index, processed, source):
        task = layer.ConsLayer(baseName=zone['label'],
            source_date = source.source_date)
        #if source.providerType() == 'memory':
        task.rename = {}
        refs = task.append_zone(source, zone, processed, index)
        """
        if task.featureCount() > 0:
            task.append_task(source, refs)
        else:
            task.append_task(self.part_gml, refs)
            if self.other_gml:
                task.append_task(self.other_gml, refs)
            task.remove_outside_parts()
            task.explode_multi_parts(getattr(self, 'address', False))
            task.remove_parts_below_ground()
            task.clean()
            task.check_levels_and_area(self.min_level, self.max_level)
        """
        return task, refs

    def process_address(self):
        if self.options.building:
            self.address.del_address(self.building_osm)
        self.address.reproject()
        address_osm = self.address.to_osm()
        del self.address
        if self.options.building:
            self.merge_address(self.building_osm, address_osm)
        self.write_osm(address_osm, 'address.osm')
        del address_osm

    def process_zoning(self):
        self.urban_zoning.clean()
        self.rustic_zoning.clean()
        self.urban_zoning.reproject()
        self.rustic_zoning.reproject()
        self.export_layer(self.urban_zoning, 'urban_zoning.geojson', 'GeoJSON')
        self.export_layer(self.rustic_zoning, 'rustic_zoning.geojson', 'GeoJSON')

    def process_building(self):
        """Process all buildings dataset"""
        #if self.debug: self.export_layer(building, 'building.shp')
        self.building.remove_outside_parts()
        self.building.explode_multi_parts(getattr(self, 'address', False))
        self.building.remove_parts_below_ground()
        self.building.clean()
        return
        if self.options.address:
            self.building.move_address(self.address)
        (self.max_level, self.min_level) = self.building.validate()
        if self.options.tasks:
            self.process_tasks(self.building)
        self.building.reproject()
        if not self.options.manual and self.building.conflate(self.current_bu_osm):
            self.write_osm(self.current_bu_osm, 'current_building.osm')
            del self.current_bu_osm
        self.building_osm = self.building.to_osm()

    def write_building(self):
        self.write_osm(self.building_osm, 'building.osm')
        for el in self.building_osm.elements:
            if 'fixme' in el.tags:
                self.fixmes += 1
        del self.building_osm

    def process_parcel(self):
        parcel_gml = self.cat.read("cadastralparcel")
        parcel = layer.ParcelLayer(source_date = parcel_gml.source_date)
        parcel.append(parcel_gml)
        del parcel_gml
        if self.debug: self.export_layer(self.parcel, 'parcel.shp')
        parcel.reproject()
        parcel_osm = parcel.to_osm()
        self.write_osm(parcel_osm, "parcel.osm")

    def end_messages(self):
        if self.options.tasks or self.options.building or self.options.taskslm:
            dlag = ', '.join(["%d: %d" % (l, c) for (l, c) in \
                OrderedDict(Counter(self.max_level.values())).items()])
            dlbg = ', '.join(["%d: %d" % (l, c) for (l, c) in \
                OrderedDict(Counter(self.min_level.values())).items()])
            log.info(_("Distribution of floors above ground %s"), dlag)
            log.info(_("Distribution of floors below ground %s"), dlbg)
        if self.fixmes:
            log.warning(_("Check %d fixme tags"), self.fixmes)
        if self.is_new:
            log.info(_("The translation file '%s' have been writen in "
                "'%s'"), 'highway_names.csv', self.path)
            log.info(_("Please, check it and run again"))
        else:
            log.info(_("Finished!"))
            log.warning(_("Only for testing purposses. Don't upload any result to OSM"))

    def exit(self):
        """Ends properly"""
        for propname in self.__dict__.keys():
            if isinstance(getattr(self, propname), QgsVectorLayer):
                delattr(self, propname)
        if hasattr(self, 'qgs'):
            self.qgs.exitQgis()

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

    def read_osm(self, ql, filename):
        """
        Reads a OSM data set from a OSM XML file. If the file not exists,
        downloads data from overpass using ql query

        Args:
            ql (str): Query to put in the url
            filename (str): File to read/write

        Returns
            Osm: OSM data set
        """
        osm_path = os.path.join(self.path, filename)
        if not os.path.exists(osm_path):
            log.info(_("Downloading '%s'") % filename)
            query = overpass.Query(self.cat.boundary_search_area).add(ql)
            query.download(osm_path)
        fo = open(osm_path, 'r')
        data = osmxml.deserialize(fo)
        if len(data.elements) == 0:
            log.warning(_("No OSM data were obtained from '%s'") % filename)
        else:
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
        with codecs.open(osm_path, "w", "utf-8") as file_obj:
            osmxml.serialize(file_obj, data)
        log.info(_("Generated '%s': %d nodes, %d ways, %d relations"),
            filename, len(data.nodes), len(data.ways), len(data.relations))

    def get_zoning(self):
        """
        Reads cadastralzoning and splits in 'MANZANA' (urban) and 'POLIGONO'
        (rustic)
        """
        zoning_gml = self.cat.read("cadastralzoning")
        self.urban_zoning = layer.ZoningLayer('u{:05}', baseName='urbanzoning')
        self.rustic_zoning = layer.ZoningLayer('r{:03}', baseName='rusticzoning')
        self.urban_zoning.append(zoning_gml, level='M')
        self.rustic_zoning.append(zoning_gml, level='P')
        self.cat.get_boundary(self.rustic_zoning)
        del zoning_gml
        self.urban_zoning.explode_multi_parts()
        self.rustic_zoning.explode_multi_parts()
        self.urban_zoning.add_topological_points()
        self.urban_zoning.merge_adjacents()
        self.rustic_zoning.task_filename = 'r%03d.osm'
        self.urban_zoning.task_filename = 'u%05d.osm'

    def read_address(self):
        """Reads Address GML dataset"""
        address_gml = self.cat.read("address")
        if address_gml.fieldNameIndex('component_href') == -1:
            address_gml = self.cat.read("address", force_zip=True)
            if address_gml.fieldNameIndex('component_href') == -1:
                raise IOError(_("Could not resolve joined tables for the "
                    "'%s' layer") % address_gml.name())
        postaldescriptor = self.cat.read("postaldescriptor")
        thoroughfarename = self.cat.read("thoroughfarename")
        self.address = layer.AddressLayer(source_date = address_gml.source_date)
        self.address.append(address_gml)
        self.address.join_field(postaldescriptor, 'PD_id', 'gml_id', ['postCode'])
        self.address.join_field(thoroughfarename, 'TN_id', 'gml_id', ['text'], 'TN_')
        if self.debug: self.export_layer(self.address, 'address.shp')

    def merge_address(self, building_osm, address_osm):
        """
        Copy address from address_osm to building_osm using 'ref' tag.

        If there exists one building with the same 'ref' that an address, copy
        the address tags to the building if isn't a 'entrace' type address or
        else to the entrance if there exist a node with the address coordinates
        in the building.

        If there exists many buildings withe the same 'ref' than an address,
        creates a multipolygon relation and copy the address tags to it. Each
        building will be a member with outer role in the relation if it's a way.
        If it's a relation, each outer member of it is aggregated to the address
        relation.

        Args:
            building_osm (Osm): OSM data set with addresses
            address_osm (Osm): OSM data set with buildings
        """
        if 'source:date' in address_osm.tags:
            building_osm.tags['source:date:addr'] = address_osm.tags['source:date']
        address_index = {}
        for ad in address_osm.nodes:
            address_index[ad.tags['ref']] = ad
        building_index = {}
        for bu in building_osm.elements:
            if 'ref' in bu.tags:
                building_index[bu.tags['ref']] = bu
        for (ref, bu) in building_index.items():
            if ref in address_index:
                ad = address_index[ref]
                if 'entrance' in ad.tags:
                    footprint = [bu] if isinstance(bu, osm.Way) \
                        else [m.element for m in bu.members if m.role == 'outer']
                    for w in footprint:
                        entrance = w.search_node(ad.x, ad.y)
                        if entrance:
                            entrance.tags.update(ad.tags)
                            entrance.tags.pop('ref', None)
                            break
                else:
                    bu.tags.update(ad.tags)

    def write_task(self, zoning, building, address=None):
        """Generates osm file for a task"""
        fn = zoning.task_filename % zoning.task_number
        zoning.task_number += 1
        base_path = os.path.join(self.path, 'tasks')
        task_path = os.path.join('tasks', fn)
        task_osm = building.to_osm(upload='yes')
        if address is not None:
            address_osm = address.to_osm(translate.address_tags)
            self.merge_address(task_osm, address_osm)
        self.write_osm(task_osm, task_path)

    def get_translations(self, address, highway):
        """
        If there exists the configuration file 'highway_types.csv', read it,
        else write one with default values. If don't exists the translations file
        'highway_names.csv', creates one parsing names_layer, else reads and returns
        it as a dictionary.

        * 'highway_types.csv' List of osm elements in json format located in the
          application path and contains translations from abreviaturs to full
          types of highways.

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
            highway.reproject(address.crs())
            highway_names = address.get_highway_names(highway)
            csvtools.dict2csv(highway_names_path, highway_names)
            is_new = True
        else:
            highway_names = csvtools.csv2dict(highway_names_path, {})
            is_new = False
        return (highway_names, is_new)

    def get_highway(self):
        """Gets OSM highways needed for street names conflation"""
        ql = ['way["highway"]["name"]',
              'relation["highway"]["name"]',
              'way["place"="square"]["name"]',
              'relation["place"="square"]["name"]']
        highway_osm = self.read_osm(ql, 'current_highway.osm')
        highway = layer.HighwayLayer()
        highway.read_from_osm(highway_osm)
        del highway_osm
        return highway

    def get_current_ad_osm(self):
        """Gets OSM address for address conflation"""
        ql = ['node["addr:street"]["addr:housenumber"]',
              'way["addr:street"]["addr:housenumber"]',
              'relation["addr:street"]["addr:housenumber"]',
              'node["addr:place"]["addr:housenumber"]',
              'way["addr:place"]["addr:housenumber"]',
              'relation["addr:place"]["addr:housenumber"]']
        address_osm = self.read_osm(ql, 'current_address.osm')
        current_address = set()
        w = 0
        for d in address_osm.elements:
            if 'addr:housenumber' not in d.tags:
                w += 1
            elif 'addr:street' in d.tags:
                current_address.add(d.tags['addr:street'] + d.tags['addr:housenumber'])
            elif 'addr:place' in d.tags:
                current_address.add(d.tags['addr:place'] + d.tags['addr:housenumber'])
        if w > 0:
            log.warning(_("There are %d address without house number in the OSM data"), w)
        return current_address

    def get_current_bu_osm(self):
        """Gets OSM buildings for building conflation"""
        ql = 'way["building"];relation["building"];'
        current_bu_osm = self.read_osm(ql, 'current_building.osm')
        return current_bu_osm

