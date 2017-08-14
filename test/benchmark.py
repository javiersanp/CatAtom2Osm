"""Benchmarking tests"""
import timeit
from qgis.core import *

import main
import layer
from catatom2osm import QgsSingleton
qgs = QgsSingleton()

N = 5
MS = 1000

class BaseTimer(object):

    def run(self):
        for p in dir(self):
            if p.startswith('test_'):
                t = timeit.timeit(getattr(self, p), number=N) * MS
                p = p[5:]
                print self.obj.__class__.__name__ + '.' + p + ': ' + str(t)

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
        self.obj = layer.AddressLayer()
        self.address_gml = QgsVectorLayer('test/address.gml', 'address', 'ogr')
        self.obj.append(self.address_gml)
        self.tn_gml = QgsVectorLayer('test/address.gml|layername=thoroughfarename', 'tn', 'ogr')
        self.pd_gml = QgsVectorLayer('test/address.gml|layername=postaldescriptor', 'pd', 'ogr')
        self.au_gml = QgsVectorLayer('test/address.gml|layername=adminUnitname', 'au', 'ogr')
        
    def test_join_field(self):
        self.obj.join_field(self.tn_gml, 'TN_id', 'gml_id', ['text'], 'TN_')
        self.obj.join_field(self.au_gml, 'AU_id', 'gml_id', ['text'], 'AU_')
        self.obj.join_field(self.pd_gml, 'PD_id', 'gml_id', ['postCode'])


TimerBaseLayer().run()
TimerPolygonLayer().run()
TimerAddressLayer().run()
