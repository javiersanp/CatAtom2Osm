"""Benchmarking tests"""
import timeit
import random
from collections import defaultdict, Counter
from lxml import etree
from qgis.core import *

import hgwnames
import main
import layer
import osmxml
from catatom2osm import QgsSingleton
qgs = QgsSingleton()

N = 1
MS = 1000
BASEPATH = '/home/javier/temp/catastro/'

class BaseTimer(object):

    def test(self, func):
        p = func.__name__
        if p.startswith('test_'): p = p[5:]
        t = timeit.timeit(func, number=N) * MS
        print self.obj.__class__.__name__ + '.' + p + ': ' + str(t)
    
    def run(self):
        set_up = None
        for p in dir(self):
            if p == 'set_up':
                set_up = getattr(self, p)
        for p in dir(self):
            if p.startswith('test_'):
                if set_up:
                    set_up()
                self.test(getattr(self, p))

class TimerBaseLayer(BaseTimer):

    def __init__(self):
        self.fixture = QgsVectorLayer('test/building.gml', 'building', 'ogr')
        self.obj = layer.BaseLayer("Polygon", "test", "memory")
        
    def test_append(self):
        self.obj.append(self.fixture)
    
    def test_reproject(self):
        self.obj.reproject()


class TimerPolygonLayer(BaseTimer):

    def __init__(self):
        self.fixture = QgsVectorLayer('test/cons.shp', 'building', 'ogr')
        self.obj = layer.PolygonLayer('Polygon', 'building', 'memory')
        self.obj.append(self.fixture, rename='')

    def test_explode_multi_parts(self):
        self.obj.explode_multi_parts()
        
    def test_get_vertices(self):
        self.obj.get_vertices()


class TimerAddressLayer(BaseTimer):

    def __init__(self):
        address_fn = 'test/address.gml'
        address_fn = BASEPATH + '{0}/A.ES.SDGC.AD.{0}.gml'.format('38900')
        self.address_gml = QgsVectorLayer(address_fn, 'address', 'ogr')
        self.tn_gml = QgsVectorLayer(address_fn + '|layername=thoroughfarename', 'tn', 'ogr')
        self.pd_gml = QgsVectorLayer(address_fn + '|layername=postaldescriptor', 'pd', 'ogr')
        self.au_gml = QgsVectorLayer(address_fn + '|layername=adminUnitname', 'au', 'ogr')
        assert(self.address_gml.isValid())
        assert(self.tn_gml.isValid())
        assert(self.pd_gml.isValid())
        assert(self.au_gml.isValid())
        
    def set_up(self):
        self.obj = layer.AddressLayer()
        self.obj.append(self.address_gml)
        self.obj.join_field(self.tn_gml, 'TN_id', 'gml_id', ['text'], 'TN_')
        self.obj.join_field(self.au_gml, 'AU_id', 'gml_id', ['text'], 'AU_')
        self.obj.join_field(self.pd_gml, 'PD_id', 'gml_id', ['postCode'])
        
    def test_delete_addres_without_number1(self):
        to_clean = [f.id for f in self.obj.getFeatures() if f['designator'] == 'S-N']
        self.obj.deleteFeatures(to_clean)

    def test_delete_addres_without_number2(self):
        to_clean = [f.id() for f in self.obj.search("designator = 'S-N'")]
        self.obj.deleteFeatures(to_clean)


class TimerAddressLayer2(BaseTimer):

    def __init__(self):
        mun = '38012'
        address_fn = 'test/address.gml'
        address_fn = BASEPATH + '{0}/A.ES.SDGC.AD.{0}.gml'.format(mun)
        self.address_gml = QgsVectorLayer(address_fn, 'address', 'ogr')
        self.tn_gml = QgsVectorLayer(address_fn + '|layername=thoroughfarename', 'tn', 'ogr')
        self.pd_gml = QgsVectorLayer(address_fn + '|layername=postaldescriptor', 'pd', 'ogr')
        self.au_gml = QgsVectorLayer(address_fn + '|layername=adminUnitname', 'au', 'ogr')
        assert(self.address_gml.isValid())
        assert(self.tn_gml.isValid())
        assert(self.pd_gml.isValid())
        assert(self.au_gml.isValid())
        osm_path = BASEPATH + mun + '/current_highway.osm'
        tree = etree.parse(osm_path)
        highway_osm = osmxml.deserialize(tree.getroot())
        self.highway = layer.HighwayLayer()
        self.highway.read_from_osm(highway_osm)
        self.highway.reproject(self.address_gml.crs())
        self.obj = layer.AddressLayer()
        self.obj.append(self.address_gml)
        self.obj.join_field(self.tn_gml, 'TN_id', 'gml_id', ['text'], 'TN_')
        self.obj.join_field(self.au_gml, 'AU_id', 'gml_id', ['text'], 'AU_')
        self.obj.join_field(self.pd_gml, 'PD_id', 'gml_id', ['postCode'])
        fid = random.randrange(self.obj.featureCount())
        request = QgsFeatureRequest().setFilterFids([fid])
        self.ad = self.obj.getFeatures(request).next()
        self.index = self.highway.get_index()
        self.features = {feat.id(): feat for feat in self.highway.getFeatures()}
        
    def test_get_highway_names1a(self):
        query = self.obj.search("TN_text='%s'" % self.ad['TN_text'])
        self.points = [f.geometry().asPoint() for f in query]

    def test_get_highway_names1b(self):
        bbox = QgsGeometry().fromMultiPoint(self.points).boundingBox()
        self.choices = [self.features[fid]['name'] for fid in self.index.intersects(bbox)]

    def test_get_highway_names1c(self):
        name = hgwnames.match(self.ad['TN_text'], self.choices)

    def _test_get_highway_names1(self):
        highway_names = {}
        for feat in self.obj.getFeatures():
            name = feat['TN_text']
            if name not in highway_names:
                query = self.obj.search("TN_text='%s'" % self.ad['TN_text'])
                points = [f.geometry().asPoint() for f in query]
                bbox = QgsGeometry().fromMultiPoint(points).boundingBox()
                choices = [self.features[fid]['name'] for fid in self.index.intersects(bbox)]
                name = hgwnames.match(name, choices)

    def test_get_highway_names2a(self):
        self.highway_names = defaultdict(list)
        for feat in self.obj.getFeatures():
            self.highway_names[feat['TN_text']].append(feat.geometry().asPoint())

    def test_get_highway_names2b(self):
        for name, points in self.highway_names.items():
            bbox = QgsGeometry().fromMultiPoint(points).boundingBox()
            choices = [self.features[fid]['name'] for fid in self.index.intersects(bbox)]
            self.highway_names[name] = hgwnames.match(name, choices)

    def test_get_highway_names2(self):
        """127x faster than test_get_highway_names1"""
        highway_names = defaultdict(list)
        for feat in self.obj.getFeatures():
            highway_names[feat['TN_text']].append(feat.geometry().asPoint())
        for name, points in highway_names.items():
            bbox = QgsGeometry().fromMultiPoint(points).boundingBox()
            choices = [self.features[fid]['name'] for fid in self.index.intersects(bbox)]
            highway_names[name] = hgwnames.match(name, choices)


class TimerConsLayer(BaseTimer):

    def __init__(self):
        self.obj = layer.ConsLayer()
        mun = '38900'
        building_fn = BASEPATH + '{0}/A.ES.SDGC.BU.{0}.building.gml'.format(mun)
        #buildingpart_fn = BASEPATH + '38001/A.ES.SDGC.BU.38001.buildingpart.gml'
        zoning_fn = BASEPATH + '{0}/A.ES.SDGC.CP.{0}.cadastralzoning.gml'.format(mun)
        self.building_gml = QgsVectorLayer(building_fn, 'building', 'ogr')
        self.obj.append(self.building_gml)
        #self.buildingpart_gml = QgsVectorLayer(buildingpart_fn, 'buildingpart', 'ogr')
        #self.zoning_gml = QgsVectorLayer(zoning_fn, 'zoning', 'ogr')
        #self.zone = self.zoning_gml.getFeatures().next()
        c = self.obj.featureCount()
        self.fids = [int(c*0.5) + i for i in range(4)]
        #self.fids = [random.randrange(c) for i in range(c/2)]
        self.request = QgsFeatureRequest().setFilterFids(self.fids)
        #self.test(self.get_features)
        #self.test(self.get_index)
        #self.fids = self.index.intersects(self.zone.geometry().boundingBox())
        osm_path = BASEPATH + mun + '/current_building.osm'
        tree = etree.parse(osm_path)
        self.current_bu_osm = osmxml.deserialize(tree.getroot())
        self.obj.reproject()
        """print 'Seleccionando {} edificios de {}'.format(len(self.fids), c)
        self.test(self.get_features)
        self.test(self.get_fids_by_loop)
        self.test(self.get_fids_by_loop2)
        self.test(self.get_fids_by_loop_mem)
        self.test(self.get_fids_by_loop_mem2)
        #self.test(self.get_fids_by_filter)
        self.test(self.get_fids_by_filter_mem)
        self.test(self.get_fids_by_dict_mem)
        """
        #self.test(self.get_fid_by_fid)
        #self.test(self.get_fids_by_select)
        #self.test(self.get_fid_by_fid_mem)
        #self.test(self.get_fids_by_select_mem)
    
    def zoning_histogram(self):
        index = QgsSpatialIndex(self.building_gml.getFeatures())
        c = {
            'MANZANA': [],
            'POLIGONO': []
        }
        for t in ('MANZANA', 'POLIGONO'):
            exp = QgsExpression("levelName = '(1:{} )'".format(t))
            request = QgsFeatureRequest(exp)
            for zone in self.zoning_gml.getFeatures(request):
                fids = index.intersects(zone.geometry().boundingBox())
                c[t].append(len(fids))
            print t, min(c[t]), max(c[t])
            print Counter(c[t])
    
    def get_features(self):
        """
        9K buildings 60 ms
        32K buildings 196 ms
        123K buildings 814 ms
        """
        self.features = {f.id(): f for f in self.obj.getFeatures()}
    
    def get_index(self):
        self.index = QgsSpatialIndex(self.building_gml.getFeatures())
        
    def get_fids_by_loop(self):
        """
        constant with the number of elements to select
        constant with the position of the elements to select
        linear with the size of the layer
        38012 (10/1972): 4x faster than get_fids_by_filter
        38012 (57/1972): 15x faster than get_fids_by_filter
        38012 (100/1972): 37x faster than get fids_by_filter
        38012 (1000/1972): 246x faster than get fids_by_filter
        38006 (10/9319): 3,6x faster than get fids_by_filter
        38006 (100/9319): 36x faster than get fids_by_filter
        """
        [f for f in self.building_gml.getFeatures() if f.id() in set(self.fids)]

    def get_fids_by_loop2(self):
        """Winner for ogr layers 1.25x faster than get_fids_by_loop"""
        s = set(self.fids)
        [f for f in self.building_gml.getFeatures() if f.id() in s]
        
    def get_fids_by_filter(self):
        """
        grows exp10 with the number of elements to select
        grows log with the position of the elements to select
        grows linear with the size of the layer
        38012 (1/1972): 1,32x faster than get_fids_by_loop 
        38006 (1/9319): 1,7x faster than get_fids_by_loop
        08900 (1/70354): 2x faster than get_fids_by_loop
        28900 (1/122921): 4x faster than get_fids_by_loop
        """
        request = QgsFeatureRequest().setFilterFids(self.fids)
        [f for f in self.building_gml.getFeatures(request)]
    
    def get_fids_by_loop_mem(self):
        """10x slower or more than get_fids_by_filter_mem"""
        [f for f in self.obj.getFeatures() if f.id() in set(self.fids)]
        
    def get_fids_by_loop_mem2(self):
        """
        Faster than get_fids_by_loop_mem (depending on the size of the 
        selecction), but still slower than get_fids_by_filter_mem
        """
        s = set(self.fids)
        [f for f in self.obj.getFeatures() if f.id() in s]
        
    def get_fids_by_dict_mem(self):
        """
        Winner if you have enough interactions to amortize the cost of build 
        the index. Example: selectiong 1K buildings from 32K ten times:
            get_fids_by_dict_mem = 200 ms + 10 * 5ms = 250 ms
            get_fids_by_filter_mem = 10 * 25 ms = 250 ms
        """
        s = set(self.fids)
        [f for f in self.features if f in s]

    def get_fids_by_filter_mem(self):
        """
        Absolute winner for one interaction
        Don't suffer grown exp10 with the number of elements to select
        200x faster than get_fids_by_loop
        """
        request = QgsFeatureRequest().setFilterFids(self.fids)
        [f for f in self.obj.getFeatures(request)]
    
    def get_fid_by_fid(self):
        """
        constant with the position of the elements to select
        grows brutally with the number of elements to select
        """
        r = []
        for fid in self.fids:
            request = QgsFeatureRequest().setFilterFids([fid])
            r.append(self.building_gml.getFeatures(request))

    def get_fid_by_fid_mem(self):
        """Initially the faster, but grows quickly with selection size"""
        r = []
        for fid in self.fids:
            request = QgsFeatureRequest().setFilterFids([fid])
            r.append(self.obj.getFeatures(request))

    def get_fids_by_select(self):
        """get_fids_by_filter ~= get_fids_by_select"""
        self.building_gml.setSelectedFeatures(self.fids)
        [f for f in self.building_gml.selectedFeatures()]
    
    def get_fids_by_select_mem(self):
        """Initially fast, but similar when selection size grows"""
        self.obj.setSelectedFeatures(self.fids)
        [f for f in self.obj.selectedFeatures()]

    def _test_append_zone(self):
        processed = []
        it = self.zoning_gml.getFeatures()
        for i in range(10):
            zone = it.next()
            self.obj.append_zone2(self.building, self.zone, processed)

    def test_conflate2(self):
        delete = True
        index = self.obj.get_index()
        num_buildings = 0
        conflicts = 0
        to_clean = set()
        for el in self.current_bu_osm.elements:
            poly = None
            if el.type == 'way' and el.is_closed() and 'building' in el.tags:
                poly = [[map(layer.Point, el.geometry())]]
            elif el.type == 'relation' and 'building' in el.tags:
                poly = [[map(layer.Point, w)] for w in el.outer_geometry()]
            if poly:
                num_buildings += 1
                geom = QgsGeometry().fromMultiPolygon(poly)
                if geom.isGeosValid():
                    conflict = False
                    fids = index.intersects(geom.boundingBox())
                    self.obj.setSelectedFeatures(fids)
                    for feat in self.obj.selectedFeatures():
                        fg = feat.geometry()
                        if geom.contains(fg) or fg.contains(geom) \
                                or geom.overlaps(fg):
                            conflict = True
                            conflicts += 1
                            break
                    if delete and not conflict:
                        to_clean.add(el)
                    if not delete and conflict:
                        el.tags['conflict'] = 'yes'
        for el in to_clean:
            self.current_bu_osm.remove(el)
        print "Detected {} conflicts in {} buildings from OSM".format(conflicts, num_buildings)


    def _test_conflate(self):
        self.obj.conflate(self.current_bu_osm)


"""
TimerBaseLayer().run()
TimerPolygonLayer().run()
TimerAddressLayer2().run()
"""
TimerConsLayer().run()

